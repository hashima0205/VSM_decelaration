from pathlib import Path
import numpy as np,pandas as pd,json,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parents[1]; BS=[1,2,3,7]; T=P/'tables';F=P/'figures';D=P/'data'
st=pd.read_csv(P/'inputs/states.csv'); ix=lambda b: int(st.loc[(st.bus==b)&(st.symbol==f'inv{b}₊droop₊δ'),'index'].iloc[0])-1

def load(tag):
 z=pd.concat([pd.read_csv(P/'checkpoints'/tag/(s+'.csv')) for s in ['pre','fault','post']],ignore_index=True)
 for b in BS:
  z[f'b{b}_df_Hz']=z[f'b{b}_omega_rad_s']/(2*np.pi)-60
  z[f'b{b}_terminal_phase_rad']=np.unwrap(np.angle(z[f'b{b}_U_r_pu']+1j*z[f'b{b}_U_i_pu']))
 return z

def savefig(name):
 plt.tight_layout();plt.savefig(F/(name+'.png'),dpi=160);plt.savefig(F/(name+'.pdf'));plt.close()

pairs=[('A_droop_center','B_vsm_center'),('C_droop_recovery','D_vsm_recovery')]
rows=[]
for a,b in pairs+[('B_vsm_center','B_vsm_strict'),('D_vsm_recovery','D_vsm_strict')]:
 if not (P/'checkpoints'/b/'DONE').exists(): continue
 x,y=load(a),load(b);assert len(x)==len(y) and np.max(abs(x.t_absolute_s-y.t_absolute_s))<1e-12
 for c in x:
  if not c.startswith('b') or c.endswith('saturated'):continue
  err=x[c].to_numpy()-y[c].to_numpy()
  rows.append(dict(reference=a,comparison=b,variable=c,max_abs_error=abs(err).max(),rms_error=np.sqrt(np.mean(err**2)),end_abs_error=abs(err[-1])))
 fig,ax=plt.subplots(4,2,figsize=(12,10),sharex=True)
 for j,bus in enumerate(BS):
  for z,style,label in [(x,'-',a),(y,'--',b)]:
   ax[j,0].plot(z.t_post_s,z[f'b{bus}_delta_rad']/(2*np.pi),style,label=label)
   ax[j,1].plot(z.t_post_s,z[f'b{bus}_df_Hz'],style,label=label)
  ax[j,0].set_ylabel(f'Bus {bus} turns');ax[j,1].set_ylabel('df [Hz]');ax[j,0].grid();ax[j,1].grid()
 ax[0,0].legend(fontsize=7);ax[-1,0].set_xlabel('Time after clearing [s]');ax[-1,1].set_xlabel('Time after clearing [s]');savefig(a+'_vs_'+b)
 # Electrical quantities for all four converters, including errors (no alignment).
 fig,ax=plt.subplots(4,4,figsize=(15,10),sharex=True)
 for j,bus in enumerate(BS):
  for k,q in enumerate(['Pcap_pu','Qcap_pu','U_r_pu','Ig_r_pu']):
   for z,sty in [(x,'-'),(y,'--')]:ax[j,k].plot(z.t_post_s,z[f'b{bus}_{q}'],sty,lw=.8)
   ax[j,k].set_title(f'Bus {bus} {q}',fontsize=8)
 savefig(a+'_electrical')
pd.DataFrame(rows).to_csv(T/'waveform_errors.csv',index=False)
if len([b for a,b in pairs if (P/'checkpoints'/b/'DONE').exists()])==2:
 eq=pd.DataFrame(rows);eq=eq[eq.comparison.isin([b for a,b in pairs])]
 # Absolute thresholds in each recorded unit; rad/s frequency threshold 1e-3.
 ok=bool((eq.max_abs_error<1e-3).all())
 (D/'equivalence_gate.json').write_text(json.dumps(dict(passed=ok,absolute_threshold=1e-3,max_error=float(eq.max_abs_error.max()),alignment='identical saved times, no phase/time shift'),indent=2))
 if not ok:raise RuntimeError('Equivalence gate failed; investigate before phase 2')
 (D/'equivalence_passed').write_text('Passed all machine observables at identical saved times\n')

metrics=[];summ=[];allz={};limits=[];relative=[]
for done in sorted((P/'checkpoints').glob('*/DONE')):
 tag=done.parent.name;z=load(tag)
 for b in BS:
  sat=z[f'b{b}_saturated'].astype(str).str.lower().isin(['true','1','1.0'])
  limits.append(dict(case=tag,bus=b,saturation_any=bool(sat.any()),saturated_samples=int(sat.sum()),samples=len(z),max_filter_current_full=float(np.hypot(z[f'b{b}_If_r_pu'],z[f'b{b}_If_i_pu']).max()),max_grid_current_full=float(np.hypot(z[f'b{b}_Ig_r_pu'],z[f'b{b}_Ig_i_pu']).max()),min_voltage_full=float(np.hypot(z[f'b{b}_U_r_pu'],z[f'b{b}_U_i_pu']).min())))
 z.to_csv(D/(tag+'_trajectory.csv.gz'),index=False,compression='gzip');z=z[z.stage=='post'].copy();allz[tag]=z
 target=np.loadtxt(D/(tag+'_post_root.csv'),delimiter=',');tail=z.t_post_s>=270
 for ba,bb in [(2,1),(3,1),(7,1),(3,2),(7,2)]:
  v=z[f'b{ba}_delta_rad']-z[f'b{bb}_delta_rad']
  relative.append(dict(case=tag,bus_a=ba,bus_b=bb,relative_turns=(v.iloc[-1]-v.iloc[0])/(2*np.pi),tail_phase_span_rad=v[tail].max()-v[tail].min(),tail_mean_df_Hz=(z[f'b{ba}_df_Hz'][tail]-z[f'b{bb}_df_Hz'][tail]).mean()))
 ms=[]
 for b in BS:
  ang=z[f'b{b}_delta_rad'].to_numpy();df=z[f'b{b}_df_Hz'];err=abs(np.angle(np.exp(1j*(ang[-1]-target[ix(b)]))));turn=(ang[-1]-ang[0])/(2*np.pi)
  rec=df[tail].abs().max()<1e-4 and err<.002;neg=turn<-2 and df[tail].max()<-.001
  u=np.hypot(z[f'b{b}_U_r_pu'],z[f'b{b}_U_i_pu']);ig=np.hypot(z[f'b{b}_Ig_r_pu'],z[f'b{b}_Ig_i_pu']);iff=np.hypot(z[f'b{b}_If_r_pu'],z[f'b{b}_If_i_pu'])
  m=dict(case=tag,bus=b,classification='recovery' if rec else 'negative_rotation' if neg else 'other_instability' if turn>2 and df[tail].min()>.001 else 'unresolved',internal_turns=turn,terminal_turns=(z[f'b{b}_terminal_phase_rad'].iloc[-1]-z[f'b{b}_terminal_phase_rad'].iloc[0])/(2*np.pi),tail_df_min=df[tail].min(),tail_df_max=df[tail].max(),tail_df_mean=np.trapezoid(df[tail],z.t_post_s[tail])/30,phase_error=err,min_voltage=u.min(),max_grid_current=ig.max(),max_filter_current=iff.max(),saturation_fraction=z[f'b{b}_saturated'].astype(str).str.lower().isin(['true','1','1.0']).mean(),terminal_phase_reliable=bool(u.min()>=.1))
  metrics.append(m);ms.append(m)
 lab='recovery' if all(m['classification']=='recovery' for m in ms) else 'negative_rotation' if all(m['classification']=='negative_rotation' for m in ms[1:]) else 'other_instability' if any(m['classification']=='other_instability' for m in ms) else 'unresolved'
 summ.append(dict(case=tag,classification=lab,remote_turns=np.mean([m['internal_turns'] for m in ms[1:]]),remote_terminal_turns=np.mean([m['terminal_turns'] for m in ms[1:]]),remote_tail_df=np.mean([m['tail_df_mean'] for m in ms[1:]]),bus1_class=ms[0]['classification'],max_alg_residual=z.alg_residual.max(),relative_remote_bus1_turns=np.mean([m['internal_turns'] for m in ms[1:]])-ms[0]['internal_turns']))
pd.DataFrame(relative).to_csv(T/'relative_phase_metrics.csv',index=False)
pd.DataFrame(limits).to_csv(T/'limit_metrics_full.csv',index=False)
pd.DataFrame(metrics).to_csv(T/'machine_metrics.csv',index=False);pd.DataFrame(summ).to_csv(T/'classifications.csv',index=False)
print(pd.DataFrame(summ).to_string(index=False))
for tags,name in [(['B_vsm_center','E_shortQ_center'],'Q_comparison'),(['F_shortQ_strong','E_shortQ_center','G_shortQ_weak'],'shortQ_SCR'),(['H_longQ_strong','B_vsm_center'],'longQ_SCR')]:
 if not all(tag in allz for tag in tags):continue
 fig,ax=plt.subplots(3,1,figsize=(10,9),sharex=True)
 for tag in tags:
  z=allz[tag];ax[0].plot(z.t_post_s,z[[f'b{b}_delta_rad' for b in BS[1:]]].mean(axis=1)/(2*np.pi),label=tag)
  ax[1].plot(z.t_post_s,z[[f'b{b}_df_Hz' for b in BS[1:]]].mean(axis=1),label=tag)
  ax[2].plot(z.t_post_s,(z[[f'b{b}_delta_rad' for b in BS[1:]]].mean(axis=1)-z.b1_delta_rad)/(2*np.pi),label=tag)
 for a,lab in zip(ax,['Remote internal angle [turns]','Remote df [Hz]','Remote - Bus1 [turns]']):a.set_ylabel(lab);a.grid();a.legend(fontsize=8)
 ax[-1].set_xlabel('Time after clearing [s]');savefig(name)

from pathlib import Path
import json
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent;R=P.parents[1]/'VSM_decelaration'
ST=pd.read_csv(R/'data/states.csv');colors={1:'#555555',2:'#0072b2',3:'#d55e00',7:'#009e73'}
plt.rcParams.update({'font.size':9,'pdf.fonttype':42})
def val(d,b,s):return d['x'+str(int(ST.loc[(ST.bus==b)&(ST.symbol==s),'index'].iloc[0]))].to_numpy()
def save(fig,name):
 for ext in ['png','pdf']:fig.savefig(P/f'{name}.{ext}',dpi=185,bbox_inches='tight')
 plt.close(fig)
def style(axs,xlim=(0,11.15)):
 for ax in axs.flat:
  ax.axvspan(1,1.15,color='red',alpha=.07);ax.axvline(1,ls=':',c='#a11',lw=.7);ax.axvline(1.15,ls='--',c='gray',lw=.7);ax.grid(alpha=.2);ax.set_xlim(*xlim)
frames={};trajectories={}
for tag in ['baseline','r56_075']:
 d=pd.read_csv(P/f'states_{tag}.csv');f=d[['t_absolute_s','t_post_s','stage']].copy();u={b:val(d,b,'busbar₊u_r')+1j*val(d,b,'busbar₊u_i') for b in [1,2,3,4,5,7,8]};u[6]=np.ones(len(d),complex)
 f['V5']=abs(u[5]);f['theta5']=np.unwrap(np.angle(u[5]))
 for b in [1,2,3,7]:
  get=lambda s:val(d,b,f'inv{b}₊{s}')
  ig=get('vsrc₊filter₊i_g_r')+1j*get('vsrc₊filter₊i_g_i');vc=get('vsrc₊filter₊V_C_r')+1j*get('vsrc₊filter₊V_C_i');sc=vc*np.conj(ig);st=u[b]*np.conj(ig)
  for k,v in {'V':abs(u[b]),'Ig':abs(ig),'If':np.hypot(get('vsrc₊filter₊i_f_r'),get('vsrc₊filter₊i_f_i')),'P':st.real,'Q':st.imag,'Pcap':sc.real,'Qcap':sc.imag,'phase':np.unwrap(np.angle(u[b])),'delta':get('droop₊δ'),'nu':(([.5 if b==1 else .4][0])-get('droop₊Pfilt'))/10,'Qf':get('droop₊Qfilt')}.items():f[f'b{b}_{k}']=v
 f['remote_delta']=sum(f[f'b{b}_delta'] for b in [2,3,7])/3;f['remote_df']=60*sum(f[f'b{b}_nu'] for b in [2,3,7])/3
 f['theta_bus5']=f.remote_delta-f.theta5
 zz=pd.read_csv(R/'data/single_line/pre_equilibrium/branches.csv').set_index('line').loc[3];z=np.full(len(d),complex(zz.R_pu,zz.X_pu))
 if tag=='r56_075':z[d.stage=='post']=complex(.75*zz.R_pu,zz.X_pu)
 i65=(1-u[5])/z;S65=np.conj(i65);S56=u[5]*np.conj(-i65)
 f['I65']=abs(i65);f['P65']=S65.real;f['Q65']=S65.imag;f['loss56']=(S65+S56).real;f['Qabs56']=(S65+S56).imag;f['Pload']=2.2682301152333055*abs(u[5])**2;f['Qcap5']=abs(u[5])**2
 assert np.max(abs(f.loss56-abs(i65)**2*z.real))<1e-10
 f.to_csv(P/f'observations_{tag}.csv',index=False);frames[tag]=f
 f[['t_absolute_s','t_post_s','stage','theta_bus5','remote_delta','remote_df','V5','theta5']].to_csv(P/f'trajectory_{tag}.csv',index=False)
for zoom in [False,True]:
 fig,axs=plt.subplots(5,2,figsize=(12,11),sharex=True,sharey='row');limits=(.9,1.7) if zoom else (0,11.15)
 for c,(tag,d) in enumerate(frames.items()):
  d=d[d.t_absolute_s.between(*limits)];t=d.t_absolute_s
  for b in [1,2,3,7]:
   for row,k in enumerate(['V','Ig','P','Q','phase']):axs[row,c].plot(t,d[f'b{b}_{k}'],lw=1,c=colors[b],label=f'Bus {b}')
  axs[0,c].set_title('Baseline R56: negative running' if tag=='baseline' else 'R56 = 75%: recovery');axs[0,c].legend(ncol=4,fontsize=8)
 for ax,label in zip(axs[:,0],['Terminal voltage\n|U| [pu]','Grid-side current\n|Ig| [pu]','Terminal active\npower P [pu]','Terminal reactive\npower Q [pu]','Terminal phase / slack\n[rad]']):ax.set_ylabel(label)
 for ax in axs[-1]:ax.set_xlabel('Time from prefault initialization [s]')
 style(axs,limits);fig.suptitle('Same H=2.5 s, D1=10, D2=100, B5=1; only postfault R56 differs');fig.tight_layout(rect=(0,0,1,.96));save(fig,'gfm_fault_zoom' if zoom else 'gfm_responses')
fig,axs=plt.subplots(5,2,figsize=(12,11),sharex=True,sharey='row')
for c,(tag,d) in enumerate(frames.items()):
 t=d.t_absolute_s
 for ax,keys in zip(axs[:,c],[['V5'],['I65'],['P65','Pload'],['Q65','Qcap5','Qabs56'],['remote_df']]):
  for k in keys:ax.plot(t,d[k],label=k,lw=1)
  ax.legend(fontsize=8)
 axs[0,c].set_title(tag)
for ax,label in zip(axs[:,0],['Bus5 voltage [pu]','Line 6–5 current [pu]','Active power [pu]','Reactive power [pu]','Remote frequency\ndeviation [Hz]']):ax.set_ylabel(label)
style(axs)
for ax in axs[-1]:ax.set_xlabel('Time from prefault initialization [s]')
fig.suptitle('Bus5 / slack: P65,Q65 = Bus6 sending end; Qcap5 = capacitor injection');fig.tight_layout(rect=(0,0,1,.96));save(fig,'bus5_slack_responses')
fig,axs=plt.subplots(3,2,figsize=(12,8),sharex=True,sharey='row')
for c,(tag,d) in enumerate(frames.items()):
 t=d.t_absolute_s
 axs[0,c].plot(t,sum(d[f'b{b}_Pcap'] for b in [2,3,7]),label='Pcap sum');axs[0,c].plot(t,sum(d[f'b{b}_P'] for b in [2,3,7]),ls='--',label='Terminal P sum');axs[0,c].axhline(1.2,c='black',ls=':');axs[0,c].legend()
 axs[1,c].plot(t,d.remote_delta,label='Mean internal angle / slack');axs[1,c].plot(t,d.theta5,ls='--',label='Bus5 voltage phase / slack');axs[1,c].legend()
 axs[2,c].plot(t,d.theta_bus5,label='Mean internal angle relative to Bus5');axs[2,c].legend();axs[0,c].set_title(tag)
for ax,label in zip(axs[:,0],['Remote active P [pu]','Slack-relative phase\n[rad]','Bus5-relative phase\n[rad]']):ax.set_ylabel(label)
style(axs)
for ax in axs[-1]:ax.set_xlabel('Time from prefault initialization [s]')
fig.tight_layout();save(fig,'internal_phase_and_power')
# All original 52 differential variables, with the four frequency slots shown as nu,
# plus the four washout states. Algebraic bus voltages are in the electrical plots.
keys=['vsrc₊cc1₊γ_q','vsrc₊cc1₊γ_d','vsrc₊filter₊i_g_i','vsrc₊filter₊i_g_r','vsrc₊filter₊V_C_i','vsrc₊filter₊V_C_r','vsrc₊filter₊i_f_i','vsrc₊filter₊i_f_r','vsrc₊vc₊γ_q','vsrc₊vc₊γ_d','droop₊Qfilt','nu','droop₊δ','z']
for tag in frames:
 raw=pd.read_csv(P/f'states_{tag}.csv');d=frames[tag];fig,axs=plt.subplots(7,2,figsize=(13,16),sharex=True)
 for ax,k in zip(axs.flat,keys):
  for j,b in enumerate([1,2,3,7]):
   y=d[f'b{b}_nu'] if k=='nu' else raw[f'z{j+1}'] if k=='z' else val(raw,b,f'inv{b}₊{k}')
   ax.plot(d.t_absolute_s,y,c=colors[b],lw=.8,label=f'Bus {b}')
  ax.set_ylabel(k.replace('₊',' / '),fontsize=8)
 style(axs)
 axs[0,0].legend(ncol=4,fontsize=8)
 for ax in axs[-1]:ax.set_xlabel('Time [s]')
 fig.suptitle(f'{tag}: all 56 differential states (native real/imaginary components)');fig.tight_layout(rect=(0,0,1,.98));save(fig,f'all_dynamic_states_{tag}')
print('Short-time response plots and all 70 saved states exported')

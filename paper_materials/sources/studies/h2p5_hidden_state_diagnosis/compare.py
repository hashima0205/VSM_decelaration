from pathlib import Path
import json
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent;R=P.parents[1]/'VSM_decelaration';S=pd.read_csv(R/'data/states.csv')
def get(d,b,k):return d['x'+str(int(S.loc[(S.bus==b)&(S.symbol==f'inv{b}₊{k}'),'index'].iloc[0]))].to_numpy()
frames={};rows=[]
for tag in ['baseline','r56_075']:
 d=pd.read_csv(P/f'../h2p5_r56_comparison/states_{tag}.csv');o=pd.read_csv(P/f'../h2p5_r56_comparison/observations_{tag}.csv');a=d[['t_absolute_s','stage']].copy()
 for b,j in zip([2,3,7],[2,3,4]):
  delta=get(d,b,'droop₊δ');nu=(.4-get(d,b,'droop₊Pfilt'))/10;z=d[f'z{j}'].to_numpy();qf=get(d,b,'droop₊Qfilt')
  for key in ['vc_γ_d','vc_γ_q','cc1_γ_d','cc1_γ_q']:
   sys,component=key.split('_',1);a[f'b{b}_{key}']=get(d,b,f'vsrc₊{sys}₊{component}')
  a[f'b{b}_delta']=delta;a[f'b{b}_nu']=nu;a[f'b{b}_D2_power']=-100*(nu-z)
  a[f'b{b}_Qlag']=qf-o[f'b{b}_Qcap'];a[f'b{b}_Qf']=qf
  for var,raw in [('Ig','i_g'),('If','i_f'),('Vc','V_C')]:
   c=get(d,b,f'vsrc₊filter₊{raw}_r')+1j*get(d,b,f'vsrc₊filter₊{raw}_i');local=c*np.exp(-1j*delta)
   a[f'b{b}_{var}_local_d']=local.real;a[f'b{b}_{var}_local_q']=local.imag
 frames[tag]=a;a.to_csv(P/f'derived_{tag}.csv',index=False)
 for t in [1.15,2.01,2.99,4.99]:
  inds=np.flatnonzero(np.isclose(a.t_absolute_s,t));idx=inds[-1];x=a.iloc[idx];v=o.iloc[idx]
  vals={'condition':tag,'t':float(x.t_absolute_s),'mean_delta_slack':np.mean([x[f'b{b}_delta'] for b in [2,3,7]]),'V5':v.V5,'mean_terminal_V':np.mean([v[f'b{b}_V'] for b in [2,3,7]]),'Qf_mean':np.mean([x[f'b{b}_Qf'] for b in [2,3,7]]),'D2_power_sum':sum(x[f'b{b}_D2_power'] for b in [2,3,7]),'max_abs_Qlag':max(abs(x[f'b{b}_Qlag']) for b in [2,3,7]),'mean_Ig_local_q':np.mean([x[f'b{b}_Ig_local_q'] for b in [2,3,7]])}
  for k in ['vc_γ_d','vc_γ_q','cc1_γ_d','cc1_γ_q']:vals[k]=np.mean([x[f'b{b}_{k}'] for b in [2,3,7]])
  rows.append(vals)
fig,axs=plt.subplots(6,2,figsize=(12,12),sharex=True,sharey='row')
for c,(tag,d) in enumerate(frames.items()):
 for b in [2,3,7]:
  for row,key in enumerate(['delta','Ig_local_q','vc_γ_q','cc1_γ_q','D2_power','Qlag']):axs[row,c].plot(d.t_absolute_s,d[f'b{b}_{key}'],lw=1,label=f'Bus {b}')
 axs[0,c].set_title(tag);axs[0,c].legend(ncol=3,fontsize=8)
for ax,label in zip(axs[:,0],['Internal angle / slack\n[rad]','Ig q-component in\ninternal-angle frame [pu]','Voltage PI\ngamma_q','Current PI\ngamma_q','Washout damping\npower -D2(nu-z) [pu]','Q-filter lag\nQf-Qcap [pu]']):ax.set_ylabel(label)
for ax in axs.flat:ax.set_xlim(0,7);ax.axvspan(1,1.15,color='red',alpha=.07);ax.grid(alpha=.2)
for ax in axs[-1]:ax.set_xlabel('Time from prefault initialization [s]')
fig.suptitle('Hidden-state comparison with electrical phasors aligned to each internal angle');fig.tight_layout(rect=(0,0,1,.97))
for ext in ['png','pdf']:fig.savefig(P/f'hidden_states.{ext}',dpi=185)
plt.close(fig)
pd.DataFrame(rows).to_csv(P/'comparison_points.csv',index=False)
print(pd.DataFrame(rows).to_string(index=False))

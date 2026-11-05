from pathlib import Path
import pandas as pd,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent
frames={}
for n in [10,20]:
 d=pd.read_csv(P/f'gfms_D1_{n}.csv');v=pd.read_csv(P/f'network_D1_{n}.csv')
 b=pd.read_csv(P/f'../h2p5_power_mechanism/budget_D1_{n}.csv').query('t_absolute_s<=11.15000001').reset_index(drop=True)
 assert np.allclose(d.t_absolute_s,b.t_absolute_s) and (d.stage==b.stage).all()
 frames[n]=pd.DataFrame({'t':d.t_absolute_s,'stage':d.stage,'df':b.remote_df_Hz,'Ig_mean':sum(d[f'b{k}_Ig'] for k in [2,3,7])/3,'Q_remote':sum(d[f'b{k}_Qterminal_pu'] for k in [2,3,7]),'V5':v.V5,'theta5':v.theta5,'D1_feedback':b.D1_feedback_pu,'power_gap':b.remote_Pset_minus_Pcap_pu,'swing_rhs':b.sum_swing_rhs_pu})
assert np.allclose(frames[10].t,frames[20].t)
out=frames[10][['t','stage']].copy()
for n,d in frames.items():
 for c in d.columns:
  if c not in ['t','stage']:out[f'{c}_D1_{n}']=d[c]
out.to_csv(P/'paired_recovery_comparison.csv',index=False)
fig,axes=plt.subplots(5,2,figsize=(11,11),sharex='col',sharey='row')
for j,limits in enumerate([(.95,2.5),(2.5,7)]):
 for n,d in frames.items():
  a=d[d.t.between(*limits)]
  for i,key in enumerate(['df','Ig_mean','Q_remote','V5','theta5']):axes[i,j].plot(a.t,a[key],lw=1.2,label=f'D1={n}')
 for ax in axes[:,j]:
  ax.set_xlim(*limits);ax.grid(alpha=.25);ax.axvspan(1,1.15,color='red',alpha=.08)
 axes[0,j].legend()
for ax,label in zip(axes[:,0],['Remote frequency\ndeviation [Hz]','Mean remote grid\ncurrent |Ig| [pu]','Remote terminal\nQ sum [pu]','Bus5 voltage\n[pu]','Bus5 phase /\nslack Bus6 [rad]']):ax.set_ylabel(label)
for ax in axes[-1]:ax.set_xlabel('Time from prefault initialization [s]')
fig.suptitle('Paired comparison: identical circuit and Q-control; only D1 differs')
fig.tight_layout(rect=(0,0,1,.96))
for ext in ['png','pdf']:fig.savefig(P/f'paired_recovery_comparison.{ext}',dpi=190)
plt.close(fig)
rows=[]
for n,d in frames.items():
 for t in [1.05,1.49,2.99,4.99]:
  a=d.iloc[np.argmin(abs(d.t-t))];rows.append({'D1':n,**a.to_dict()})
summary=pd.DataFrame(rows);summary.to_csv(P/'paired_comparison_points.csv',index=False)
print(summary.to_string(index=False))

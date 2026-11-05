from pathlib import Path
import json
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent
summary=pd.concat([pd.read_csv(f) for f in sorted(P.glob('summary_w*.csv'))],ignore_index=True)
assert len(summary)==9 and summary['case'].nunique()==9
summary.to_csv(P/'results.csv',index=False)
labels={'control':'No transplant','voltage_PI':'Voltage PI states','current_PI':'Current PI states','Q_filter':'Q-filter states','washout':'D2 washout states','electrical_local':'Local electrical states','angle_speed':'Angle/speed (electrical phasors aligned)','all_hidden_controls':'All hidden controller states','full_recovered':'Full recovered state'}
fig,axs=plt.subplots(2,2,figsize=(12,8),sharex='col')
for tag in labels:
 d=pd.read_csv(P/tag/'compact.csv');t=d.t_since_transplant_s
 axs[0,0].plot(t,(d.remote_internal_angle_rad-d.remote_internal_angle_rad.iloc[0])/(2*np.pi),lw=1,label=labels[tag])
 axs[1,0].plot(t,d.remote_df_Hz.rolling(11,center=True,min_periods=1).mean(),lw=.8)
 e=pd.read_csv(P/tag/'early.csv');pc=sum(e[f'b{b}_Pcap_pu'] for b in [2,3,7]);th=sum(e[f'b{b}_delta_rad'] for b in [2,3,7])/3
 axs[0,1].plot(e.t_since_transplant_s,pc,lw=.9);axs[1,1].plot(e.t_since_transplant_s,th,lw=.9)
for ax,label in zip(axs.flat,['Phase change after transplant [turns]','Remote total Pcap [pu]','Remote frequency deviation [Hz]','Remote internal angle / slack [rad]']):ax.set_ylabel(label)
for ax in axs.flat:ax.grid(alpha=.2)
for ax in axs[1]:ax.set_xlabel('Time since transplant at original absolute t=2.99 s [s]')
fig.legend(*axs[0,0].get_legend_handles_labels(),loc='lower center',ncol=3,fontsize=8)
fig.suptitle('Same original post-fault circuit and controls; selected states transplanted from R75 recovery')
fig.tight_layout(rect=(0,.12,1,.95))
for ext in ['png','pdf']:fig.savefig(P/f'state_transplants.{ext}',dpi=190)
plt.close(fig)
a=np.loadtxt(P/'stable.csv',delimiter=',');b=np.loadtxt(P/'root_2.csv',delimiter=',');ai=np.array([30,45,66])-1
rootinfo={}
for name,x in [('stable',a),('saddle',b)]:rootinfo[name]={'internal_phase_slack_rad':float(x[ai].mean()),'V5_pu':float(np.hypot(x[47],x[48])),'internal_phase_Bus5_rad':float(x[ai].mean()-np.angle(x[47]+1j*x[48]))}
rootinfo['gap_slack_rad']=rootinfo['stable']['internal_phase_slack_rad']-rootinfo['saddle']['internal_phase_slack_rad'];rootinfo['gap_Bus5_rad']=rootinfo['stable']['internal_phase_Bus5_rad']-rootinfo['saddle']['internal_phase_Bus5_rad']
(P/'equilibrium_comparison.json').write_text(json.dumps(rootinfo,indent=2)+'\n')
plt.rcParams.update({'font.size':9})
fig,axs=plt.subplots(3,1,figsize=(8,7),sharex=True)
o=pd.read_csv(P/'../h2p5_r56_comparison/observations_baseline.csv')
for ax,key,rkey,label in zip(axs,['remote_delta','theta_bus5','V5'],['internal_phase_slack_rad','internal_phase_Bus5_rad','V5_pu'],['Internal angle / slack [rad]','Internal angle / Bus5 [rad]','Bus5 voltage [pu]']):
 ax.plot(o.t_absolute_s,o[key],label='Baseline orbit')
 for name,ls in [('stable','--'),('saddle',':')]:ax.axhline(rootinfo[name][rkey],ls=ls,color='black' if name=='stable' else 'red',label=f'{name} projection')
 ax.set_ylabel(label);ax.set_xlim(1.15,5);ax.grid(alpha=.25);ax.legend(fontsize=8)
axs[-1].set_xlabel('Absolute time [s]');fig.suptitle('Equilibrium projections: proximity in 2D does not establish a basin boundary');fig.tight_layout()
for ext in ['png','pdf']:fig.savefig(P/f'equilibrium_projections.{ext}',dpi=190)
plt.close(fig)
print(summary.to_string(index=False));print(rootinfo)

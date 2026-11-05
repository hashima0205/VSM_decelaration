from pathlib import Path
import json
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent
s=pd.concat([pd.read_csv(f) for f in sorted(P.glob('summary_late_w*.csv'))],ignore_index=True);assert len(s)==4
early=pd.read_csv(P/'verified.csv').set_index('case')
independent=pd.read_csv(P/'reclassified.csv').set_index('case')
st=pd.read_csv(P.parents[1]/'VSM_decelaration/data/states.csv');held=np.r_[st.loc[st.mass!=0,'index'].to_numpy()-1,np.arange(66,70)]
initial=np.loadtxt(P/"reference_late70.csv",delimiter=",");rows=[]
fig,ax=plt.subplots(2,2,figsize=(11,7),sharex='col')
for row in s.to_dict('records'):
 tag=row['case'];ref=tag.replace('late_','');assert row['classification']==independent.loc[tag,'classification']
 row['validated_root_reference']=ref;row['validated_root_max_real']=float(early.loc[ref,'root_max_real'])
 assert np.array_equal(np.loadtxt(P/tag/'parameters.csv',delimiter=','),np.loadtxt(P/ref/'parameters.csv',delimiter=','))
 d=pd.read_csv(P/tag/'budget.csv').drop_duplicates('t_post_s',keep='last');assert np.isclose(d.t_post_s.iloc[-1],1000)
 assert d.balance_error.abs().max()<1e-8
 x=np.loadtxt(P/tag/'initial70.csv',delimiter=',')
 assert np.array_equal(initial[held],x[held])
 a=d[d.t_post_s>=950];t=a.t_post_s
 vals={f'tail_{c}':float(np.trapezoid(a[c],t)/(t.iloc[-1]-t.iloc[0])) for c in a.columns if c!='t_post_s'}
 rows.append({**row,**vals})
 label=tag.replace('late_','').replace('_',' ')
 ax[0,0].plot(d.t_post_s,(d.theta_remote_slack_rad-d.theta_remote_slack_rad.iloc[0])/(2*np.pi),label=label,lw=1)
 ax[1,0].plot(d.t_post_s,d.remote_df_Hz.rolling(51,center=True,min_periods=1).mean(),lw=1)
 a=d[d.t_post_s<=30];ax[0,1].plot(a.t_post_s,a.Pcap_remote.rolling(11,center=True,min_periods=1).mean(),lw=1)
 ax[1,1].plot(a.t_post_s,a.Ploss.rolling(11,center=True,min_periods=1).mean(),lw=1)
result=pd.DataFrame(rows);result.to_csv(P/'late_verified.csv',index=False)
(P/'late_validation.json').write_text(json.dumps({'original_physical_intervention_time_s':21.15,'identical_dynamic_and_filter_states_to_original_20s':True,'cases':len(rows),'max_power_balance_error':float(max(abs(pd.read_csv(P/r['case']/'budget.csv').balance_error).max() for r in rows))},indent=2)+'\n')
ax[0,0].set_ylabel('Phase change since intervention [turns]');ax[1,0].set_ylabel('Remote frequency deviation [Hz]');ax[0,1].set_ylabel('Remote Pcap sum [pu]');ax[1,1].set_ylabel('All line losses [pu]');ax[0,1].axhline(1.2,ls=':',c='black',lw=.8)
for a in ax.flat:a.grid(alpha=.25)
for a in ax[1]:a.set_xlabel('Time since intervention [s]')
fig.legend(*ax[0,0].get_legend_handles_labels(),loc='lower center',ncol=4,fontsize=9)
fig.suptitle('Interventions after running has begun: original post-fault time 20 s');fig.tight_layout(rect=(0,.07,1,.95))
for ext in ['png','pdf']:fig.savefig(P/f'late_interventions.{ext}',dpi=200)
plt.close(fig)
print(result[['case','classification','turns','tail_remote_df_Hz','tail_Pcap_remote','tail_Ploss','tail_Pload','root_max_real']].to_string(index=False))

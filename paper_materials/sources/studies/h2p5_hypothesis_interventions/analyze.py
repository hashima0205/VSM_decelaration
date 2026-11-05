from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent
summ=pd.concat([pd.read_csv(f) for f in sorted(P.glob('summary_w*.csv'))],ignore_index=True)
assert len(summ)==8 and summ['case'].nunique()==8
frames={};rows=[]
for r in summ.to_dict('records'):
 d=pd.read_csv(P/r['case']/'budget.csv').drop_duplicates('t_post_s',keep='last');frames[r['case']]=d
 assert np.isclose(d.t_post_s.iloc[-1],1000) and d.balance_error.abs().max()<1e-8
 tail=d[d.t_post_s>=950];tt=tail.t_post_s
 means={c:float(np.trapezoid(tail[c],tt)/(tt.iloc[-1]-tt.iloc[0])) for c in tail.columns if c!='t_post_s'}
 means={f'tail_{k}':v for k,v in means.items()}
 rows.append({**r,**means,'max_balance_error':float(d.balance_error.abs().max())})
result=pd.DataFrame(rows);result.to_csv(P/'verified.csv',index=False)
# Verify identical full differential and washout initial states, and exact allowed parameter changes.
st=pd.read_csv(P.parents[1]/'VSM_decelaration/data/states.csv');dynamic=st.loc[st.mass!=0,'index'].to_numpy()-1
base=np.loadtxt(P/'baseline/initial70.csv',delimiter=',');param=np.loadtxt(P/'baseline/parameters.csv',delimiter=',')
held=np.r_[dynamic,np.arange(66,70)];initerr=0
for r in rows:
 a=np.loadtxt(P/r['case']/'initial70.csv',delimiter=',');initerr=max(initerr,float(abs(a[held]-base[held]).max()))
 assert np.array_equal(a[held],base[held])
 changed=np.flatnonzero(np.loadtxt(P/r['case']/'parameters.csv',delimiter=',')!=param)+1
 exported=np.atleast_1d(np.loadtxt(P/r['case']/'changed_parameter_indices.csv',delimiter=',')) if (P/r['case']/'changed_parameter_indices.csv').stat().st_size else np.array([])
 assert np.array_equal(changed,exported)
old=pd.read_csv(P/'../h2p5_power_mechanism/budget_D1_10.csv');old=old[old.stage=='post']
b=frames['baseline'];a=old.iloc[-1]
assert abs(b.theta_remote_slack_rad.iloc[-1]-a.theta_remote_slack_rad)<1e-6
labels={'baseline':'Baseline','r56_075':'R56 = 75%','r56_050':'R56 = 50%','r56_025':'R56 = 25%','r56_zero':'R56 = 0','keep_line45':'Keep line 4-5','all_R_zero':'All line R = 0','x56_050':'X56 = 50%'}
order=list(labels)
fig,axes=plt.subplots(2,2,figsize=(12,8),sharex='col')
for tag in order:
 d=frames[tag];t=d.t_post_s.to_numpy();theta=(d.theta_remote_slack_rad-d.theta_remote_slack_rad.iloc[0])/(2*np.pi)
 axes[0,0].plot(t,theta,lw=1,label=labels[tag])
 # 1-second moving average only for readable plotting; summaries use unfiltered signals.
 freq=d.remote_df_Hz.rolling(51,center=True,min_periods=1).mean()
 axes[1,0].plot(t,freq,lw=.8)
 short=t<=15
 axes[0,1].plot(t[short],d.Pcap_remote[short].rolling(11,center=True,min_periods=1).mean(),lw=1)
 axes[1,1].plot(t[short],d.Ploss[short].rolling(11,center=True,min_periods=1).mean(),lw=1)
axes[0,0].set_ylabel('Remote internal phase change [turns]');axes[1,0].set_ylabel('Remote mean frequency deviation [Hz]')
axes[0,1].set_ylabel('Remote total Pcap [pu]');axes[0,1].axhline(1.2,color='black',ls=':',lw=.8)
axes[1,1].set_ylabel('All line active-power losses [pu]')
for ax in axes[1]:ax.set_xlabel('Time after clearing [s]')
for ax in axes.flat:ax.grid(alpha=.25)
fig.legend(*axes[0,0].get_legend_handles_labels(),loc='lower center',ncol=4,fontsize=9)
fig.suptitle('Matched-initial-state interventions: H=2.5 s, D1=10, D2=100, B5=1 pu')
fig.tight_layout(rect=(0,.09,1,.96))
for ext in ['png','pdf']:fig.savefig(P/f'interventions.{ext}',dpi=200)
plt.close(fig)
# Algebraic decomposition of the observed baseline postfault remote power burden.
pref=old # Full source loaded again to retain prefault row.
original=pd.read_csv(P/'../h2p5_power_mechanism/budget_D1_10.csv');pre=original[original.stage=='pre'].iloc[0]
base_row=result[result['case']=='baseline'].iloc[0]
decomp={'lost_45_import':float(base_row.tail_P5to4-pre.P5_to_4_pu),'tie56_terminal_change':float(base_row.tail_P5to6-pre.P5_to_6_pu),'remote_internal_loss_change':float(base_row.tail_Ploss_internal-pre.remote_internal_loss_P_pu),'load_change':float(base_row.tail_Pload-pre.load_P_pu)}
metadata={'initial_dynamic_and_washout_max_difference':initerr,'prefault_B5':1.,'prefault_V5_pu':.996594323887269,'fixed_H_s':2.5,'fixed_M':5,'fixed_Ddroop':10,'fixed_D1':10,'fixed_D2':100,'horizon_s':1000,'max_power_balance_error':float(result.max_balance_error.max()),'baseline_reproduction_endpoint_phase_error_rad':float(abs(b.theta_remote_slack_rad.iloc[-1]-a.theta_remote_slack_rad)),'baseline_burden_decomposition_pu':decomp,'source_sha256':{f:hashlib.sha256((P/f).read_bytes()).hexdigest() for f in ['run.jl','analyze.py']},'interpretation':'Changing line R changes losses, voltage and the P-delta characteristic. Keeping line 4-5 also changes transfer capability and the postfault equilibria. These are matched-initial-state interventions, not isolated replacements of a scalar loss term.'}
(P/'validation.json').write_text(json.dumps(metadata,indent=2)+'\n')
print(result[['case','classification','turns','tail_remote_df_Hz','tail_Pcap_remote','tail_Ploss','tail_Pload','tail_Pslack','root_max_real']].to_string(index=False))

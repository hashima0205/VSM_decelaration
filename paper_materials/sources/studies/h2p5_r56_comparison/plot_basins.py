from pathlib import Path
import json
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
P=Path(__file__).resolve().parent;old=P/'../h2p5_bus5_basins'
s0=pd.read_csv(old/'samples.csv').query('D1==10').sort_values('point').copy();s0['condition']='baseline'
s1=pd.concat([pd.read_csv(f) for f in sorted(P.glob('samples_w*.csv'))],ignore_index=True).sort_values('point');s1['condition']='r56_075'
assert len(s0)==len(s1)==43
samples=pd.concat([s0,s1],ignore_index=True);samples.to_csv(P/'basin_comparison.csv',index=False)
faces=pd.read_csv(old/'triangles_D1_10.csv').to_numpy(dtype=int)
tr={tag:pd.read_csv(P/f'trajectory_{tag}.csv') for tag in ['baseline','r56_075']}
roots={tag:np.loadtxt(P/f'../h2p5_hypothesis_interventions/{"baseline" if tag=="baseline" else "r56_075"}/root.csv',delimiter=',') for tag in tr}
ai=np.array([30,45,66])-1
stable={tag:float(x[ai].mean()-np.angle(complex(x[47],x[48]))) for tag,x in roots.items()}
colors={'R':'#9ecae1','N':'#fdae6b','P':'#bc80bd','U':'#ddd'}
def cat(c):return 'R' if c.startswith('recovery') else {'negative_running':'N','positive_running':'P'}.get(c,'U')
legend=[Patch(facecolor=colors['R'],label='Finite-time recovery'),Patch(facecolor=colors['N'],label='Negative running (slack reference)'),Patch(facecolor='#eee',hatch='////',edgecolor='#bbb',label='Mixed sampled outcomes'),Patch(facecolor=colors['U'],label='Unresolved'),Line2D([],[],c='#762a83',label='Fault-on trajectory'),Line2D([],[],c='#111',label='Post-fault trajectory (first 10 s)'),Line2D([],[],marker='^',ls='',c='#2166ac',label='Prefault point'),Line2D([],[],marker='o',ls='',mfc='white',mec='black',label='Clearing projection'),Line2D([],[],marker='*',ls='',mfc='#ffe259',mec='black',ms=10,label='Stable equilibrium projection'),Line2D([],[],c='gray',ls=':',label='Algebraic phase jump at switching')]
plt.rcParams.update({'font.size':10,'pdf.fonttype':42})
for zoom in [False,True]:
 fig,axes=plt.subplots(1,2,figsize=(12,5.8),sharex=True,sharey=True)
 for ax,tag,s in zip(axes,['baseline','r56_075'],[s0,s1]):
  xy=s[['theta_bus5_rad','df_Hz']].to_numpy();labs=np.array([cat(v) for v in s.classification]);same=[];co=[];mixed=[]
  for f in faces:
   if len(set(labs[f]))==1:same.append(xy[f]);co.append(colors[labs[f[0]]])
   else:mixed.append(xy[f])
  if same:ax.add_collection(PolyCollection(same,facecolors=co,edgecolors='none',alpha=.65))
  if mixed:ax.add_collection(PolyCollection(mixed,facecolors='#eee',edgecolors='#bbb',linewidths=.3,hatch='////',alpha=.65))
  ax.scatter(*xy.T,c=[colors[c] for c in labs],edgecolors='#555',linewidths=.4,s=13,zorder=3)
  d=tr[tag]
  for stage,c in [('pre','#2166ac'),('fault','#762a83'),('post','#111')]:
   a=d[d.stage==stage];ax.plot(a.theta_bus5,a.remote_df,c=c,lw=1.1,zorder=5)
   if stage=='post':
    for tt in [.2,.5,1.,2.,4.]:
     i=np.searchsorted(a.t_post_s,tt);j=i+3
     if j<len(a):
      u,v=a.iloc[i],a.iloc[j];ax.annotate('',xy=(v.theta_bus5,v.remote_df),xytext=(u.theta_bus5,u.remote_df),arrowprops=dict(arrowstyle='-|>',color=c,lw=.7,mutation_scale=9),zorder=6)
  for first,second in [('pre','fault'),('fault','post')]:
   a=d[d.stage==first].iloc[-1];b=d[d.stage==second].iloc[0]
   ax.plot([a.theta_bus5,b.theta_bus5],[a.remote_df,b.remote_df],c='gray',ls=':',lw=.9,zorder=4)
  a=d.iloc[0];b=d[d.stage=='post'].iloc[0]
  ax.plot(a.theta_bus5,a.remote_df,'^',mfc='#2166ac',mec='white',ms=8,zorder=9)
  ax.plot(b.theta_bus5,b.remote_df,'o',mfc='white',mec='black',ms=6,zorder=8)
  ax.plot(stable[tag],0,'*',mfc='#ffe259',mec='black',ms=12,zorder=8)
  ax.set_title('Baseline R56: running' if tag=='baseline' else 'R56 reduced by 25%: recovery')
  ax.set_xlim((.05,.69) if zoom else (min(s0.theta_bus5_rad.min(),s1.theta_bus5_rad.min())-.03,max(s0.theta_bus5_rad.max(),s1.theta_bus5_rad.max())+.03))
  ax.set_ylim((-.3,.025) if zoom else (-1.24,.08));ax.grid(alpha=.18)
  ax.set_xlabel(r'Mean internal angle relative to Bus5 $\theta_5$ [rad]')
 axes[0].set_ylabel('Remote mean frequency deviation\nfrom 60 Hz [Hz]')
 fig.suptitle('Bus5-referenced conditional basins: H=2.5 s, D1=10, D2=100, B5=1 pu\n43 matched differential initial states per circuit; actual orbit starts at prefault point',fontsize=11)
 fig.legend(handles=legend,loc='lower center',ncol=3,fontsize=8,bbox_to_anchor=(.5,-.01));fig.tight_layout(rect=(0,.22,1,.91))
 name='basins_bus5_zoom' if zoom else 'basins_bus5'
 for ext in ['png','pdf']:fig.savefig(P/f'{name}.{ext}',dpi=200,bbox_inches='tight')
 plt.close(fig)
# Audit common full differential initial states and actual Bus5 coordinates.
st=pd.read_csv(P.parents[1]/'VSM_decelaration/data/states.csv');dyn=st.loc[st.mass!=0,'index'].to_numpy()-1
held=np.r_[dyn,np.arange(66,70)];err=0.;coorderr=0
for i in range(1,44):
 tag=f'D1_10_p{i:03d}';a=np.loadtxt(old/tag/'initial.csv',delimiter=',');b=np.loadtxt(P/tag/'initial.csv',delimiter=',');assert np.array_equal(a[held],b[held])
 theta=b[ai].mean()-np.angle(complex(b[47],b[48]));target=s1[s1.point==i].iloc[0].theta_bus5_rad;coorderr=max(coorderr,abs(theta-target))
assert coorderr<1e-9
# The reference change is an offset over this fixed-current initial slice, not a dynamic orbit translation.
offset=s1.theta_bus5_rad.to_numpy()-s0.theta_bus5_rad.to_numpy();assert np.ptp(offset)<1e-9
metadata={'phase_definition':'mean(delta2,delta3,delta7) - unwrap(arg(U5(t)))','frequency_reference':'60 Hz; vertical coordinate is not d(theta5)/dt divided by 2pi','baseline_samples_reused':43,'R75_samples_newly_simulated':43,'common_dynamic_and_washout_state_pairs':43,'fixed_other_initial_states':'Both slices use the baseline equilibrium for the other original differential states; z=0. New R75 equilibrium is a projection and need not lie in this slice.','R75_initial_Bus5_coordinate_offset_rad':float(offset.mean()),'max_coordinate_error_rad':coorderr,'root_projections_Bus5_rad':stable,'classification_horizons_s':[30,100,300],'trajectory_display_horizon_postfault_s':10,'sample_counts':samples.groupby(['condition','classification']).size().rename('count').reset_index().to_dict('records'),'max_algebraic_residual':float(samples.max_algebraic_residual.max())}
(P/'basin_validation.json').write_text(json.dumps(metadata,indent=2)+'\n')
print(samples.groupby(['condition','classification']).size().to_string());print('Matched 43 full differential / filter state pairs')

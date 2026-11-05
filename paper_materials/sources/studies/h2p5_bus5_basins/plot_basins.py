from pathlib import Path
import json,hashlib,subprocess
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
P=Path(__file__).resolve().parent
plt.rcParams.update({'font.size':10,'pdf.fonttype':42})
COL={'R':'#9ecae1','N':'#fdae6b','P':'#bc80bd','U':'#d9d9d9'}
def category(s):
 if s.startswith('recovery'):return 'R'
 return {'negative_running':'N','positive_running':'P'}.get(s,'U')
def save(fig,name):
 for ext in ['png','pdf']:fig.savefig(P/f'{name}.{ext}',dpi=210,bbox_inches='tight')
 plt.close(fig)
samples=pd.concat([pd.read_csv(f) for f in sorted(P.glob('samples_w*.csv'))],ignore_index=True)
assert not samples.duplicated(['D1','point']).any()
samples.to_csv(P/'samples.csv',index=False)
trajectories={i:pd.read_csv(P/f'trajectory_D1_{i}.csv') for i in [10,20]}
checks=[]
for d1,d in trajectories.items():
 pre=d[d.stage=='pre'];assert pre.V5_pu.min()>=.98
 assert np.allclose(d.theta_remote_internal_rad-d.bus5_phase_unwrapped_rad,d.theta_bus5_rad,atol=1e-10,rtol=0)
 assert d.V5_pu.min()>.1
 for stage,g in d.groupby('stage',sort=False):
  step=np.abs(np.diff(g.bus5_phase_unwrapped_rad))
  assert step.max()<np.pi/2
  checks.append(dict(D1=d1,stage=stage,min_V5_pu=float(g.V5_pu.min()),max_bus5_phase_step_rad=float(step.max())))
 assert abs(pre.theta_bus5_rad.iloc[0]-.1829742768426999)<1e-9
 stable=pd.read_csv(P/'stable.csv',header=None).iloc[:,0].to_numpy()
 stable_x=np.mean(stable[np.array([30,45,66])-1])-np.angle(complex(stable[47],stable[48]))
 assert abs(stable_x-.1755816466119504)<1e-9

def background(ax,s):
 xy=s[['theta_bus5_rad','df_Hz']].to_numpy();labels=np.array([category(c) for c in s.classification])
 tri=mtri.Triangulation(*xy.T);same=[];colors=[];mixed=[]
 for face in tri.triangles:
  ls=set(labels[face])
  if len(ls)==1:same.append(xy[face]);colors.append(COL[next(iter(ls))])
  else:mixed.append(xy[face])
 if same:ax.add_collection(PolyCollection(same,facecolors=colors,edgecolors='none',alpha=.65,zorder=0))
 if mixed:ax.add_collection(PolyCollection(mixed,facecolors='#eeeeee',edgecolors='#b0b0b0',linewidths=.3,hatch='////',alpha=.6,zorder=1))
 ax.scatter(*xy.T,s=14,c=[COL[c] for c in labels],edgecolors='#555',linewidths=.45,zorder=3)
 pd.DataFrame(tri.triangles,columns=['i','j','k']).to_csv(P/f'triangles_D1_{int(s.D1.iloc[0])}.csv',index=False)

def trajectory(ax,d,post_limit=30):
 parts={stage:d[d.stage==stage] for stage in ['pre','fault','post']}
 for stage,g in parts.items():
  if stage=='post':g=g[g.t_post_s<=post_limit]
  ax.plot(g.theta_bus5_rad,g.df_mean_Hz,color={'pre':'#2166ac','fault':'#762a83','post':'#202020'}[stage],lw=1.1,zorder=4)
 for a,b in [('pre','fault'),('fault','post')]:
  v=parts[a].iloc[-1];w=parts[b].iloc[0]
  ax.plot([v.theta_bus5_rad,w.theta_bus5_rad],[v.df_mean_Hz,w.df_mean_Hz],ls=':',color='#777',lw=1,zorder=5)
 pre=parts['pre'].iloc[0];clear=parts['post'].iloc[0]
 ax.plot(pre.theta_bus5_rad,pre.df_mean_Hz,'^',mfc='#2166ac',mec='white',ms=8,zorder=9)
 ax.plot(clear.theta_bus5_rad,clear.df_mean_Hz,'o',mfc='white',mec='#111',ms=6,zorder=8)
 ax.plot(stable_x,0,'*',mfc='#ffe259',mec='#111',ms=12,zorder=8)
 for stage,ts in [('fault',[1.04,1.10]),('post',[.1,.5,1.5,3.])]:
  g=parts[stage];times=g.t_absolute_s if stage=='fault' else g.t_post_s
  for at in ts:
   i=np.searchsorted(times,at);j=i+(8 if stage=='fault' else 3)
   if j>=len(g):continue
   a,b=g.iloc[i],g.iloc[j]
   ax.annotate('',xy=(b.theta_bus5_rad,b.df_mean_Hz),xytext=(a.theta_bus5_rad,a.df_mean_Hz),arrowprops=dict(arrowstyle='-|>',color='#762a83' if stage=='fault' else '#111',lw=.8,mutation_scale=9),zorder=7)

legend=[Patch(facecolor=COL['R'],label='Finite-time recovery'),Patch(facecolor=COL['N'],label='Negative running (60 Hz reference)'),Patch(facecolor='#eee',edgecolor='#bbb',hatch='////',label='Mixed sampled outcomes'),Patch(facecolor=COL['U'],label='Unresolved'),Line2D([],[],color='#762a83',label='Fault-on trajectory'),Line2D([],[],color='#202020',label='Post-fault trajectory (first 30 s)'),Line2D([],[],marker='^',ls='',color='#2166ac',label='Prefault operating point'),Line2D([],[],marker='o',ls='',mfc='white',mec='black',label='Post-switch clearing point'),Line2D([],[],marker='*',ls='',mfc='#ffe259',mec='black',ms=11,label='Post-fault stable equilibrium'),Line2D([],[],color='#777',ls=':',label='Algebraic jump at switching')]
for zoom in [False,True]:
 fig,axes=plt.subplots(1,2,figsize=(11,5.8),sharex=True,sharey=True)
 for ax,d1 in zip(axes,[10,20]):
  s=samples[samples.D1==d1].sort_values('point');background(ax,s);trajectory(ax,trajectories[d1])
  ax.set_title(f'D1 = {d1}; {len(s)} sampled initial states')
  ax.set_xlim(*((.08,.66) if zoom else (-.12,.82)))
  ax.set_ylim(*((-.28,.022) if zoom else (-1.24,.08)))
  ax.set_xlabel(r'Mean internal angle relative to Bus5 $\theta_5$ [rad]');ax.grid(alpha=.2)
 axes[0].set_ylabel(r'Mean internal frequency deviation from 60 Hz $\Delta f$ [Hz]')
 fig.suptitle('VSM conditional recovery regions: H = 2.5 s, B5 = 1 pu\nPhase zero = instantaneous Bus5 voltage; trajectories start at prefault state',fontsize=11)
 fig.legend(handles=legend,loc='lower center',ncol=3,fontsize=8,bbox_to_anchor=(.5,-.01))
 fig.tight_layout(rect=(0,.22,1,.91));save(fig,'basins_bus5_zoom' if zoom else 'basins_bus5')
fig,axes=plt.subplots(3,1,figsize=(9,7.5),sharex=True)
for d1,d in trajectories.items():
 for ax,y in zip(axes,[d.theta_bus5_rad,(d.theta_remote_internal_rad-d.theta_remote_internal_rad.iloc[0])/(2*np.pi),d.df_mean_Hz]):ax.plot(d.t_absolute_s,y,lw=.7,label=f'D1 = {d1}')
for ax in axes:ax.grid(alpha=.2);ax.axvline(1,color='#762a83',lw=.6,ls=':');ax.axvline(1.15,color='#777',lw=.6,ls=':')
axes[0].set_ylabel('Bus5-relative internal\nphase [rad]');axes[1].set_ylabel('Internal phase change\nrelative to 60 Hz frame [turns]');axes[2].set_ylabel('Frequency deviation\nfrom 60 Hz [Hz]');axes[2].set_xlabel('Time from prefault initialization [s]');axes[0].legend()
fig.suptitle('Bus5 moves with the remote group during negative running');fig.tight_layout();save(fig,'phase_reference_comparison')
meta={'phase_definition':'theta5 = (delta2+delta3+delta7)/3 - unwrap(arg(V5(t))); no prefault or postfault angle subtraction','frequency_definition':'mean internal frequency of Bus2/3/7 minus 60 Hz; NOT the derivative of theta5 divided by 2pi','prefault_theta5_rad':.1829742768426999,'postfault_stable_theta5_rad':stable_x,'section':'Remote three internal angles and frequency states shifted uniformly; other 46 original differential states and all 4 D2 washout states at postfault stable equilibrium initially. All differential states then integrated.','initial_washout':'z=0 at all four machines','note':'Conditional slice in 56 differential dimensions; actual event trajectory is a projection and generally outside this slice. Mixed triangles are not a resolved boundary.','sample_count':len(samples),'classification_horizons_s':[30,100,300],'coordinate_checks':checks,'source_sha256':{f:hashlib.sha256((P/f).read_bytes()).hexdigest() for f in ['run_basins.jl','export_trajectories.jl','plot_basins.py']},'simulation_commit':subprocess.check_output(['git','-C',str(P.parents[1]/'VSM_decelaration'),'rev-parse','HEAD'],text=True).strip()}
(P/'definition.json').write_text(json.dumps(meta,indent=2)+'\n')
print(samples.groupby(['D1','classification']).size().to_string());print('Sampled',len(samples),'states')

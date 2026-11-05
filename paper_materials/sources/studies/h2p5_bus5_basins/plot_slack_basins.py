"""Reproject the same full-state basin samples and event trajectories onto Bus6 phase zero."""
from pathlib import Path
import json,hashlib
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
s=pd.read_csv(P/'samples.csv');assert len(s)==86
ai=np.array([30,45,66])-1
for i,r in s.iterrows():
 x=np.loadtxt(P/r['case']/'initial.csv',delimiter=',')
 s.loc[i,'theta_slack_rad']=x[ai].mean()
 assert abs(x[ai].mean()-np.angle(complex(x[47],x[48]))-r.theta_bus5_rad)<1e-9
s.to_csv(P/'samples_slack.csv',index=False)
stable=np.loadtxt(P/'stable.csv',delimiter=',')[ai].mean()
pre=np.loadtxt(P/'pre.csv',delimiter=',')[ai].mean()
tr={i:pd.read_csv(P/f'trajectory_D1_{i}.csv') for i in [10,20]}
for d1,d in tr.items():
 d['theta_slack_rad']=d.theta_remote_internal_rad
 assert abs(d.theta_slack_rad.iloc[0]-pre)<1e-9
 assert np.allclose(d.theta_slack_rad,d.theta_bus5_rad+d.bus5_phase_unwrapped_rad,rtol=0,atol=1e-10)
 for a,b in [('pre','fault'),('fault','post')]:
  aa=d[d.stage==a].iloc[-1];bb=d[d.stage==b].iloc[0]
  assert abs(aa.theta_slack_rad-bb.theta_slack_rad)<1e-9
 d.to_csv(P/f'trajectory_slack_D1_{d1}.csv',index=False)
col={'R':'#9ecae1','N':'#fdae6b','P':'#bc80bd','U':'#d9d9d9'}
def cat(c):return 'R' if c.startswith('recovery') else {'negative_running':'N','positive_running':'P'}.get(c,'U')
def background(ax,ss):
 xy=ss[['theta_slack_rad','df_Hz']].to_numpy();labels=np.array([cat(c) for c in ss.classification])
 # Preserve exactly the Bus5 figure's triangles; only change their coordinates.
 faces=pd.read_csv(P/f'triangles_D1_{int(ss.D1.iloc[0])}.csv').to_numpy(dtype=int)
 same=[];colors=[];mixed=[]
 for f in faces:
  ls=set(labels[f])
  if len(ls)==1:same.append(xy[f]);colors.append(col[next(iter(ls))])
  else:mixed.append(xy[f])
 if same:ax.add_collection(PolyCollection(same,facecolors=colors,edgecolors='none',alpha=.65,zorder=0))
 if mixed:ax.add_collection(PolyCollection(mixed,facecolors='#eee',edgecolors='#b0b0b0',linewidths=.3,hatch='////',alpha=.6,zorder=1))
 ax.scatter(*xy.T,s=14,c=[col[c] for c in labels],edgecolors='#555',linewidths=.4,zorder=3)

def trajectory(ax,d):
 for stage,color in [('pre','#2166ac'),('fault','#762a83'),('post','#202020')]:
  g=d[d.stage==stage]
  if stage=='post':g=g[g.t_post_s<=30]
  ax.plot(g.theta_slack_rad,g.df_mean_Hz,color=color,lw=1.1,zorder=4)
  for at in ([1.04,1.10] if stage=='fault' else [.1,.5,1.,2.,4.] if stage=='post' else []):
   times=g.t_absolute_s if stage=='fault' else g.t_post_s
   i=np.searchsorted(times,at);j=i+(8 if stage=='fault' else 3)
   if j<len(g):
    a,b=g.iloc[i],g.iloc[j]
    ax.annotate('',xy=(b.theta_slack_rad,b.df_mean_Hz),xytext=(a.theta_slack_rad,a.df_mean_Hz),arrowprops=dict(arrowstyle='-|>',color=color,lw=.8,mutation_scale=9),zorder=7)
 a=d.iloc[0];b=d[d.stage=='post'].iloc[0]
 ax.plot(a.theta_slack_rad,a.df_mean_Hz,'^',mfc='#2166ac',mec='white',ms=8,zorder=9)
 ax.plot(b.theta_slack_rad,b.df_mean_Hz,'o',mfc='white',mec='#111',ms=6,zorder=8)
 ax.plot(stable,0,'*',mfc='#ffe259',mec='#111',ms=12,zorder=8)

legend=[Patch(facecolor=col['R'],label='Finite-time recovery'),Patch(facecolor=col['N'],label='Negative running'),Patch(facecolor='#eee',edgecolor='#bbb',hatch='////',label='Mixed sampled outcomes'),Line2D([],[],color='#762a83',label='Fault-on trajectory'),Line2D([],[],color='#202020',label='Post-fault trajectory (first 30 s)'),Line2D([],[],marker='^',ls='',color='#2166ac',label='Prefault operating point'),Line2D([],[],marker='o',ls='',mfc='white',mec='black',label='Clearing point'),Line2D([],[],marker='*',ls='',mfc='#ffe259',mec='black',ms=11,label='Post-fault stable equilibrium')]
for wide in [False,True]:
 fig,axes=plt.subplots(1,2,figsize=(11,5.6),sharex=True,sharey=True)
 for ax,d1 in zip(axes,[10,20]):
  ss=s[s.D1==d1].sort_values('point');background(ax,ss);trajectory(ax,tr[d1])
  ax.set_title(f'D1 = {d1}; 43 sampled initial states')
  ax.set_xlim(*((-120,0) if wide else (-2.25,-.2)));ax.set_ylim(-1.25,.08)
  ax.set_xlabel(r'Mean internal angle relative to slack Bus6 $\theta_6$ [rad]');ax.grid(alpha=.2)
  if not wide and d1==10:ax.text(.02,.04,'Negative-running orbit continues left',transform=ax.transAxes,fontsize=8,bbox=dict(facecolor='white',alpha=.8,edgecolor='none'))
 axes[0].set_ylabel(r'Mean internal frequency deviation from 60 Hz $\Delta f$ [Hz]')
 fig.suptitle('VSM conditional recovery regions: slack Bus6 phase = 0 rad\nH = 2.5 s, B5 = 1 pu; trajectories start at the prefault state',fontsize=11)
 fig.legend(handles=legend,loc='lower center',ncol=3,fontsize=8,bbox_to_anchor=(.5,-.01))
 fig.tight_layout(rect=(0,.20,1,.91))
 name='basins_slack_wide' if wide else 'basins_slack'
 for ext in ['png','pdf']:fig.savefig(P/f'{name}.{ext}',dpi=210,bbox_inches='tight')
 plt.close(fig)
metadata={'reference':'Fixed slack/infinite bus Bus6, phase=0 rad, frequency=60 Hz','phase_definition':'(delta2+delta3+delta7)/3; unwrapped; no equilibrium or prefault subtraction','prefault_theta_rad':pre,'postfault_stable_theta_rad':stable,'sample_count':len(s),'same_classifications_and_triangles_as':'Bus5 reference figures','main_view_xlim_rad':[-2.25,-.2],'wide_view_xlim_rad':[-120,0],'display_postfault_horizon_s':30,'numerical_integration':'No new integration; transformed coordinates from existing initial 70-state vectors and saved event trajectories.','source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(P/'slack_definition.json').write_text(json.dumps(metadata,indent=2)+'\n')
(P/'SLACK_REFERENCE.md').write_text(f'''# slack母線Bus6基準の引き込み領域図

固定slack母線Bus6の位相0 rad、周波数60 Hzを基準とした。遠方3機Bus2・3・7の平均内部角を横軸に用い、事故前点を原点へ移す操作や±πへの折返しは行っていない。

- [引き込み領域と事故軌道 PNG](basins_slack.png) / [PDF](basins_slack.pdf)
- [事故後30秒の広域表示 PNG](basins_slack_wide.png) / [PDF](basins_slack_wide.pdf)
- 事故前点：{pre:.12f} rad。事故後安定点：{stable:.12f} rad。
- D1=10はslack母線に対して位相が負方向へ進み続ける。主図の表示範囲を左へ離れるため、広域図に30秒までの軌道全体を示した。D1=20は安定点へ戻る。
- 背景はBus5基準図と同じ各43初期値・分類・三角形。初期全70状態からslack基準の位相を直接計算している。背景は初期値断面の条件付き領域であり、事故軌道は断面外の投影を含む。斜線は分類混在域で厳密な境界ではない。
- この座標では内部角と周波数は系統切替時にも連続。Bus5基準図での代数電圧位相の跳びは横軸に現れない。
- [描画用背景点](samples_slack.csv)、trajectory_slack_D1_10.csv / trajectory_slack_D1_20.csv、[基準・検証情報](slack_definition.json)。
- 再描画：`MPLCONFIGDIR=/tmp/vsm_mpl /home/students1/miniconda3/envs/julia/bin/python studies/h2p5_bus5_basins/plot_slack_basins.py`。再積分は不要。

[Bus5基準・元計算の詳細](README.md)
''')
print('Slack Bus6 reference: prefault',pre,'stable',stable,'samples',len(s))

from pathlib import Path
import numpy as np,pandas as pd,json,hashlib,subprocess
P=Path(__file__).resolve().parents[1];T=P/'tables';D=P/'data'
# Recompute external SCR independently from the frozen branch R/X values.
lines=pd.read_csv(P/'inputs/lines.csv');ref=pd.read_csv(T/'SCR_source.csv');rows=[]
for k in [.8,1.02,1.0299,1.031]:
 for stage in ['pre','post']:
  y=np.zeros((8,8),complex)
  for r in lines.itertuples():
   j=int(r.line);a=int(r.from_bus)-1;b=int(r.to_bus)-1
   if stage=='post' and j==7:continue
   z=complex(r.R_pu,r.X_pu)*(k/1.0299 if j in [2,3] else 1)
   v=1/z;y[a,a]+=v;y[b,b]+=v;y[a,b]-=v;y[b,a]-=v
  keep=[0,1,2,3,4,6,7];z=np.linalg.inv(y[np.ix_(keep,keep)])
  for b in [1,2,3,7]:
   zz=z[keep.index(b-1),keep.index(b-1)];scr=1/abs(zz);old=ref.loc[np.isclose(ref.k,k),f'{stage}_scr{b}'].iloc[0]
   assert abs(scr-old)<1e-12
   rows.append(dict(k=k,stage=stage,bus=b,SCR=scr,Zth_R=zz.real,Zth_X=zz.imag,old_difference=scr-old))
pd.DataFrame(rows).to_csv(T/'SCR_verified.csv',index=False)
# Compare complete actual parameter vectors, not only declared settings.
rows=[]
for a,b,n in [('A_droop_center','B_vsm_center',0),('C_droop_recovery','D_vsm_recovery',0),('B_vsm_center','E_shortQ_center',4),('E_shortQ_center','F_shortQ_strong',4),('E_shortQ_center','G_shortQ_weak',4),('B_vsm_center','H_longQ_strong',4),('B_vsm_center','B_vsm_strict',0),('D_vsm_recovery','D_vsm_strict',0)]:
 for stage in ['pre','fault','post']:
  fa=P/'checkpoints'/a/(stage+'_parameters.csv');fb=P/'checkpoints'/b/(stage+'_parameters.csv')
  if not fb.exists():continue
  x=np.loadtxt(fa,delimiter=',');y=np.loadtxt(fb,delimiter=',');di=np.where(x!=y)[0];assert len(di)==n,(a,b,di)
  if n==0:rows.append(dict(reference=a,comparison=b,stage=stage,index=0,before=0,after=0,n_changed=0))
  for j in di:rows.append(dict(reference=a,comparison=b,stage=stage,index=j+1,before=x[j],after=y[j],n_changed=n))
pd.DataFrame(rows).to_csv(T/'parameter_changes.csv',index=False)
# Independently verify tail classification and integration completion for available cases.
c=pd.read_csv(T/'classifications.csv');roots=pd.read_csv(D/'roots.csv');ev=pd.read_csv(D/'events.csv');assert ev.algebraic_residual.max()<1e-8 and ev.dynamic_change.max()<1e-12
assert roots.residual.max()<1e-8
assert set(c.classification)<=set(['negative_rotation','recovery','other_instability','unresolved'])
for tag in c['case']:
 z=pd.read_csv(P/'checkpoints'/tag/'post.csv');assert abs(z.t_post_s.iloc[-1]-300)<1e-10
 assert np.isfinite(z.select_dtypes('number')).all().all()
 if tag.startswith(('B_','D_')):
  # Verify actual VSM state at the end matches reported frequency.
  s=np.loadtxt(P/'checkpoints'/tag/'post_end.csv',delimiter=',');mp=pd.read_csv(D/'mapping.csv').drop_duplicates('bus')
  for r in mp.itertuples():assert abs(s[int(r.pf_index)-1]*60-(z[f'b{int(r.bus)}_omega_rad_s'].iloc[-1]/(2*np.pi)-60))<1e-12
checks=dict(cases=len(c),parameters_verified=True,external_SCR_verified=True,event_continuity_verified=True,finite_300s_trajectories=True,all_roots_locally_stable=bool((roots.max_real<0).all()),max_root_residual=float(roots.residual.max()),max_event_residual=float(ev.algebraic_residual.max()))
(T/'quality.json').write_text(json.dumps(checks,indent=2));print(json.dumps(checks,indent=2))
for base,strict in [('B_vsm_center','B_vsm_strict'),('D_vsm_recovery','D_vsm_strict')]:
 if strict not in set(c['case']):continue
 a=c[c['case']==base].iloc[0];b=c[c['case']==strict].iloc[0]
 assert a.classification==b.classification
 assert abs(a.remote_turns-b.remote_turns)<.001
 er=pd.read_csv(T/'waveform_errors.csv');er=er[er.comparison==strict]
 assert len(er)>0 and er.max_abs_error.max()<.001
for a,b in [('A_droop_center','B_vsm_center'),('C_droop_recovery','D_vsm_recovery')]:
 for stage in ['pre','fault','post']:
  x=pd.read_csv(P/'checkpoints'/a/(stage+'.csv'));y=pd.read_csv(P/'checkpoints'/b/(stage+'.csv'))
  assert np.array_equal(x.filter(like='saturated').to_numpy(),y.filter(like='saturated').to_numpy())
print('Matched saturation flags and available refined classifications verified.')

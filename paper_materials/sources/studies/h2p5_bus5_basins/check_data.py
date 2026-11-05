"""Audit saved basin coordinates, matched initial states and root checks; no integration."""
from pathlib import Path
import json
import pandas as pd,numpy as np
p=Path(__file__).resolve().parent;s=pd.read_csv(p/'samples.csv')
stable=np.loadtxt(p/'stable.csv',delimiter=',');states=pd.read_csv(p.parents[1]/'VSM_decelaration/data/states.csv')
dyn=states.loc[states.mass!=0,'index'].to_numpy()-1
changed=np.array([30,45,66,29,44,65])-1;held=np.setdiff1d(dyn,changed)
assert len(s)==86 and not s.duplicated(['D1','point']).any()
errors=[]
for i in range(1,44):
 a=np.loadtxt(p/f'D1_10_p{i:03}/initial.csv',delimiter=',');b=np.loadtxt(p/f'D1_20_p{i:03}/initial.csv',delimiter=',')
 assert a.shape==(70,) and np.array_equal(a,b)
 assert np.max(abs(a[held]-stable[held]))==0 and np.max(abs(a[66:]))==0
 theta=np.mean(a[np.array([30,45,66])-1])-np.angle(complex(a[47],a[48]))
 df=60*np.mean((.4-a[np.array([29,44,65])-1])/10)
 sample=s[(s.D1==10)&(s.point==i)].iloc[0]
 errors.append([abs(theta-sample.theta_bus5_rad),abs(df-sample.df_Hz)])
assert np.max(errors)<1e-9 and s.max_algebraic_residual.max()<1e-7
roots=pd.concat([pd.read_csv(f) for f in p.glob('roots_w*.csv')]);assert (roots.residual<1e-8).all() and (roots.max_real_eigen<0).all()
m=pd.read_csv(p/'machines.csv');assert len(m)==86*4
counts=s.groupby(['D1','classification']).size().rename('count').reset_index().to_dict('records')
horizons=s.groupby(['D1','horizon_s']).size().rename('count').reset_index().to_dict('records')
result={'matched_full_70_state_pairs':43,'held_original_differential_states':len(held),'held_filter_states':4,'max_coordinate_error':np.max(errors,axis=0).tolist(),'max_algebraic_residual':float(s.max_algebraic_residual.max()),'classification_counts':counts,'horizons':horizons}
(p/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
print('86 points audited; 43 identical full-state pairs; max algebraic residual',result['max_algebraic_residual'])

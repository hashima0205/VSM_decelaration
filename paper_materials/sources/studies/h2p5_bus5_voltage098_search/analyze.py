from pathlib import Path
import sys,json,hashlib
import numpy as np,pandas as pd
p=Path(__file__).resolve().parent;root=p.parents[1]/'VSM_decelaration'
sys.path.insert(0,str(root/'code'))
import classify
from classify import measure
classify.D=p/'classifications';(classify.D/'results').mkdir(parents=True,exist_ok=True)
screen=pd.read_csv(p/'screen.csv')
rows=[];frames={};detail=[]
for directory in sorted(p.iterdir()):
 if not directory.is_dir() or not (directory/'post.csv').exists():continue
 tag=directory.name;setting=screen.set_index('case').loc[tag]
 d=pd.concat([pd.read_csv(directory/(s+'.csv')) for s in ['pre','fault','post']],ignore_index=True)
 d=d.sort_values('t_absolute_s',kind='stable')
 for b in [1,2,3,7]:
  u=d[f'b{b}_U_r_pu']+1j*d[f'b{b}_U_i_pu']
  d[f'b{b}_terminal_phase_unwrapped_rad']=np.unwrap(np.angle(u))
  d[f'b{b}_terminal_phase_reliable']=abs(u)>=.1
  d[f'b{b}_df_Hz']=d[f'b{b}_omega_rad_s']/(2*np.pi)-60
  d[f'b{b}_V_pu']=abs(u)
 d['theta_mean_rad']=d[[f'b{b}_delta_rad' for b in [2,3,7]]].mean(axis=1)
 d['df_mean_Hz']=d[[f'b{b}_df_Hz' for b in [2,3,7]]].mean(axis=1)
 assert np.isfinite(d.select_dtypes('number').to_numpy()).all()
 target=np.loadtxt(directory/'post_root.csv',delimiter=',')
 result=measure(tag,d,target,target)  # No saddle candidate is assumed; phase tolerance is 0.002 rad.
 result.update(setting.to_dict());assert setting.pre_V5>=.98;result['classification_verified']=measure(tag,d,target,target)['classification']
 detail.append(result)
 rows.append({k:v for k,v in result.items() if k!='machines'})
 for s in ['pre','fault','post']:
  assert (directory/(s+'_parameters.csv')).exists()
 frames[tag]=d[d.stage=='post']
(p/'verified.json').write_text(json.dumps(detail,indent=2)+'\n')
pd.DataFrame(rows).to_csv(p/'verified.csv',index=False)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,axs=plt.subplots(2,1,figsize=(9,6),sharex=True)
for tag,d in frames.items():
 t=d.t_post_s.to_numpy();a=(d.theta_mean_rad-d.theta_mean_rad.iloc[0])/(2*np.pi)
 label=('1000 s, dtmax=0.00125 s' if tag.endswith('_fine') else '1000 s, dtmax=0.005 s' if '_h1000' in tag else '300 s, dtmax=0.005 s')
 axs[0].plot(t,a,label=label)
 axs[1].plot(t,d.df_mean_Hz,label=label)
axs[0].set_ylabel('Remote mean internal phase\nchange [turns]');axs[1].set_ylabel('Remote mean frequency\ndeviation [Hz]');axs[1].set_xlabel('Time after fault clearance [s]')
for ax in axs:ax.grid(alpha=.3)
axs[0].legend(fontsize=7);fig.suptitle('Bus5 capacitive shunt: VSM H=2.5 s, M=5 s');fig.tight_layout()
fig.savefig(p/'comparison.png',dpi=180);fig.savefig(p/'comparison.pdf')
metadata={'capacitor_model':'Constant capacitive shunt present in all stages, Qcap=Bcap*abs(V5)^2; PQLoad Q_load_p=-Bcap*vref2.', 'simulation_commit':__import__('subprocess').check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip(),'search_source_sha256':hashlib.sha256((p/'search.jl').read_bytes()).hexdigest(),'scope':'Finite-horizon search with Bus5 capacitive shunt and pre_V5>=0.98; network topology/dispatch retained, line2/3 impedance changed using grid_k/1.0299; load conductance multiplier recorded.'}
(p/'provenance.json').write_text(json.dumps(metadata,indent=2)+'\n')
print(pd.DataFrame(rows)[['case','Bcap','grid_k','pre_V5','Ddroop','D1','D2','load_factor','horizon','classification_verified','remote_turns','pre_max_real','post_max_real']].to_string(index=False))

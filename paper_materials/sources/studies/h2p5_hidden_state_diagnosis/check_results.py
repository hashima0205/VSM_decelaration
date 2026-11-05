from pathlib import Path
import numpy as np,pandas as pd,json,hashlib
p=Path(__file__).resolve().parent;source=p/'../h2p5_r56_comparison'
st=pd.read_csv(p.parents[1]/'VSM_decelaration/data/states.csv');native=pd.read_csv(source/'states_baseline.csv');rec=pd.read_csv(source/'states_r56_075.csv');k=int(np.argmin(abs(native.t_absolute_s-2.99)))
x0=native.iloc[k,3:].to_numpy(float);xr=rec.iloc[k,3:].to_numpy(float);dyn=np.r_[st.loc[st.mass!=0,'index'].to_numpy()-1,np.arange(66,70)]
ctrl=np.loadtxt(p/'control/initial70.csv',delimiter=',');controlerr=np.max(abs(ctrl[dyn]-x0[dyn]));assert controlerr<1e-12

def ix(b,key):return int(st.loc[(st.bus==b)&(st.symbol==f'inv{b}₊{key}'),'index'].iloc[0])-1
angle=np.loadtxt(p/'angle_speed/initial70.csv',delimiter=',');elect=np.loadtxt(p/'electrical_local/initial70.csv',delimiter=',');err=0
for b in [2,3,7]:
 di=ix(b,'droop₊δ');assert abs(angle[di]-xr[di])<1e-12
 for key in ['V_C','i_g','i_f']:
  ir=ix(b,f'vsrc₊filter₊{key}_r');ii=ix(b,f'vsrc₊filter₊{key}_i')
  orig=complex(x0[ir],x0[ii])*np.exp(-1j*x0[di]);new=complex(angle[ir],angle[ii])*np.exp(-1j*angle[di]);err=max(err,abs(orig-new))
  origR=complex(xr[ir],xr[ii])*np.exp(-1j*xr[di]);newE=complex(elect[ir],elect[ii])*np.exp(-1j*elect[di]);assert abs(origR-newE)<1e-12
assert err<1e-12
s=pd.read_csv(p/'results.csv');m=pd.read_csv(p/'machines.csv');assert len(m)==36 and len(s)==9
for tag in s.loc[s.classification=='negative_running','case']:
 assert (m[(m['case']==tag)&m.bus.isin([2,3,7])].classification=='negative_running').all()
J=np.loadtxt(p/'saddle_jacobian.csv',delimiter=',');modes=pd.read_csv(p/'unstable_mode.csv');lam=modes['lambda'].iloc[0];v=modes.right_vector.to_numpy();left=modes.left_vector.to_numpy()
assert np.linalg.norm(J@v-lam*v)<1e-7 and np.linalg.norm(J.T@left-lam*left)<1e-7
assert sum(np.linalg.eigvals(J).real>1e-7)==1
projection=pd.read_csv(p/'mode_projection.csv');assert np.max(abs(projection[['angle','frequency','washout','Q_filter','voltage_PI','current_PI','electrical']].sum(axis=1)-projection.mode_amplitude_rad))<1e-10
meta={'cases':9,'horizon_s':1000,'transplant_absolute_time_s':float(native.iloc[k].t_absolute_s),'control_initial_dynamic_state_CSV_comparison_max_error':float(controlerr),'max_local_phasor_alignment_error':float(err),'all_rotating_cases_remote_machines_negative_running':True,'max_sampled_alg_residual':float(s.max_alg_residual.max()),'saddle_positive_eigenvalue':float(lam),'positive_eigenvalues':1,'source_sha256':{name:hashlib.sha256((p/name).read_bytes()).hexdigest() for name in ['run.jl','mode_analysis.jl','compare.py','analyze_results.py']}}
(p/'validation.json').write_text(json.dumps(meta,indent=2)+'\n');print('PASS: state alignment, nine cases, per-machine classification, saddle eigenpair and mode decomposition')

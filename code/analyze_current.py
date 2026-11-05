"""Plot the current case and independently verify its saved reference trajectory."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
B=[1,2,3,7];R=B[1:]
def compact(data):
    out=data[['t_absolute_s','t_post_s','stage']].copy()
    for b in B:
        out[f'b{b}_delta_rad']=data[f'b{b}_delta_rad']
        out[f'b{b}_df_Hz']=data[f'b{b}_omega_rad_s']/(2*np.pi)-60
    out['remote_delta_rad']=out[[f'b{b}_delta_rad' for b in R]].mean(axis=1)
    out['remote_df_Hz']=out[[f'b{b}_df_Hz' for b in R]].mean(axis=1)
    out['remote_Pcap_pu']=sum(data[f'b{b}_Pcap_pu'] for b in R)
    out['remote_Qterminal_pu']=sum(data[f'b{b}_Qterminal_pu'] for b in R)
    out['remote_mean_Ig_pu']=sum(np.hypot(data[f'b{b}_Ig_r_pu'],data[f'b{b}_Ig_i_pu']) for b in R)/3
    return out

def classify(d,target):
    states=pd.read_csv(ROOT/'data/states.csv');post=d[d.stage=='post'].drop_duplicates('t_post_s',keep='last')
    t=post.t_post_s.to_numpy();finish=t[-1];tail=post[t>=finish-min(50,finish/3)];rows=[]
    for b in B:
        ai=int(states.loc[states.symbol.eq(f'inv{b}₊droop₊δ'),'index'].iloc[0])-1
        angle=post[f'b{b}_delta_rad'].to_numpy();shift=angle-angle[0];turns=shift[-1]/(2*np.pi)
        err=abs(np.angle(np.exp(1j*(angle[-1]-target[ai]))));width=np.ptp(tail[f'b{b}_delta_rad']);fmax=tail[f'b{b}_df_Hz'].abs().max()
        windows=np.diff(np.interp(np.linspace(.4*finish,finish,4),t,angle))/(2*np.pi)
        if fmax<1e-4 and err<.002 and width<.005:label='recovery_after_slip' if max(abs(shift))>=2*np.pi else 'recovery'
        elif turns < -2 and max(windows)<-.2 and sum(windows)/(.6*finish)<-1e-4:label='negative_running'
        elif turns > 2 and min(windows)>.2 and sum(windows)/(.6*finish)>1e-4:label='positive_running'
        else:label='unresolved'
        rows.append(dict(bus=b,classification=label,turns=turns,tail_max_abs_df_Hz=fmax,phase_error_rad=err,phase_width_rad=width))
    return pd.DataFrame(rows)

def plot(d,out,settings):
    out.mkdir(parents=True,exist_ok=True);post=d[d.stage=='post'];short=d[d.t_absolute_s<=11.15]
    fig,axs=plt.subplots(2,2,figsize=(10,7))
    axs[0,0].plot(post.t_post_s,(post.remote_delta_rad-post.remote_delta_rad.iloc[0])/(2*np.pi))
    axs[0,1].plot(post.t_post_s,post.remote_df_Hz)
    axs[1,0].plot(short.t_absolute_s,short.remote_delta_rad)
    axs[1,1].plot(short.t_absolute_s,short.remote_df_Hz)
    for ax,label in zip(axs.flat,['Remote internal phase change [turns]','Remote frequency deviation [Hz]','Remote internal angle / slack [rad]','Remote frequency deviation [Hz]']):ax.set_ylabel(label);ax.grid(alpha=.25)
    for ax in axs[0]:ax.set_xlabel('Time after fault clearance [s]')
    for ax in axs[1]:ax.set_xlabel('Absolute time [s]');ax.axvspan(1,1.15,color='red',alpha=.07)
    fig.suptitle(f'VSM: H={settings["H"]:g} s, mp={100*settings["mp"]:g}%, D1={settings["D1"]:g}, D2={settings["D2"]:g}, Bus5 B={settings["Bcap"]:g} pu')
    fig.tight_layout(rect=(0,0,1,.95))
    for ext in ['png','pdf']:fig.savefig(out/f'trajectory.{ext}',dpi=190)
    plt.close(fig)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('directory',nargs='?',type=Path);ap.add_argument('--saved',action='store_true');args=ap.parse_args()
    ref=ROOT/'results/current_reference'
    if args.saved:
        settings=json.loads((ref/'provenance.json').read_text())
        d=pd.read_csv(ref/'response.csv.gz');plot(d,ROOT/'figures/current',settings);print('Plotted bundled current reference');return
    directory=args.directory or ROOT/'runs/current/current_D1_0_H2p5_mp0p10_B1'
    data=pd.read_csv(directory/'observations.csv');d=compact(data);target=np.loadtxt(directory/'post_root.csv',delimiter=',')
    settings=dict(pd.read_csv(directory/'settings.csv').itertuples(index=False,name=None))
    actual=classify(d,target);saved=pd.read_csv(directory/'machines.csv')
    assert actual.classification.tolist()==saved.classification.tolist()
    assert np.max(abs(actual.turns-saved.turns))<1e-9
    d.to_csv(directory/'response.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    record={'per_machine_classification_verified':True,'max_algebraic_residual':float(data.alg_residual.max()),'horizon_s':float(d.t_post_s.max())}
    reference=json.loads((ref/'provenance.json').read_text())
    matches_reference=all(abs(settings[k]-v)<1e-12 for k,v in reference['parameters'].items())
    if matches_reference and (ref/'response.csv.gz').exists():
        expected=pd.read_csv(ref/'response.csv.gz');end=min(expected.t_absolute_s.max(),d.t_absolute_s.max())
        a=d[d.t_absolute_s<=end].reset_index(drop=True);b=expected[expected.t_absolute_s<=end].reset_index(drop=True)
        assert len(a)==len(b) and a.stage.tolist()==b.stage.tolist()
        assert np.max(abs(a.t_absolute_s-b.t_absolute_s))<1e-10
        err=max(float(np.max(abs(a[c]-b[c]))) for c in a if c not in ['stage','t_absolute_s','t_post_s'])
        assert err<2e-6,f'Current reference trajectory mismatch: {err}'
        record['max_saved_response_error']=err
    (directory/'validation.json').write_text(json.dumps(record,indent=2)+'\n');plot(d,directory/'figures',settings)
    print(actual.to_string(index=False));print(json.dumps(record,indent=2))
if __name__=='__main__':main()

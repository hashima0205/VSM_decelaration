"""Plot saved phasor envelopes over the short mechanism-relevant interval; no integration."""
from pathlib import Path
import json
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent;ROOT=P.parents[1]/'VSM_decelaration'
COLORS={1:'#555555',2:'#0072b2',3:'#d55e00',7:'#009e73'}
plt.rcParams.update({'font.size':10,'pdf.fonttype':42})
frames={};network={}
for d1 in [10,20]:
 source=P/f'../h2p5_bus5_voltage098_d1/D1_{d1}p0_h1000'
 d=pd.concat([pd.read_csv(source/f'{stage}.csv').query('t_absolute_s <= 11.15000001') for stage in ['pre','fault','post']],ignore_index=True)
 for b in [1,2,3,7]:
  u=d[f'b{b}_U_r_pu']+1j*d[f'b{b}_U_i_pu'];ig=d[f'b{b}_Ig_r_pu']+1j*d[f'b{b}_Ig_i_pu']
  d[f'b{b}_V']=abs(u);d[f'b{b}_Ig']=abs(ig);d[f'b{b}_If']=np.hypot(d[f'b{b}_If_r_pu'],d[f'b{b}_If_i_pu'])
  d[f'b{b}_phase']=np.unwrap(np.angle(u))
  assert np.allclose(u*np.conj(ig),d[f'b{b}_Pterminal_pu']+1j*d[f'b{b}_Qterminal_pu'],rtol=0,atol=1e-9)
 frames[d1]=d
 v=pd.read_csv(P/f'../h2p5_bus5_basins/trajectory_D1_{d1}.csv').query('t_absolute_s <= 11.15000001').reset_index(drop=True)
 assert np.allclose(d.t_absolute_s,v.t_absolute_s,atol=1e-10,rtol=0) and (d.stage==v.stage).all()
 u5=v.V5_pu.to_numpy()*np.exp(1j*v.bus5_phase_unwrapped_rad.to_numpy())
 line=pd.read_csv(ROOT/'data/single_line/pre_equilibrium/branches.csv').set_index('line').loc[3]
 z=complex(line.R_pu,line.X_pu);i65=(1-u5)/z;s65=np.conj(i65);s56=u5*np.conj(-i65)
 g=2.2682301152333055;B=1.
 n=pd.DataFrame({'t_absolute_s':d.t_absolute_s,'t_post_s':d.t_post_s,'stage':d.stage,'V5':abs(u5),'I65':abs(i65),'Iload':g*abs(u5),'Icap':B*abs(u5),'P6to5':s65.real,'P5to6':s56.real,'Q6to5':s65.imag,'Q5to6':s56.imag,'Pload':g*abs(u5)**2,'Qcap':B*abs(u5)**2,'theta5':v.bus5_phase_unwrapped_rad,'line56_Ploss':(s65+s56).real})
 assert np.max(abs(n.line56_Ploss-abs(i65)**2*z.real))<1e-10
 network[d1]=n;n.to_csv(P/f'network_D1_{d1}.csv',index=False)
 # A compact reproducible export of exactly the GFM quantities drawn.
 cols=['t_absolute_s','t_post_s','stage']+[f'b{b}_{k}' for b in [1,2,3,7] for k in ['V','Ig','If','Pterminal_pu','Qterminal_pu','Pcap_pu','delta_rad','phase']]
 d[cols].to_csv(P/f'gfms_D1_{d1}.csv',index=False)

def save(fig,name):
 for ext in ['png','pdf']:fig.savefig(P/f'{name}.{ext}',dpi=190,bbox_inches='tight')
 plt.close(fig)
def events(axes,limits):
 for ax in axes.flat:
  ax.axvspan(1,1.15,color='#b2182b',alpha=.10)
  ax.axvline(1,color='#a51b28',ls=':',lw=.8);ax.axvline(1.15,color='#555',ls='--',lw=.8)
  ax.set_xlim(*limits);ax.grid(alpha=.22)
 for ax in axes[-1]:ax.set_xlabel('Time from prefault initialization [s]')

def gfm_fig(limits,name):
 fig,axes=plt.subplots(5,2,figsize=(12,12),sharex=True,sharey='row')
 for c,d1 in enumerate([10,20]):
  d=frames[d1];d=d[d.t_absolute_s.between(*limits)];t=d.t_absolute_s
  for b in [1,2,3,7]:
   for r,k in enumerate(['V','Ig','Pterminal_pu','Qterminal_pu','phase']):
    axes[r,c].plot(t,d[f'b{b}_{k}'],color=COLORS[b],lw=1,label=f'Bus {b}')
  axes[0,c].set_title(f'D1 = {d1}'+(' : negative running' if d1==10 else ' : synchronization recovery'))
  axes[0,c].legend(ncol=4,fontsize=8)
 for ax,label in zip(axes[:,0],['Terminal voltage\n|U| [pu]','Grid-side current\n|Ig| [pu]','Terminal active\npower P [pu]','Terminal reactive\npower Q [pu]','Terminal phase / Bus6\n[rad]']):ax.set_ylabel(label)
 events(axes,limits)
 fig.suptitle('Four-GFM responses: H=2.5 s, B5=1 pu\nFault applied at 1.00 s; cleared and line 4-5 opened at 1.15 s',fontsize=12)
 fig.tight_layout(rect=(0,0,1,.95));save(fig,name)
gfm_fig((0,11.15),'gfm_responses')
gfm_fig((.9,1.7),'gfm_fault_zoom')
fig,axes=plt.subplots(5,2,figsize=(12,12),sharex=True,sharey='row')
for c,d1 in enumerate([10,20]):
 d=network[d1];t=d.t_absolute_s
 for ax,cols in zip(axes[:,c],[['V5'],['I65','Iload','Icap'],['P6to5','Pload'],['Q6to5','Qcap'],['theta5']]):
  for k in cols:ax.plot(t,d[k],lw=1,label={'V5':'Bus5 voltage','I65':'Line 6-5 current','Iload':'Load current','Icap':'Shunt-capacitor current','P6to5':'Sending-end P: 6 to line 5-6','Pload':'Bus5 consumed P','Q6to5':'Sending-end Q: 6 to line 5-6','Qcap':'Bus5 capacitor Q injection','theta5':'Bus5 phase / Bus6'}[k])
  ax.legend(fontsize=8,loc='best')
 axes[0,c].axhline(1,color='gray',ls=':',lw=.8,label='Bus6 voltage = 1 pu')
 axes[4,c].axhline(0,color='gray',ls=':',lw=.8)
 axes[0,c].set_title(f'D1 = {d1}')
for ax,label in zip(axes[:,0],['Voltage magnitude\n[pu]','Current magnitude\n[pu]','Active power\n[pu]','Reactive power\n[pu]','Terminal phase / Bus6\n[rad]']):ax.set_ylabel(label)
events(axes,(0,11.15));fig.suptitle('Bus5 load / capacitor and slack interconnection 5-6\nP6to5 and Q6to5 are powers from Bus6 into the line, before line losses',fontsize=12);fig.tight_layout(rect=(0,0,1,.95));save(fig,'bus5_slack_responses')
# The power used in the swing equation is capacitor-side Pcap, distinct from terminal P.
fig,axes=plt.subplots(3,2,figsize=(12,8),sharex=True,sharey='row')
for c,d1 in enumerate([10,20]):
 d=frames[d1];t=d.t_absolute_s
 pc=sum(d[f'b{b}_Pcap_pu'] for b in [2,3,7]);pt=sum(d[f'b{b}_Pterminal_pu'] for b in [2,3,7])
 axes[0,c].plot(t,pc,label='Remote total Pcap');axes[0,c].plot(t,pt,ls='--',label='Remote total Pterminal');axes[0,c].axhline(1.2,c='black',ls=':',label='Total Pset=1.2');axes[0,c].legend(fontsize=8)
 internal=sum(d[f'b{b}_delta_rad'] for b in [2,3,7])/3
 terminal=sum(d[f'b{b}_phase'] for b in [2,3,7])/3
 axes[1,c].plot(t,internal,label='Remote mean internal angle');axes[1,c].plot(t,terminal,ls='--',label='Remote mean terminal phase');axes[1,c].legend(fontsize=8)
 for b in [1,2,3,7]:
  axes[2,c].plot(t,d[f'b{b}_If'],c=COLORS[b],label=f'Bus {b} filter-side |If|')
 axes[2,c].legend(fontsize=8,ncol=2);axes[0,c].set_title(f'D1 = {d1}')
for ax,label in zip(axes[:,0],['Remote active power\n[pu]','Phase / slack Bus6\n[rad]','Filter-side current\n|If| [pu]']):ax.set_ylabel(label)
events(axes,(0,11.15));fig.suptitle('Supplement: swing-equation power, internal angle and filter current',fontsize=12);fig.tight_layout(rect=(0,0,1,.95));save(fig,'internal_power_and_current')
metadata={'absolute_time_range_s':[0,11.15],'postfault_display_horizon_s':10,'fault_on_s':1.,'clearing_s':1.15,'phase_reference':'Fixed slack Bus6 voltage phase=0; voltage phases unwrapped without resetting the prefault phase','voltage_current_representation':'Magnitudes of the simulated complex voltage/current envelopes in pu; not instantaneous 60 Hz carrier waveforms','primary_power_definition':'P/Q at each bus terminal; supplementary plot includes Pcap used by the VSM swing equation','sampling_s':{'pre':.01,'fault':.0005,'post':.02},'source':'Existing D1=10/20, H=2.5 s, B5=1, grid_k=0.6812730259441179 baseline trajectories; no interventions and no new integration','sample_counts':{n:len(d) for n,d in frames.items()}}
(P/'definition.json').write_text(json.dumps(metadata,indent=2)+'\n')
print('Created four short-time figures in PNG/PDF, and plotted-data CSVs')

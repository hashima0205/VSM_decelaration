"""Fixed eight-bus single-line diagram, with voltages and signed terminal P/Q.

Geometry follows ref_file/4gfm_bus_system_ver2.png; numerical input comes from
export_single_line_data.jl. No simulation, interpolation or flow-direction guesses.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch

ROOT=Path(__file__).resolve().parents[1]
# The circuit is deliberately specific to the four-GFM/eight-bus study.
TOPOLOGY={1:(1,4),2:(4,6),3:(5,6),4:(3,5),5:(2,3),6:(2,5),7:(4,5),8:(2,8),9:(2,7),10:(7,8),11:(5,8)}
BARS={1:((5,11.7),(5,14.7)),4:((11,11.7),(11,14.7)),6:((17.5,15),(20.6,15)),7:((3.8,5.9),(3.8,9.6)),8:((8,9.5),(12.4,9.5)),2:((8,5.4),(12.4,5.4)),5:((16.6,9.5),(21,9.5)),3:((16.6,5.4),(21,5.4))}
# Paths start at from_bus and end at to_bus, including the dogleg conductors.
PATHS={1:[(5,13),(11,13)],2:[(11,13.9),(18,13.9),(18,15)],3:[(19.4,9.5),(19.4,15)],4:[(19.4,5.4),(19.4,9.5)],5:[(12,5.4),(12,4.2),(17.2,4.2),(17.2,5.4)],6:[(11.6,5.4),(11.6,6.7),(17.8,6.7),(17.8,9.5)],7:[(11,12.2),(17.8,12.2),(17.8,9.5)],8:[(10.4,5.4),(10.4,9.5)],9:[(8.8,5.4),(8.8,7),(3.8,7)],10:[(3.8,8.3),(8.5,8.3),(8.5,9.5)],11:[(17.2,9.5),(17.2,8.35),(11.6,8.35),(11.6,9.5)]}
LINE_LABELS={1:(8,13.9),2:(14.7,14.65),3:(21.4,12.8),4:(20.75,6.6),5:(14.6,3.35),6:(14.6,7.4),7:(14.6,11.35),8:(11.05,7.65),9:(6.25,6.15),10:(6.2,8.95),11:(14.5,9.15)}
BUS_LABELS={1:(5,15.65,'center'),4:(11,15.65,'center'),6:(21.2,15.05,'left'),7:(3.8,10.35,'center'),8:(10.3,10.35,'center'),2:(7.7,5.45,'right'),3:(21.2,5.45,'left'),5:(22.8,9.5,'left')}
P_COLOR='#155d9c';Q_COLOR='#16806a';INK='#111111'


def load_snapshot(folder:Path):
    """Return audited bus/line powers from actual complex voltages and impedances."""
    v=pd.read_csv(folder/'voltages.csv').set_index('bus')
    edges=pd.read_csv(folder/'branches.csv').sort_values('line').copy()
    meta=pd.read_csv(folder/'metadata.csv').iloc[0].to_dict()
    if set(v.index)!=set(range(1,9)) or len(v)!=8 or len(edges)!=11 or set(edges.line)!=set(TOPOLOGY):raise ValueError('Expected this study\'s eight buses and eleven branches')
    U={b:complex(v.loc[b,'U_r_pu'],v.loc[b,'U_i_pu']) for b in range(1,9)}
    if not all(np.isfinite([z.real,z.imag]).all() for z in U.values()):raise ValueError('Nonfinite bus voltages')
    if abs(U[6]-(1+0j))>1e-9:raise ValueError('This renderer expects the fixed Bus6 = 1 pu / 0 deg source')
    currents={b:0j for b in U};rows=[]
    for r in edges.itertuples(index=False):
        j=int(r.line);a=int(r.from_bus);b=int(r.to_bus)
        if j not in TOPOLOGY or TOPOLOGY[j]!=(a,b):raise ValueError(f'Unexpected topology for line {j}')
        if r.active not in [0,1] or r.R_pu<0 or r.X_pu<=0:raise ValueError(f'Invalid impedance/switch value for line {j}')
        z=complex(r.R_pu,r.X_pu);i=(U[a]-U[b])/z if r.active else 0j
        currents[a]+=i;currents[b]-=i
        sa=U[a]*np.conj(i);sb=U[b]*np.conj(-i)
        if abs(sa+sb-abs(i)**2*z)>1e-10:raise ValueError('Branch complex-power balance failed')
        rows.append(dict(line=j,from_bus=a,to_bus=b,active=bool(r.active),R_pu=r.R_pu,X_pu=r.X_pu,current_pu=abs(i),P_from_pu=sa.real,Q_from_pu=sa.imag,P_to_pu=sb.real,Q_to_pu=sb.imag,P_loss_pu=(sa+sb).real,Q_loss_pu=(sa+sb).imag))
    lines=pd.DataFrame(rows).set_index('line');busrows=[];errors=[]
    for b in range(1,9):
        net=U[b]*np.conj(currents[b]);ref=complex(v.loc[b,'reference_P_injection_pu'],v.loc[b,'reference_Q_injection_pu'])
        if b!=6:
            errors.append(abs(net-ref))
            if not np.isfinite(abs(ref)) or abs(net-ref)>1e-7:raise ValueError(f'KCL/model injection mismatch at Bus{b}: {net-ref}')
        busrows.append(dict(bus=b,V_pu=abs(U[b]),angle_deg=float(np.angle(U[b],deg=True)),P_injection_pu=net.real,Q_injection_pu=net.imag))
    buses=pd.DataFrame(busrows).set_index('bus')
    G=float(meta['load_G_pu']);B=float(meta['capacitor_B_pu']);faultG=float(meta['fault_G_pu'])
    if min(G,B,faultG)<0:raise ValueError('Expected consuming conductances and capacitive Bus5 shunt')
    load=G*abs(U[5])**2;cap=B*abs(U[5])**2;fault=faultG*abs(U[4])**2
    if abs(buses.loc[5,'P_injection_pu']+load)>1e-7 or abs(buses.loc[5,'Q_injection_pu']-cap)>1e-7:raise ValueError('Bus5 load/shunt mismatch')
    if abs(buses.loc[4,'P_injection_pu']+fault)>1e-7:raise ValueError('Fault-shunt mismatch')
    gfm=buses.loc[[1,2,3,7],'P_injection_pu'].sum();slack=buses.loc[6,'P_injection_pu'];loss=lines.P_loss_pu.sum()
    error=gfm+slack-load-fault-loss
    if abs(error)>1e-7:raise ValueError('System active-power balance failed')
    summary=dict(GFM_terminal_P_pu=float(gfm),slack_P_pu=float(slack),load_P_pu=float(load),capacitor_Q_pu=float(cap),fault_P_pu=float(fault),line_P_loss_pu=float(loss),line_Q_loss_pu=float(lines.Q_loss_pu.sum()),P_balance_error_pu=float(error),max_nodal_power_error_pu=float(max(errors)))
    return buses,lines,meta,summary


def polyline(ax,points,**kwargs):
    xy=np.array(points);ax.plot(xy[:,0],xy[:,1],solid_capstyle='butt',**kwargs)


def ground(ax,x,y):
    for k,w in enumerate([.32,.22,.11]):polyline(ax,[(x-w,y-.12*k),(x+w,y-.12*k)],color=INK,lw=1.1)


def source(ax,b,x,y,port):
    radius=.63
    if b in [1,7]:polyline(ax,[(x+radius,y),port],color=INK,lw=1.5)
    else:polyline(ax,[(x,y+radius),port],color=INK,lw=1.5)
    ax.add_patch(Circle((x,y),radius,facecolor='white',edgecolor=INK,lw=1.6,zorder=4))
    xx=np.linspace(-.35,.35,70);ax.plot(x+xx,y+.14*np.sin(xx/.35*np.pi),color=INK,lw=1.7,zorder=5)


def along(path,frac):
    xy=np.array(path,float);lengths=np.linalg.norm(np.diff(xy,axis=0),axis=1);d=frac*lengths.sum()
    j=min(np.searchsorted(np.cumsum(lengths),d),len(lengths)-1)
    t=(d-(lengths[:j].sum()))/lengths[j];direction=(xy[j+1]-xy[j])/lengths[j]
    return xy[j]+t*(xy[j+1]-xy[j]),direction


def terminal_arrow(ax,path,at,power,kind):
    if abs(power)<5e-5:return
    point,direction=along(path,at)
    # At the far end positive power points back toward the line, from its bus.
    if at>.5:direction=-direction
    if power<0:direction=-direction
    # Use the path orientation for offsets, independent of the power sign.
    _,tangent=along(path,at);normal=np.array([-tangent[1],tangent[0]])
    point=point+(.14 if kind=='P' else -.14)*normal
    color=P_COLOR if kind=='P' else Q_COLOR
    ax.add_patch(FancyArrowPatch(point-.29*direction,point+.29*direction,arrowstyle='-|>',mutation_scale=10,lw=1.15,color=color,zorder=6))


def open_line(ax,j):
    # The interruption is drawn electrically open, never as a connected dashed edge.
    path=PATHS[j]
    if j!=7:raise ValueError('Only the study contingency line 4-5 is expected to be open')
    polyline(ax,[path[0],(14.1,12.2)],color=INK,lw=1.3)
    polyline(ax,[(15.0,12.2),*path[1:]],color=INK,lw=1.3)
    for x in [14.1,15.0]:ax.add_patch(Circle((x,12.2),.055,color='white',ec=INK,lw=1,zorder=6))
    polyline(ax,[(14.1,12.2),(14.88,12.65)],color=INK,lw=1.3)


def draw_single_line(buses,lines,meta,summary,*,schematic=False,flow='both',digits=3,title=None):
    """Return a Matplotlib Figure; this function writes no files."""
    plt.rcParams.update({'font.family':'DejaVu Sans','pdf.fonttype':42,'svg.fonttype':'none'})
    fig,ax=plt.subplots(figsize=(16.5,11.5));fig.patch.set_facecolor('white')
    ax.set(xlim=(.1,26.4),ylim=(.2,17.1),aspect='equal');ax.axis('off')
    for j,r in lines.iterrows():
        if r.active:polyline(ax,PATHS[j],color=INK,lw=1.3,zorder=1)
        else:open_line(ax,j)
    for a,b in BARS.values():polyline(ax,[a,b],color=INK,lw=4,zorder=3)
    for b,x,y,port in [(1,2.7,13,(5,13)),(7,1.5,7.7,(3.8,7.7)),(2,9.7,2.5,(9.7,5.4)),(3,19.4,2.5,(19.4,5.4))]:
        source(ax,b,x,y,port)
        ax.text(x,y-.91,'GFM / VSM',ha='center',va='top',fontsize=10)
        if not schematic:
            r=buses.loc[b];ax.text(x,y-1.29,f'P {r.P_injection_pu:+.{digits}f}  Q {r.Q_injection_pu:+.{digits}f}',ha='center',va='top',fontsize=8.8)
    # The hatched infinite-bus termination follows the user's reference image.
    for x in np.linspace(17.8,20.2,5):polyline(ax,[(x,15),(x+.32,15.55)],color=INK,lw=2.1)
    ax.text(19.0,16.0,'Infinite grid / slack',ha='center',fontsize=10)
    if not schematic:
        r=buses.loc[6];ax.text(21.2,14.2,f'Grid injection\nP {r.P_injection_pu:+.{digits}f}\nQ {r.Q_injection_pu:+.{digits}f}',fontsize=9,ha='left',va='top')
    # Separate constant-impedance load and capacitive shunt at Bus5.
    polyline(ax,[(20.6,9.5),(20.6,10.8),(22.2,10.8)],color=INK,lw=1.3)
    ax.add_patch(FancyArrowPatch((22.1,10.8),(22.75,10.8),arrowstyle='-|>',mutation_scale=15,color=INK,lw=1.3))
    loadtext='Load' if schematic else f'Load\nP = {summary["load_P_pu"]:.{digits}f} pu'
    ax.text(23.0,10.8,loadtext,ha='left',va='center',fontsize=9.5)
    if float(meta['capacitor_B_pu'])>0:
        polyline(ax,[(20.9,9.5),(22.2,9.5),(22.2,8.1)],color=INK,lw=1.3)
        for y in [8.1,7.85]:polyline(ax,[(21.83,y),(22.57,y)],color=INK,lw=1.7)
        polyline(ax,[(22.2,7.85),(22.2,7.15)],color=INK,lw=1.3);ground(ax,22.2,7.15)
        captext='Shunt capacitor' if schematic else f'Shunt capacitor\nB = {float(meta["capacitor_B_pu"]):g} pu\nQ = +{summary["capacitor_Q_pu"]:.{digits}f} pu'
        ax.text(22.9,7.95,captext,ha='left',va='center',fontsize=9.2)
    if float(meta['fault_G_pu'])>0:
        polyline(ax,[(11,11.7),(11,10.9)],color=INK,lw=1.3)
        polyline(ax,[(11.14,10.95),(10.89,10.6),(11.13,10.65),(10.91,10.25)],color='#b2182b',lw=1.8)
        ground(ax,11,10.2);ax.text(11.5,10.75,f'Fault shunt\nP = {summary["fault_P_pu"]:.{digits}f}',fontsize=8.5,va='top')
    for b,(x,y,ha) in BUS_LABELS.items():
        r=buses.loc[b]
        label=f'Bus {b}'
        if not schematic:label+=f'\n{r.V_pu:.{digits}f} pu  /  {r.angle_deg:+.2f}°'
        ax.text(x,y,label,ha=ha,va='center',fontsize=10.2,linespacing=1.5,bbox=dict(facecolor='white',edgecolor='none',pad=1.5),zorder=7)
    if not schematic:
        for j,r in lines.iterrows():
            x,y=LINE_LABELS[j];a,b=TOPOLOGY[j]
            if not r.active:
                ax.text(x,y,f'L{j}  OPEN',ha='center',va='center',fontsize=9,color='#a31a1a',bbox=dict(facecolor='white',edgecolor='none',pad=1),zorder=8);continue
            ax.text(x,y+.34,f'L{j}  ({a} / {b})',fontsize=8.4,ha='center',va='center',bbox=dict(facecolor='white',edgecolor='none',pad=.6),zorder=8)
            for k,yy,color in [('P',y,P_COLOR),('Q',y-.32,Q_COLOR)]:
                if flow not in ['both',k.lower()]:continue
                va=float(r[f'{k}_from_pu']);vb=float(r[f'{k}_to_pu'])
                ax.text(x,yy,f'{k}  {va:+.{digits}f} / {vb:+.{digits}f}',fontsize=8.3,color=color,ha='center',va='center',bbox=dict(facecolor='white',edgecolor='none',pad=.6),zorder=8)
                for at,power in [(.16,va),(.84,vb)]:terminal_arrow(ax,PATHS[j],at,power,k)
    if title is None:title='Eight-bus four-GFM system' if schematic else str(meta['snapshot']).replace('_',' ')
    fig.suptitle(title,fontsize=15,y=.98)
    if not schematic:
        context='Equilibrium' if int(meta['is_equilibrium']) else f'Saved dynamic state, t = {float(meta["time_absolute_s"]):g} s'
        fig.text(.5,.945,f'{context}   |   H = {float(meta["H_s"]):g} s, D₁ = {float(meta["D1"]):g}, D₂ = {float(meta["D2"]):g}   |   Bus6 = 1 pu ∠0°',ha='center',fontsize=10)
        fig.text(.5,.065,'P: blue arrows     Q: green arrows     Line labels (a / b): signed power from each bus into the line [pu].',ha='center',fontsize=9)
        fig.text(.5,.044,'Two positive terminal Q values mean reactive absorption along the line. Device P/Q: positive injection into the network.',ha='center',fontsize=8.5)
        fig.text(.5,.023,f'GFM {summary["GFM_terminal_P_pu"]:.{digits}f} + grid {summary["slack_P_pu"]:+.{digits}f} = load {summary["load_P_pu"]:.{digits}f} + fault {summary["fault_P_pu"]:.{digits}f} + line losses {summary["line_P_loss_pu"]:.{digits}f} pu',ha='center',fontsize=9)
    fig.subplots_adjust(left=.015,right=.985,bottom=.095 if not schematic else .03,top=.91)
    return fig


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'data/single_line/pre_equilibrium',help='Exported voltages.csv / branches.csv / metadata.csv directory')
    parser.add_argument('--output',type=Path,default=ROOT/'figures/single_line/pre_equilibrium',help='Output path prefix (without extension)')
    parser.add_argument('--schematic-only',action='store_true',help='Draw only circuit symbols and labels')
    parser.add_argument('--flow',choices=['both','p','q','none'],default='both')
    parser.add_argument('--digits',type=int,choices=range(2,7),default=3)
    parser.add_argument('--title')
    args=parser.parse_args();b,l,m,total=load_snapshot(args.input)
    fig=draw_single_line(b,l,m,total,schematic=args.schematic_only,flow=args.flow,digits=args.digits,title=args.title)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    for ext in ['png','pdf','svg']:fig.savefig(str(args.output)+'.'+ext,dpi=220,facecolor='white')
    plt.close(fig)
    b.to_csv(str(args.output)+'_buses.csv');l.to_csv(str(args.output)+'_lines.csv')
    record={'snapshot':m,'balance':total,'input_directory':str(args.input.resolve()),'line_sign_convention':'P_from,Q_from: from_bus into line; P_to,Q_to: to_bus into line. Absorbed complex power = sum of both terminal powers.'}
    Path(str(args.output)+'_audit.json').write_text(json.dumps(record,indent=2)+'\n')
    print('Created',args.output,'[png / pdf / svg]; max nodal power error',total['max_nodal_power_error_pu'])
if __name__=='__main__':main()

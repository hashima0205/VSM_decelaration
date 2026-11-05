const ROOT=normpath(joinpath(@__DIR__,"../../VSM_decelaration"))
runner=joinpath(ROOT,"code/run.jl")
include_string(Main,first(split(read(runner,String),"\nmanifest=readlines")),runner)
using Serialization,Statistics,SHA
const OUT=@__DIR__
const INPUT=joinpath(OUT,"../h2p5_bus5_voltage098_d1/D1_10p0_h1000/full_states.bin")
const BASE=deserialize(INPUT)
const PP=BASE.parts[end].p
const INITIAL=BASE.parts[end].u[1]
const Z0=BASE.parts[end].z[1]
const INDEX=NWState(NW,Float64.(1:length(INITIAL)),copy(PP),0.)
const P_INDEX=NWState(NW,copy(INITIAL),Float64.(1:length(PP)),0.)
const R5=Int(INDEX[VIndex(5,:busbar₊u_r)]);const I5=Int(INDEX[VIndex(5,:busbar₊u_i)])
const BUS=Dict(b=>(Int(INDEX[VIndex(b,:busbar₊u_r)]),Int(INDEX[VIndex(b,:busbar₊u_i)])) for b in [1,2,3,4,5,7,8])
const ENDS=[(1,4),(4,6),(5,6),(3,5),(2,3),(2,5),(4,5),(2,8),(2,7),(7,8),(5,8)]
eidx(j,k)=Int(P_INDEX.p[EIndex(Symbol("line",j),Symbol("line_sym₊",k))])
const RP=[eidx(j,"R") for j in 1:11];const XP=[eidx(j,"X") for j in 1:11];const ON=[eidx(j,"active") for j in 1:11]
const DI010=AI;const PI010=PFI;const KP010=PP[KP];const PS010=PP[PS]
include(joinpath(ROOT,"code/adaptive_probe_metrics.jl"))
const CASES=[("baseline",1.,1.,false,false),("r56_075",.75,1.,false,false),("r56_050",.5,1.,false,false),("r56_025",.25,1.,false,false),("r56_zero",0.,1.,false,false),("keep_line45",1.,1.,true,false),("all_R_zero",1.,1.,false,true),("x56_050",1.,.5,false,false)]
function export_series(dir,parts,p)
 open(joinpath(dir,"budget.csv"),"w") do io
  println(io,"t_post_s,theta_remote_slack_rad,theta5_slack_raw_rad,remote_df_Hz,V5_pu,Pcap_remote,Pterm_remote,Pslack,Pload,Ploss,Ploss56,Ploss_internal,P5to6,P6to5,P5to4,power_gap,droop_feedback,D1_feedback,D2_feedback,swing_rhs,balance_error")
  maxerror=0.
  for part in parts,(t,x,z) in zip(part.t,part.u,part.z)
   U=Dict(b=>complex(x[ids[1]],x[ids[2]]) for (b,ids) in BUS);U[6]=1+0im
   pc=[x[VR[j]]*x[IR[j]]+x[VI[j]]*x[II[j]] for j in 1:4]
   pt=[real(U[b]*conj(complex(x[IR[j]],x[II[j]]))) for (j,b) in enumerate(ALLG)]
   loss=zeros(11);slack=0.;p56=0.;p65=0.;p54=0.
   for (j,(a,b)) in enumerate(ENDS)
    zz=complex(p[RP[j]],p[XP[j]]);cur=p[ON[j]]>0 ? (U[a]-U[b])/zz : 0im
    sa=real(U[a]*conj(cur));sb=real(U[b]*conj(-cur));loss[j]=abs2(cur)*real(zz)
    if a==6;slack+=sa;end;if b==6;slack+=sb;end
    if j==3;p56=sa;p65=sb;end;if j==7;p54=sb;end
   end
   load=2.2682301152333055*abs2(U[5]);error=sum(pt)+slack-load-sum(loss);@assert abs(error)<1e-8;maxerror=max(maxerror,abs(error))
   nu=to_vsm(x,p)[PFI];gap=1.2-sum(pc[2:4]);dr=-10sum(nu[2:4]);d1=-10sum(nu[2:4]);d2=-100sum(nu[2:4]-z[2:4])
   println(io,join([t-1.15,mean(x[AI[2:4]]),atan(imag(U[5]),real(U[5])),60mean(nu[2:4]),abs(U[5]),sum(pc[2:4]),sum(pt[2:4]),slack,load,sum(loss),loss[3],sum(loss[[4,5,6,8,9,10,11]]),p56,p65,p54,gap,dr,d1,d2,gap+dr+d1+d2,error],','))
  end
  return maxerror
 end
end
function main()
 worker=parse(Int,ARGS[1]);@assert worker in 1:3
 signature=bytes2hex(sha256(vcat(read(@__FILE__),read(joinpath(ROOT,"code/vsm.jl")),codeunits(bytes2hex(sha256(read(INPUT)))))))
 @assert BASE.pre_V5>=.98 && BASE.H==2.5 && BASE.M==5 && BASE.c.d1==10.
 for ci in worker:3:length(CASES)
  tag,rf,xf,keep,allzero=CASES[ci];dir=joinpath(OUT,tag);mkpath(dir);p=copy(PP)
  p[RP[3]]*=rf;p[XP[3]]*=xf
  if keep;p[ON[7]]=1.;end
  if allzero;p[RP].=0.;end
  changed=findall(p.!=PP);allowed=keep ? [ON[7]] : allzero ? RP : xf!=1. ? [XP[3]] : rf!=1. ? [RP[3]] : Int[]
  @assert all(j in allowed for j in changed)
  savevec(joinpath(dir,"parameters.csv"),p);savevec(joinpath(dir,"changed_parameter_indices.csv"),changed)
  done=joinpath(dir,"outcome.bin")
  if isfile(done);@assert deserialize(done).signature==signature;println("REUSED ",tag);continue;end
  y=copy(INITIAL);before=copy(y[DYN]);er=algfix!(y,p);@assert er<1e-8 && y[DYN]==before
  savevec(joinpath(dir,"initial70.csv"),vcat(y,Z0))
  target=copy(keep ? BASE.pre : BASE.target);rootok=false;rooterr=Inf;ev=NaN;nunstable=-1
  try
   target,rooterr=stationary(NW,target,p)
   if rooterr<1e-8
    rooterr,ev,nunstable=damped_eqcheck(target,p;damping=BASE.c);rootok=rooterr<1e-8
   end
  catch err
   println("ROOT_CORRECTION_FAILED ",tag," ",typeof(err));flush(stdout)
  end
  if !rootok;target=fill(NaN,length(INITIAL));end
  parts=[];last=1.15;z=copy(Z0);tick=time()
  for horizon in [300.,1000.]
   file=joinpath(dir,"h$(Int(horizon)).bin")
   if isfile(file)
    a=deserialize(file);@assert a.signature==signature;part=a.part
   else
    println("START ",tag," horizon=",horizon);flush(stdout)
    sol=solve_vsm(y,p,(last,1.15+horizon),Rodas5P();damping=BASE.c,washout_state=z,reltol=1e-9,abstol=1e-11,dtmax=.005,maxiters=10^8,saveat=.02,save_everystep=false,dense=false)
    @assert string(sol.retcode)=="Success"
    part=(t=sol.t,u=sol.u,z=sol.washout);serialize(file,(signature=signature,part=part))
   end
   @assert maximum(abs.(part.z[1]-z))<1e-10
   push!(parts,part);y=copy(part.u[end]);z=copy(part.z[end]);last=1.15+horizon
   println("SEGMENT_DONE ",tag," ",horizon);flush(stdout)
  end
  times=vcat(parts[1].t,parts[2].t[2:end]).-1.15;states=vcat(parts[1].u,parts[2].u[2:end])
  label,turns,ms=classify_probe(times,states,target)
  f=similar(y);NW(f,y,p,last);dynamicres=maximum(abs.(f[DYN]))
  # If continuation failed, attempt a root correction from a settled endpoint.
  if !rootok && maximum(abs.(to_vsm(y,p)[PFI].*60))<1e-4
   trial,ee=stationary(NW,copy(y),p)
   if ee<1e-8
    target=trial;rooterr,ev,nunstable=damped_eqcheck(target,p;damping=BASE.c);rootok=rooterr<1e-8
    label,turns,ms=classify_probe(times,states,target)
   end
  end
  if rootok;savevec(joinpath(dir,"root.csv"),target);end
  maxres=export_series(dir,parts,p)
  serialize(done,(signature=signature,tag=tag,label=label,turns=turns,machines=ms,rootok=rootok,rooterr=rooterr,root_eigen=ev,root_unstable=nunstable,full_residual=dynamicres,changed=changed,rf=rf,xf=xf,keep45=keep,allRzero=allzero,max_balance_error=maxres))
  appendrow(joinpath(OUT,"summary_w$(worker).csv"),"case,classification,turns,root_found,root_residual,root_max_real,root_unstable,endpoint_dynamic_residual,solve_s",[tag,label,turns,rootok,rooterr,ev,nunstable,dynamicres,time()-tick])
  println("DONE ",tag," ",label," turns=",turns," root=",rootok," ev=",ev);flush(stdout)
 end
end
main()

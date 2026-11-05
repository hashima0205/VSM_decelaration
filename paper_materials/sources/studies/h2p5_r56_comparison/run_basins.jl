# A new VSM conditional basin; never reuse the upstream Droop labels.
const ROOT=normpath(joinpath(@__DIR__,"../../VSM_decelaration"))
runner=joinpath(ROOT,"code/run.jl")
include_string(Main,first(split(read(runner,String),"\nmanifest=readlines")),runner)
using Serialization,Statistics,SHA
const OUT=@__DIR__
const SOURCE=joinpath(OUT,"../h2p5_bus5_voltage098_d1")
const PRE_ROOT=vec(readdlm(joinpath(SOURCE,"D1_10p0_h1000/pre_root.csv"),',',Float64))
const TARGET=vec(readdlm(joinpath(SOURCE,"D1_10p0_h1000/post_root.csv"),',',Float64))
const PP=[vec(readdlm(joinpath(SOURCE,"D1_10p0_h1000/"*s*"_parameters.csv"),',',Float64)) for s in ["pre","fault","post"]]
const PB=vec(readdlm(joinpath(OUT,"../h2p5_hypothesis_interventions/r56_075/parameters.csv"),',',Float64))
const RECOVERY_TARGET=vec(readdlm(joinpath(OUT,"../h2p5_hypothesis_interventions/r56_075/root.csv"),',',Float64))
const INDEX=NWState(NW,Float64.(1:length(TARGET)),copy(PB),0.)
const R5=Int(INDEX[VIndex(5,:busbar₊u_r)]);const I5=Int(INDEX[VIndex(5,:busbar₊u_i)])
const ORIGIN=mean(TARGET[AI[2:4]])-atan(TARGET[I5],TARGET[R5])
const DI010=AI;const PI010=PFI;const KP010=PB[KP];const PS010=PB[PS]
include(joinpath(ROOT,"code/adaptive_probe_metrics.jl"))
const THETAS=[-.1,.1,ORIGIN,.25,.4,.6,.8]
const FREQS=[-1.2,-.6,-.15,0.,.05]
const POINTS=vcat([(a,f,"global") for f in FREQS for a in THETAS],[(a,f,"local") for f in [-.01,.01] for a in [.1,ORIGIN,.25,.4]])
const HORIZONS=[30.,100.,300.]
function main()
 worker=parse(Int,ARGS[1]);@assert worker in 1:3
 @assert hypot(PRE_ROOT[R5],PRE_ROOT[I5])>=.98
 signature=bytes2hex(sha256(vcat(read(@__FILE__),read(joinpath(ROOT,"code/vsm.jl")),reinterpret(UInt8,PB),reinterpret(UInt8,TARGET))))
 if worker==1
  savevec(joinpath(OUT,"stable.csv"),RECOVERY_TARGET);savevec(joinpath(OUT,"pre.csv"),PRE_ROOT);savevec(joinpath(OUT,"post_parameters.csv"),PB)
  write(joinpath(OUT,"configuration.sha256"),signature*"\n")
  open(joinpath(OUT,"grid.csv"),"w") do io
   println(io,"point,theta_bus5_requested_rad,df_requested_Hz,grid")
   for (i,(a,f,g)) in enumerate(POINTS);println(io,join([i,a,f,g],','));end
  end
 end
 for d1 in [10.]
  c=(d1=d1,d2=100.,omega_d=50.)
  for (name,x,p) in [("pre",PRE_ROOT,PP[1]),("post",RECOVERY_TARGET,PB)]
   er,ev,n=damped_eqcheck(x,p;damping=c);@assert er<1e-8&&ev<0
   appendrow(joinpath(OUT,"roots_w$(worker).csv"),"D1,stage,residual,max_real_eigen,unstable_modes",[d1,name,er,ev,n])
  end
  for i in worker:3:length(POINTS)
   theta,df,grid=POINTS[i];tag="D1_$(Int(d1))_p$(lpad(i,3,'0'))";dir=joinpath(OUT,tag);mkpath(dir)
   done=joinpath(dir,"outcome.bin")
   if isfile(done);@assert deserialize(done).signature==signature;println("REUSED ",tag);flush(stdout);continue;end
   x=copy(TARGET);x[AI[2:4]].+=theta-ORIGIN
   x[PFI[2:4]].-=df*2pi ./PB[KP[2:4]]
   initial_d=copy(x[DYN]);alg=algfix!(x,PB)
   @assert alg<1e-8 && x[DYN]==initial_d
   actual=mean(x[AI[2:4]])-atan(x[I5],x[R5])
   @assert isfinite(actual) # Actual Bus5 reference is recomputed after the R change.
   z=zeros(4) # Other 50 augmented differential states start at the stable root.
   savevec(joinpath(dir,"initial.csv"),vcat(x,z))
   t=[0.];u=[copy(x)];last=0.;label="unresolved";turns=0.;ms=[];maxres=0.;wall=0.;ff=similar(x)
   for stop in HORIZONS
    file=joinpath(dir,"h$(Int(stop)).bin")
    if isfile(file)
     saved=deserialize(file);@assert saved.signature==signature;sol=saved.sol;elapsed=saved.elapsed
    else
     tick=time();sol=solve_vsm(u[end],PB,(last,stop),Rodas5P();damping=c,washout_state=z,reltol=1e-9,abstol=1e-11,dtmax=.005,maxiters=10^8,saveat=.05,save_everystep=false,dense=false);elapsed=time()-tick
     @assert string(sol.retcode)=="Success" "Numerical failure $tag"
     serialize(file,(signature=signature,sol=sol,elapsed=elapsed))
    end
    @assert sol.t[1]==last && sol.t[end]==stop
    if last>0;@assert maximum(abs.(z-sol.washout[1]))<1e-10;end
    append!(t,sol.t[2:end]);append!(u,sol.u[2:end]);z=copy(sol.washout[end]);last=stop;wall+=elapsed
    label,turns,ms=classify_probe(t,u,RECOVERY_TARGET)
    appendrow(joinpath(OUT,"history_w$(worker).csv"),"case,horizon_s,classification,solve_s",[tag,stop,label,elapsed])
    label in ["unresolved","other"] || break
   end
   for (tt,xx) in zip(t,u);NW(ff,xx,PB,tt);maxres=max(maxres,maximum(abs.(ff[ALG])));end
   @assert maxres<1e-7
   endpoint=vcat(u[end],z);savevec(joinpath(dir,"endpoint.csv"),endpoint)
   serialize(done,(signature=signature,case=tag,point=i,D1=d1,theta=actual,df=df,grid=grid,classification=label,horizon=last,turns=turns,machines=ms,maxres=maxres,initial_alg=alg,solve_s=wall))
   appendrow(joinpath(OUT,"samples_w$(worker).csv"),"case,point,D1,theta_bus5_rad,df_Hz,grid,classification,horizon_s,remote_turns,max_algebraic_residual,solve_s",[tag,i,d1,actual,df,grid,label,last,turns,maxres,wall])
   println("BASIN ",tag," ",i,"/",length(POINTS)," ",label," horizon=",last," solve_s=",round(wall;digits=2));flush(stdout)
  end
 end
 println("DONE worker ",worker);flush(stdout)
end
main()

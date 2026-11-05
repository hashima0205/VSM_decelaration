const ROOT=normpath(joinpath(@__DIR__,"../../VSM_decelaration"))
runner=joinpath(ROOT,"code/run.jl");include_string(Main,first(split(read(runner,String),"\nmanifest=readlines")),runner)
using Serialization,Statistics,SHA
const OUT=@__DIR__
const INPUT=joinpath(OUT,"../h2p5_bus5_voltage098_d1/D1_10p0_h1000/full_states.bin")
const BASE=deserialize(INPUT);const PP=BASE.parts[end].p
const A=deserialize(joinpath(OUT,"../h2p5_hypothesis_interventions/baseline/h300.bin")).part
const B=deserialize(joinpath(OUT,"../h2p5_hypothesis_interventions/r56_075/h300.bin")).part
const J=argmin(abs.(A.t.-2.99));@assert abs(A.t[J]-B.t[J])<1e-10
const TC=A.t[J];const X0=copy(A.u[J]);const Z0=copy(A.z[J]);const XR=copy(B.u[J]);const ZR=copy(B.z[J])
const VCPI=[si(b,k) for b in [2,3,7] for k in ["vsrc₊vc₊γ_d","vsrc₊vc₊γ_q"]]
const CCPI=[si(b,k) for b in [2,3,7] for k in ["vsrc₊cc1₊γ_d","vsrc₊cc1₊γ_q"]]
const QFI=[si(b,"droop₊Qfilt") for b in [2,3,7]]
const PAIRS=[(si(b,"vsrc₊filter₊"*name*"_r"),si(b,"vsrc₊filter₊"*name*"_i")) for b in [2,3,7] for name in ["V_C","i_g","i_f"]]
const DI010=AI;const PI010=PFI;const KP010=PP[KP];const PS010=PP[PS]
include(joinpath(ROOT,"code/adaptive_probe_metrics.jl"))
const TAGS=["control","voltage_PI","current_PI","Q_filter","washout","electrical_local","angle_speed","all_hidden_controls","full_recovered"]
function transplanted(tag)
 x=copy(X0);z=copy(Z0)
 if tag in ["voltage_PI","all_hidden_controls"];x[VCPI]=XR[VCPI];end
 if tag in ["current_PI","all_hidden_controls"];x[CCPI]=XR[CCPI];end
 if tag in ["Q_filter","all_hidden_controls"];x[QFI]=XR[QFI];end
 if tag in ["washout","all_hidden_controls"];z[2:4]=ZR[2:4];end
 if tag=="electrical_local"
  for (k,(ir,ii)) in enumerate(PAIRS)
   j=div(k-1,3)+2;v=complex(XR[ir],XR[ii])*cis(X0[AI[j]]-XR[AI[j]]);x[ir]=real(v);x[ii]=imag(v)
  end
 end
 if tag=="angle_speed"
  x[AI[2:4]]=XR[AI[2:4]];x[PFI[2:4]]=XR[PFI[2:4]]
  for (k,(ir,ii)) in enumerate(PAIRS)
   j=div(k-1,3)+2;v=complex(X0[ir],X0[ii])*cis(XR[AI[j]]-X0[AI[j]]);x[ir]=real(v);x[ii]=imag(v)
  end
 end
 if tag=="full_recovered";x=copy(XR);z=copy(ZR);end
 x,z
end
function rootscan()
 roots=[copy(BASE.target)]
 for shift in [-.02,-.04,-.08,.02]
  x=copy(BASE.target);x[AI[2:4]].+=shift
  for (ir,ii) in PAIRS;v=complex(x[ir],x[ii])*cis(shift);x[ir]=real(v);x[ii]=imag(v);end
  try
   y,er=stationary(NW,x,PP)
   if er<1e-8 && all(norm(y-r)>1e-4 for r in roots)
    er,ev,n=damped_eqcheck(y,PP;damping=BASE.c);push!(roots,y);savevec(joinpath(OUT,"root_$(length(roots)).csv"),y)
    appendrow(joinpath(OUT,"root_scan.csv"),"root,seed_shift,residual,max_real,unstable_modes,remote_mean_delta",[length(roots),shift,er,ev,n,mean(y[AI[2:4]])])
   end
  catch err;println("ROOT_SCAN ",shift," ",typeof(err));end
 end
 savevec(joinpath(OUT,"stable.csv"),BASE.target)
end
function main()
 w=parse(Int,ARGS[1]);@assert w in 1:3
 signature=bytes2hex(sha256(vcat(read(@__FILE__),read(joinpath(ROOT,"code/vsm.jl")))))
 if w==1;rootscan();end
 for i in w:3:length(TAGS)
  tag=TAGS[i];dir=joinpath(OUT,tag);mkpath(dir);done=joinpath(dir,"outcome.bin")
  if isfile(done);@assert deserialize(done).signature==signature;continue;end
  x,z=transplanted(tag);changed=findall(vcat(x,z).!=vcat(X0,Z0));before=copy(x[DYN]);alg=algfix!(x,PP);@assert alg<1e-8 && x[DYN]==before
  savevec(joinpath(dir,"initial70.csv"),vcat(x,z));savevec(joinpath(dir,"changed_before_algfix.csv"),changed)
  println("START ",tag);flush(stdout)
  tick=time();sol=solve_vsm(x,PP,(TC,TC+1000),Rodas5P();damping=BASE.c,washout_state=z,reltol=1e-9,abstol=1e-11,dtmax=.005,maxiters=10^8,saveat=.02,save_everystep=false,dense=false)
  @assert string(sol.retcode)=="Success"
  label,turns,ms=classify_probe(sol.t.-TC,sol.u,BASE.target)
  serialize(joinpath(dir,"trajectory.bin"),(t=sol.t,u=sol.u,z=sol.washout))
  open(joinpath(dir,"early.csv"),"w") do io
   println(io,join(vcat(["t_absolute_s","t_since_transplant_s"],["b$(b)_$(k)" for b in ALLG for k in KEYNAMES],["z$j" for j in 1:4]),','))
   for (t,x,z) in zip(sol.t,sol.u,sol.washout)
    t>TC+10&&break
    println(io,join(vcat([t,t-TC],obs(x,PP,t)[1:end-1],z),','))
   end
  end
  maxres=0.;f=similar(x)
  for k in 1:100:length(sol.t);NW(f,sol.u[k],PP,sol.t[k]);maxres=max(maxres,maximum(abs.(f[ALG])));end
  @assert maxres<1e-7
  serialize(done,(signature=signature,tag=tag,label=label,turns=turns,machines=ms,changed=changed,alg=alg,maxres=maxres))
  appendrow(joinpath(OUT,"summary_w$(w).csv"),"case,classification,turns,max_alg_residual,solve_s",[tag,label,turns,maxres,time()-tick])
  println("DONE ",tag," ",label," turns=",turns);flush(stdout)
 end
end
main()

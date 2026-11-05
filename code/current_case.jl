# Current capacitor-compensated VSM cases. The legacy model bootstrap is retained.
using Serialization,Statistics
const CURRENT_HEADER="case,H,mp,D1,D2,omega_d,Bcap,grid_k,load_G,P1,P2,P3,P7,tauq,fault_on,T,fault_G,horizon,level"
const CURRENT_REF=joinpath(DATA,"current_reference")
const CURRENT_OUT=joinpath(PACK,"runs","current")
function current_parameters(a)
 r=Dict(k=>parse(Float64,v) for (k,v) in eachrow(readdlm(joinpath(CURRENT_REF,"settings.csv"),',',String;skipstart=1)))
 ps=[vec(readdlm(joinpath(CURRENT_REF,s*"_parameters.csv"),',',Float64)) for s in ["pre","fault","post"]]
 seed=vec(readdlm(joinpath(CURRENT_REF,"pre_root.csv"),',',Float64))
 db=1/a["mp"];tau=2a["H"]/db
 for (i,p) in enumerate(ps)
  p[KP].=p[WB]./db;p[TP].=tau
  st=NWState(NW,copy(seed),p,0.)
  for (j,b) in enumerate(ALLG)
   st.p[VIndex(b,Symbol("inv$(b)₊droop₊Pset"))]=a["P$(b)"]
   st.p[VIndex(b,Symbol("inv$(b)₊droop₊τ_q"))]=a["tauq"]
  end
  st.p[VIndex(5,:PQLoad₊P_load_p)]*=a["load_G"]/r["load_G"]
  st.p[VIndex(5,:PQLoad₊Q_load_p)]*=a["Bcap"]/r["Bcap"]
  for line in [2,3],name in ["R","X"]
   st.p[EIndex(Symbol("line",line),Symbol("line_sym₊",name))]*=a["grid_k"]/r["grid_k"]
  end
  st.p[VIndex(4,:fault_load₊G_fault_p)]*=a["fault_G"]/r["fault_G"]
  st.p[VIndex(4,:fault_load₊t_fault_p)]=a["fault_on"]
  st.p[VIndex(4,:fault_load₊t_clear_p)]=a["fault_on"]+a["T"]
 end
 @assert maximum(abs.(ps[1][TP].*ps[1][WB]./ps[1][KP].-2a["H"]))<1e-10
 ps,db,tau
end
function current_classify(t,u,p,target)
 finish=t[end];tail=findall(t.>=finish-min(50.,finish/3));machines=[]
 at(a,q)=begin j=clamp(searchsortedlast(t,q),1,length(t)-1);a[j]+(a[j+1]-a[j])*(q-t[j])/(t[j+1]-t[j]) end
 for (j,b) in enumerate(ALLG)
  angle=[x[AI[j]] for x in u];df=[p[KP[j]]*(p[PS[j]]-x[PFI[j]])/(2pi) for x in u]
  shift=angle.-angle[1];turns=shift[end]/(2pi);err=abs(atan(sin(angle[end]-target[AI[j]]),cos(angle[end]-target[AI[j]])))
  width=maximum(angle[tail])-minimum(angle[tail]);fmax=maximum(abs.(df[tail]));windows=diff([at(angle,q) for q in range(.4finish,finish;length=4)])/(2pi)
  label=if fmax<1e-4 && err<.002 && width<.005
   maximum(abs.(shift))>=2pi ? "recovery_after_slip" : "recovery"
  elseif turns< -2 && maximum(windows)< -.2 && sum(windows)/(.6finish)< -1e-4
   "negative_running"
  elseif turns>2 && minimum(windows)>.2 && sum(windows)/(.6finish)>1e-4
   "positive_running"
  else;"unresolved";end
  push!(machines,(b,label,turns,fmax,err,width,minimum(windows),maximum(windows)))
 end
 labs=[m[2] for m in machines]
 label=all(l in ["recovery","recovery_after_slip"] for l in labs) ? ("recovery_after_slip" in labs ? "recovery_after_slip" : "recovery") : "negative_running" in labs ? "negative_running" : "positive_running" in labs ? "positive_running" : "unresolved"
 label,sum(u[end][AI[2:4]]-u[1][AI[2:4]])/(6pi),machines
end
function current_case(row)
 cols=split(CURRENT_HEADER,',');cells=split(row,',');@assert length(cells)==length(cols)
 tag=String(cells[1]);level=String(cells[end]);@assert occursin(r"^[A-Za-z0-9_.-]+$",tag)&&!occursin("..",tag)
 a=Dict(cols[i]=>parse(Float64,cells[i]) for i in 2:length(cols)-1)
 @assert all(isfinite,values(a))
 @assert all(a[k]>0 for k in ["H","mp","omega_d","grid_k","load_G","tauq","fault_on","T","horizon"])
 @assert all(a[k]>=0 for k in ["D1","D2","Bcap","fault_G"])
 @assert a["Bcap"]>0 "Current cases require capacitive compensation."
 @assert level in ["A","B"]
 ps,db,tau=current_parameters(a);c=(d1=a["D1"],d2=a["D2"],omega_d=a["omega_d"]);check_damping(c)
 paths=vcat([joinpath(@__DIR__,f) for f in ["run.jl","current_case.jl","vsm.jl","engine12.jl","model.jl"]],sort(readdir(CURRENT_REF;join=true)))
 signature=bytes2hex(sha256(row*join(bytes2hex(sha256(read(f))) for f in paths)))
 dir=joinpath(CURRENT_OUT,tag);mkpath(dir);sigfile=joinpath(dir,"configuration.sha256")
 if isfile(sigfile);@assert strip(read(sigfile,String))==signature "Changed inputs/code: choose a new case name or preserve the old output first."
 else;@assert isempty(readdir(dir));write(sigfile,signature*"\n");end
 pre=vec(readdlm(joinpath(CURRENT_REF,"pre_root.csv"),',',Float64));target=vec(readdlm(joinpath(CURRENT_REF,"post_root.csv"),',',Float64))
 pre,ep=stationary(NW,pre,ps[1]);target,eq=stationary(NW,target,ps[3]);@assert max(ep,eq)<1e-8
 precheck=damped_eqcheck(pre,ps[1];damping=c);postcheck=damped_eqcheck(target,ps[3];damping=c)
 @assert precheck[1]<1e-8 && postcheck[1]<1e-8 && precheck[2]<0 && postcheck[2]<0
 ix=NWState(NW,Float64.(1:length(pre)),copy(ps[1]),0.)
 ir=Int(ix[VIndex(5,:busbar₊u_r)]);ii=Int(ix[VIndex(5,:busbar₊u_i)])
 vpre=hypot(pre[ir],pre[ii]);@assert vpre>=.98 "The current study requires prefault Bus5 voltage >=0.98 pu."
 savevec(joinpath(dir,"pre_root.csv"),pre);savevec(joinpath(dir,"post_root.csv"),target)
 open(joinpath(dir,"settings.csv"),"w") do io
  println(io,"name,value");for k in sort(collect(keys(a)));println(io,k,',',a[k]);end
  println(io,"Ddroop,",db);println(io,"M,",2a["H"]);println(io,"tau_p_equivalent,",tau);println(io,"pre_V5,",vpre)
 end
 rt,at,dt=level=="A" ? (1e-9,1e-11,.005) : (1e-10,1e-12,.0025)
 clear=a["fault_on"]+a["T"];schedule=[("pre",ps[1],0.,a["fault_on"],.01),("fault",ps[2],a["fault_on"],clear,.0005),("post",ps[3],clear,clear+a["horizon"],.02)]
 x=copy(pre);z=to_vsm(x,ps[1])[PFI];parts=[];maxz=0.;maxalg=0.;minpre=Inf;tick=time()
 for (stage,p,start,stop,step) in schedule
  held=copy(x[DYN]);@assert algfix!(x,p)<1e-8 && x[DYN]==held
  savevec(joinpath(dir,stage*"_parameters.csv"),p)
  checkpoint=joinpath(dir,stage*".bin")
  if isfile(checkpoint)
   cache=deserialize(checkpoint);@assert cache.signature==signature;part=cache.part
  else
   println("CURRENT_START ",tag," ",stage," ",start," -> ",stop);flush(stdout)
   samples=sort(unique(vcat(collect(start:step:stop),[start,stop])))
   sol=solve_vsm(x,p,(start,stop),Rodas5P();damping=c,washout_state=z,reltol=rt,abstol=at,dtmax=dt,maxiters=10^8,saveat=samples,save_everystep=false,dense=false)
   @assert string(sol.retcode)=="Success"
   part=(stage=stage,p=copy(p),t=sol.t,u=sol.u,z=sol.washout)
   serialize(checkpoint,(signature=signature,part=part))
  end
  jump=maximum(abs.(part.z[1]-z));maxz=max(maxz,jump);@assert jump<1e-12
  push!(parts,part);x=copy(part.u[end]);z=copy(part.z[end])
 end
 open(joinpath(dir,"observations.csv"),"w") do io
  println(io,join(vcat(["t_absolute_s","t_post_s","stage"],["b$(b)_$(k)" for b in ALLG for k in KEYNAMES],"alg_residual"),','))
  for part in parts,(t,x) in zip(part.t,part.u)
   v=obs(x,part.p,t);maxalg=max(maxalg,v[end]);part.stage=="pre"&&(minpre=min(minpre,hypot(x[ir],x[ii])))
   println(io,join(vcat(Any[t,t-clear,part.stage],v),','))
  end
 end
 @assert maxalg<1e-8 && minpre>=.98
 post=parts[end];label,turns,machines=current_classify(post.t.-clear,post.u,ps[3],target)
 open(joinpath(dir,"machines.csv"),"w") do io
  println(io,"bus,classification,turns,tail_max_abs_df_Hz,phase_error_rad,phase_width_rad,min_window_turns,max_window_turns")
  for m in machines;println(io,join(m,','));end
 end
 serialize(joinpath(dir,"full_states.bin"),(parts=parts,pre=pre,target=target,db=db,c=c,H=a["H"],M=2a["H"],Bcap=a["Bcap"],grid_k=a["grid_k"],pre_V5=vpre,dtmax=dt))
 open(joinpath(dir,"result.csv"),"w") do io
  println(io,"case,H,mp,Ddroop,D1,D2,omega_d,Bcap,pre_V5,horizon,classification,remote_turns,pre_max_real,post_max_real,max_algebraic_residual,max_event_z_error")
  println(io,join([tag,a["H"],a["mp"],db,c.d1,c.d2,c.omega_d,a["Bcap"],vpre,a["horizon"],label,turns,precheck[2],postcheck[2],maxalg,maxz],','))
 end
 println("CURRENT_DONE ",tag," ",label," turns=",turns," wall_s=",time()-tick);flush(stdout)
end
function current_manifest(lines)
 @assert lines[1]==CURRENT_HEADER "Unrecognized case CSV header. See data/representative.csv or data/legacy/."
 for row in lines[2:end];isempty(strip(row))||current_case(row);end
end

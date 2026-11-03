include("model.jl")
include("vsm.jl")
using Pkg
open(joinpath(PACK,"provenance/runtime.txt"),"w") do io
    println(io,"Julia ",VERSION,"\nPowerDynamics ",pathof(PowerDynamics));Pkg.status(;io)
end
function settings(k,tp,tq)
    out=deepcopy(PARAMETERS)
    for p in values(out)
        s=NWState(NW,copy(INITIAL),p,0.)
        for b in ALLG
            s.p[VIndex(b,Symbol("inv$(b)₊droop₊τ_p"))]=tp
            s.p[VIndex(b,Symbol("inv$(b)₊droop₊τ_q"))]=tq
        end
        for j in [2,3],q in ["R","X"];s.p[EIndex(Symbol("line",j),Symbol("line_sym₊",q))]*=k/1.0299;end
    end
    out
end
function checkroot(tag,stage,seed,p,isv)
    x,err=stationary(NW,seed,p);@assert err<1e-8
    y=isv ? to_vsm(x,p) : x;fun=isv ? VSM : NW
    f=similar(y);fun(f,y,p,0.);J=fd(fun,y,p)
    ev=eigvals(Diagonal(1 ./ MASS[DYN])*(J[DYN,DYN]-J[DYN,ALG]*(J[ALG,ALG]\J[ALG,DYN])))
    writedlm(joinpath(DATA,tag*"_"*stage*"_eigen.csv"),hcat(real.(ev),imag.(ev)),',')
    savevec(joinpath(DATA,tag*"_"*stage*"_root.csv"),y)
    appendrow(joinpath(DATA,"roots.csv"),"case,stage,residual,max_real,unstable,near_zero",[tag,stage,maximum(abs.(f)),maximum(real.(ev)),sum(real.(ev).>1e-7),sum(abs.(ev).<1e-7)])
    y,x
end
function runone(tag,isv,tp,tq,k,strict=false)
    isfile(joinpath(CHECK,tag,"DONE"))&&return
    p=settings(k,tp,tq);grid=k==1.0299 ? "k1p0299" : k==1.02 ? "k1p02" : k==.8 ? "k0p8" : "k1p031"
    preseed=vec(readdlm(joinpath(DATA,"seeds",grid*"_pre0.csv"),',',Float64))
    postseed=vec(readdlm(joinpath(DATA,"seeds",grid*"_post0.csv"),',',Float64))
    y,_=checkroot(tag,"pre",preseed,p["pre"],isv)
    _,target=checkroot(tag,"post",postseed,p["post"],isv)
    # Verify pointwise conjugacy independently of integration, including perturbed states.
    for stage in ["pre","fault","post"]
        pp=p[stage];x=copy(INITIAL);x[AI].+=.03;x[PFI].+=.01
        a=similar(x);NW(a,x,pp,0.);b=similar(x);vsm_rhs!(b,to_vsm(x,pp),pp,0.)
        for j in eachindex(ALLG);a[PFI[j]]*= -pp[KP[j]]/pp[WB[j]];end
        er=maximum(abs.(a-b));@assert er<1e-9
        appendrow(joinpath(DATA,"conjugacy.csv"),"case,stage,max_rhs_error",[tag,stage,er])
    end
    dir=joinpath(CHECK,tag);mkpath(dir);fun=isv ? VSM : NW
    for (stage,a,b,step) in [("pre",0.,1.,.01),("fault",1.,1.15,.0005),("post",1.15,301.15,.02)]
        pp=p[stage];x=isv ? to_droop(y,pp) : copy(y);before=copy(y[DYN]);er=algfix!(x,pp);@assert er<1e-8
        y=isv ? to_vsm(x,pp) : x;@assert maximum(abs.(before-y[DYN]))<1e-12
        appendrow(joinpath(DATA,"events.csv"),"case,stage,algebraic_residual,dynamic_change",[tag,stage,er,maximum(abs.(before-y[DYN]))])
        savevec(joinpath(dir,stage*"_initial.csv"),y);savevec(joinpath(dir,stage*"_parameters.csv"),pp)
        times=sort(unique(vcat(collect(a:step:b),collect(a:.0001:min(b,a+.02)),[a,b])))
        println("START ",tag," ",stage);flush(stdout);tick=time()
        sol=solve(ODEProblem(fun,y,(a,b),pp),Rodas5P(autodiff=false);reltol=1e-9,abstol=1e-11,dtmax=strict ? .00125 : .005,maxiters=10^8,saveat=times,save_everystep=false,dense=false)
        @assert string(sol.retcode)=="Success"
        @assert maximum(abs.(sol.u[1][DYN]-y[DYN]))<1e-12
        open(joinpath(dir,stage*".csv"),"w") do io
            println(io,join(vcat(["t_absolute_s","t_post_s","stage"],["b$(b)_$(q)" for b in ALLG for q in KEYNAMES],"alg_residual"),","))
            for (t,u) in zip(sol.t,sol.u)
                xx=isv ? to_droop(u,pp) : u
                println(io,join(vcat([t,t-1.15,stage],obs(xx,pp,t)),","))
            end
        end
        y=copy(sol.u[end]);savevec(joinpath(dir,stage*"_end.csv"),y)
        appendrow(joinpath(DATA,"progress.csv"),"case,stage,runtime,retcode,strict",[tag,stage,time()-tick,sol.retcode,strict]);println("DONE ",tag," ",stage," ",time()-tick);flush(stdout)
    end
    write(joinpath(dir,"DONE"),"Success\n")
end
for tp in [1.087,1.]
 for j in eachindex(ALLG)
  p=PARAMETERS["pre"];d=p[WB[j]]/p[KP[j]]
  appendrow(joinpath(DATA,"mapping.csv"),"bus,tau_p,Kp_rad_s,Kp_pu,M,D,H,M_over_D,pf_index,angle_index",[ALLG[j],tp,p[KP[j]],1/d,tp*d,d,tp*d/2,tp,PFI[j],AI[j]])
 end
end
jobs=[("A_droop_center",false,1.087,1.087,1.0299,false),("B_vsm_center",true,1.087,1.087,1.0299,false),("C_droop_recovery",false,1.,1.,1.0299,false),("D_vsm_recovery",true,1.,1.,1.0299,false)]
# Phase 2 only runs after the independent Python equivalence gate has succeeded.
if get(ENV,"VSM_PHASE","1")=="2"
 @assert isfile(joinpath(DATA,"equivalence_passed"))
 jobs=[("E_shortQ_center",true,1.087,.02,1.0299,false),("F_shortQ_strong",true,1.087,.02,.8,false),("G_shortQ_weak",true,1.087,.02,1.031,false),("H_longQ_strong",true,1.087,1.087,1.02,false),("B_vsm_strict",true,1.087,1.087,1.0299,true),("D_vsm_strict",true,1.,1.,1.0299,true)]
end
for job in jobs;runone(job...);end

# Standalone search: fixed H=2.5 s, M=5 s. Original model and equilibrium inputs.
const ROOT=normpath(joinpath(@__DIR__,"../../VSM_decelaration"))
runner=joinpath(ROOT,"code/run.jl")
include_string(Main,first(split(read(runner,String),"\nmanifest=readlines")),runner)
using Serialization
const OUTSEARCH=@__DIR__
const SUMMARY=joinpath(OUTSEARCH,"screen_"*ARGS[1]*".csv")
const BASEPRE=vec(readdlm(joinpath(DATA,"seeds/nf02_1_pre0.csv"),',',Float64))
const BASEPOST=vec(readdlm(joinpath(DATA,"seeds/nf02_1_post0.csv"),',',Float64))
const CAP_B=Ref(0.)
const GRID_K=Ref(1.0299)
const V5_MIN=.98
function configuration(db,loadfactor)
    pp=params(2.461761102780045,[.5,.4,.4,.4],.1,.02)
    for p in pp
        p[KP].=p[WB]./db;p[TP].=5/db
        s=NWState(NW,copy(BASEPRE),p,0.)
        s.p[VIndex(5,:PQLoad₊P_load_p)]*=loadfactor
        s.p[VIndex(5,:PQLoad₊Q_load_p)]=-CAP_B[]*s.p[VIndex(5,:PQLoad₊vref2)]
        for j in [2,3],name in ["R","X"]
            s.p[EIndex(Symbol("line",j),Symbol("line_sym₊",name))]*=GRID_K[]/1.0299
        end
    end
    pp
end
function root_path(pre,post,ppfun,step0,tag)
    w=0.;step=step0;count=0
    function corrected(x,w,trial,stage)
        p=ppfun(w)[stage];h=1e-5
        a=similar(x);b=similar(x)
        NW(a,x,ppfun(w+h)[stage],0.);NW(b,x,ppfun(w-h)[stage],0.)
        tangent=-(fd(NW,x,p)\((a-b)/(2h)))
        y=x+(trial-w)*tangent;f=similar(x);q=ppfun(trial)[stage]
        for i in 1:25
            NW(f,y,q,0.);er=maximum(abs.(f));er<1e-9 && return y,er
            all(isfinite,y) || return y,Inf
            dy=fd(NW,y,q)\f;norm(dy,Inf)<100 || return y,Inf
            y-=dy
        end
        NW(f,y,q,0.);y,maximum(abs.(f))
    end
    while w<1-1e-12
        trial=min(1.,w+step)
        xp,ep=corrected(pre,w,trial,1);xq,eq=corrected(post,w,trial,3)
        if max(ep,eq)<1e-8
            pre=xp;post=xq;w=trial;count+=1
            step=min(step0*4,step*1.4)
            if count%50==0;println("ROOT_CONTINUATION ",tag," fraction=",w);flush(stdout);end
        else
            step/=2
            if step<1e-8
                println("ROOT_UNRESOLVED ",tag," fraction=",trial," residual=",max(ep,eq));flush(stdout);return nothing
            end
        end
    end
    pre,post
end
function cap_roots(B,lf,k)
    pre=copy(BASEPRE);post=copy(BASEPOST)
    gridfun=w->begin CAP_B[]=0.;GRID_K[]=1.0299+w*(k-1.0299);configuration(50.,1.) end
    pair=root_path(pre,post,gridfun,min(1.,.002/abs(k-1.0299)),"grid k=$(k)")
    pair===nothing && return nothing
    pre,post=pair;GRID_K[]=k
    loadfun=w->begin CAP_B[]=0.;GRID_K[]=k;configuration(50.,1+w*(lf-1)) end
    pair=root_path(pre,post,loadfun,lf==1 ? 1. : min(1.,.0005/abs(lf-1)),"load=$(lf)")
    pair===nothing && return nothing
    pre,post=pair
    capfun=w->begin GRID_K[]=k;CAP_B[]=B*w;configuration(50.,lf) end
    pair=root_path(pre,post,capfun,min(1.,.001/B),"B=$(B)")
    CAP_B[]=B;GRID_K[]=k
    pair
end
function voltage5(x,p)
    state=NWState(NW,copy(x),p,0.)
    hypot(state[VIndex(5,:busbar₊u_r)],state[VIndex(5,:busbar₊u_i)])
end
function classifyquick(states,times,p,target)
    turns=(states[end][AI]-states[1][AI])/(2pi)
    start=max(times[end]-min(30.,times[end]/3),0.)
    tail=findall(>=(start),times)
    freqs=hcat([(to_vsm(x,p)[PFI].*p[WB]/(2pi)) for x in states[tail]]...)
    phaseerr=abs.(atan.(sin.(states[end][AI]-target[AI]),cos.(states[end][AI]-target[AI])))
    recovery=all(vec(maximum(abs.(freqs),dims=2)).<1e-4)&&all(phaseerr.<.002)
    remote_negative=all(turns[2:4].< -2)&&all(freqs[2:4,:].< -.001)
    remote_positive=all(turns[2:4].>2)&&all(freqs[2:4,:].>.001)
    label=recovery ? "recovery" : remote_negative ? "negative_rotation_candidate" : remote_positive ? "positive_rotation_candidate" : "unresolved"
    label,sum(turns[2:4])/3,turns,vec(sum(freqs,dims=2)/length(tail))
end
function integratecase(tag,db,d1,d2,loadfactor,roots;horizon=300.,dtmax=.005,savefull=false)
    pp=configuration(db,loadfactor);c=(d1=d1,d2=d2,omega_d=50.)
    pre,target=roots
    rp,ep,np=damped_eqcheck(pre,pp[1];damping=c)
    rq,eq,nq=damped_eqcheck(target,pp[3];damping=c)
    if max(rp,rq)>=1e-8 || max(ep,eq)>=0
        appendrow(SUMMARY,"case,Bcap,grid_k,pre_V5,Ddroop,D1,D2,load_factor,H,M,horizon,classification,remote_turns,pre_max_real,post_max_real",[tag,CAP_B[],GRID_K[],voltage5(pre,pp[1]),db,d1,d2,loadfactor,2.5,5,horizon,"root_not_locally_stable",NaN,ep,eq]);return "root_not_locally_stable"
    end
    y=copy(pre);z=nothing;parts=[]
    for (stage,p,a,b,step) in [("pre",pp[1],0.,1.,.01),("fault",pp[2],1.,1.15,.0005),("post",pp[3],1.15,1.15+horizon,.02)]
        @assert algfix!(y,p)<1e-8
        sample=sort(unique(vcat(collect(a:step:b),[a,b])))
        sol=solve_vsm(y,p,(a,b),Rodas5P();damping=c,washout_state=z,reltol=1e-9,abstol=1e-11,dtmax=dtmax,maxiters=10^8,saveat=sample,save_everystep=false,dense=false)
        string(sol.retcode)=="Success" || error("Numerical failure $tag $stage $(sol.retcode)")
        push!(parts,(stage=stage,p=copy(p),t=copy(sol.t),u=sol.u,z=sol.washout))
        y=copy(sol.u[end]);z=copy(sol.washout[end])
    end
    part=parts[end];label,turns,each,df=classifyquick(part.u,part.t.-1.15,pp[3],target)
    appendrow(SUMMARY,"case,Bcap,grid_k,pre_V5,Ddroop,D1,D2,load_factor,H,M,horizon,classification,remote_turns,pre_max_real,post_max_real",[tag,CAP_B[],GRID_K[],voltage5(pre,pp[1]),db,d1,d2,loadfactor,2.5,5,horizon,label,turns,ep,eq])
    println("RESULT ",tag," ",label," remote_turns=",turns," post_eigen=",eq);flush(stdout)
    if savefull || occursin("rotation_candidate",label)
        dir=joinpath(OUTSEARCH,tag);mkpath(dir)
        serialize(joinpath(dir,"full_states.bin"),(parts=parts,target=target,pre=pre,db=db,c=c,loadfactor=loadfactor,H=2.5,M=5,dtmax=dtmax,Bcap=CAP_B[],grid_k=GRID_K[],pre_V5=voltage5(pre,pp[1])))
        for part in parts
            open(joinpath(dir,part.stage*".csv"),"w") do io
                println(io,join(vcat(["t_absolute_s","t_post_s","stage"],["b$(b)_$(k)" for b in ALLG for k in KEYNAMES],"alg_residual"),","))
                for (t,u) in zip(part.t,part.u);println(io,join(vcat([t,t-1.15,part.stage],obs(u,part.p,t)),","));end
            end
        end
        savevec(joinpath(dir,"pre_root.csv"),pre);savevec(joinpath(dir,"post_root.csv"),target)
        for (stage,p) in zip(["pre","fault","post"],pp);savevec(joinpath(dir,stage*"_parameters.csv"),p);end
    end
    label
end
function sensitivity_main()
    @assert length(ARGS)==3 "worker_id, comma-separated D1 values, horizon"
    @assert !isfile(SUMMARY) "Use a fresh worker id"
    CAP_B[]=1.;GRID_K[]=.6812730259441179
    previous=joinpath(OUTSEARCH,"../h2p5_bus5_voltage098_search/B1.0_k0.6812730259441179_L1.0_D10.0_D10.0_D2100.0_h1000")
    pre=vec(readdlm(joinpath(previous,"pre_root.csv"),',',Float64))
    target=vec(readdlm(joinpath(previous,"post_root.csv"),',',Float64))
    pp=configuration(10.,1.)
    pre,ep=stationary(NW,pre,pp[1]);target,eq=stationary(NW,target,pp[3]);@assert max(ep,eq)<1e-8
    vpre=voltage5(pre,pp[1]);@assert vpre>=V5_MIN
    println("VOLTAGE_CHECK ",vpre);flush(stdout)
    horizon=parse(Float64,ARGS[3])
    for d1 in parse.(Float64,split(ARGS[2],','))
        tag="D1_"*replace(string(d1),'.'=>'p')*"_h"*string(Int(horizon))
        println("START ",tag);flush(stdout)
        label=integratecase(tag,10.,d1,100.,1.,(pre,target);horizon=horizon,savefull=true)
        println("COMPLETE D1=",d1," ",label);flush(stdout)
    end
end
sensitivity_main()

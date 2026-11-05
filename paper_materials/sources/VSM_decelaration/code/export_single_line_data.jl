# Export actual model parameters and saved DAE states for the fixed eight-bus diagram.
# No integration. Uses the same Julia environment as code/run.jl.
if isempty(ARGS) || ARGS==["--help"]
    println("Usage: julia --project=provenance code/export_single_line_data.jl --bundle full_states.bin --output data/single_line [--compare-bundle other.bin] [--post-time 5]")
    exit()
end
const RUNNER=joinpath(@__DIR__,"run.jl")
include_string(Main,first(split(read(RUNNER,String),"\nmanifest=readlines")),RUNNER)
using Serialization,SHA,Printf
const NETWORK_BRANCHES=[(1,4),(4,6),(5,6),(3,5),(2,3),(2,5),(4,5),(2,8),(2,7),(7,8),(5,8)]
function export_snapshot(bundle,part,x,output,label,source;time_s=0.,equilibrium=false)
    mkpath(output);p=part.p;s=NWState(NW,copy(x),copy(p),time_s)
    @assert maximum(abs.(p[WB]./p[KP].-bundle.db))<1e-10
    @assert maximum(abs.(p[TP].*p[WB]./p[KP].-bundle.M))<1e-10
    @assert abs(bundle.M-2bundle.H)<1e-10
    val(b,k)=s[VIndex(b,Symbol(k))]
    par(b,k)=s.p[VIndex(b,Symbol(k))]
    g=par(5,"PQLoad₊P_load_p")/par(5,"PQLoad₊vref2")
    B=-par(5,"PQLoad₊Q_load_p")/par(5,"PQLoad₊vref2")
    enabled=par(4,"fault_load₊fault_enabled_p");@assert enabled in [0.,1.]
    faultg=-enabled*par(4,"fault_load₊G_fault_p")
    f=similar(x);NW(f,x,p,time_s);alg=maximum(abs.(f[ALG]));@assert alg<1e-8
    equilibrium && @assert maximum(abs.(f))<1e-8
    open(joinpath(output,"voltages.csv"),"w") do io
        println(io,"bus,U_r_pu,U_i_pu,reference_P_injection_pu,reference_Q_injection_pu")
        for b in 1:8
            u=complex(val(b,"busbar₊u_r"),val(b,"busbar₊u_i"))
            if b in ALLG
                ig=complex(val(b,"inv$(b)₊vsrc₊filter₊i_g_r"),val(b,"inv$(b)₊vsrc₊filter₊i_g_i"));S=u*conj(ig)
            elseif b==5;S=complex(-g,B)*abs2(u)
            elseif b==4;S=complex(-faultg*abs2(u),0.)
            elseif b==8;S=0im
            else;S=nothing
            end
            println(io,join([b,real(u),imag(u),S===nothing ? "" : real(S),S===nothing ? "" : imag(S)],','))
        end
    end
    open(joinpath(output,"branches.csv"),"w") do io
        println(io,"line,from_bus,to_bus,R_pu,X_pu,active")
        for (j,(a,b)) in enumerate(NETWORK_BRANCHES)
            v(k)=s.p[EIndex(Symbol("line",j),Symbol("line_sym₊",k))]
            println(io,join([j,a,b,v("R"),v("X"),v("active")],','))
        end
    end
    open(joinpath(output,"metadata.csv"),"w") do io
        println(io,"snapshot,stage,time_absolute_s,is_equilibrium,H_s,M_s,Ddroop,D1,D2,omega_d,load_G_pu,capacitor_B_pu,fault_G_pu,max_algebraic_residual,max_full_residual,source_sha256")
        println(io,join([label,part.stage,time_s,Int(equilibrium),bundle.H,bundle.M,bundle.db,bundle.c.d1,bundle.c.d2,bundle.c.omega_d,g,B,faultg,alg,maximum(abs.(f)),bytes2hex(sha256(read(source)))],','))
    end
    savevec(joinpath(output,"state.csv"),x)
    println("EXPORTED ",label," t=",time_s," alg=",alg);flush(stdout)
end
function main()
    opts=Dict{String,String}();@assert iseven(length(ARGS)) "Use --bundle PATH --output DIR [--compare-bundle PATH] [--post-time SECONDS]"
    for i in 1:2:length(ARGS);opts[ARGS[i]]=ARGS[i+1];end
    @assert all(k in ["--bundle","--output","--compare-bundle","--post-time"] for k in keys(opts))
    input=opts["--bundle"];output=opts["--output"];b=deserialize(input)
    pre=only(filter(p->p.stage=="pre",b.parts));post=only(filter(p->p.stage=="post",b.parts))
    export_snapshot(b,pre,b.pre,joinpath(output,"pre_equilibrium"),"Pre-fault equilibrium",input;equilibrium=true)
    export_snapshot(b,post,b.target,joinpath(output,"post_equilibrium"),"Post-fault stable equilibrium",input;equilibrium=true)
    tpost=parse(Float64,get(opts,"--post-time","5"));@assert tpost>=0
    for file in unique([input,get(opts,"--compare-bundle",input)])
        bb=deserialize(file);pp=only(filter(p->p.stage=="post",bb.parts));j=argmin(abs.(pp.t.-(1.15+tpost)))
        @assert abs(pp.t[j]-(1.15+tpost))<.021 "Requested time not present in saved trajectory"
        name="D1_$(Int(bb.c.d1))_post_t$(@sprintf("%g",tpost))"
        export_snapshot(bb,pp,pp.u[j],joinpath(output,name),name,file;time_s=pp.t[j])
    end
end
main()

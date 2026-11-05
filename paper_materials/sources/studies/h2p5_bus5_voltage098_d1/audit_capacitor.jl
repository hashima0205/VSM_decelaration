using Serialization,DelimitedFiles,LinearAlgebra
const OUT=@__DIR__
state_table=readdlm(joinpath(OUT,"../../VSM_decelaration/data/states.csv"),',',Any;skipstart=1)
index5(symbol)=Int(only([r[1] for r in eachrow(state_table) if r[2]==5 && r[3]==symbol]))
ir=index5("busbar₊u_r");ii=index5("busbar₊u_i")
open(joinpath(OUT,"capacitor_audit.csv"),"w") do io
    println(io,"case,Bcap,pre_V5,pre_trace_min_V5,post_root_V5,pre_Qcap_injection,post_root_Qcap_injection,pre_load_P,post_root_load_P,max_washout_event_jump")
    for dir in sort(readdir(OUT;join=true))
        file=joinpath(dir,"full_states.bin");isfile(file)||continue
        b=deserialize(file);@assert b.Bcap>0 && b.H==2.5 && b.M==5 && b.pre_V5>=.98
        jump=maximum(maximum(abs.(b.parts[j].z[end]-b.parts[j+1].z[1])) for j in 1:length(b.parts)-1)
        @assert jump<1e-10
        vpre=hypot(b.pre[ir],b.pre[ii]);vpost=hypot(b.target[ir],b.target[ii])
        vmin=minimum(hypot(x[ir],x[ii]) for x in b.parts[1].u);@assert vmin>=.98
        println(io,join([basename(dir),b.Bcap,vpre,vmin,vpost,b.Bcap*vpre^2,b.Bcap*vpost^2,2.2682301152333055*b.loadfactor*vpre^2,2.2682301152333055*b.loadfactor*vpost^2,jump],','))
        open(joinpath(dir,"bus5_capacitor.csv"),"w") do out
            println(out,"t_absolute_s,t_post_s,stage,V5_pu,Qcap_injection_pu")
            for part in b.parts,(t,x) in zip(part.t,part.u)
                v=hypot(x[ir],x[ii]);println(out,join([t,t-1.15,part.stage,v,b.Bcap*v^2],','))
            end
        end
    end
end
println("Capacitor voltage, injection and filter event-state audit complete.")

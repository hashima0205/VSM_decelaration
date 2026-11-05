using Serialization,DelimitedFiles,Statistics
const OUT=@__DIR__
const STATES=readdlm(joinpath(OUT,"../../VSM_decelaration/data/states.csv"),',',Any;skipstart=1)
idx(b,s)=Int(only([r[1] for r in eachrow(STATES) if r[2]==b&&r[3]==s]))
const AI=[idx(b,"inv$(b)₊droop₊δ") for b in [1,2,3,7]]
const PF=[idx(b,"inv$(b)₊droop₊Pfilt") for b in [1,2,3,7]]
const R5=idx(5,"busbar₊u_r");const I5=idx(5,"busbar₊u_i")
for d1 in [10,20]
 source=joinpath(OUT,"../h2p5_bus5_voltage098_d1/D1_$(d1)p0_h1000/full_states.bin")
 b=deserialize(source);phase=atan(b.pre[I5],b.pre[R5]);last=phase
 open(joinpath(OUT,"trajectory_D1_$(d1).csv"),"w") do io
  println(io,"t_absolute_s,t_post_s,stage,theta_bus5_rad,theta_remote_internal_rad,bus5_phase_unwrapped_rad,df_mean_Hz,V5_pu")
  for part in b.parts,(t,x) in zip(part.t,part.u)
   raw=atan(x[I5],x[R5]);phase=last+atan(sin(raw-last),cos(raw-last));last=phase
   println(io,join([t,t-1.15,part.stage,mean(x[AI[2:4]])-phase,mean(x[AI[2:4]]),phase,60*mean(([.4,.4,.4]-x[PF[2:4]])/10),hypot(x[R5],x[I5])],','))
  end
 end
 for (name,x) in [("pre",b.pre),("stable",b.target)]
  println("ROOT D1=",d1," ",name," theta5=",mean(x[AI[2:4]])-atan(x[I5],x[R5])," theta6=",mean(x[AI[2:4]]))
 end
end

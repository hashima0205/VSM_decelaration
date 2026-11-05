using Serialization,DelimitedFiles
const OUT=@__DIR__
b=deserialize(joinpath(OUT,"../h2p5_bus5_voltage098_d1/D1_10p0_h1000/full_states.bin"))
for tag in ["baseline","r56_075"]
 post=deserialize(joinpath(OUT,"../h2p5_hypothesis_interventions",tag,"h300.bin")).part
 stages=[b.parts[1],b.parts[2],(stage="post",t=post.t,u=post.u,z=post.z)]
 open(joinpath(OUT,"states_$(tag).csv"),"w") do io
  println(io,join(vcat(["t_absolute_s","t_post_s","stage"],["x$i" for i in 1:66],["z$i" for i in 1:4]),','))
  for part in stages,(t,x,z) in zip(part.t,part.u,part.z)
   t>11.15000001&&continue
   println(io,join(vcat([t,t-1.15,part.stage],x,z),','))
  end
 end
end
println("Short 70-state histories exported for both cases")

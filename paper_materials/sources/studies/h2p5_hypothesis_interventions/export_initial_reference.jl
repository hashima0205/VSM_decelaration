using Serialization,DelimitedFiles
const OUT=@__DIR__
b=deserialize(joinpath(OUT,"../h2p5_bus5_voltage098_d1/D1_10p0_h1000/full_states.bin"))
i=argmin(abs.(b.parts[end].t.-21.15))
writedlm(joinpath(OUT,"reference_late70.csv"),vcat(b.parts[end].u[i],b.parts[end].z[i]),',')
writedlm(joinpath(OUT,"reference_clearing70.csv"),vcat(b.parts[end].u[1],b.parts[end].z[1]),',')
println("Reference physical late time: ",b.parts[end].t[i])

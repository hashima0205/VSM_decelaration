# Independent classification from saved trajectories, reusing a validated root
# when the entire parameter vector is identical (early and late interventions).
using Serialization,DelimitedFiles
const OUT=@__DIR__
const ALLG=[1,2,3,7];const DI010=[15,30,45,66];const PI010=[14,29,44,65];const DELTA=DI010[2:4]
const KP010=fill(2pi*60/10,4);const PS010=[.5,.4,.4,.4]
include(joinpath(OUT,"../../VSM_decelaration/code/adaptive_probe_metrics.jl"))
open(joinpath(OUT,"reclassified.csv"),"w") do io
 open(joinpath(OUT,"machines.csv"),"w") do mi
  println(io,"case,root_reference_case,classification,turns")
  println(mi,"case,bus,classification,internal_turns,tail_max_abs_df_Hz,phase_error_rad,tail_phase_width_rad,min_window_turns,max_window_turns")
  for dir in sort(readdir(OUT;join=true))
   isfile(joinpath(dir,"outcome.bin"))||continue
   tag=basename(dir);ref=startswith(tag,"late_") ? tag[6:end] : tag
   @assert readdlm(joinpath(dir,"parameters.csv"),',',Float64)==readdlm(joinpath(OUT,ref,"parameters.csv"),',',Float64)
   root=vec(readdlm(joinpath(OUT,ref,"root.csv"),',',Float64))
   a=deserialize(joinpath(dir,"h300.bin")).part;b=deserialize(joinpath(dir,"h1000.bin")).part
   t=vcat(a.t,b.t[2:end]).-a.t[1];u=vcat(a.u,b.u[2:end])
   label,turns,ms=classify_probe(t,u,root)
   println(io,join([tag,ref,label,turns],','))
   for m in ms;println(mi,join(vcat([tag],collect(m)),','));end
  end
 end
end
println("Saved-state reclassification complete")

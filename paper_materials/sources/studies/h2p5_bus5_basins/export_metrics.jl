using Serialization
const OUT=@__DIR__
open(joinpath(OUT,"machines.csv"),"w") do io
 println(io,"case,D1,bus,classification,internal_turns,tail_max_abs_df_Hz,phase_error_rad,tail_phase_width_rad,min_window_turns,max_window_turns")
 for dir in sort(readdir(OUT;join=true))
  f=joinpath(dir,"outcome.bin");isfile(f)||continue
  b=deserialize(f)
  for m in b.machines;println(io,join(vcat([b.case,b.D1],collect(m)),','));end
 end
end

using Serialization,DelimitedFiles,Statistics
const OUT=@__DIR__
open(joinpath(OUT,"machines.csv"),"w") do io
 println(io,"case,bus,classification,turns,tail_max_df_Hz,phase_error_rad,tail_width_rad,min_window_turns,max_window_turns")
 for dir in sort(readdir(OUT;join=true))
  f=joinpath(dir,"outcome.bin");isfile(f)||continue;b=deserialize(f)
  for m in b.machines;println(io,join(vcat([b.tag],collect(m)),','));end
  a=deserialize(joinpath(dir,"trajectory.bin"));t0=a.t[1]
  open(joinpath(dir,"compact.csv"),"w") do out
   println(out,"t_since_transplant_s,remote_internal_angle_rad,remote_df_Hz")
   ids=sort(unique(vcat(collect(1:5:length(a.t)),[length(a.t)])))
   for i in ids
    x=a.u[i];println(out,join([a.t[i]-t0,mean(x[[30,45,66]]),60mean((0.4 .- x[[29,44,65]])/10)],','))
   end
  end
 end
end

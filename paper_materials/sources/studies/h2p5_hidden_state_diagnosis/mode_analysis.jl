const SRC=joinpath(@__DIR__,"run.jl")
include_string(Main,first(split(read(SRC,String),"\nfunction main()")),SRC)
x=vec(readdlm(joinpath(OUT,"root_2.csv"),',',Float64));y=vcat(to_vsm(x,PP),zeros(4));f=similar(y)
fun=(du,u,p,t)->damped_rhs!(du,u,p,t,BASE.c)
Jfull=fd(fun,y,PP);dynamic=vcat(DYN,collect(67:70));mass=vcat(MASS[DYN],ones(4))
Jred=Diagonal(1 ./ mass)*(Jfull[dynamic,dynamic]-Jfull[dynamic,ALG]*(Jfull[ALG,ALG]\Jfull[ALG,dynamic]))
e=eigen(Jred);k=argmax(real.(e.values));lambda=real(e.values[k]);@assert lambda>0 && abs(imag(e.values[k]))<1e-8
v=real(e.vectors[:,k]);anglepos=[findfirst(==(i),dynamic) for i in AI[2:4]];v.*=-1/mean(v[anglepos])
l=eigen(transpose(Jred));kk=argmin(abs.(l.values.-lambda));left=real(l.vectors[:,kk]);left./=dot(left,v)
@assert norm(Jred*v-lambda*v)<1e-7 && norm(transpose(Jred)*left-lambda*left)<1e-7
savevec(joinpath(OUT,"saddle_jacobian.csv"),Jred)
qall=[si(b,"droop₊Qfilt") for b in ALLG];vcpi=[si(b,k) for b in ALLG for k in ["vsrc₊vc₊γ_d","vsrc₊vc₊γ_q"]];ccpi=[si(b,k) for b in ALLG for k in ["vsrc₊cc1₊γ_d","vsrc₊cc1₊γ_q"]]
group(i)=i in AI ? "angle" : i in PFI ? "frequency" : i>=67 ? "washout" : i in qall ? "Q_filter" : i in vcpi ? "voltage_PI" : i in ccpi ? "current_PI" : "electrical"
open(joinpath(OUT,"unstable_mode.csv"),"w") do io
 println(io,"state_index,group,right_vector,left_vector,lambda")
 for (j,i) in enumerate(dynamic);println(io,join([i,group(i),v[j],left[j],lambda],','));end
end
open(joinpath(OUT,"mode_projection.csv"),"w") do io
 groups=["angle","frequency","washout","Q_filter","voltage_PI","current_PI","electrical"]
 println(io,join(vcat(["condition","t_absolute_s","mode_amplitude_rad"],groups),','))
 for tag in ["baseline","r56_075"]
  table=readdlm(joinpath(OUT,"../h2p5_r56_comparison/states_$(tag).csv"),',',Any;skipstart=1)
  for row in eachrow(table)
   t=Float64(row[1]); t>5.01&&continue
   xx=Float64.(row[4:69]);zz=Float64.(row[70:73]);yy=vcat(to_vsm(xx,PP),zz);terms=left.*(yy[dynamic]-y[dynamic])
   parts=[sum(terms[[group(i)==g for i in dynamic]]) for g in groups]
   println(io,join(vcat([tag,t,sum(terms)],parts),','))
  end
 end
end
println("UNSTABLE_MODE lambda=",lambda," angle gap=",mean(BASE.target[AI[2:4]]-x[AI[2:4]]))

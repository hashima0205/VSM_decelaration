using Serialization,DelimitedFiles,Statistics
const OUT=@__DIR__
const ST=readdlm(joinpath(OUT,"../../VSM_decelaration/data/states.csv"),',',Any;skipstart=1)
idx(b,s)=Int(only([r[1] for r in eachrow(ST) if r[2]==b&&r[3]==s]))
const BUS=Dict(b=>(idx(b,"busbar₊u_r"),idx(b,"busbar₊u_i")) for b in [1,2,3,4,5,7,8])
const AI=[idx(b,"inv$(b)₊droop₊δ") for b in [1,2,3,7]]
const PF=[idx(b,"inv$(b)₊droop₊Pfilt") for b in [1,2,3,7]]
const VC=[(idx(b,"inv$(b)₊vsrc₊filter₊V_C_r"),idx(b,"inv$(b)₊vsrc₊filter₊V_C_i")) for b in [1,2,3,7]]
const IG=[(idx(b,"inv$(b)₊vsrc₊filter₊i_g_r"),idx(b,"inv$(b)₊vsrc₊filter₊i_g_i")) for b in [1,2,3,7]]
complexat(x,ids)=complex(x[ids[1]],x[ids[2]])
for d1 in [10,20]
 b=deserialize(joinpath(OUT,"../h2p5_bus5_voltage098_d1/D1_$(d1)p0_h1000/full_states.bin"))
 open(joinpath(OUT,"budget_D1_$(d1).csv"),"w") do io
  println(io,"t_absolute_s,t_post_s,stage,theta_remote_slack_rad,theta5_terminal_slack_rad,V5_pu,remote_df_Hz,remote_Pcap_pu,remote_Pterminal_pu,bus1_Pterminal_pu,slack_P_pu,load_P_pu,fault_P_pu,line_loss_P_pu,tie46_loss_P_pu,tie56_loss_P_pu,remote_internal_loss_P_pu,P5_to_6_pu,P6_to_5_pu,remote_Pset_minus_Pcap_pu,droop_feedback_pu,D1_feedback_pu,D2_feedback_pu,sum_swing_rhs_pu,balance_error_pu,P5_to_4_pu")
  for part in b.parts
   stage=part.stage;params=readdlm(joinpath(OUT,"../../VSM_decelaration/data/single_line/",stage=="post" ? "post_equilibrium" : "pre_equilibrium","branches.csv"),',',Any;skipstart=1)
   for (t,x,zfilter) in zip(part.t,part.u,part.z)
    U=Dict(bb=>complexat(x,ids) for (bb,ids) in BUS);U[6]=1+0im
    pc=[real(complexat(x,VC[j])*conj(complexat(x,IG[j]))) for j in 1:4]
    pt=[real(U[bb]*conj(complexat(x,IG[j]))) for (j,bb) in enumerate([1,2,3,7])]
    loss=zeros(11);grid=0.;p56=0.;p65=0.;p54=0.
    for r in eachrow(params)
     j,a,bb=Int.(r[1:3]);zz=complex(Float64(r[4]),Float64(r[5]));on=Bool(r[6]);current=on ? (U[a]-U[bb])/zz : 0im
     sa=real(U[a]*conj(current));sb=real(U[bb]*conj(-current));loss[j]=real(zz)*abs2(current)
     if a==6;grid+=sa;end;if bb==6;grid+=sb;end
     if j==3;p56=sa;p65=sb;end
     if j==7;p54=sb;end
    end
    load=2.2682301152333055*abs2(U[5]);fault=stage=="fault" ? 20abs2(U[4]) : 0.
    error=sum(pt)+grid-load-fault-sum(loss);@assert abs(error)<1e-8
    nu=([.5,.4,.4,.4]-x[PF])/10
    gap=1.2-sum(pc[2:4]);dr=-10sum(nu[2:4]);damp=-d1*sum(nu[2:4]);wash=-100sum(nu[2:4]-zfilter[2:4])
    vals=[t,t-1.15,stage,mean(x[AI[2:4]]),atan(imag(U[5]),real(U[5])),abs(U[5]),60mean(nu[2:4]),sum(pc[2:4]),sum(pt[2:4]),pt[1],grid,load,fault,sum(loss),loss[2],loss[3],sum(loss[[4,5,6,8,9,10,11]]),p56,p65,gap,dr,damp,wash,gap+dr+damp+wash,error,p54]
    println(io,join(vals,','))
   end
  end
 end
 println("EXPORTED D1=",d1)
end

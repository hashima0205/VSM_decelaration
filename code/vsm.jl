# State-coordinate replacement on the compiled full PowerDynamics DAE.
# Four Pfilt slots become dw_pu. No Pfilt state remains in the VSM integrator.
# The legacy vector field supplies ONLY unchanged circuit/Q/PI equations.
# Its four P-filter and four angle rows are overwritten explicitly below.
const IDXFULL=NWState(NW,Float64.(1:length(STABLE)),copy(PARAM),0.)
const IPFULL=NWState(NW,copy(STABLE),Float64.(1:length(PARAM)),0.)
si(b,k)=Int(IDXFULL[VIndex(b,Symbol("inv$(b)₊",k))])
pii(b,k)=Int(IPFULL.p[VIndex(b,Symbol("inv$(b)₊droop₊",k))])
const PFI=[si(b,"droop₊Pfilt") for b in ALLG]
const AI=[si(b,"droop₊δ") for b in ALLG]
const KP=[pii(b,"Kp") for b in ALLG];const PS=[pii(b,"Pset") for b in ALLG]
const TP=[pii(b,"τ_p") for b in ALLG];const WB=[pii(b,"ω0") for b in ALLG]
const VR=[si(b,"vsrc₊filter₊V_C_r") for b in ALLG];const VI=[si(b,"vsrc₊filter₊V_C_i") for b in ALLG]
const IR=[si(b,"vsrc₊filter₊i_g_r") for b in ALLG];const II=[si(b,"vsrc₊filter₊i_g_i") for b in ALLG]
@assert all(MASS[PFI].==1)&&all(MASS[AI].==1)
function to_vsm(x,p)
    y=copy(x)
    for j in eachindex(ALLG);y[PFI[j]]=p[KP[j]]/p[WB[j]]*(p[PS[j]]-x[PFI[j]]);end
    y
end
function to_droop(y,p)
    x=copy(y)
    for j in eachindex(ALLG);x[PFI[j]]=p[PS[j]]-p[WB[j]]/p[KP[j]]*y[PFI[j]];end
    x
end
function vsm_rhs!(dy,y,p,t)
    x=to_droop(y,p)
    NW(dy,x,p,t)
    for j in eachindex(ALLG)
        damping=p[WB[j]]/p[KP[j]];inertia=p[TP[j]]*damping
        power=y[VR[j]]*y[IR[j]]+y[VI[j]]*y[II[j]]
        dy[PFI[j]]=(p[PS[j]]-power-damping*y[PFI[j]])/inertia
        dy[AI[j]]=p[WB[j]]*y[PFI[j]]
    end
    nothing
end
const VSM=ODEFunction(vsm_rhs!;mass_matrix=NW.mass_matrix)

# Keep the upstream Droop-coordinate file/analysis interface. Only the ODE
# integrator carries nu in the four former Pfilt slots.
function solve_vsm(x, p, tspan, algorithm; kwargs...)
    @assert all(isfinite.(p[KP])) && all(p[KP] .> 0)
    @assert all(isfinite.(p[WB])) && all(p[WB] .> 0)
    @assert all(isfinite.(p[TP])) && all(p[TP] .> 0)
    native=solve(ODEProblem(VSM,to_vsm(x,p),tspan,copy(p)),algorithm;kwargs...)
    (;t=native.t, u=[to_droop(y,p) for y in native.u], retcode=native.retcode,
      vsm_u=native.u)
end

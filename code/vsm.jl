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
function solve_vsm(x, p, tspan, algorithm; damping=VSM_DAMPING, washout_state=nothing, kwargs...)
    check_damping(damping)
    @assert all(isfinite.(p[KP])) && all(p[KP] .> 0)
    @assert all(isfinite.(p[WB])) && all(p[WB] .> 0)
    @assert all(isfinite.(p[TP])) && all(p[TP] .> 0)
    y=to_vsm(x,p);n=length(y)
    z=washout_state===nothing ? copy(y[PFI]) : copy(washout_state)
    @assert length(z)==4 && all(isfinite.(z))
    if damping.d1==damping.d2==0
        native=solve(ODEProblem(VSM,y,tspan,copy(p)),algorithm;kwargs...)
        zs=[copy(u[PFI]) for u in native.u]
        return (;t=native.t,u=[to_droop(u,p) for u in native.u],retcode=native.retcode,
                 vsm_u=native.u,washout=zs)
    end
    mass=Diagonal(vcat(MASS,ones(4)))
    fun=ODEFunction((dy,y,p,t)->damped_rhs!(dy,y,p,t,damping);mass_matrix=mass)
    native=solve(ODEProblem(fun,vcat(y,z),tspan,copy(p)),algorithm;kwargs...)
    (;t=native.t,u=[to_droop(u[1:n],p) for u in native.u],retcode=native.retcode,
      vsm_u=[u[1:n] for u in native.u],washout=[u[n+1:end] for u in native.u])
end

# Additional damping, independent of the existing 1/R=50 droop feedback.
const VSM_DAMPING=(d1=parse(Float64,get(ENV,"VSM_D1","0")),
                   d2=parse(Float64,get(ENV,"VSM_D2","100")),
                   omega_d=parse(Float64,get(ENV,"VSM_OMEGA_D","50")))
function check_damping(c)
    @assert isfinite(c.d1) && c.d1>=0
    @assert isfinite(c.d2) && c.d2>=0
    @assert isfinite(c.omega_d) && c.omega_d>0
    c
end
check_damping(VSM_DAMPING)
const VSM_CONTINUATION=Dict{String,Vector{Float64}}()
function damped_rhs!(dy,y,p,t,c)
    n=length(STABLE);vsm_rhs!(view(dy,1:n),view(y,1:n),p,t)
    for j in eachindex(ALLG)
        nu=y[PFI[j]];z=y[n+j]
        inertia=p[TP[j]]*p[WB[j]]/p[KP[j]]
        dy[PFI[j]]-=(c.d1*nu+c.d2*(nu-z))/inertia
        dy[n+j]=c.omega_d*(nu-z)
    end
    nothing
end

function damped_eqcheck(x,p;damping=VSM_DAMPING)
    y=to_vsm(x,p);u=vcat(y,y[PFI]);f=similar(u)
    fun=(du,u,p,t)->damped_rhs!(du,u,p,t,damping)
    fun(f,u,p,0.);J=fd(fun,u,p)
    dynamic=vcat(DYN,collect(length(x)+1:length(x)+4))
    masses=vcat(MASS[DYN],ones(4))
    ev=eigvals(Diagonal(1 ./ masses)*(J[dynamic,dynamic]-J[dynamic,ALG]*(J[ALG,ALG]\J[ALG,dynamic])))
    maximum(abs.(f)),maximum(real.(ev)),sum(real.(ev).>1e-7)
end

using DelimitedFiles,LinearAlgebra,SHA
const PACK=normpath(joinpath(@__DIR__,".."))
const SNAP=joinpath(PACK,"provenance/source_snapshot")
const DATA=joinpath(PACK,"data");const CHECK=joinpath(PACK,"checkpoints");const MODE="scr"
ENV["BASIN_DEFINITIONS_ONLY"]="1"
println("BOOT Julia ",VERSION," case0788 taup=tauq=1.087 s, T=0.15 s");flush(stdout)
include(joinpath(SNAP,"studies/04_clearing/08_state_space/code/run.jl"))
const NW=BB.f;const ALLG=[1,2,3,7];const DYN=findall(!iszero,MASS)
const INPUT=joinpath(PACK,"inputs")
const INITIAL=vec(readdlm(joinpath(INPUT,"prefault.csv"),',',Float64))
const STABLE=vec(readdlm(joinpath(INPUT,"stable.csv"),',',Float64))
const UNSTABLE=vec(readdlm(joinpath(INPUT,"saddle.csv"),',',Float64))
const PARAMETERS=Dict(stage=>vec(readdlm(joinpath(INPUT,stage*"_parameters.csv"),',',Float64)) for stage in ["pre","fault","post"])
# Original study38 measurement/reinitialization routines. Legacy stages()/tauall!
# are not used: actual case0788 parameter vectors are read without modification.
include(joinpath(@__DIR__,"engine12.jl"))
@assert length(DYN)==52&&length(ALG)==14
for (stage,p) in PARAMETERS
    s=NWState(NW,copy(INITIAL),p,0.)
    for (i,b) in enumerate(ALLG)
        @assert s.p[VIndex(b,Symbol("inv$(b)₊droop₊τ_p"))]==1.087
        @assert s.p[VIndex(b,Symbol("inv$(b)₊droop₊τ_q"))]==1.087
        @assert s.p[VIndex(b,Symbol("inv$(b)₊droop₊Pset"))]==[.5,.4,.4,.4][i]
    end
end
for (name,x,p) in [("pre",INITIAL,PARAMETERS["pre"]),("post_stable",STABLE,PARAMETERS["post"]),("post_saddle",UNSTABLE,PARAMETERS["post"])]
    residual,eigen,modes=eqcheck(x,p);@assert residual<1e-8
    @assert name=="post_saddle" ? modes==1 : eigen<0
    println("CASE0788_ROOT ",name," ",residual," ",eigen," ",modes);flush(stdout)
    appendrow(joinpath(DATA,"equilibrium_checks.csv"),"root,residual,max_real_eigen,unstable_modes",[name,residual,eigen,modes])
end

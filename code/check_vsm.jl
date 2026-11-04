# Validate the imported VSM against the unchanged upstream network equations.
# Use upstream parameter construction, without running the production case loop.
runner=joinpath(@__DIR__,"run.jl")
include_string(Main,first(split(read(runner,String),"\nmanifest=readlines")),runner)
using Test
@testset "VSM coordinate replacement" begin
    @test length(DYN)==52 && length(ALG)==14
    @test length(PFI)==length(AI)==4
    unchanged=setdiff(eachindex(STABLE),vcat(PFI,AI))
    max_rhs=0.;max_short=0.
    for tau in [.1,1.16,1.18,1.2]
        for (stage,p) in zip(["pre","fault","post"],params(2.461761102780045,[.5,.4,.4,.4],tau,.02))
            seed=vec(readdlm(joinpath(DATA,"seeds","nf02_1_"*(stage=="post" ? "post0" : "pre0")*".csv"),',',Float64))
            x=copy(seed);x[AI].+=.03;x[PFI].+=.01
            y=to_vsm(x,p)
            @test maximum(abs.(to_droop(y,p)-x))<1e-14
            @test y[setdiff(eachindex(x),PFI)]==x[setdiff(eachindex(x),PFI)]
            a=similar(x);b=similar(x);NW(a,x,p,0.);vsm_rhs!(b,y,p,0.)
            @test maximum(abs.(a[unchanged]-b[unchanged]))<1e-10
            for j in eachindex(PFI);a[PFI[j]]*= -p[KP[j]]/p[WB[j]];end
            err=maximum(abs.(a-b));max_rhs=max(max_rhs,err)
            @test err<1e-9
            @test p[TP].*(p[WB]./p[KP])./(p[WB]./p[KP]) ≈ fill(tau,4)
            # Each event topology, using the same original solver settings.
            if tau==1.2
                @test algfix!(x,p)<1e-8
                times=collect(0.:.001:.02)
                opts=(reltol=1e-9,abstol=1e-11,dtmax=.005,saveat=times,save_everystep=false,dense=false)
                droop=solve(ODEProblem(NW,copy(x),(0.,.02),copy(p)),Rodas5P();opts...)
                vsm=solve_vsm(x,p,(0.,.02),Rodas5P();damping=(d1=0.,d2=0.,omega_d=50.),opts...)
                @test string(droop.retcode)==string(vsm.retcode)=="Success"
                @test droop.t==vsm.t
                er=maximum(maximum(abs.(a-b)) for (a,b) in zip(droop.u,vsm.u))
                max_short=max(max_short,er);@test er<2e-7
                @test maximum(abs.(vsm.vsm_u[1]-to_vsm(x,p)))<1e-10
            end
        end
    end
    println("MAX_RHS_ERROR=",max_rhs)
    println("MAX_SHORT_TRAJECTORY_ERROR=",max_short)
end

@testset "Additional proportional and washout damping" begin
    c=(d1=10.,d2=100.,omega_d=50.)
    p=params(2.461761102780045,[.5,.4,.4,.4],1.2,.02)[3]
    x=vec(readdlm(joinpath(DATA,"seeds/nf02_1_post0.csv"),',',Float64))
    y=to_vsm(x,p);y[PFI].=.001;n=length(y)
    dy=zeros(n+4);base=zeros(n);vsm_rhs!(base,y,p,0.)
    damped_rhs!(dy,vcat(y,zeros(4)),p,0.,c)
    inertia=p[TP].*p[WB]./p[KP]
    @test dy[PFI] ≈ base[PFI]-(c.d1+c.d2)*.001 ./ inertia
    @test dy[n+1:end] ≈ fill(.05,4)
    @test dy[setdiff(1:n,PFI)] ≈ base[setdiff(1:n,PFI)]
    # Constant frequency offset: washout output decays to zero, D1 remains.
    damped_rhs!(dy,vcat(y,y[PFI]),p,0.,c)
    @test dy[PFI] ≈ base[PFI]-c.d1*.001 ./ inertia
    @test dy[n+1:end]==zeros(4)
    filter_rhs=(dz,z,_,t)->begin
        damped_rhs!(dy,vcat(y,z),p,t,c)
        dz.=dy[n+1:end]
    end
    f=solve(ODEProblem(filter_rhs,zeros(4),(0.,.1)),Tsit5();reltol=1e-11,abstol=1e-13,saveat=[0.,.02,.1])
    for (t,z) in zip(f.t,f.u)
        @test z ≈ fill(.001*(1-exp(-50t)),4) atol=1e-11
    end
    # A split integration must preserve memory, using the final washout state.
    x=to_droop(y,p);@test algfix!(x,p)<1e-8
    opts=(damping=c,reltol=1e-9,abstol=1e-11,dtmax=.001,save_everystep=false,dense=false)
    whole=solve_vsm(x,p,(0.,.04),Rodas5P();washout_state=zeros(4),opts...)
    a=solve_vsm(x,p,(0.,.02),Rodas5P();washout_state=zeros(4),opts...)
    b=solve_vsm(a.u[end],p,(.02,.04),Rodas5P();washout_state=a.washout[end],opts...)
    @test string(whole.retcode)==string(a.retcode)==string(b.retcode)=="Success"
    @test maximum(abs.(whole.u[end]-b.u[end]))<2e-7
    @test maximum(abs.(whole.washout[end]-b.washout[end]))<1e-9
    @test length(whole.u[end])==66 && length(whole.washout[end])==4
    @test_throws AssertionError check_damping((d1=-1.,d2=0.,omega_d=50.))
    @test_throws AssertionError check_damping((d1=0.,d2=1.,omega_d=0.))
end

import itertools
from interval_identification import addition_bounds, removal_bounds, quorum_count_bounds


def _grid(a,b,n=41):
    if a==b: return [a]
    return [a+(b-a)*i/(n-1) for i in range(n)]


def test_event_bounds_exhaustive_integer_grid():
    # Exhaustive small grid checks the closed forms against dense latent-time enumeration.
    for l in range(0,4):
        for u in range(l,5):
            for s in range(0,4):
                for e in range(s+1,6):
                    av=_grid(l,u)
                    add=[max(0.0,min(e,a)-s) for a in av]
                    rem=[max(0.0,e-max(s,a)) for a in av]
                    ba=addition_bounds(l,u,s,e); br=removal_bounds(l,u,s,e)
                    assert abs(ba.lower-min(add))<1e-12 and abs(ba.upper-max(add))<1e-12
                    assert abs(br.lower-min(rem))<1e-12 and abs(br.upper-max(rem))<1e-12
                    assert ba.width <= min(u-l,e-s)+1e-12
                    assert br.width <= min(u-l,e-s)+1e-12


def test_quorum_extrema_match_all_endpoint_assignments():
    # Under separability, lower/upper local endpoints attain exact quorum count extrema.
    cases=[
        [addition_bounds(0,2,1,4), removal_bounds(1,4,0,3), addition_bounds(3,5,1,2)],
        [removal_bounds(0,3,1,5), addition_bounds(1,1,0,4), removal_bounds(2,6,0,4)],
    ]
    for xs in cases:
        for tau in (0.0,0.5,1.5,3.0):
            lo,hi=quorum_count_bounds(xs,tau)
            attainable=[]
            for choices in itertools.product(*[(b.lower,b.upper) for b in xs]):
                attainable.append(sum(v>tau for v in choices))
            assert lo==min(attainable)
            assert hi==max(attainable)


def test_threshold_decision_boundary_equivalence():
    for l in (0.0,1.0,2.0):
        for u in (l,l+1.0,l+3.0):
            for s,e in ((0.0,4.0),(1.0,5.0),(2.0,3.0)):
                for tau in (0.0,0.25,0.75):
                    if tau >= e-s:
                        continue
                    for a in _grid(l,u,31):
                        d_add=max(0.0,min(e,a)-s)
                        d_rem=max(0.0,e-max(s,a))
                        assert (d_add>tau) == (a>s+tau)
                        assert (d_rem>tau) == (a<e-tau)

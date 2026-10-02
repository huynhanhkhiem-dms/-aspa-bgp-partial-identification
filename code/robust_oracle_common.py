"""Oracle-only geometry, deliberately independent of interval_identification.py."""
EPS=1e-12

def pos(x):
    return max(0.0,float(x))

def local_bounds(direction,l,u,s,e):
    if l>u or s>=e:
        raise ValueError('invalid local geometry')
    if direction=='addition':
        return pos(min(e,l)-s), pos(min(e,u)-s)
    if direction=='removal':
        return pos(e-max(s,u)), pos(e-max(s,l))
    raise ValueError('invalid direction')

def vals(lo,hi,tau):
    a=int(lo>tau); b=int(hi>tau)
    return (a,) if a==b else (0,1)

def source_theta_interval(l,u,a,b):
    if l>u or a>b:
        raise ValueError('invalid interval')
    return l-b,u-a

def cond_interval(l,u,a,b,theta):
    if l>u or a>b:
        raise ValueError('invalid interval')
    lo=max(l,theta+a); hi=min(u,theta+b)
    if lo>hi+EPS:
        raise ValueError('incompatible')
    if lo>hi:
        lo=hi=(lo+hi)/2.0
    return lo,hi

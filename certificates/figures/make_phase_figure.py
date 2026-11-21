"""Fourier illustrations of the limit density and its bias boundary.

These are numerical illustrations, not certificates. Characteristic functions
are evaluated with Arb moments before conversion to doubles for Simpson
quadrature. A doubled frequency grid checks discretization. The critical
parameter comes from the separate certified enclosure.
"""
from pathlib import Path
import json
import sys
import time
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.optimize import minimize_scalar
from scipy.integrate import simpson
from scipy.special import gammaln
from scipy.interpolate import CubicSpline

P=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(P))
from threshold_pointwise import ERW, arb

ASTAR=0.6688128600145994
# Q_* from the certified enclosure in Table 1 of the paper.
QSTAR=9.86698769
OUT=Path(__file__).parent
CACHE=P/'data/limit_phase_illustration.npz'
# The conditional density h_a and its reflection, for the upper right panel.
COND_A=0.72
COND_CACHE=P/'data/limit_phase_conditional.npz'

def cf_grid(a):
    # The decay slows near memory one. The last grid sample is checked below.
    T=16 if a<0.73 else (32 if a<0.84 else 64)
    e=ERW(str(a),N=1600,prec=2000,K=24)
    while abs(complex(float(e.Pre(arb(T)).mid()),float(e.Pim(arb(T)).mid())))>=1e-11:
        T*=2
        if T>256: raise RuntimeError('No resolved frequency cutoff')
    t=np.linspace(0,T,2049)
    z=np.empty(t.size,dtype=complex)
    worst=0.
    for j,v in enumerate(t):
        av=arb(float(v))
        re,im=e.Pre(av),e.Pim(av)
        z[j]=complex(float(re.mid()),float(im.mid()))
        worst=max(worst,float(re.rad()),float(im.rad()))
    trunc=float(e.tail(arb(T)))
    if not (worst<1e-13 and trunc<1e-13 and abs(z[-1])<1e-11):
        raise RuntimeError(f'Unresolved Fourier grid at a={a}: {worst}, {trunc}, {abs(z[-1])}')
    return t,z,{'a':a,'T':T,'evaluation_radius':worst,'series_tail_bound':trunc,'last_cf_modulus':abs(z[-1])}

def densities(t,z,u,stride=1):
    t,z=t[::stride],z[::stride]
    theta=np.outer(u,t)
    return simpson(np.cos(theta)*z.real+np.sin(theta)*z.imag,x=t,axis=1)/np.pi

def slope(t,z,u):
    return simpson(t*(z.imag*np.cos(t*u)-z.real*np.sin(t*u)),x=t)/np.pi

def boundary(t,z):
    u=np.linspace(0,2.8,701)
    theta=np.outer(u,t)
    positive=simpson(t*(z.imag*np.cos(theta)-z.real*np.sin(theta)),x=t,axis=1)/np.pi
    negative=simpson(t*(z.imag*np.cos(theta)+z.real*np.sin(theta)),x=t,axis=1)/np.pi
    ok=(positive>1e-8)&(negative>=-1e-9)&(positive+negative>1e-7)
    values=np.full(u.size,.5)
    values[ok]=negative[ok]/(positive[ok]+negative[ok])
    j=int(np.argmin(values))
    if values[j]>=.5: return .5
    def ratio(v):
        pos,neg=slope(t,z,v),slope(t,z,-v)
        return neg/(pos+neg) if pos>0 and pos+neg>1e-7 else .5
    result=minimize_scalar(ratio,bounds=(u[max(0,j-2)],u[min(len(u)-1,j+2)]),method='bounded',options={'xatol':1e-11})
    return float(np.clip(result.fun,0,.5))

def compute():
    start=time.monotonic()
    avals=np.unique(np.r_[.62,.64,.66,ASTAR,np.linspace(.675,.9,19)])
    u=np.linspace(-3.4,3.4,1001)
    bounds=[]; audit=[]; curves=[]
    selected=[.64,ASTAR,.72]
    for a in np.unique(np.r_[avals,selected]):
        print('Limit-density grid',a,flush=True)
        checkpoint=OUT/'phase_work'
        checkpoint.mkdir(exist_ok=True)
        name=checkpoint/f'{a:.16f}.npz'
        if name.exists():
            saved=np.load(name)
            t,z=saved['t'],saved['z']
            record=json.loads(str(saved['record']))
        else:
            t,z,record=cf_grid(float(a))
            np.savez(name,t=t,z=z,record=json.dumps(record))
        b=boundary(t,z)
        b_coarse=boundary(t[::2],z[::2])
        if a<=ASTAR: b=b_coarse=.5
        record.update(b=b,b_coarse=b_coarse,b_grid_difference=abs(b-b_coarse))
        if abs(b-b_coarse)>2e-5: raise RuntimeError('Unstable bias boundary')
        if a in avals: bounds.append((a,b))
        if a in selected:
            density=(densities(t,z,u)+densities(t,z,-u))/2
            coarse=(densities(t,z,u,2)+densities(t,z,-u,2))/2
            record['density_grid_difference']=float(np.max(np.abs(density-coarse)))
            if record['density_grid_difference']>2e-6: raise RuntimeError('Unstable density plot')
            curves.append((a,density))
        audit.append(record)
    bounds=np.array(bounds)
    np.savez(CACHE,a=bounds[:,0],b=bounds[:,1],u=u,curve_a=np.array([c[0] for c in curves]),density=np.array([c[1] for c in curves]))
    (P/'data/limit_phase_illustration.json').write_text(json.dumps({'scope':'illustration, not a certificate','quadrature':'composite Simpson, 2049 and 1025 frequencies','precision_bits':2000,'moments':1600,'runs':audit,'elapsed_seconds':time.monotonic()-start},indent=2)+'\n')

def compute_conditional():
    # h_a(u) is the density of the limit given a positive first step.
    u=np.linspace(-3.4,3.4,1001)
    checkpoint=OUT/'phase_work'
    checkpoint.mkdir(exist_ok=True)
    name=checkpoint/f'{COND_A:.16f}.npz'
    if name.exists():
        saved=np.load(name)
        t,z=saved['t'],saved['z']
    else:
        t,z,record=cf_grid(COND_A)
        np.savez(name,t=t,z=z,record=json.dumps(record))
    h=densities(t,z,u)
    coarse=densities(t,z,u,2)
    if float(np.max(np.abs(h-coarse)))>2e-6: raise RuntimeError('Unstable conditional density')
    np.savez(COND_CACHE,a=COND_A,u=u,h=h)

def smooth_boundary(a,b):
    # Interpolate (1/2-b)/(a-a_*)^(3/2) in s=sqrt(a-a_*), anchored at Q_* for s=0.
    # The curve passes through every computed point and leaves q=1/2 with zero slope.
    up=a>ASTAR+1e-12
    s=np.r_[0.,np.sqrt(a[up]-ASTAR)]
    r=np.r_[QSTAR,(.5-b[up])/s[1:]**3]
    spline=CubicSpline(s,r)
    sf=np.linspace(0,s[-1],400)
    af=ASTAR+sf**2
    bf=.5-sf**3*spline(sf)
    low=a<ASTAR
    return np.r_[a[low],af],np.r_[b[low],bf]

def draw():
    d=np.load(CACHE)
    # Plain black curves with the fonts of the paper. The panels have no titles,
    # since the caption of the figure describes them.
    plt.rcParams.update({'font.family':'serif','font.serif':['cmr10','Computer Modern Roman','DejaVu Serif'],
        'mathtext.fontset':'cm','axes.formatter.use_mathtext':True,'axes.unicode_minus':False,
        'font.size':9,'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,
        'lines.linewidth':0.9,'axes.linewidth':0.5,'xtick.major.width':0.5,'ytick.major.width':0.5,
        'xtick.major.size':2.5,'ytick.major.size':2.5,
        'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
    fig=plt.figure(figsize=(6.0,4.3),layout='constrained')
    gs=fig.add_gridspec(2,3,height_ratios=[1.2,1])
    ax=fig.add_subplot(gs[0,:2])
    a,b=smooth_boundary(d['a'],d['b'])
    ax.fill_between(a,b,1-b,color='0.85',linewidth=0)
    ax.plot(a,b,color='k'); ax.plot(a,1-b,color='k')
    ax.axvline(ASTAR,color='k',ls=':',lw=0.6)
    ax.text(.805,.5,'two modes',ha='center',va='center')
    ax.text(.73,.95,'one mode',ha='center',va='top')
    ax.text(.73,.05,'one mode',ha='center',va='bottom')
    ax.set_xticks([.65,.70,.75,.80,.85,.90])
    ax.text(ASTAR,-.105,r'$a_*$',ha='center',va='top',transform=ax.get_xaxis_transform())
    ax.set(xlabel=r'$a$',ylabel=r'$q$',xlim=(.62,.9),ylim=(0,1))
    # The conditional density, its reflection and their fair mixture.
    ax=fig.add_subplot(gs[0,2])
    c=np.load(COND_CACHE)
    u,h=c['u'],c['h']
    ax.plot(u,h,color='k',lw=0.7)
    ax.plot(u,h[::-1],color='k',lw=0.7,ls='--')
    ax.plot(u,(h+h[::-1])/2,color='k',lw=1.2)
    ax.text(1.5,float(h.max())*1.06,r'$h_a(u)$',ha='center',fontsize=8)
    ax.text(-1.5,float(h.max())*1.06,r'$h_a(-u)$',ha='center',fontsize=8)
    ax.set(xlabel=r'$u$',xlim=(-3.4,3.4),ylim=(0,float(h.max())*1.2))
    for k,(a,y) in enumerate(zip(d['curve_a'],d['density'])):
        ax=fig.add_subplot(gs[1,k]); ax.plot(d['u'],y,color='k')
        ax.text(.04,.93,r'$a=a_*$' if k==1 else rf'$a={a:.2f}$',transform=ax.transAxes,ha='left',va='top',fontsize=8)
        ax.set(xlim=(-3.4,3.4),ylim=(0,float(np.max(y))*1.18),xlabel=r'$u$')
        if k==0: ax.set_ylabel(r'$g_a(u)$')
    fig.savefig(OUT/'phase.pdf')
    fig.savefig(OUT/'phase.png',dpi=180)
    print('Wrote',OUT/'phase.pdf',flush=True)

if __name__=='__main__':
    if '--rebuild' in sys.argv or not CACHE.exists(): compute()
    if '--rebuild' in sys.argv or not COND_CACHE.exists(): compute_conditional()
    draw()

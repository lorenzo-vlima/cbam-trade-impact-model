"""
Elasticidades-preço por grupo de produto — VERSÃO PONDERADA POR VALOR EXPORTADO.
Paralela a _graficos_elasticidades_combinado.py (que é por volume).
Brasil, Argentina e Global numa única figura. Setores: FA e AL.
Tudo derivado dos outputs v2 (betas por produto) e dos valores 2023-25.
"""
import csv, sys
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from matplotlib import rcParams

sys.stdout.reconfigure(encoding='utf-8')
import os; root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(chr(92), '/')
out  = root + '/figuras_geradas/'
base = root + '/outputs'
rcParams['font.family'] = 'sans-serif'
rcParams['font.size']   = 10

# ── load betas + group + value weights per sector ─────────────────────────────
def load_sector(setor):
    bdir = f'{base}/{setor}_brasil_e_argentina_individual_post_tax_j3_v2'
    binfo = {}
    with open(f'{bdir}/8_tabela_betas_grupos.csv', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            p = r['product'].strip()
            try:
                binfo[p] = {
                    'BR': float(r['beta_sim_BR']),
                    'AR': float(r['beta_sim_AR']),
                    'GL': float(r['beta_base']),
                    'grupo': (r.get('grupo_label','').strip()
                              or r.get('grupo','').strip()),
                }
            except: pass
    val = {'BR': defaultdict(float), 'AR': defaultdict(float)}
    with open(f'{bdir}/28_analise_share_vol_base.csv', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            e = r['exporter'].strip()
            if e in val:
                try: val[e][r['product'].strip()] += float(r['euro_exportado'])
                except: pass
    return binfo, val

def group_betas(binfo, val):
    """Returns {grupo: {'BR':beta,'AR':beta,'GL':beta,'volBR':%,'volAR':%}}"""
    tot = {'BR': sum(val['BR'].values()), 'AR': sum(val['AR'].values())}
    acc = defaultdict(lambda: {'BR':[0.,0.],'AR':[0.,0.],'GL':[0.,0.],
                               'vBR':0.,'vAR':0.})
    for p, b in binfo.items():
        g = b['grupo'] or '(sem grupo)'
        for c in ['BR','AR']:
            w = val[c].get(p, 0.)
            if w > 0:
                acc[g][c][0] += b[c]*w; acc[g][c][1] += w
            acc[g]['v'+c] += w
        wt = val['BR'].get(p,0.) + val['AR'].get(p,0.)
        if wt > 0:
            acc[g]['GL'][0] += b['GL']*wt; acc[g]['GL'][1] += wt
    res = {}
    for g, d in acc.items():
        def wm(x): return d[x][0]/d[x][1] if d[x][1] > 0 else float('nan')
        res[g] = {'BR': wm('BR'), 'AR': wm('AR'), 'GL': wm('GL'),
                  'volBR': d['vBR']/tot['BR']*100 if tot['BR']>0 else 0,
                  'volAR': d['vAR']/tot['AR']*100 if tot['AR']>0 else 0}
    return res

def sector_beta(binfo, val, c):
    num=den=0.
    for p,b in binfo.items():
        w=val[c].get(p,0.)
        if w>0: num+=b[c]*w; den+=w
    return num/den if den>0 else float('nan')

def sector_beta_global(binfo, val):
    num=den=0.
    for p,b in binfo.items():
        w=val['BR'].get(p,0.)+val['AR'].get(p,0.)
        if w>0: num+=b['GL']*w; den+=w
    return num/den if den>0 else float('nan')

# ── group ordering (primary -> complex), matching the volume figure ───────────
ORDER = {
    'ferro_aco': ['Produtos primários','Semiacabados e planos','Longos e tubulares'],
    'aluminio':  ['Primário e semi-acabado','Laminados e tubulares','Manufaturados e acabados'],
}
LABELS = {
    'Produtos primários':'Primaries\n(ore/pig iron)',
    'Semiacabados e planos':'Semi-finished\n& flat',
    'Longos e tubulares':'Long &\ntubular',
    'Primário e semi-acabado':'Primary &\nsemi-finished',
    'Laminados e tubulares':'Rolled &\ntubular',
    'Manufaturados e acabados':'Manufactured\n& finished',
}

COR_FA='#2c6e9e'; COR_AL='#c0392b'
COR_AR='#e67e22'; COR_GL='#888888'

FS_TITLE=13; FS_XLABEL=10.5; FS_XTICK=9; FS_YTICK=10.5
FS_VOL=8.5; FS_BETA=7.8; FS_SET=7.5; FS_LEGEND=9.5; FS_NOTE=8
BETA_THR=0.08
LBBOX=dict(boxstyle='round,pad=0.12',facecolor='white',edgecolor='none',alpha=0.88)


def vol_annot(ax, val, yy, col, vol):
    if vol <= 2.0: return
    kw=dict(boxstyle='round,pad=0.08',facecolor='white',edgecolor='none',alpha=0.82)
    side=-18 if val>-0.5 else 11
    ha='right' if side<0 else 'left'
    ax.annotate(f'{vol:.0f}%',xy=(val,yy),xytext=(side,0),
                textcoords='offset points',fontsize=FS_VOL,color=col,
                va='center',ha=ha,alpha=0.85,clip_on=False,bbox=kw)


def plot_panel(ax, setor, cor_setor, titulo, x_min, x_max):
    binfo, val = load_sector(setor)
    grp = group_betas(binfo, val)
    order = [g for g in ORDER[setor] if g in grp]
    n = len(order)
    y_pos = list(range(n, 0, -1))

    for y, g in zip(y_pos, order):
        d = grp[g]
        b_br, b_ar, b_gl = d['BR'], d['AR'], d['GL']
        v_br, v_ar = d['volBR'], d['volAR']

        bs = [v for v in [b_br,b_ar,b_gl] if v==v]
        if bs:
            ax.plot([min(bs),max(bs)],[y,y],color='#cccccc',lw=1.3,zorder=1,alpha=0.8)
        if b_gl==b_gl:
            ax.scatter(b_gl,y,s=80,color=COR_GL,marker='s',zorder=3,
                       linewidths=0.6,edgecolors='#666',alpha=0.85)
        if b_ar==b_ar:
            ax.scatter(b_ar,y,s=max(75,60+v_ar*14),color=COR_AR,marker='^',
                       zorder=5,linewidths=1.2,edgecolors='white',alpha=0.95)
        if b_br==b_br:
            ax.scatter(b_br,y,s=max(75,60+v_br*14),color=cor_setor,marker='o',
                       zorder=6,linewidths=1.2,edgecolors='white',alpha=0.95)
            ax.text(b_br,y+0.22,f'{b_br:.2f}',fontsize=FS_BETA,color=cor_setor,
                    ha='center',va='bottom',zorder=8,clip_on=False,bbox=LBBOX)
        if b_ar==b_ar:
            ax.text(b_ar,y-0.22,f'{b_ar:.2f}',fontsize=FS_BETA,color=COR_AR,
                    ha='center',va='top',zorder=8,clip_on=False,bbox=LBBOX)
        if b_gl==b_gl and (b_br!=b_br or abs(b_gl-b_br)>BETA_THR) \
                       and (b_ar!=b_ar or abs(b_gl-b_ar)>BETA_THR):
            ax.text(b_gl,y+0.22,f'{b_gl:.2f}',fontsize=FS_BETA-0.5,color='#666',
                    ha='center',va='bottom',zorder=7,clip_on=False,bbox=LBBOX)
        vol_annot(ax,b_br,y,cor_setor,v_br)
        vol_annot(ax,b_ar,y,COR_AR,v_ar)

    # sector betas
    bsec_br=sector_beta(binfo,val,'BR'); bsec_ar=sector_beta(binfo,val,'AR')
    bsec_gl=sector_beta_global(binfo,val)
    for bsec,col,ls,lw in [(bsec_br,cor_setor,':',1.4),
                            (bsec_ar,COR_AR,'-.',1.2),
                            (bsec_gl,COR_GL,'--',1.0)]:
        if bsec==bsec:
            ax.axvline(bsec,color=col,lw=lw,ls=ls,alpha=0.55,zorder=0)
            ax.text(bsec+0.07,0.35,f'{bsec:.3f}',fontsize=FS_SET,color=col,
                    alpha=0.85,va='bottom',ha='left')

    ax.axvline(0,color='#cccccc',lw=0.8,ls='--',zorder=0)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([LABELS.get(g,g) for g in order],fontsize=FS_YTICK)
    ax.set_title(titulo,fontsize=FS_TITLE,fontweight='bold',color=cor_setor,pad=10)
    ax.set_xlim(x_min,x_max); ax.set_ylim(0.2,n+1.0)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.grid(axis='x',alpha=0.18,linestyle='--')
    ax.tick_params(axis='x',labelsize=FS_XTICK)


fig, axes = plt.subplots(1, 2, figsize=(11, 5.4),
                         gridspec_kw={'width_ratios':[1,1]})
plot_panel(axes[0],'ferro_aco',COR_FA,'Iron & Steel',x_min=-4.2,x_max=0.6)
plot_panel(axes[1],'aluminio', COR_AL,'Aluminium',   x_min=-2.5,x_max=0.5)
axes[0].set_xlabel('Market share price elasticity (β)',fontsize=FS_XLABEL,labelpad=7)
axes[1].set_xlabel('Market share price elasticity (β)',fontsize=FS_XLABEL,labelpad=7)

dot_br=mlines.Line2D([],[],color=COR_FA,marker='o',linestyle='None',markersize=8,
                     label='Brazil (circle, size ∝ export VALUE share 2023–25)')
dot_ar=mlines.Line2D([],[],color=COR_AR,marker='^',linestyle='None',markersize=8,
                     label='Argentina (triangle, size ∝ export VALUE share)')
dot_gl=mlines.Line2D([],[],color=COR_GL,marker='s',linestyle='None',markersize=6,
                     label='Global β (gray square)')
lin_br=mlines.Line2D([],[],color=COR_FA,linestyle=':',linewidth=1.4,
                     label='Sector β — Brazil (value-weighted, dotted)')
lin_ar=mlines.Line2D([],[],color=COR_AR,linestyle='-.',linewidth=1.2,
                     label='Sector β — Argentina (dash-dot)')
lin_gl=mlines.Line2D([],[],color=COR_GL,linestyle='--',linewidth=1.0,
                     label='Sector β — Global (dashed)')
fig.legend(handles=[dot_br,dot_ar,dot_gl,lin_br,lin_ar,lin_gl],
           fontsize=FS_LEGEND,loc='lower center',ncol=3,
           bbox_to_anchor=(0.5,0.0),framealpha=0.95)

fig.text(0.01,-0.06,
         'Note: β above = Brazil; β below = Argentina; global β omitted when ≈ Brazil. '
         'Bubbles & sector β weighted by EXPORT VALUE (€).',
         fontsize=FS_NOTE,color='#555',style='italic')

fig.suptitle('Market-share price elasticities by product group — value-weighted '
             '(Brazil, Argentina, Global)',
             fontsize=FS_TITLE,fontweight='bold',y=1.03)

plt.tight_layout(w_pad=2.8,rect=[0,0.14,1,1])
plt.savefig(out+'G1_elasticidades_combinado_valor.png',dpi=300,bbox_inches='tight')
plt.close()
print('Salvo: G1_elasticidades_combinado_valor.png')

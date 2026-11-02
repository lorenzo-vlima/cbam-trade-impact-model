"""
Bubble chart — CBAM impact per product, Brazil and Argentina side by side.
  X = market-share change (pp)
  Y = base export volume (kt)
  bubble size = |Δ revenue| (M€)
  color = gain (green) / loss (red)
Sector: Iron & Steel | scenario 75€/tCO2, MFN
"""
import csv, sys, math
from collections import defaultdict
import matplotlib.pyplot as plt
from matplotlib import rcParams

sys.stdout.reconfigure(encoding='utf-8')
import os; root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(chr(92), '/')
# Run folder = <sector>_<RUN>_<TAG>. RUN is NOME in rodar_modelo.R; override with the
# environment variables CBAM_RUN / CBAM_TAG if your runs are named differently.
RUN = os.environ.get('CBAM_RUN', 'brazil_and_argentina')
TAG = os.environ.get('CBAM_TAG', 'individual_post_tax_j3_v2')
out  = root + '/figuras_geradas/'
os.makedirs(out, exist_ok=True)
base = root + '/outputs'
rcParams['font.family'] = 'sans-serif'

SETOR = 'ferro_aco'
NOME  = 'Iron & Steel'
CEN   = '75/tCO2'
TAR   = 'MFN'

vdir = f'{base}/{SETOR}_{RUN}_{TAG}'

# base volume & value per exporter×product
basevol = {}
with open(f'{vdir}/28_analise_share_vol_base.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        basevol[(r['exporter'].strip(), r['product'].strip())] = {
            'ton': float(r['ton_pais']),
            'eur': float(r['euro_exportado']),
        }

# CBAM impact per product (delta_share_pp, delta_share_pct)
rows = defaultdict(list)
with open(f'{vdir}/14_cbam_resumo_product.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        if r['cenario_carbono'].strip()!=CEN or r['cenario_tarifa'].strip()!=TAR:
            continue
        exp = r['exporter'].strip(); prod = r['product'].strip()
        bv = basevol.get((exp, prod))
        if not bv: continue
        try:
            dpp  = float(r['delta_share_pp'])      # share change in pp (fraction)
            dpct = float(r['delta_share_pct'])     # % change of share
        except: continue
        # Δ revenue: relative share change applied to base export value.
        d_eur = (dpct/100.0) * bv['eur']
        rows[exp].append({
            'prod':  prod,
            'dpp':   dpp*100,              # market-share change in pp
            'ton':   bv['ton'],            # tonnes (for volume share calc)
            'd_eur': d_eur/1e6,            # M€ (signed)
        })

# convert base volume to each country's % of total CBAM-affected volume
for exp, lst in rows.items():
    tot = sum(d['ton'] for d in lst)
    for d in lst:
        d['vol_share'] = d['ton']/tot*100 if tot>0 else 0

COR_GAIN = '#2ca02c'
COR_LOSS = '#d62728'

from matplotlib.lines import Line2D

from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset

def _draw_bubbles(ax, data, emax, label=True, fs=9.5):
    xs   = [d['dpp']  for d in data]
    ys   = [d['ton']/1e3 for d in data]
    eur  = [abs(d['d_eur']) for d in data]
    cols = [COR_GAIN if d['dpp']>=0 else COR_LOSS for d in data]
    sizes = [80 + 2600*(e/emax) for e in eur]
    ax.axvline(0, ls='--', color='gray', lw=1.0, alpha=0.7)
    ax.scatter(xs, ys, s=sizes, c=cols, alpha=0.55,
               edgecolors='white', linewidths=0.7, zorder=3)
    if label:
        for k, d in enumerate(sorted(data, key=lambda d: d['dpp'])):
            up = (k % 2 == 0)
            ax.annotate(d['prod'], (d['dpp'], d['ton']/1e3),
                        xytext=(0, 11 if up else -14),
                        textcoords='offset points',
                        fontsize=fs, color='#333', ha='center',
                        va='bottom' if up else 'top', zorder=6)

def make_fig(exp, nome_p, cor_t, fname, zoom_frac=0.18):
    alldata = rows.get(exp, [])
    if not alldata:
        print(f'no data for {exp}'); return

    data = sorted(alldata, key=lambda d: -abs(d['d_eur']))[:10]
    emax = max(abs(d['d_eur']) for d in data) or 1

    fig, ax = plt.subplots(figsize=(11, 4.6))
    _draw_bubbles(ax, data, emax, label=True)

    xs = [d['dpp'] for d in data]; ys = [d['ton']/1e3 for d in data]
    xmin, xmax = min(xs), max(xs)
    span = max(xmax - xmin, 1e-4)
    ax.set_xlim(xmin - span*0.20, xmax + span*0.20)
    ymax = max(ys) if ys else 1
    ax.set_ylim(-ymax*0.10, ymax*1.20)

    ax.set_xlabel('Market-share change (pp)', fontsize=12.5)
    ax.set_ylabel('Base export\nvolume (kt)', fontsize=12)
    ax.set_title(f'{NOME} — CBAM impact, top 10 products — {nome_p}  '
                 f'(scenario {CEN}, {TAR})',
                 fontsize=13.5, fontweight='bold', color=cor_t, pad=10)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(alpha=0.12, ls='--')
    ax.tick_params(labelsize=11)

    # ── zoom inset on the cluster near x=0 (low-volume, small-share products) ──
    # cluster = products with both small |Δshare| and low volume (the messy area)
    vol_thr = ymax * 0.25
    cluster = [d for d in data
               if abs(d['dpp']) <= span*zoom_frac and d['ton']/1e3 <= vol_thr]
    if len(cluster) >= 2:
        cx = [d['dpp'] for d in cluster]; cy = [d['ton']/1e3 for d in cluster]
        zx0, zx1 = min(cx), max(cx)
        zy0, zy1 = min(cy), max(cy)
        zsx = max(zx1 - zx0, span*0.04); zsy = max(zy1 - zy0, ymax*0.04)
        axins = inset_axes(ax, width='40%', height='46%',
                           loc='upper right',
                           bbox_to_anchor=(-0.02, -0.02, 1, 1),
                           bbox_transform=ax.transAxes)
        # smaller bubble scaling inside the zoom so they don't overflow
        for d in cluster:
            e = abs(d['d_eur'])
            axins.scatter([d['dpp']], [d['ton']/1e3],
                          s=40 + 900*(e/emax),
                          c=COR_GAIN if d['dpp']>=0 else COR_LOSS,
                          alpha=0.55, edgecolors='white', linewidths=0.6, zorder=3)
        axins.axvline(0, ls='--', color='gray', lw=0.8, alpha=0.7)
        # spread labels: cycle through 4 positions (up/down × near/far) and
        # alternate horizontal anchor so neighbouring labels don't overlap
        cl_sorted = sorted(cluster, key=lambda d: d['dpp'])
        pos_cycle = [(11, 'bottom', 'left'), (-13, 'top', 'right'),
                     (20, 'bottom', 'right'), (-22, 'top', 'left')]
        for k, d in enumerate(cl_sorted):
            dy, va, ha = pos_cycle[k % 4]
            dx = 4 if ha == 'left' else -4
            axins.annotate(d['prod'], (d['dpp'], d['ton']/1e3),
                           xytext=(dx, dy), textcoords='offset points',
                           fontsize=7.3, color='#333', ha=ha, va=va, zorder=6)
        axins.set_xlim(zx0 - zsx*0.9, zx1 + zsx*0.9)
        axins.set_ylim(zy0 - zsy*1.3, zy1 + zsy*1.6)
        axins.tick_params(labelsize=7)
        axins.grid(alpha=0.12, ls='--')
        for sp in axins.spines.values():
            sp.set_edgecolor('#888'); sp.set_linewidth(0.9)
        axins.set_title('zoom: cluster near 0', fontsize=7.5, color='#666', pad=2)
        mark_inset(ax, axins, loc1=2, loc2=4, fc='none', ec='#999', lw=0.8)

    refs = [v for v in [emax*0.25, emax*0.5, emax] if v>0]
    handles = [Line2D([0],[0], marker='o', linestyle='none',
                      markerfacecolor='gray', markeredgecolor='white',
                      markersize=math.sqrt(80+2600*(rv/emax))/2.4,
                      label=f'{rv:.1f}') for rv in refs]
    leg1 = ax.legend(handles=handles, title='|Δ revenue| (M€)',
                     loc='center left', bbox_to_anchor=(1.01, 0.35),
                     fontsize=9.5, title_fontsize=9.5,
                     framealpha=0.9, labelspacing=1.6, borderpad=0.9)
    ax.add_artist(leg1)
    gl = [Line2D([0],[0], marker='o', linestyle='none', markerfacecolor=COR_GAIN,
                 markeredgecolor='white', markersize=10, label='Share gain'),
          Line2D([0],[0], marker='o', linestyle='none', markerfacecolor=COR_LOSS,
                 markeredgecolor='white', markersize=10, label='Share loss')]
    ax.legend(handles=gl, loc='center left', bbox_to_anchor=(1.01, 0.80),
              fontsize=10, framealpha=0.9)

    plt.tight_layout()
    plt.savefig(out + fname, dpi=300, bbox_inches='tight')
    plt.close()
    print(f'Saved: {fname}')

make_fig('BR', 'Brazil',    '#2c6e9e', 'G_bubble_br.png')
make_fig('AR', 'Argentina', '#e67e22', 'G_bubble_ar.png')

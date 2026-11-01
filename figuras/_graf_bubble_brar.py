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
root = 'C:/Users/loren/OneDrive/Documentos/TCC CBAM/Projeto R/Versão Claude code/MODELO_OFICIAL'
out  = root + '/figuras_geradas/'
base = root + '/outputs'
rcParams['font.family'] = 'sans-serif'

SETOR = 'ferro_aco'
NOME  = 'Iron & Steel'
CEN   = '75/tCO2'
TAR   = 'MFN'

vdir = f'{base}/{SETOR}_brasil_e_argentina_individual_post_tax_j3_v2'

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

fig, axes = plt.subplots(1, 2, figsize=(15, 6.5), sharey=False)

cfg = [('BR','Brazil','#2c6e9e'), ('AR','Argentina','#e67e22')]

for ax, (exp, nome_p, cor_t) in zip(axes, cfg):
    data = rows.get(exp, [])
    if not data:
        ax.set_visible(False); continue

    xs   = [d['dpp']       for d in data]
    ys   = [d['vol_share'] for d in data]
    eur  = [abs(d['d_eur']) for d in data]
    cols = [COR_GAIN if d['dpp']>=0 else COR_LOSS for d in data]

    emax = max(eur) if eur else 1
    sizes = [40 + 1400*(e/emax) for e in eur]   # area scaling

    ax.axvline(0, ls='--', color='gray', lw=1.0, alpha=0.7)
    ax.scatter(xs, ys, s=sizes, c=cols, alpha=0.55,
               edgecolors='white', linewidths=0.6, zorder=3)
    ax.set_ylim(-4, 100)

    # label the most relevant bubbles (by |Δ revenue|), alternating offset
    ranked = sorted(data, key=lambda d: -abs(d['d_eur']))
    to_label = [d for d in ranked[:14]]
    to_label_sorted = sorted(to_label, key=lambda d: d['dpp'])
    for k, d in enumerate(to_label_sorted):
        up = (k % 2 == 0)
        ax.annotate(d['prod'], (d['dpp'], d['vol_share']),
                    xytext=(0, 11 if up else -14),
                    textcoords='offset points',
                    fontsize=7.8, color='#333', ha='center',
                    va='bottom' if up else 'top', zorder=6)

    ax.set_xlabel('Market-share change (pp)', fontsize=11)
    if exp=='BR':
        ax.set_ylabel('Share of country export volume (%)', fontsize=11)
    ax.set_title(nome_p, fontsize=14, fontweight='bold', color=cor_t, pad=8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(alpha=0.12, ls='--')
    ax.tick_params(labelsize=10)

    # per-country bubble-size legend
    from matplotlib.lines import Line2D
    refs = [v for v in [emax*0.25, emax*0.5, emax] if v>0]
    handles = [Line2D([0],[0], marker='o', linestyle='none',
                      markerfacecolor='gray', markeredgecolor='white',
                      markersize=math.sqrt(40+1400*(rv/emax))/2.2,
                      label=f'{rv:.0f}') for rv in refs]
    leg1 = ax.legend(handles=handles, title='|Δ revenue| (M€)',
                     loc='lower left', fontsize=8, title_fontsize=8,
                     framealpha=0.9, labelspacing=1.4, borderpad=1.0)
    ax.add_artist(leg1)
    gl = [Line2D([0],[0], marker='o', linestyle='none', markerfacecolor=COR_GAIN,
                 markeredgecolor='white', markersize=8, label='Share gain'),
          Line2D([0],[0], marker='o', linestyle='none', markerfacecolor=COR_LOSS,
                 markeredgecolor='white', markersize=8, label='Share loss')]
    ax.legend(handles=gl, loc='lower right', fontsize=8.5, framealpha=0.9)

fig.suptitle(
    f'{NOME} — CBAM impact per product (scenario {CEN}, {TAR})\n'
    f'X: market-share change (pp)  |  Y: share of country export volume (%)  |  bubble: |Δ revenue| (M€)',
    fontsize=12.5, fontweight='bold', y=1.02)

plt.tight_layout(w_pad=3.0)
plt.savefig(out + 'G_bubble_brar.png', dpi=300, bbox_inches='tight')
plt.close()
print('Saved: G_bubble_brar.png')

"""
Aluminium summary — v2: Brazil only (Argentina aluminium not simulated).
Market share, volume and value impact, by carbon price and tariff regime.
Label rule: each metric's numbers (MFN bold | Mercosur lighter) sit ABOVE
its line, except the value (red) line, whose numbers sit BELOW.
"""
import csv, sys
import matplotlib.pyplot as plt
from matplotlib import rcParams

sys.stdout.reconfigure(encoding='utf-8')
root = 'C:/Users/loren/OneDrive/Documentos/TCC CBAM/Projeto R/Versão Claude code/MODELO_OFICIAL'
out  = root + '/figuras_geradas/'
base = root + '/outputs'
rcParams['font.family'] = 'sans-serif'

path = f'{base}/aluminio_brasil_e_argentina_individual_post_tax_j3_v2/13_cbam_resumo_pais.csv'
rows = list(csv.DictReader(open(path, encoding='utf-8')))

carb = [75, 95, 115]
def serie(exp, tarifa, col):
    d = {int(float(r['preco_carbono_eur'])): float(r[col]) for r in rows
         if r['exporter']==exp and r['cenario_tarifa']==tarifa}
    return [d[c] for c in carb]

COR_SHARE = '#7f8c8d'
COR_TON   = '#2c6e9e'
COR_EUR   = '#c0392b'

fig, ax = plt.subplots(figsize=(9.0, 4.6))

metrics = [
    ('variacao_relativa_pct', COR_SHARE, 'Market share', 'D', 'above'),
    ('delta_ton_pct',         COR_TON,   'Volume (ton)', 'o', 'above'),
    ('delta_euro_pct',        COR_EUR,   'Value (€)',    's', 'below'),
]

for col, cor, lbl, mk, side in metrics:
    mfn = serie('BR', 'MFN', col)
    mer = serie('BR', 'Mercosul', col)
    ax.plot(carb, mfn, color=cor, lw=2.4, marker=mk, ms=8,
            label=f'{lbl} — MFN')
    ax.plot(carb, mer, color=cor, lw=1.8, marker=mk, ms=6,
            ls='--', alpha=0.65, label=f'{lbl} — Mercosur')

    # Number next to its own line: above all lines, except value (red) -> below.
    dyo = 11 if side == 'above' else -12
    va  = 'bottom' if side == 'above' else 'top'

    # For Market share and Value, the first/last scenario MFN labels go to the
    # lateral (left on 75, right on 115) to avoid the legend / crowded center.
    lateral_metric = col in ('variacao_relativa_pct', 'delta_euro_pct')

    # market share (gray): force its middle-scenario number BELOW the line
    is_share = (col == 'variacao_relativa_pct')

    for idx, (xv, yv) in enumerate(zip(carb, mfn)):
        if lateral_metric and idx == 0:        # left lateral
            ax.annotate(f'{yv:.1f}', (xv, yv), xytext=(-8, 0),
                        textcoords='offset points', fontsize=9.5,
                        color=cor, ha='right', va='center', fontweight='bold')
        elif lateral_metric and idx == 2:      # right lateral
            ax.annotate(f'{yv:.1f}', (xv, yv), xytext=(8, 0),
                        textcoords='offset points', fontsize=9.5,
                        color=cor, ha='left', va='center', fontweight='bold')
        else:
            d, v = (dyo, va)
            if is_share and idx == 1:          # gray middle -> below
                d, v = (-12, 'top')
            ax.annotate(f'{yv:.1f}', (xv, yv), xytext=(0, d),
                        textcoords='offset points', fontsize=9.5,
                        color=cor, ha='center', va=v, fontweight='bold')
    for idx, (xv, yv) in enumerate(zip(carb, mer)):
        d, v = (dyo, va)
        if is_share and idx == 1:              # gray middle Mercosur -> below
            d, v = (-12, 'top')
        ax.annotate(f'{yv:.1f}', (xv, yv), xytext=(0, d),
                    textcoords='offset points', fontsize=9,
                    color=cor, ha='center', va=v, alpha=0.6)

ax.axhline(0, color='#888', lw=0.9)
ax.set_xticks(carb)
ax.set_xlim(carb[0]-14, carb[-1]+14)
ax.set_xlabel('Carbon price (€/tCO₂)', fontsize=12.5)
ax.set_ylabel('Change in EU exports (%)', fontsize=12.5)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.grid(axis='y', alpha=0.15, ls='--')
ax.tick_params(labelsize=11.5)
# horizontal legend at the top
ax.legend(fontsize=11, loc='lower center', bbox_to_anchor=(0.5, 1.10),
          framealpha=0.95, ncol=3)

fig.suptitle(
    'Aluminium — CBAM impact on Brazilian EU exports',
    fontsize=14, fontweight='bold', y=1.16)

plt.tight_layout()
plt.savefig(out + 'G_sim_AL_resumo_v2.png', dpi=300, bbox_inches='tight')
plt.close()
print('Saved: G_sim_AL_resumo_v2.png')

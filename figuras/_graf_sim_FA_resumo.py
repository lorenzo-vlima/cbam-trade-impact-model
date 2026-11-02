"""
Iron & Steel summary figure: physical impact (tonnes) vs. economic impact (euros)
across the carbon price, MFN vs Mercosul, Brazil and Argentina.

Mostra a imagem espelhada:
  Brazil    -> the euro impact AMPLIFIES the physical one (high-value products)
  Argentina -> the euro impact DAMPENS the physical one (lower-value products)
"""
import csv, sys
import matplotlib.pyplot as plt
from matplotlib import rcParams

sys.stdout.reconfigure(encoding='utf-8')
import os; root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(chr(92), '/')
out  = root + '/figuras_geradas/'
base = root + '/outputs'
rcParams['font.family'] = 'sans-serif'

path = f'{base}/ferro_aco_brasil_e_argentina_individual_post_tax_j3_v2/13_cbam_resumo_pais.csv'
rows = list(csv.DictReader(open(path, encoding='utf-8')))

carb = [75, 95, 115]
def serie(exp, tarifa, col):
    d = {int(float(r['preco_carbono_eur'])): float(r[col]) for r in rows
         if r['exporter']==exp and r['cenario_tarifa']==tarifa}
    return [d[c] for c in carb]

COR_TON  = '#2c6e9e'
COR_EUR  = '#c0392b'

fig, axes = plt.subplots(1, 2, figsize=(12, 5.5), sharey=True)

for ax, exp, nome in zip(axes, ['BR','AR'], ['Brazil','Argentina']):
    ton_mfn = serie(exp,'MFN','delta_ton_pct')
    ton_mer = serie(exp,'Mercosul','delta_ton_pct')
    eur_mfn = serie(exp,'MFN','delta_euro_pct')
    eur_mer = serie(exp,'Mercosul','delta_euro_pct')

    ax.plot(carb, ton_mfn, color=COR_TON, lw=2.2, marker='o', ms=7,
            label='Volume (ton) — MFN')
    ax.plot(carb, ton_mer, color=COR_TON, lw=1.8, marker='o', ms=6,
            ls='--', alpha=0.7, label='Volume (ton) — Mercosul')
    ax.plot(carb, eur_mfn, color=COR_EUR, lw=2.2, marker='s', ms=7,
            label='Value (€) — MFN')
    ax.plot(carb, eur_mer, color=COR_EUR, lw=1.8, marker='s', ms=6,
            ls='--', alpha=0.7, label='Value (€) — Mercosul')

    # annotations on the extreme MFN points (115)
    ax.annotate(f'{ton_mfn[-1]:.1f}%', (carb[-1], ton_mfn[-1]),
                xytext=(6,0), textcoords='offset points', fontsize=8.5,
                color=COR_TON, va='center', fontweight='bold')
    ax.annotate(f'{eur_mfn[-1]:.1f}%', (carb[-1], eur_mfn[-1]),
                xytext=(6,0), textcoords='offset points', fontsize=8.5,
                color=COR_EUR, va='center', fontweight='bold')

    ax.axhline(0, color='#ccc', lw=0.8)
    ax.set_title(nome, fontsize=13, fontweight='bold',
                 color=COR_TON if exp=='BR' else '#e67e22')
    ax.set_xlabel('Carbon price (€/tCO₂)', fontsize=10.5)
    ax.set_xticks(carb)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', alpha=0.15, ls='--')
    ax.tick_params(labelsize=9.5)

axes[0].set_ylabel('Change in EU exports (%)', fontsize=10.5)
axes[0].legend(fontsize=8.5, loc='lower left', framealpha=0.95)

fig.suptitle(
    'Iron & Steel — CBAM impact on Brazilian and Argentine EU exports\n'
    'Physical (volume) vs. economic (value) impact, by carbon price and tariff regime',
    fontsize=11.5, fontweight='bold', y=1.02)

plt.tight_layout()
plt.savefig(out + 'G_sim_FA_resumo.png', dpi=300, bbox_inches='tight')
plt.close()
print('Saved: G_sim_FA_resumo.png')

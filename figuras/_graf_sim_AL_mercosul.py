"""
Aluminium summary figure: the Mercosul effect reverses the sign.
Brazil: Δ share under MFN (loss) vs. Mercosul (gain/neutralisation).
Removing the MFN tariff (~6%) offsets the CBAM cost (~6% at EUR 75).
"""
import csv, sys
import matplotlib.pyplot as plt
from matplotlib import rcParams

sys.stdout.reconfigure(encoding='utf-8')
import os; root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(chr(92), '/')
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

COR_MFN = '#c0392b'
COR_MER = '#27ae60'

fig, ax = plt.subplots(figsize=(9, 5.5))

x = range(len(carb))
width = 0.36

mfn = serie('BR','MFN','variacao_relativa_pct')
mer = serie('BR','Mercosul','variacao_relativa_pct')

b1 = ax.bar([i-width/2 for i in x], mfn, width, color=COR_MFN, alpha=0.85,
            label='CBAM only (MFN tariff kept)', edgecolor='white')
b2 = ax.bar([i+width/2 for i in x], mer, width, color=COR_MER, alpha=0.85,
            label='CBAM + EU–Mercosur (MFN tariff removed)', edgecolor='white')

for bars in (b1, b2):
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x()+bar.get_width()/2, h + (0.15 if h>=0 else -0.15),
                f'{h:+.1f}%', ha='center', va='bottom' if h>=0 else 'top',
                fontsize=9, fontweight='bold',
                color=COR_MFN if bar in b1 else COR_MER)

ax.axhline(0, color='#444', lw=1.0)
ax.set_xticks(list(x))
ax.set_xticklabels([f'{c}€/tCO₂' for c in carb], fontsize=10.5)
ax.set_ylabel('Change in market share (%)', fontsize=10.5)
ax.set_xlabel('Carbon price', fontsize=10.5)
ax.legend(fontsize=9.5, loc='upper right', framealpha=0.95)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.grid(axis='y', alpha=0.15, ls='--')
ax.tick_params(labelsize=9.5)

# faixa de destaque do flip
ax.axhspan(0, ax.get_ylim()[1], alpha=0.04, color='green')
ax.axhspan(ax.get_ylim()[0], 0, alpha=0.04, color='red')

fig.suptitle(
    'Aluminium — Brazil: the EU–Mercosur agreement offsets the CBAM\n'
    'Removing the ~6% MFN tariff compensates the ~6% CBAM cost (at 75€/tCO₂),\n'
    'flipping the market-share impact from loss to gain',
    fontsize=11, fontweight='bold', y=1.04)

plt.tight_layout()
plt.savefig(out + 'G_sim_AL_mercosul.png', dpi=300, bbox_inches='tight')
plt.close()
print('Saved: G_sim_AL_mercosul.png')

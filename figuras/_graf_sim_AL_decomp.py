"""
Aluminium — Brazil: decomposing the Mercosur share effect into
  (i) CBAM carbon penalty (MFN regime, tariff kept) — negative
  (ii) Mercosur tariff relief (Mercosur − MFN)       — positive, ~constant
  (iii) Net effect (Mercosur)                         — the sum

Shows WHY Brazil gains share in every scenario: the unilateral ~5% tariff
relief outweighs the carbon penalty, while the penalty (vs the CBAM-exempt
EU/EFTA bloc, ~71% of the market) grows with the carbon price and erodes
— but does not flip — the net gain.
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
def val(tarifa, c):
    for r in rows:
        if (r['exporter']=='BR' and r['cenario_tarifa']==tarifa
                and int(float(r['preco_carbono_eur']))==c):
            return float(r['variacao_relativa_pct'])
    return float('nan')

carbon_eff = [val('MFN', c)               for c in carb]            # negative
net_eff    = [val('Mercosul', c)          for c in carb]            # net
tariff_eff = [net_eff[i]-carbon_eff[i]    for i in range(len(carb))]# positive

COR_CARB = '#c0392b'   # carbon penalty (red)
COR_TAR  = '#27ae60'   # tariff relief (green)
COR_NET  = '#2c3e50'   # net (dark)

fig, ax = plt.subplots(figsize=(10, 6))

x = range(len(carb))
w = 0.26

# Carbon penalty (negative, from 0 downward)
b1 = ax.bar([i-w for i in x], carbon_eff, w, color=COR_CARB, alpha=0.85,
            edgecolor='white', label='CBAM carbon penalty (MFN, tariff kept)')
# Tariff relief (positive)
b2 = ax.bar([i for i in x], tariff_eff, w, color=COR_TAR, alpha=0.85,
            edgecolor='white', label='Mercosur tariff relief (unilateral to Brazil)')
# Net
b3 = ax.bar([i+w for i in x], net_eff, w, color=COR_NET, alpha=0.85,
            edgecolor='white', label='Net effect (CBAM + Mercosur)')

for bars in (b1, b2, b3):
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x()+bar.get_width()/2,
                h + (0.18 if h>=0 else -0.18),
                f'{h:+.1f}', ha='center',
                va='bottom' if h>=0 else 'top',
                fontsize=9, fontweight='bold', color=bar.get_facecolor())

ax.axhline(0, color='#444', lw=1.0)
ax.set_xticks(list(x))
ax.set_xticklabels([f'{c}€/tCO₂' for c in carb], fontsize=11)
ax.set_ylabel('Change in market share (%)', fontsize=11)
ax.set_xlabel('Carbon price', fontsize=11)
ax.legend(fontsize=9.5, loc='upper center', bbox_to_anchor=(0.5, -0.10), ncol=1,
          framealpha=0.95)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.grid(axis='y', alpha=0.15, ls='--')
ax.tick_params(labelsize=10)

fig.suptitle(
    'Aluminium — Brazil: why the share gain persists across all scenarios\n'
    'Tariff relief is unilateral and ~constant (~+6.7 pp); the carbon penalty grows\n'
    'with the carbon price but the net effect stays positive (+3.3 → +1.5 pp)',
    fontsize=11, fontweight='bold', y=1.00)

plt.tight_layout(rect=[0, 0.04, 1, 1])
plt.savefig(out + 'G_sim_AL_decomp.png', dpi=300, bbox_inches='tight')
plt.close()
print('Saved: G_sim_AL_decomp.png')

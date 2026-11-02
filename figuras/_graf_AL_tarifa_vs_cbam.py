"""
Aluminium — Brazil: CBAM ad-valorem equivalent vs. existing MFN tariff,
across carbon prices. Shows the cost break-even (~68 €/tCO2) where the
CBAM ad-valorem equals the tariff the EU-Mercosur deal would remove.
"""
import sys
import matplotlib.pyplot as plt
from matplotlib import rcParams

sys.stdout.reconfigure(encoding='utf-8')
import os; root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(chr(92), '/')
out  = root + '/figuras_geradas/'
os.makedirs(out, exist_ok=True)
rcParams['font.family'] = 'sans-serif'

# from analysis
TARIFF   = 5.15           # % applied MFN tariff (value-weighted)
SLOPE    = 0.0759         # CBAM ad-valorem per €/tCO2
BREAKEVEN= TARIFF/SLOPE   # ~67.8 €/t
scen     = {75:5.69, 95:7.21, 115:8.73}

COR_CBAM='#c0392b'; COR_TAR='#27ae60'

fig, ax = plt.subplots(figsize=(9, 5.6))

xs = list(range(50, 121))
cbam = [SLOPE*x for x in xs]

# shaded regions
ax.axvspan(50, BREAKEVEN, alpha=0.06, color='green')
ax.axvspan(BREAKEVEN, 121, alpha=0.06, color='red')

ax.plot(xs, cbam, color=COR_CBAM, lw=2.6, label='CBAM ad-valorem equivalent')
ax.axhline(TARIFF, color=COR_TAR, lw=2.2, ls='--',
           label=f'Applied MFN tariff ({TARIFF:.1f}%) — removed under Mercosur')

# scenario markers
for cp, v in scen.items():
    ax.scatter([cp],[v], s=80, color=COR_CBAM, zorder=5,
               edgecolors='white', linewidths=0.8)
    ax.annotate(f'{v:.1f}%', (cp, v), xytext=(6, -12),
                textcoords='offset points', fontsize=9.5,
                color=COR_CBAM, fontweight='bold')
    ax.axvline(cp, color='#bbb', lw=0.7, ls=':', alpha=0.7)
    ax.annotate(f'{cp}€', (cp, 0.4), fontsize=9, color='#666', ha='center')

# break-even marker
ax.scatter([BREAKEVEN],[TARIFF], s=120, color='#222', marker='X', zorder=6)
ax.annotate(f'Cost break-even\n≈ {BREAKEVEN:.0f} €/tCO₂',
            (BREAKEVEN, TARIFF), xytext=(-12, 22),
            textcoords='offset points', fontsize=9.5, color='#222',
            ha='right', fontweight='bold',
            arrowprops=dict(arrowstyle='->', color='#222', lw=1.0))

ax.text(0.02, 0.96,
        'Left of break-even: Mercosur tariff removal\nmore than offsets the CBAM cost',
        transform=ax.transAxes, fontsize=8.5, color='#1a7a3a',
        va='top', style='italic')
ax.text(0.98, 0.30,
        'Right: CBAM cost exceeds the\nremoved tariff (but Brazil may still\ngain SHARE — see note)',
        transform=ax.transAxes, fontsize=8.5, color='#a03020',
        va='top', ha='right', style='italic')

ax.set_xlim(50, 121)
ax.set_ylim(0, 10)
ax.set_xlabel('Carbon price (€/tCO₂)', fontsize=11.5)
ax.set_ylabel('Ad-valorem equivalent (% of price)', fontsize=11.5)
ax.set_title('Aluminium — Brazil: CBAM cost vs. existing tariff\n'
             'Why the EU–Mercosur agreement offsets the CBAM',
             fontsize=13, fontweight='bold', pad=10)
ax.legend(fontsize=10, loc='lower right', framealpha=0.95)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
ax.grid(alpha=0.13, ls='--')
ax.tick_params(labelsize=10)

fig.text(0.5, -0.02,
         'Note: the cost break-even (~68 €/t) is where CBAM = tariff in absolute terms. '
         'Brazil keeps a SHARE gain beyond it because the CBAM also raises rival prices '
         '(carbon-intensity advantage).',
         fontsize=8, color='#555', ha='center', style='italic')

plt.tight_layout()
plt.savefig(out+'G_AL_tarifa_vs_cbam.png', dpi=300, bbox_inches='tight')
plt.close()
print('Saved: G_AL_tarifa_vs_cbam.png')

"""
Gráfico de barras empilhadas: R² de variação de share (primeiras diferenças)
para Global, Brasil e Argentina, por setor.
Barras sempre somam 100% (contribuições incrementais).
"""
import math, sys
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import rcParams

sys.stdout.reconfigure(encoding='utf-8')

import os; root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(chr(92), '/')
out  = root + '/figuras_geradas/'
rcParams['font.family'] = 'sans-serif'

# ── Dados (r2_price, r2_both) ─────────────────────────────────────────────────
# Fonte: _r2_decomp_delta.py e _r2_decomp_delta_brar.py
data = {
    'Iron &\nSteel': {
        'Global':    (0.216, 0.232),
        'Brazil':    (0.309, 0.328),
        'Argentina': (0.293, 0.321),
    },
    'Aluminium': {
        'Global':    (0.180, 0.197),
        'Brazil':    (0.420, 0.446),
        'Argentina': (0.007, 0.051),
    },
    'Cement': {
        'Global':    (0.334, 0.344),
        'Brazil':    (0.057, 0.347),
        'Argentina': (0.039, 0.210),
    },
}

setores   = list(data.keys())
paises    = ['Global', 'Brazil', 'Argentina']
n_sec     = len(setores)
n_pais    = len(paises)
width     = 0.22
gap       = 0.04

COL_PRICE  = '#3498db'
COL_DEMAND = '#95a5a6'
COL_RESID  = '#dfe6e9'

COR_PAIS = {'Global': '#555555', 'Brazil': '#2c6e9e', 'Argentina': '#e67e22'}

fig, ax = plt.subplots(figsize=(11, 4.6))

for s_idx, setor in enumerate(setores):
    x_center = s_idx * (n_pais * (width + gap) + 0.18)

    for p_idx, pais in enumerate(paises):
        r2_price, r2_both = data[setor][pais]

        p   = r2_price * 100
        add = max((r2_both - r2_price) * 100, 0)
        rs  = (1 - r2_both) * 100

        x = x_center + p_idx * (width + gap)

        bar_p = ax.bar(x, p,   bottom=0,     width=width,
                       color=COL_PRICE,  alpha=0.90, edgecolor='white', linewidth=0.4)
        bar_a = ax.bar(x, add, bottom=p,     width=width,
                       color=COL_DEMAND, alpha=0.80, edgecolor='white', linewidth=0.4)
        bar_r = ax.bar(x, rs,  bottom=p+add, width=width,
                       color=COL_RESID,  alpha=0.90, edgecolor='white', linewidth=0.4)

        # Borda colorida por país
        ax.bar(x, 100, width=width, bottom=0,
               color='none', edgecolor=COR_PAIS[pais], linewidth=1.5, zorder=4)

        # Preço
        if p > 4:
            ax.text(x, p/2, f'{p:.1f}%', ha='center', va='center',
                    fontsize=7.5, color='white', fontweight='bold')
        else:
            ax.text(x, p/2 + 1, f'{p:.1f}%', ha='center', va='bottom',
                    fontsize=7, color='#2980b9', fontweight='bold')

        # Tendência de demanda
        if add > 1.5:
            ax.text(x, p + add/2, f'+{add:.1f}%', ha='center', va='center',
                    fontsize=7, color='black')

        # Resíduo
        rs_mid = p + add + rs/2
        ax.text(x, rs_mid, f'{rs:.1f}%', ha='center', va='center',
                fontsize=7, color='black')

        # Label do país abaixo
        ax.text(x, -4, pais, ha='center', va='top', fontsize=8,
                color=COR_PAIS[pais], fontweight='bold',
                rotation=0)

    # Label do setor no centro do grupo
    x_mid = x_center + (n_pais - 1) / 2 * (width + gap)
    ax.text(x_mid, 101.5, setor, ha='center', va='bottom',
            fontsize=11, fontweight='bold', color='#333')

ax.set_ylim(0, 108)
ax.set_xlim(-0.2, x_center + n_pais * (width + gap) + 0.1)
ax.axhline(100, color='#aaa', lw=0.8, ls='--')
ax.set_ylabel('% of Δ log(share) variation explained', fontsize=10.5)
ax.set_xticks([])
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['bottom'].set_visible(False)
ax.tick_params(bottom=False, labelsize=9)
ax.grid(axis='y', alpha=0.15, ls='--')

# Legenda componentes
p1 = mpatches.Patch(color=COL_PRICE,  alpha=0.90, label='Relative price  (β_i × Δ log price_rel)')
p2 = mpatches.Patch(color=COL_DEMAND, alpha=0.80, label='Demand trend  (incremental)')
p3 = mpatches.Patch(color=COL_RESID,  alpha=0.90, label='Residual  (1 − R²_combined)')
ax.legend(handles=[p1, p2, p3], fontsize=9, loc='upper center',
          bbox_to_anchor=(0.5, 1.18), framealpha=0.95, ncol=3)

ax.set_title(
    'R² decomposition for share variation\n'
    'Δ log(share) = β × Δ log(price_rel) + Δγ(p,t) + residual',
    fontsize=11.5, fontweight='bold', pad=55)

plt.tight_layout(rect=[0, 0.02, 1, 0.97])
plt.savefig(out + 'G_r2_delta_combinado.png', dpi=300, bbox_inches='tight')
plt.close()
print('Saved: G_r2_delta_combinado.png')

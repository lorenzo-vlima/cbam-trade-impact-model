"""
Merged explanatory-power figure (replaces the level TABLE + the variation CHART).
Two panels (Iron & Steel, Aluminium). Each panel shows:
  • LEVEL decomposition  (global only): Fixed effects | Price | Error
  • VARIATION decomposition (Global, Brazil, Argentina): Price | Demand | Residual
Price is the comparable component -> same blue in both, so the reader sees it
grow from ~12% (level) to ~18-22% (variation) once FE is differenced out.
English. No cement.
"""
import sys
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import rcParams

sys.stdout.reconfigure(encoding='utf-8')
root = 'C:/Users/loren/OneDrive/Documentos/TCC CBAM/Projeto R/Versão Claude code/MODELO_OFICIAL'
out  = root + '/figuras_geradas/'
rcParams['font.family'] = 'sans-serif'

# ── Data ──────────────────────────────────────────────────────────────────────
# LEVEL (global only): (fixed_effects, price, error)   — from Table 4
level = {
    'Iron & Steel': (0.812, 0.123, 0.065),
    'Aluminium':    (0.782, 0.123, 0.094),
}
# VARIATION: (r2_price, r2_both) -> price / incremental demand / residual
variation = {
    'Iron & Steel': {'Global': (0.216, 0.232), 'Brazil': (0.309, 0.328), 'Argentina': (0.293, 0.321)},
    'Aluminium':    {'Global': (0.180, 0.197), 'Brazil': (0.420, 0.446), 'Argentina': (0.007, 0.051)},
}

# colours
COL_PRICE  = '#3498db'   # price (comparable across level & variation)
COL_FE     = '#7f8c8d'   # fixed effects (level)
COL_DEMAND = '#b0bec5'   # demand trend (variation)
COL_OTHER  = '#e0e6e8'   # error / residual
COR_PAIS   = {'Global': '#555555', 'Brazil': '#2c6e9e', 'Argentina': '#e67e22'}

fig, axes = plt.subplots(1, 2, figsize=(13, 5.0), sharey=True)

for ax, setor in zip(axes, level.keys()):
    fe, pr_lvl, err = level[setor]

    # rows: LEVEL(global) on top, then a small gap, then 3 VARIATION rows
    # y positions (top→bottom)
    y_level = 4.4
    y_var   = {'Global': 3.0, 'Brazil': 2.0, 'Argentina': 1.0}

    # ── LEVEL bar (global) ──
    ax.barh(y_level, fe*100,            left=0,               height=0.62,
            color=COL_FE, edgecolor='white')
    ax.barh(y_level, pr_lvl*100,        left=fe*100,          height=0.62,
            color=COL_PRICE, edgecolor='white')
    ax.barh(y_level, err*100,           left=(fe+pr_lvl)*100, height=0.62,
            color=COL_OTHER, edgecolor='white')
    # labels
    ax.text(fe*100/2, y_level, f'{fe*100:.0f}%', ha='center', va='center',
            fontsize=8.5, color='white', fontweight='bold')
    ax.text(fe*100 + pr_lvl*100/2, y_level, f'{pr_lvl*100:.0f}%',
            ha='center', va='center', fontsize=8.5, color='white', fontweight='bold')
    ax.text((fe+pr_lvl)*100 + err*100/2, y_level, f'{err*100:.0f}%',
            ha='center', va='center', fontsize=8, color='#444')
    ax.text(-2, y_level, 'LEVEL\n(global)', ha='right', va='center',
            fontsize=8.5, fontweight='bold', color='#333')

    # ── VARIATION bars ──
    for country, yv in y_var.items():
        pr, both = variation[setor][country]
        p   = pr*100
        add = max((both - pr)*100, 0)
        res = (1 - both)*100
        ax.barh(yv, p,   left=0,     height=0.62, color=COL_PRICE,  edgecolor='white')
        ax.barh(yv, add, left=p,     height=0.62, color=COL_DEMAND, edgecolor='white')
        ax.barh(yv, res, left=p+add, height=0.62, color=COL_OTHER,  edgecolor='white')
        # country label with its colour
        ax.text(-2, yv, country, ha='right', va='center', fontsize=8.5,
                fontweight='bold', color=COR_PAIS[country])
        # price value — inside if wide enough, else just left of the bar
        if p > 5:
            ax.text(p/2, yv, f'{p:.1f}%', ha='center', va='center',
                    fontsize=8, color='white', fontweight='bold')
        else:
            ax.text(-2, yv - 0.32, f'price {p:.1f}%', ha='right', va='center',
                    fontsize=7, color=COL_PRICE, fontweight='bold')
        # demand increment only when it has room (avoid the AR-AL clutter)
        if add > 5:
            ax.text(p+add/2, yv, f'+{add:.0f}', ha='center', va='center',
                    fontsize=7, color='#333')
        ax.text(p+add+res/2, yv, f'{res:.0f}%', ha='center', va='center',
                fontsize=8, color='#555')

    # divider between LEVEL and VARIATION blocks — label BELOW the line
    ax.axhline(3.75, color='#ccc', lw=0.9, ls='--')
    ax.text(50, 3.70, 'VARIATION  (Δ log share)', ha='center', va='top',
            fontsize=8, color='#888', style='italic')

    ax.set_xlim(0, 104)
    ax.set_ylim(0.4, 5.0)
    ax.set_yticks([])
    ax.axvline(100, color='#ccc', lw=0.7, ls='--')
    ax.set_xlabel('Share of explained variation (%)', fontsize=10.5)
    title_col = '#2c6e9e' if setor == 'Iron & Steel' else '#c0392b'
    ax.set_title(setor, fontsize=13, fontweight='bold', color=title_col, pad=10)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.tick_params(labelsize=9)

# legend
handles = [
    mpatches.Patch(color=COL_FE,     label='Fixed effects (level only)'),
    mpatches.Patch(color=COL_PRICE,  label='Relative price (β)'),
    mpatches.Patch(color=COL_DEMAND, label='Demand trend (variation only)'),
    mpatches.Patch(color=COL_OTHER,  label='Error / Residual'),
]
fig.legend(handles=handles, fontsize=9.5, loc='lower center', ncol=4,
           bbox_to_anchor=(0.5, -0.02), framealpha=0.95)

fig.suptitle(
    "Model explanatory power: share LEVEL vs. share VARIATION",
    fontsize=12.5, fontweight='bold', y=1.02)

plt.tight_layout(rect=[0.02, 0.06, 1, 1], w_pad=3.0)
plt.savefig(out + 'G_r2_mesclado.png', dpi=300, bbox_inches='tight')
plt.close()
print('Saved: G_r2_mesclado.png')

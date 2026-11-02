import sys
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from matplotlib import rcParams

sys.stdout.reconfigure(encoding='utf-8')

import os; root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(chr(92), '/')
out  = root + '/figuras_geradas/'

rcParams['font.family'] = 'sans-serif'
rcParams['font.size']   = 10

# ── Data (model 2010-2025, volumes 2023-2025) ────────────────────────────────
# (label, β_BR, β_AR, β_global, vol_BR%, vol_AR%)
# Order: least processed (bottom) → most processed (top)
grupos_FA = [
    ('Long &\ntubular',           -1.352, -0.790, -1.512,  2.9, 95.0),
    ('Semi-finished\n& flat',     -3.482, -1.859, -2.303, 16.5,  5.0),
    ('Primaries\n(ore/pig iron)', -0.168, -0.187, -0.187, 80.6,  0.0),
]
grupos_AL = [
    ('Manufactured\n& finished',  -1.280, -1.129, -1.029,  0.9,  0.4),
    ('Rolled &\ntubular',         -1.515, -1.976, -1.123, 10.3,  0.7),
    ('Primary &\nsemi-finished',  -0.556, -0.334, -0.572, 88.8, 98.9),
]
grupos_CE = [
    ('Special\ncements',  -0.156, -1.225, -1.225,   0.0,   0.0),
    ('Portland\ncement',  -1.054, -1.231, -1.231,   0.0,   0.0),
    ('Clinker',           -1.305, -0.219, -1.376,   0.0,   0.0),
    ('Clay',              -1.611, -0.188, -1.485, 100.0, 100.0),
]

COR_FA = '#2c6e9e'
COR_AL = '#c0392b'
COR_CE = '#27ae60'

COR_FA_AR = '#7fb3d3'
COR_AL_AR = '#e08080'
COR_CE_AR = '#76c893'

beta_setor = {
    'FA': {'BR': -0.749, 'AR': -0.844},
    'AL': {'BR': -0.662, 'AR': -0.349},
    'CE': {'BR': -1.611, 'AR': -0.188},
}

BETA_THR = 0.08   # minimum difference to show the global β separately
FS_BETA  = 6.5

def _vol_annot(ax, val, yy, col, vol):
    if vol <= 2.0:
        return
    if vol > 35:
        ax.annotate(f'{vol:.0f}%', xy=(val, yy), xytext=(-14, 0),
                    textcoords='offset points', fontsize=8.5, color=col,
                    va='center', ha='right', alpha=0.9, clip_on=False)
    else:
        ax.annotate(f'{vol:.0f}%', xy=(val, yy), xytext=(8, 0),
                    textcoords='offset points', fontsize=8.5, color=col,
                    va='center', ha='left', alpha=0.9, clip_on=False)

def plot_painel_single(ax, grupos, cor_pais, setor_key, titulo,
                       idx_beta, idx_vol, marker, pais_label, x_min=-6.5):
    """
    idx_beta : 1 = BR, 2 = AR
    idx_vol  : 4 = vol_BR%, 5 = vol_AR%
    """
    n     = len(grupos)
    y_pos = list(range(n, 0, -1))
    x_max = 1.5

    for y, grupo in zip(y_pos, grupos):
        label  = grupo[0]
        b_pais = grupo[idx_beta]
        b_glb  = grupo[3]
        vol    = grupo[idx_vol]

        close = abs(b_pais - b_glb) < 0.25

        # Country → global line
        ax.plot([b_pais, b_glb], [y, y], color='#cccccc',
                linewidth=1.2, zorder=1, alpha=0.7)

        # Global (quadrado cinza)
        ax.scatter(b_glb, y, s=75, color='#aaaaaa', marker='s',
                   zorder=3, linewidths=0.5, edgecolors='#888888', alpha=0.85)

        # Country
        s_pais = max(60, 55 + vol * 14)
        ax.scatter(b_pais, y, s=s_pais, color=cor_pais, marker=marker,
                   zorder=5, linewidths=1.2, edgecolors='white',
                   alpha=1.0 if close else 0.92)

        # Volume (horizontal, ao lado do marcador)
        _vol_annot(ax, b_pais, y, cor_pais, vol)

        # country β, ABOVE the marker (does not clash with the volume beside it)
        ax.text(b_pais, y + 0.14, f'{b_pais:.2f}', fontsize=FS_BETA,
                color=cor_pais, ha='center', va='bottom', alpha=0.92,
                zorder=6, clip_on=False)

        # global β, BELOW the global square, only if different from the country
        if abs(b_glb - b_pais) > BETA_THR:
            ax.text(b_glb, y - 0.15, f'{b_glb:.2f}', fontsize=FS_BETA,
                    color='#888888', ha='center', va='top', alpha=0.85,
                    zorder=6, clip_on=False)

    # Sector line
    b_set = beta_setor[setor_key][pais_label]
    ax.axvline(b_set, color=cor_pais, linewidth=1.3, linestyle=':',
               alpha=0.55, zorder=0)
    x_txt = b_set + 0.07 if b_set > x_min + 0.5 else b_set - 0.07
    ha_txt = 'left' if b_set > x_min + 0.5 else 'right'
    ax.text(x_txt, 0.35, f'{b_set:.3f}', fontsize=7.5, color=cor_pais,
            alpha=0.85, va='bottom', ha=ha_txt)

    ax.axvline(0, color='#cccccc', linewidth=0.7, linestyle='--', zorder=0)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([g[0] for g in grupos], fontsize=10)
    ax.set_xlabel('Market share price elasticity (β)', fontsize=9.5)
    ax.set_title(titulo, fontsize=12, fontweight='bold', color=cor_pais, pad=10)
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(0.1, n + 1.0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='x', alpha=0.2, linestyle='--')


# ══════════════════════════════════════════════════════════════════════════════
# FIGURA — Brazil only
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 3, figsize=(14, 5.5),
                         gridspec_kw={'width_ratios': [3, 3, 4]})

plot_painel_single(axes[0], grupos_FA, COR_FA, 'FA', 'Iron & Steel',
                   idx_beta=1, idx_vol=4, marker='o', pais_label='BR', x_min=-6.5)
plot_painel_single(axes[1], grupos_AL, COR_AL, 'AL', 'Aluminium',
                   idx_beta=1, idx_vol=4, marker='o', pais_label='BR', x_min=-3.5)
plot_painel_single(axes[2], grupos_CE, COR_CE, 'CE', 'Cement',
                   idx_beta=1, idx_vol=4, marker='o', pais_label='BR', x_min=-3.5)

dot_br  = mlines.Line2D([], [], color='#444', marker='o', linestyle='None',
                         markersize=9, label='Brazil (circle, size ∝ volume share, 2023–2025)')
dot_glb = mlines.Line2D([], [], color='#aaa', marker='s', linestyle='None',
                         markersize=7, label='Global β (gray square)')
lin_set = mlines.Line2D([], [], color='#888', linestyle=':',
                         linewidth=1.4, label='Sector-level β (dotted line)')
fig.legend(handles=[dot_br, dot_glb, lin_set],
           fontsize=8.5, loc='lower center', ncol=3,
           bbox_to_anchor=(0.5, -0.03), framealpha=0.9)

note = ('Note: Sector β = volume-weighted average across product groups. '
        'Country β (colored) and global β (gray) shown; global omitted when virtually equal.')
fig.text(0.02, -0.07, note, fontsize=7.5, color='#555', style='italic')

fig.suptitle('Estimated market share price elasticities by product group — Brazil',
             fontsize=12, fontweight='bold', y=1.02)

plt.tight_layout()
plt.savefig(out + 'G1_elasticidades_brasil.png', dpi=160, bbox_inches='tight')
plt.close()
print('Saved: G1_elasticidades_brasil.png')


# ══════════════════════════════════════════════════════════════════════════════
# FIGURA — Argentina only
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 3, figsize=(14, 5.5),
                         gridspec_kw={'width_ratios': [3, 3, 4]})

plot_painel_single(axes[0], grupos_FA, COR_FA_AR, 'FA', 'Iron & Steel',
                   idx_beta=2, idx_vol=5, marker='^', pais_label='AR', x_min=-6.5)
plot_painel_single(axes[1], grupos_AL, COR_AL_AR, 'AL', 'Aluminium',
                   idx_beta=2, idx_vol=5, marker='^', pais_label='AR', x_min=-3.5)
plot_painel_single(axes[2], grupos_CE, COR_CE_AR, 'CE', 'Cement',
                   idx_beta=2, idx_vol=5, marker='^', pais_label='AR', x_min=-3.5)

dot_ar  = mlines.Line2D([], [], color='#888', marker='^', linestyle='None',
                         markersize=9, label='Argentina (triangle, size ∝ volume share, 2023–2025)')
dot_glb = mlines.Line2D([], [], color='#aaa', marker='s', linestyle='None',
                         markersize=7, label='Global β (gray square)')
lin_set = mlines.Line2D([], [], color='#888', linestyle=':',
                         linewidth=1.4, label='Sector-level β (dotted line)')
fig.legend(handles=[dot_ar, dot_glb, lin_set],
           fontsize=8.5, loc='lower center', ncol=3,
           bbox_to_anchor=(0.5, -0.03), framealpha=0.9)

note = ('Note: Sector β = volume-weighted average across product groups. '
        'Country β (colored) and global β (gray) shown; global omitted when virtually equal.')
fig.text(0.02, -0.07, note, fontsize=7.5, color='#555', style='italic')

fig.suptitle('Estimated market share price elasticities by product group — Argentina',
             fontsize=12, fontweight='bold', y=1.02)

plt.tight_layout()
plt.savefig(out + 'G1_elasticidades_argentina.png', dpi=160, bbox_inches='tight')
plt.close()
print('Saved: G1_elasticidades_argentina.png')

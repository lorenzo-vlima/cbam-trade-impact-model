"""
v2: designed to be legible in Word (portrait A4, ~17 cm wide).
Principle: small figure (10 in.) + large fonts = legible text after scaling.
Colour = sector; shape = country (circle = Brazil, triangle = Argentina).
"""
import sys
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from matplotlib import rcParams

sys.stdout.reconfigure(encoding='utf-8')

import os; root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(chr(92), '/')
out  = root + '/figuras_geradas/'
os.makedirs(out, exist_ok=True)

rcParams['font.family'] = 'sans-serif'
rcParams['font.size']   = 10

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

# Colour = sector (same for Brazil and Argentina)
COR_FA = '#2c6e9e'
COR_AL = '#c0392b'
COR_CE = '#27ae60'

beta_setor = {
    'FA': {'BR': -0.749, 'AR': -0.844},
    'AL': {'BR': -0.662, 'AR': -0.349},
    'CE': {'BR': -1.611, 'AR': -0.188},
}
beta_setor_global = {
    'FA': -1.635,
    'AL': -0.769,
    'CE': -1.298,
}

BETA_THR = 0.08

FS_TITLE  = 14
FS_XLABEL = 11
FS_XTICK  = 10
FS_YTICK  = 11
FS_VOL    = 9
FS_BETA   = 8.5
FS_SET    = 8
FS_LEGEND = 10
FS_NOTE   = 8

LBBOX = dict(boxstyle='round,pad=0.15', facecolor='white', edgecolor='none', alpha=0.88)


def _vol_annot(ax, val, yy, col, vol):
    if vol <= 2.0:
        return
    kw = dict(boxstyle='round,pad=0.1', facecolor='white', edgecolor='none', alpha=0.85)
    if vol > 35:
        ax.annotate(f'{vol:.0f}%', xy=(val, yy), xytext=(-15, 0),
                    textcoords='offset points', fontsize=FS_VOL, color=col,
                    va='center', ha='right', alpha=0.9, clip_on=False, bbox=kw)
    else:
        ax.annotate(f'{vol:.0f}%', xy=(val, yy), xytext=(9, 0),
                    textcoords='offset points', fontsize=FS_VOL, color=col,
                    va='center', ha='left', alpha=0.9, clip_on=False, bbox=kw)


def plot_painel_single(ax, grupos, cor_pais, setor_key, titulo,
                       idx_beta, idx_vol, marker, pais_label,
                       x_min=-4.0, x_max=1.0):
    n     = len(grupos)
    y_pos = list(range(n, 0, -1))

    for y, grupo in zip(y_pos, grupos):
        b_pais = grupo[idx_beta]
        b_glb  = grupo[3]
        vol    = grupo[idx_vol]

        ax.plot([b_pais, b_glb], [y, y], color='#cccccc',
                linewidth=1.4, zorder=1, alpha=0.7)

        ax.scatter(b_glb, y, s=95, color='#aaaaaa', marker='s',
                   zorder=3, linewidths=0.6, edgecolors='#888888', alpha=0.85)

        s_pais = max(80, 65 + vol * 16)
        ax.scatter(b_pais, y, s=s_pais, color=cor_pais, marker=marker,
                   zorder=5, linewidths=1.4, edgecolors='white', alpha=1.0)

        _vol_annot(ax, b_pais, y, cor_pais, vol)

        ax.text(b_pais, y + 0.19, f'{b_pais:.2f}', fontsize=FS_BETA,
                color=cor_pais, ha='center', va='bottom',
                zorder=7, clip_on=False, bbox=LBBOX)
        if abs(b_glb - b_pais) > BETA_THR:
            ax.text(b_glb, y - 0.19, f'{b_glb:.2f}', fontsize=FS_BETA,
                    color='#666666', ha='center', va='top',
                    zorder=7, clip_on=False, bbox=LBBOX)

    # country sector β
    b_set = beta_setor[setor_key][pais_label]
    ax.axvline(b_set, color=cor_pais, linewidth=1.4, linestyle=':',
               alpha=0.6, zorder=0)
    x_txt  = b_set + 0.06 if b_set > x_min + 0.5 else b_set - 0.06
    ha_txt = 'left' if b_set > x_min + 0.5 else 'right'
    ax.text(x_txt, 0.38, f'{b_set:.3f}', fontsize=FS_SET,
            color=cor_pais, alpha=0.88, va='bottom', ha=ha_txt)
    # β setorial global
    b_g = beta_setor_global[setor_key]
    ax.axvline(b_g, color='#888888', linewidth=1.2, linestyle='--',
               alpha=0.55, zorder=0)
    x_g    = b_g + 0.06 if b_g > x_min + 0.5 else b_g - 0.06
    ha_g   = 'left' if b_g > x_min + 0.5 else 'right'
    ax.text(x_g, 0.22, f'{b_g:.3f}', fontsize=FS_SET,
            color='#888888', alpha=0.82, va='bottom', ha=ha_g)

    ax.axvline(0, color='#cccccc', linewidth=0.8, linestyle='--', zorder=0)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([g[0] for g in grupos], fontsize=FS_YTICK)
    ax.set_xlabel('')
    ax.set_title(titulo, fontsize=FS_TITLE, fontweight='bold', color=cor_pais, pad=12)
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(0.2, n + 0.9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='x', alpha=0.2, linestyle='--')
    ax.tick_params(axis='x', labelsize=FS_XTICK)


# ══════════════════════════════════════════════════════════════════════════════
# FIGURA — Brazil v2
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 3, figsize=(10, 5.5),
                         gridspec_kw={'width_ratios': [1, 1, 1]})

plot_painel_single(axes[0], grupos_FA, COR_FA, 'FA', 'Iron & Steel', 1, 4, 'o', 'BR')
plot_painel_single(axes[1], grupos_AL, COR_AL, 'AL', 'Aluminium',   1, 4, 'o', 'BR')
plot_painel_single(axes[2], grupos_CE, COR_CE, 'CE', 'Cement',      1, 4, 'o', 'BR')
axes[1].set_xlabel('Market share price elasticity (β)', fontsize=FS_XLABEL, labelpad=6)

dot_br  = mlines.Line2D([], [], color='#444', marker='o', linestyle='None',
                         markersize=8, label='Brazil (circle, size ∝ volume share, 2023–2025)')
dot_glb = mlines.Line2D([], [], color='#aaa', marker='s', linestyle='None',
                         markersize=6, label='Global β (gray square)')
lin_set_c = mlines.Line2D([], [], color='#444', linestyle=':',
                          linewidth=1.3, label='Country sector β (dotted)')
lin_set_g = mlines.Line2D([], [], color='#888', linestyle='--',
                          linewidth=1.3, label='Global sector β (dashed)')
fig.legend(handles=[dot_br, dot_glb, lin_set_c, lin_set_g],
           fontsize=FS_LEGEND, loc='lower center', ncol=4,
           bbox_to_anchor=(0.5, 0.0), framealpha=0.95)

note = ('Note: Sector β = volume-weighted average across product groups. '
        'β values shown next to each marker; global β (gray) omitted when virtually equal.')
fig.text(0.02, -0.05, note, fontsize=FS_NOTE, color='#555', style='italic')

fig.suptitle('Estimated market share price elasticities by product group — Brazil',
             fontsize=FS_TITLE, fontweight='bold', y=1.04)

plt.tight_layout(w_pad=2.5, rect=[0, 0.13, 1, 1])
plt.savefig(out + 'G1_elasticidades_brasil_v2.png', dpi=300, bbox_inches='tight')
plt.close()
print('Saved: G1_elasticidades_brasil_v2.png')


# ══════════════════════════════════════════════════════════════════════════════
# FIGURE — Argentina v2  (same sector colours as Brazil, shape = triangle)
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 3, figsize=(10, 5.5),
                         gridspec_kw={'width_ratios': [1, 1, 1]})

plot_painel_single(axes[0], grupos_FA, COR_FA, 'FA', 'Iron & Steel', 2, 5, '^', 'AR')
plot_painel_single(axes[1], grupos_AL, COR_AL, 'AL', 'Aluminium',   2, 5, '^', 'AR')
plot_painel_single(axes[2], grupos_CE, COR_CE, 'CE', 'Cement',      2, 5, '^', 'AR')
axes[1].set_xlabel('Market share price elasticity (β)', fontsize=FS_XLABEL, labelpad=6)

dot_ar  = mlines.Line2D([], [], color='#444', marker='^', linestyle='None',
                         markersize=8, label='Argentina (triangle, size ∝ volume share, 2023–2025)')
dot_glb = mlines.Line2D([], [], color='#aaa', marker='s', linestyle='None',
                         markersize=6, label='Global β (gray square)')
lin_set_c = mlines.Line2D([], [], color='#444', linestyle=':',
                          linewidth=1.3, label='Country sector β (dotted)')
lin_set_g = mlines.Line2D([], [], color='#888', linestyle='--',
                          linewidth=1.3, label='Global sector β (dashed)')
fig.legend(handles=[dot_ar, dot_glb, lin_set_c, lin_set_g],
           fontsize=FS_LEGEND, loc='lower center', ncol=4,
           bbox_to_anchor=(0.5, 0.0), framealpha=0.95)

note = ('Note: Sector β = volume-weighted average across product groups. '
        'β values shown next to each marker; global β (gray) omitted when virtually equal.')
fig.text(0.02, -0.05, note, fontsize=FS_NOTE, color='#555', style='italic')

fig.suptitle('Estimated market share price elasticities by product group — Argentina',
             fontsize=FS_TITLE, fontweight='bold', y=1.04)

plt.tight_layout(w_pad=2.5, rect=[0, 0.13, 1, 1])
plt.savefig(out + 'G1_elasticidades_argentina_v2.png', dpi=300, bbox_inches='tight')
plt.close()
print('Saved: G1_elasticidades_argentina_v2.png')

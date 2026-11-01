"""
v2 — desenhado para aparecer legível em Word (portrait A4 ~17cm largura).
Princípio: figura pequena (10 pol.) + fontes grandes = texto legível após escalar.
"""
import sys
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from matplotlib import rcParams

sys.stdout.reconfigure(encoding='utf-8')

root = 'C:/Users/loren/OneDrive/Documentos/TCC CBAM/Projeto R/Versão Claude code/MODELO_OFICIAL'
out  = root + '/figuras_geradas/'

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

# Cor = setor (mesma para Brasil e Argentina); forma = país
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

Y_OFF    = 0.22
BETA_THR = 0.10

FS_TITLE  = 14
FS_XLABEL = 11
FS_XTICK  = 10
FS_YTICK  = 11
FS_VOL    = 9
FS_BETA   = 8.5
FS_SETOR  = 8
FS_LEGEND = 10
FS_NOTE   = 8

LBBOX = dict(boxstyle='round,pad=0.15', facecolor='white', edgecolor='none', alpha=0.88)


def _vol_annot(ax, val, yy, col, vol):
    if vol <= 2.0:
        return
    kw = dict(boxstyle='round,pad=0.1', facecolor='white', edgecolor='none', alpha=0.85)
    if vol > 35:
        ax.annotate(f'{vol:.0f}%', xy=(val, yy), xytext=(-14, 0),
                    textcoords='offset points', fontsize=FS_VOL, color=col,
                    va='center', ha='right', alpha=0.9, clip_on=False, bbox=kw)
    else:
        ax.annotate(f'{vol:.0f}%', xy=(val, yy), xytext=(9, 0),
                    textcoords='offset points', fontsize=FS_VOL, color=col,
                    va='center', ha='left', alpha=0.9, clip_on=False, bbox=kw)


def plot_painel(ax, grupos, cor_br, cor_ar, titulo, setor_key,
                x_min=-4.0, x_max=1.0):
    n     = len(grupos)
    y_pos = list(range(n, 0, -1))

    for y, (label, bBR, bAR, bGlb, vol_BR, vol_AR) in zip(y_pos, grupos):
        yBR = y + Y_OFF
        yAR = y - Y_OFF

        ax.plot([bBR, bAR], [yBR, yAR], color='#cccccc',
                linewidth=1.2, zorder=1, alpha=0.7)

        ax.scatter(bGlb, y, s=55, color='#aaaaaa', marker='s',
                   zorder=3, linewidths=0.5, edgecolors='#888888', alpha=0.85)

        sBR = max(50, 45 + vol_BR * 11)
        ax.scatter(bBR, yBR, s=sBR, color=cor_br, marker='o', zorder=5,
                   linewidths=1.2, edgecolors='white', alpha=1.0)

        sAR = max(50, 45 + vol_AR * 11)
        ax.scatter(bAR, yAR, s=sAR, color=cor_ar, marker='^', zorder=4,
                   linewidths=1.2, edgecolors='white', alpha=1.0)

        _vol_annot(ax, bBR, yBR, cor_br, vol_BR)
        _vol_annot(ax, bAR, yAR, cor_ar, vol_AR)

        ax.text(bBR, yBR + 0.19, f'{bBR:.2f}', fontsize=FS_BETA, color=cor_br,
                ha='center', va='bottom', zorder=7, clip_on=False, bbox=LBBOX)
        ax.text(bAR, yAR - 0.19, f'{bAR:.2f}', fontsize=FS_BETA, color=cor_ar,
                ha='center', va='top', zorder=7, clip_on=False, bbox=LBBOX)
        if abs(bGlb - bBR) > BETA_THR and abs(bGlb - bAR) > BETA_THR:
            ax.text(bGlb, y - 0.19, f'{bGlb:.2f}', fontsize=FS_BETA,
                    color='#666666', ha='center', va='top', zorder=7,
                    clip_on=False, bbox=LBBOX)

    # Linhas de β setorial: país (colorido) + global (cinza)
    for pais, col, ytext in [('BR', cor_br, 0.42), ('AR', cor_ar, 0.24)]:
        b = beta_setor[setor_key][pais]
        ax.axvline(b, color=col, linewidth=1.2, linestyle=':', alpha=0.6, zorder=0)
        x_txt  = b + 0.05 if b > x_min + 0.5 else b - 0.05
        ha_txt = 'left' if b > x_min + 0.5 else 'right'
        ax.text(x_txt, ytext, f'{pais}: {b:.3f}',
                fontsize=FS_SETOR, color=col, alpha=0.85, va='bottom', ha=ha_txt)
    b_g = beta_setor_global[setor_key]
    ax.axvline(b_g, color='#888888', linewidth=1.2, linestyle='--', alpha=0.55, zorder=0)
    x_txt  = b_g + 0.05 if b_g > x_min + 0.5 else b_g - 0.05
    ha_txt = 'left' if b_g > x_min + 0.5 else 'right'
    ax.text(x_txt, 0.06, f'Glb: {b_g:.3f}',
            fontsize=FS_SETOR, color='#888888', alpha=0.82, va='bottom', ha=ha_txt)

    ax.axvline(0, color='#cccccc', linewidth=0.7, linestyle='--', zorder=0)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([g[0] for g in grupos], fontsize=FS_YTICK)
    ax.set_xlabel('')
    ax.set_title(titulo, fontsize=FS_TITLE, fontweight='bold', color=cor_br, pad=10)
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(0.2, n + 0.9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='x', alpha=0.2, linestyle='--')
    ax.tick_params(axis='x', labelsize=FS_XTICK)


fig, axes = plt.subplots(1, 3, figsize=(10, 5.5),
                         gridspec_kw={'width_ratios': [1, 1, 1]})

plot_painel(axes[0], grupos_FA, COR_FA, COR_FA, 'Iron & Steel', 'FA')
plot_painel(axes[1], grupos_AL, COR_AL, COR_AL, 'Aluminium',   'AL')
plot_painel(axes[2], grupos_CE, COR_CE, COR_CE, 'Cement',      'CE')
axes[1].set_xlabel('Market share price elasticity (β)', fontsize=FS_XLABEL, labelpad=6)

dot_br  = mlines.Line2D([], [], color='#444', marker='o', linestyle='None',
                         markersize=8, label='Brazil (circle, size ∝ volume share, 2023–2025)')
dot_ar  = mlines.Line2D([], [], color='#444', marker='^', linestyle='None',
                         markersize=8, label='Argentina (triangle, size ∝ volume share, 2023–2025)')
dot_glb = mlines.Line2D([], [], color='#aaa', marker='s', linestyle='None',
                         markersize=6, label='Global β (gray square)')
lin_set_c = mlines.Line2D([], [], color='#444', linestyle=':',
                          linewidth=1.3, label='Country sector β (dotted)')
lin_set_g = mlines.Line2D([], [], color='#888', linestyle='--',
                          linewidth=1.3, label='Global sector β (dashed)')
fig.legend(handles=[dot_br, dot_ar, dot_glb, lin_set_c, lin_set_g],
           fontsize=FS_LEGEND, loc='lower center', ncol=5,
           bbox_to_anchor=(0.5, 0.0), framealpha=0.95)

note = ('Note: Sector β = volume-weighted average across product groups. '
        'β values shown next to each marker; global β (gray) omitted when virtually equal.')
fig.text(0.02, -0.05, note, fontsize=FS_NOTE, color='#555', style='italic')

fig.suptitle('Estimated market share price elasticities by product group\n— Brazil and Argentina',
             fontsize=FS_TITLE, fontweight='bold', y=1.04)

plt.tight_layout(w_pad=2.5, rect=[0, 0.13, 1, 1])
plt.savefig(out + 'G1_elasticidades_grupos_v2.png', dpi=300, bbox_inches='tight')
plt.close()
print('Salvo: G1_elasticidades_grupos_v2.png')

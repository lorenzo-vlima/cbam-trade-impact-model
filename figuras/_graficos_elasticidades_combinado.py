"""
Figura combinada: Brasil, Argentina e Global numa única figura.
Substituição das Figuras 1 e 2 separadas por um único painel 1×3.
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

# Estrutura: (label, beta_BR, beta_AR, beta_global, vol_BR, vol_AR)
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
COR_BR = '#2c6e9e'   # círculo cheio — cor do setor
COR_AR = '#e67e22'   # triângulo cheio — laranja para distinguir do setor
COR_GL = '#888888'   # quadrado cinza

beta_setor_BR  = {'FA': -0.749, 'AL': -0.662, 'CE': -1.611}
beta_setor_AR  = {'FA': -0.844, 'AL': -0.349, 'CE': -0.188}
beta_setor_GL  = {'FA': -1.635, 'AL': -0.769, 'CE': -1.298}

FS_TITLE  = 13
FS_XLABEL = 10.5
FS_XTICK  = 9
FS_YTICK  = 10.5
FS_VOL    = 8.5
FS_BETA   = 7.8
FS_SET    = 7.5
FS_LEGEND = 9.5
FS_NOTE   = 8
BETA_THR  = 0.08
LBBOX = dict(boxstyle='round,pad=0.12', facecolor='white', edgecolor='none', alpha=0.88)


def _vol_annot(ax, val, yy, col, vol, offset_y=0.0):
    if vol <= 2.0:
        return
    kw = dict(boxstyle='round,pad=0.08', facecolor='white', edgecolor='none', alpha=0.82)
    side = -18 if val > -0.5 else 11
    ha   = 'right' if side < 0 else 'left'
    ax.annotate(f'{vol:.0f}%', xy=(val, yy + offset_y),
                xytext=(side, 0), textcoords='offset points',
                fontsize=FS_VOL, color=col, va='center', ha=ha,
                alpha=0.85, clip_on=False, bbox=kw)


def plot_painel(ax, grupos, cor_setor, setor_key, titulo, x_min=-4.5, x_max=0.6):
    n     = len(grupos)
    y_pos = list(range(n, 0, -1))

    for y, g in zip(y_pos, grupos):
        b_br, b_ar, b_gl = g[1], g[2], g[3]
        v_br, v_ar        = g[4], g[5]

        # Linha conectando os três pontos
        betas_sorted = sorted([b_br, b_ar, b_gl])
        ax.plot([betas_sorted[0], betas_sorted[-1]], [y, y],
                color='#cccccc', linewidth=1.3, zorder=1, alpha=0.8)

        # Global (quadrado cinza) — sempre visível
        ax.scatter(b_gl, y, s=80, color=COR_GL, marker='s',
                   zorder=3, linewidths=0.6, edgecolors='#666', alpha=0.85)

        # Argentina (triângulo laranja)
        s_ar = max(75, 60 + v_ar * 14)
        ax.scatter(b_ar, y, s=s_ar, color=COR_AR, marker='^',
                   zorder=5, linewidths=1.2, edgecolors='white', alpha=0.95)

        # Brasil (círculo cor do setor)
        s_br = max(75, 60 + v_br * 14)
        ax.scatter(b_br, y, s=s_br, color=cor_setor, marker='o',
                   zorder=6, linewidths=1.2, edgecolors='white', alpha=0.95)

        # Anotações de beta — Brasil acima, Argentina abaixo, Global abaixo
        ax.text(b_br, y + 0.22, f'{b_br:.2f}', fontsize=FS_BETA,
                color=cor_setor, ha='center', va='bottom', zorder=8,
                clip_on=False, bbox=LBBOX)
        ax.text(b_ar, y - 0.22, f'{b_ar:.2f}', fontsize=FS_BETA,
                color=COR_AR, ha='center', va='top', zorder=8,
                clip_on=False, bbox=LBBOX)
        if abs(b_gl - b_br) > BETA_THR and abs(b_gl - b_ar) > BETA_THR:
            ax.text(b_gl, y + 0.22, f'{b_gl:.2f}', fontsize=FS_BETA - 0.5,
                    color='#666', ha='center', va='bottom', zorder=7,
                    clip_on=False, bbox=LBBOX)

        # Volume share
        _vol_annot(ax, b_br, y, cor_setor, v_br, offset_y=0.0)
        _vol_annot(ax, b_ar, y, COR_AR,    v_ar, offset_y=0.0)

    # Linhas verticais dos betas setoriais
    for bsec, col, ls, lw in [
        (beta_setor_BR[setor_key],  cor_setor, ':',  1.4),
        (beta_setor_AR[setor_key],  COR_AR,    '-.',  1.2),
        (beta_setor_GL[setor_key],  COR_GL,    '--', 1.0),
    ]:
        ax.axvline(bsec, color=col, linewidth=lw, linestyle=ls,
                   alpha=0.55, zorder=0)
        x_txt = bsec + 0.07
        ax.text(x_txt, 0.35, f'{bsec:.3f}', fontsize=FS_SET,
                color=col, alpha=0.85, va='bottom', ha='left')

    ax.axvline(0, color='#cccccc', linewidth=0.8, linestyle='--', zorder=0)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([g[0] for g in grupos], fontsize=FS_YTICK)
    ax.set_title(titulo, fontsize=FS_TITLE, fontweight='bold',
                 color=cor_setor, pad=10)
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(0.2, n + 1.0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='x', alpha=0.18, linestyle='--')
    ax.tick_params(axis='x', labelsize=FS_XTICK)


# ── Figura ────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(13, 5.8),
                         gridspec_kw={'width_ratios': [1, 1, 1]})

plot_painel(axes[0], grupos_FA, COR_FA, 'FA', 'Ferro & Aço',  x_min=-4.5, x_max=0.6)
plot_painel(axes[1], grupos_AL, COR_AL, 'AL', 'Alumínio',     x_min=-2.5, x_max=0.5)
plot_painel(axes[2], grupos_CE, COR_CE, 'CE', 'Cimento',      x_min=-2.0, x_max=0.3)

axes[1].set_xlabel('Elasticidade-preço do market share (β)', fontsize=FS_XLABEL, labelpad=7)

# Legenda
dot_br  = mlines.Line2D([], [], color=COR_BR, marker='o', linestyle='None',
                         markersize=8,  label='Brasil (círculo, tamanho ∝ vol. exportado 2023–25)')
dot_ar  = mlines.Line2D([], [], color=COR_AR, marker='^', linestyle='None',
                         markersize=8,  label='Argentina (triângulo, tamanho ∝ vol. exportado 2023–25)')
dot_gl  = mlines.Line2D([], [], color=COR_GL, marker='s', linestyle='None',
                         markersize=6,  label='Global β (quadrado cinza)')
lin_br  = mlines.Line2D([], [], color=COR_BR, linestyle=':',   linewidth=1.4,
                         label='β setorial — Brasil (pontilhado)')
lin_ar  = mlines.Line2D([], [], color=COR_AR, linestyle='-.',  linewidth=1.2,
                         label='β setorial — Argentina (traço-ponto)')
lin_gl  = mlines.Line2D([], [], color=COR_GL, linestyle='--',  linewidth=1.0,
                         label='β setorial — Global (tracejado)')

fig.legend(handles=[dot_br, dot_ar, dot_gl, lin_br, lin_ar, lin_gl],
           fontsize=FS_LEGEND, loc='lower center', ncol=3,
           bbox_to_anchor=(0.5, 0.0), framealpha=0.95)

note = ('Nota: β acima = Brasil; β abaixo = Argentina; β omitido quando virtualmente idêntico ao Brasil. '
        'Volume share (%) anotado junto ao marcador quando > 2%.')
fig.text(0.01, -0.07, note, fontsize=FS_NOTE, color='#555', style='italic')

fig.suptitle(
    'Elasticidades-preço do market share por grupo de produto — Brasil, Argentina e Global',
    fontsize=FS_TITLE, fontweight='bold', y=1.03)

plt.tight_layout(w_pad=2.8, rect=[0, 0.14, 1, 1])
plt.savefig(out + 'G1_elasticidades_combinado.png', dpi=300, bbox_inches='tight')
plt.close()
print('Salvo: G1_elasticidades_combinado.png')

import csv, math, sys
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import numpy as np
from matplotlib import rcParams

sys.stdout.reconfigure(encoding='utf-8')

root = 'C:/Users/loren/OneDrive/Documentos/TCC CBAM/Projeto R/Versão Claude code/MODELO_OFICIAL'
out  = root + '/figuras_geradas/'

rcParams['font.family'] = 'sans-serif'
rcParams['font.size']   = 10

COR_FA = '#2c6e9e'
COR_AL = '#c0392b'

# ══════════════════════════════════════════════════════════════════════════════
# TABELA 1 — Capacidade explicativa (R²)
# ══════════════════════════════════════════════════════════════════════════════

fig, ax = plt.subplots(figsize=(9, 3.6))
ax.axis('off')

# R² values — v2
r2_fe    = [0.782, 0.812, 0.721]
r2_total = [0.906, 0.935, 0.916]
dr2      = [0.123, 0.123, 0.195]
erro     = [round(1 - r, 3) for r in r2_total]  # nao explicado

def pct(v): return f'{v*100:.1f}%'

dados = [
    ['Pseudo-R² — só efeitos fixos',
     '0,782', '0,812', '0,721'],
    ['Pseudo-R² — modelo completo (FEs + preço)',
     '0,906', '0,935', '0,916'],
    ['ΔR² marginal do preço',
     '0,123', '0,123', '0,195'],
    ['% variância — efeitos fixos',
     pct(r2_fe[0]), pct(r2_fe[1]), pct(r2_fe[2])],
    ['% variância — preço relativo',
     pct(dr2[0]),   pct(dr2[1]),   pct(dr2[2])],
    ['% variância — não explicada (erro)',
     pct(erro[0]),  pct(erro[1]),  pct(erro[2])],
]

col_labels = ['Métrica', 'Alumínio', 'Ferro e Aço', 'Cimento']

table = ax.table(
    cellText=dados,
    colLabels=col_labels,
    cellLoc='center',
    loc='center',
    colWidths=[0.46, 0.18, 0.18, 0.18],
)
table.auto_set_font_size(False)
table.set_fontsize(9.5)
table.scale(1, 1.65)

# Cabeçalho
for j in range(4):
    cell = table[0, j]
    cell.set_facecolor('#2d3748')
    cell.set_text_props(color='white', fontweight='bold')

# Linhas alternadas + destaques
for i in range(1, len(dados) + 1):
    bg = '#f7fafc' if i % 2 == 0 else 'white'
    for j in range(4):
        cell = table[i, j]
        cell.set_facecolor(bg)
        cell.set_edgecolor('#e2e8f0')
        if j == 0:
            cell.set_text_props(ha='left')
        if i in [4, 5, 6]:
            cell.set_text_props(fontweight='bold' if j > 0 else 'normal')

# Linha "não explicado" em vermelho suave
for j in range(4):
    table[6, j].set_facecolor('#fff5f5')
    if j > 0:
        table[6, j].set_text_props(color='#c0392b', fontweight='bold')

# Separadores entre blocos
for j in range(4):
    table[3, j].set_edgecolor('#2d3748')   # após R² total
    table[4, j].set_edgecolor('#aaaaaa')   # início bloco %

ax.set_title('Decomposição da capacidade explicativa — PPML (pseudo-R²)',
             fontsize=11, fontweight='bold', pad=12, loc='left')

note = ('Nota: % variância calculada em relação à variância total (1). '
        'Efeitos fixos: exporter×produto e produto×ano. '
        'A soma das três parcelas é 100% por construção.')
fig.text(0.02, 0.01, note, fontsize=7.5, color='#555555', style='italic')

plt.tight_layout()
plt.savefig(out + 'T_capacidade_explicativa.png', dpi=160, bbox_inches='tight')
plt.close()
print('Salvo: T_capacidade_explicativa.png')


# ══════════════════════════════════════════════════════════════════════════════
# FIGURA 1 — Dot plot: elasticidades por grupo + nível de setor
# ══════════════════════════════════════════════════════════════════════════════

# (label, β_BR, β_AR, β_global, vol_BR%, vol_AR%)
# Valores de _calcula_grupos.py — modelo 2010-2025, volumes 2023-2025
# Ordem: menos processado (baixo) → mais processado (cima)
grupos_FA = [
    ('Long &\ntubular',           -1.352, -0.790, -1.512,  2.9, 95.0),  # mais processado → topo
    ('Semi-finished\n& flat',     -3.482, -1.859, -2.303, 16.5,  5.0),
    ('Primaries\n(ore/pig iron)', -0.168, -0.187, -0.187, 80.6,  0.0),  # menos → base
]
grupos_AL = [
    ('Manufactured\n& finished',  -1.280, -1.129, -1.029,  0.9,  0.4),  # mais → topo
    ('Rolled &\ntubular',         -1.515, -1.976, -1.123, 10.3,  0.7),
    ('Primary &\nsemi-finished',  -0.556, -0.334, -0.572, 88.8, 98.9),  # menos → base
]
grupos_CE = [
    ('Special\ncements',  -0.156, -1.225, -1.225,   0.0,   0.0),  # mais → topo
    ('Portland\ncement',  -1.054, -1.231, -1.231,   0.0,   0.0),
    ('Clinker',           -1.305, -0.219, -1.376,   0.0,   0.0),
    ('Clay',              -1.611, -0.188, -1.485, 100.0, 100.0),  # menos → base
]

COR_CE    = '#27ae60'
COR_FA_AR = '#7fb3d3'
COR_AL_AR = '#e08080'
COR_CE_AR = '#76c893'

beta_setor = {
    'FA': {'BR': -0.749, 'AR': -0.844},
    'AL': {'BR': -0.662, 'AR': -0.349},
    'CE': {'BR': -1.611, 'AR': -0.188},
}

Y_OFF    = 0.20   # offset vertical entre dots BR e AR
BETA_THR = 0.10   # diferença mínima para mostrar β global separado
FS_BETA  = 6.5    # fontsize das anotações de β

def _vol_annot(ax, val, yy, col, vol, x_min, x_max):
    """Anotação de volume; garante que não sai pelos bordos."""
    if vol <= 2.0:
        return
    if vol > 35:
        # texto à esquerda do ponto
        ax.annotate(f'{vol:.0f}%', xy=(val, yy), xytext=(-14, 0),
                    textcoords='offset points', fontsize=8, color=col,
                    va='center', ha='right', alpha=0.9, clip_on=False)
    else:
        ax.annotate(f'{vol:.0f}%', xy=(val, yy), xytext=(8, 0),
                    textcoords='offset points', fontsize=8, color=col,
                    va='center', ha='left', alpha=0.9, clip_on=False)

def plot_painel(ax, grupos, cor_br, cor_ar, titulo, setor_key, x_min=-6.5):
    n     = len(grupos)
    y_pos = list(range(n, 0, -1))
    x_max = 1.5

    for y, (label, bBR, bAR, bGlb, vol_BR, vol_AR) in zip(y_pos, grupos):
        yBR = y + Y_OFF
        yAR = y - Y_OFF

        # Linha de conexão BR-AR
        ax.plot([bBR, bAR], [yBR, yAR], color='#cccccc',
                linewidth=1.2, zorder=1, alpha=0.7)

        # Global (quadrado cinza)
        ax.scatter(bGlb, y, s=75, color='#aaaaaa', marker='s',
                   zorder=3, linewidths=0.5, edgecolors='#888888', alpha=0.85)

        # Brazil (círculo) — mais opaco quando sobrepõe
        sBR   = max(60, 55 + vol_BR * 14)
        close = abs(bBR - bAR) < 0.25
        ax.scatter(bBR, yBR, s=sBR, color=cor_br, marker='o', zorder=5,
                   linewidths=1.2, edgecolors='white', alpha=1.0 if close else 0.92)

        # Argentina (triângulo)
        sAR = max(60, 55 + vol_AR * 14)
        ax.scatter(bAR, yAR, s=sAR, color=cor_ar, marker='^', zorder=4,
                   linewidths=1.2, edgecolors='white', alpha=1.0 if close else 0.92)

        # Anotações de volume (horizontal, ao lado do marcador)
        _vol_annot(ax, bBR, yBR, cor_br, vol_BR, x_min, x_max)
        _vol_annot(ax, bAR, yAR, cor_ar, vol_AR, x_min, x_max)

        # Valores de β — separados verticalmente dos rótulos de volume:
        #   BR:  ACIMA do dot BR (não conflita com volume que está no mesmo y)
        #   AR:  ABAIXO do dot AR
        #   Glb: ABAIXO do quadrado global (y central)
        ax.text(bBR, yBR + 0.13, f'{bBR:.2f}', fontsize=FS_BETA, color=cor_br,
                ha='center', va='bottom', alpha=0.92, zorder=6, clip_on=False)
        ax.text(bAR, yAR - 0.13, f'{bAR:.2f}', fontsize=FS_BETA, color=cor_ar,
                ha='center', va='top', alpha=0.92, zorder=6, clip_on=False)
        # Global só se diferente de ambos os países
        if abs(bGlb - bBR) > BETA_THR and abs(bGlb - bAR) > BETA_THR:
            ax.text(bGlb, y - 0.16, f'{bGlb:.2f}', fontsize=FS_BETA, color='#888888',
                    ha='center', va='top', alpha=0.85, zorder=6, clip_on=False)

    # Linhas de setor (BR e AR)
    for pais, col, ytext in [('BR', cor_br, 0.40), ('AR', cor_ar, 0.22)]:
        b = beta_setor[setor_key][pais]
        ax.axvline(b, color=col, linewidth=1.3, linestyle=':', alpha=0.55, zorder=0)
        # posiciona rótulo para não sobrepor borda
        x_txt = b + 0.07 if b > x_min + 0.5 else b - 0.07
        ha_txt = 'left' if b > x_min + 0.5 else 'right'
        ax.text(x_txt, ytext, f'{pais}: {b:.3f}',
                fontsize=7, color=col, alpha=0.8, va='bottom', ha=ha_txt)

    ax.axvline(0, color='#cccccc', linewidth=0.7, linestyle='--', zorder=0)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([g[0] for g in grupos], fontsize=10)
    ax.set_xlabel('Market share price elasticity (β)', fontsize=9.5)
    ax.set_title(titulo, fontsize=12, fontweight='bold', color=cor_br, pad=10)
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(0.1, n + 1.0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='x', alpha=0.2, linestyle='--')

fig, axes = plt.subplots(1, 3, figsize=(17, 5.5),
                         gridspec_kw={'width_ratios': [3, 3, 4]})

plot_painel(axes[0], grupos_FA, COR_FA,  COR_FA_AR, 'Iron & Steel', 'FA', x_min=-6.5)
plot_painel(axes[1], grupos_AL, COR_AL,  COR_AL_AR, 'Aluminium',    'AL', x_min=-3.5)
plot_painel(axes[2], grupos_CE, COR_CE,  COR_CE_AR, 'Cement',       'CE', x_min=-3.5)

# Legenda
dot_br  = mlines.Line2D([], [], color='#444', marker='o', linestyle='None',
                         markersize=9, label='Brazil (circle, size ∝ volume share, 2023–2025)')
dot_ar  = mlines.Line2D([], [], color='#888', marker='^', linestyle='None',
                         markersize=9, label='Argentina (triangle, size ∝ volume share, 2023–2025)')
dot_glb = mlines.Line2D([], [], color='#aaa', marker='s', linestyle='None',
                         markersize=7, label='Global β (gray square)')
lin_set = mlines.Line2D([], [], color='#888', linestyle=':',
                         linewidth=1.4, label='Sector-level β (dotted line)')
fig.legend(handles=[dot_br, dot_ar, dot_glb, lin_set],
           fontsize=8.5, loc='lower center', ncol=4,
           bbox_to_anchor=(0.5, -0.04), framealpha=0.9)

note = ('Note: Sector β = volume-weighted average across product groups. '
        'β values shown next to each marker; global β (gray) omitted when virtually equal to country-specific.')
fig.text(0.02, -0.08, note, fontsize=7.5, color='#555', style='italic')

fig.suptitle('Estimated market share price elasticities by product group — Brazil and Argentina',
             fontsize=12, fontweight='bold', y=1.02)

plt.tight_layout()
plt.savefig(out + 'G1_elasticidades_grupos.png', dpi=160, bbox_inches='tight')
plt.close()
print('Salvo: G1_elasticidades_grupos.png')


# ══════════════════════════════════════════════════════════════════════════════
# TABELA 2 — Validação out-of-sample
# ══════════════════════════════════════════════════════════════════════════════

fig, ax = plt.subplots(figsize=(11, 4.2))
ax.axis('off')

dados_oos = [
    # Métrica, AL-BR, AL-AR, FA-BR, FA-AR
    ['N observações (produto × ano)',        '29',    '14',   '108',  '26'],
    ['Correlação Δprev × Δrealizado',        '0,781', '0,018','0,626','0,736'],
    ['Hit ratio (acerto de sinal)',          '86,2%', '71,4%','66,7%','73,1%'],
    ['Hit ratio ajustado (vs. 50% random)', '+36,2pp','+21,4pp','+16,7pp','+23,1pp'],
    ['Theil U — vs. persistência (Δ=0)',    '0,687', '0,987', '0,803','0,750'],
    ['Theil U — vs. média histórica',       '0,690', '1,176', '0,807','0,753'],
    ['Cor. magnitude quando acerta sinal',  '0,800', '−0,109','0,731','0,799'],
    ['MAE quando erra sinal',               '0,985', '1,437', '1,075','1,011'],
]

col_labels_oos = ['Métrica',
                  'Alumínio\nBrasil', 'Alumínio\nArgentina',
                  'Ferro e Aço\nBrasil', 'Ferro e Aço\nArgentina']

table2 = ax.table(
    cellText=dados_oos,
    colLabels=col_labels_oos,
    cellLoc='center',
    loc='center',
    colWidths=[0.38, 0.155, 0.155, 0.155, 0.155],
)
table2.auto_set_font_size(False)
table2.set_fontsize(9)
table2.scale(1, 1.75)

# Cabeçalho
for j in range(5):
    cell = table2[0, j]
    cell.set_facecolor('#2d3748')
    cell.set_text_props(color='white', fontweight='bold')

# Cores de coluna para AL e FA
col_cores = {1: '#ebf5fb', 2: '#ebf5fb', 3: '#eaf4f0', 4: '#eaf4f0'}

for i in range(1, len(dados_oos) + 1):
    for j in range(5):
        cell = table2[i, j]
        if j in col_cores:
            bg = col_cores[j] if i % 2 == 1 else 'white'
        else:
            bg = '#f7fafc' if i % 2 == 0 else 'white'
        cell.set_facecolor(bg)
        cell.set_edgecolor('#e2e8f0')
        if j == 0:
            cell.set_text_props(ha='left')

# Destaque Theil U > 1 (pior que naive) — AR alumínio
table2[6, 2].set_facecolor('#fdecea')
table2[6, 2].set_text_props(color='#c0392b', fontweight='bold')

# Separadores visuais
for j in range(5):
    table2[2, j].set_edgecolor('#555')   # após N
    table2[5, j].set_edgecolor('#555')   # após Theil U persist

ax.set_title('Validação out-of-sample — variação de share (Δshare, pooled 2023–2025)\n'
             'Modelo treinado até 2022; testado em 2023–2025',
             fontsize=11, fontweight='bold', pad=12, loc='left')

note2 = ('Nota: Theil U < 1 indica que o modelo supera o benchmark naive. '
         'Theil U > 1 (vermelho) indica que o modelo é inferior ao naive naquela dimensão. '
         'Cimento omitido por N insuficiente (6 obs Brasil, Argentina indisponível).')
fig.text(0.02, 0.0, note2, fontsize=7.5, color='#555', style='italic')

plt.tight_layout()
plt.savefig(out + 'T_validacao_oos.png', dpi=160, bbox_inches='tight')
plt.close()
print('Salvo: T_validacao_oos.png')

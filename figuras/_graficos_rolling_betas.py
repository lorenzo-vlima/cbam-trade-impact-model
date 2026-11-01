"""
Rolling beta stability plot.
Shows how sector-level and group-level betas evolve
as more years are added to the estimation window.
"""
import csv, math, sys
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from matplotlib import rcParams

sys.stdout.reconfigure(encoding='utf-8')

import os; root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(chr(92), '/')
out  = root + '/figuras_geradas/'
base = root + '/outputs'

rcParams['font.family'] = 'sans-serif'

COR_FA = '#2c6e9e'
COR_AL = '#c0392b'
COR_BR = '#2c6e9e'
COR_AR = '#e67e22'

# Map end-year -> folder suffix
windows = {
    2015: 'j3_roll2015',
    2017: 'j3_roll2017',
    2019: 'j3_2019test',
    2022: 'j3_roll2022',
    2024: 'j1_2025test',
    2025: 'j3_v2',
}

# File name per suffix type (rolling uses 4_betas, v2/test use 8_tabela)
def beta_file(suf):
    if 'v2' in suf:
        return '8_tabela_betas_grupos.csv'
    return '4_betas_simulacao_cbam.csv'

# Volume weights for sector-level beta (from full model 28_analise_share_vol_base.csv)
# We use full-model weights as reference — stable across windows
def load_vol_weights(setor):
    path = f'{base}/{setor}_brasil_e_argentina_individual_post_tax_j3_v2/28_analise_share_vol_base.csv'
    w = {}
    total = 0
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            prod = row['product'].strip()
            ton  = float(row['ton_total_mercado'])
            w[prod] = w.get(prod, 0) + ton
            total += ton
    return {p: v/total for p,v in w.items()}

def load_group_map(setor):
    """Load product->grupo mapping from full v2 model."""
    path = f'{base}/{setor}_brasil_e_argentina_individual_post_tax_j3_v2/8_tabela_betas_grupos.csv'
    gmap = {}
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            gmap[row['product'].strip()] = row.get('grupo','').strip()
    return gmap

def load_betas(setor, suf):
    fname = beta_file(suf)
    path  = f'{base}/{setor}_brasil_e_argentina_individual_post_tax_{suf}/{fname}'
    gmap  = load_group_map(setor)
    try:
        rows = {}
        with open(path, encoding='utf-8') as f:
            for row in csv.DictReader(f):
                prod = row['product'].strip()
                rows[prod] = {
                    'beta_sim_BR': row.get('beta_sim_BR',''),
                    'beta_sim_AR': row.get('beta_sim_AR',''),
                    'beta_base':   row.get('beta_base',''),
                    'grupo':       gmap.get(prod, ''),
                }
        return rows
    except:
        return None

def weighted_beta(betas, weights, col):
    total_w, total_wb = 0, 0
    for prod, w in weights.items():
        b = betas.get(prod, {}).get(col, '')
        try:
            bv = float(b)
            if math.isfinite(bv):
                total_w  += w
                total_wb += w * bv
        except:
            pass
    return total_wb / total_w if total_w > 0 else float('nan')

def group_weighted_beta(betas, weights, col, grupo):
    total_w, total_wb = 0, 0
    for prod, row in betas.items():
        if row.get('grupo','') != grupo: continue
        w = weights.get(prod, 0)
        b = row.get(col, '')
        try:
            bv = float(b)
            if math.isfinite(bv):
                total_w  += w
                total_wb += w * bv
        except:
            pass
    return total_wb / total_w if total_w > 0 else float('nan')

# ── Build series ──────────────────────────────────────────────────────────────
anos = sorted(windows.keys())

setores_cfg = [
    ('ferro_aco', 'Iron & Steel', COR_FA,
     [('1','Primaries'), ('2','Semi-finished & flat'), ('3','Long & tubular')]),
    ('aluminio',  'Aluminium',    COR_AL,
     [('1','Primary & semi-finished'), ('2','Rolled & tubular'), ('3','Manufactured')]),
]

fig, axes = plt.subplots(2, 2, figsize=(12, 9), sharey=False)

for row_idx, (setor, nome, cor_setor, grupos) in enumerate(setores_cfg):
    weights = load_vol_weights(setor)

    # Left panel: sector-level beta BR and AR
    ax_sec = axes[row_idx][0]
    # Right panel: group-level betas (global) over time
    ax_grp = axes[row_idx][1]

    ser_BR, ser_AR, ser_GL = [], [], []
    grp_series = {g: [] for g,_ in grupos}

    for ano in anos:
        suf   = windows[ano]
        betas = load_betas(setor, suf)
        if betas is None:
            for lst in [ser_BR, ser_AR, ser_GL] + list(grp_series.values()):
                lst.append(float('nan'))
            continue

        ser_BR.append(weighted_beta(betas, weights, 'beta_sim_BR'))
        ser_AR.append(weighted_beta(betas, weights, 'beta_sim_AR'))
        ser_GL.append(weighted_beta(betas, weights, 'beta_base'))
        for g, _ in grupos:
            grp_series[g].append(group_weighted_beta(betas, weights, 'beta_base', g))

    # ── Left: sector beta BR, AR, Global ──
    def plot_line(ax, y, color, label, ls='-', marker='o', lw=1.8, alpha=1.0):
        valid = [(x, v) for x, v in zip(anos, y) if not math.isnan(v)]
        if len(valid) < 2: return
        xs, ys = zip(*valid)
        ax.plot(xs, ys, color=color, lw=lw, ls=ls, marker=marker,
                markersize=6, label=label, alpha=alpha, zorder=3)

    plot_line(ax_sec, ser_BR, COR_BR,    'Brazil (β_sim)',  ls='-',  marker='o')
    plot_line(ax_sec, ser_AR, COR_AR,    'Argentina (β_sim)', ls='-', marker='^')
    plot_line(ax_sec, ser_GL, '#888888', 'Global (β_base)', ls='--', marker='s',
              lw=1.2, alpha=0.7)

    ax_sec.axhline(0, color='#cccccc', lw=0.7, ls='--')
    ax_sec.set_title(f'{nome} — sector β (volume-weighted)', fontsize=11,
                     fontweight='bold', color=cor_setor)
    ax_sec.set_ylabel('β estimate', fontsize=10)
    ax_sec.legend(fontsize=8, loc='lower left', framealpha=0.9)
    ax_sec.spines['top'].set_visible(False)
    ax_sec.spines['right'].set_visible(False)
    ax_sec.set_xticks(anos)
    ax_sec.tick_params(labelsize=8)
    ax_sec.grid(axis='y', alpha=0.2, ls='--')

    # ── Right: group-level global beta ──
    colors_grp = ['#1f77b4', '#ff7f0e', '#2ca02c']
    for (g, glabel), col in zip(grupos, colors_grp):
        plot_line(ax_grp, grp_series[g], col, glabel, marker='D', lw=1.6)

    ax_grp.axhline(0, color='#cccccc', lw=0.7, ls='--')
    ax_grp.set_title(f'{nome} — group β (global, volume-weighted)', fontsize=11,
                     fontweight='bold', color=cor_setor)
    ax_grp.legend(fontsize=8, loc='lower left', framealpha=0.9)
    ax_grp.spines['top'].set_visible(False)
    ax_grp.spines['right'].set_visible(False)
    ax_grp.set_xticks(anos)
    ax_grp.tick_params(labelsize=8)
    ax_grp.grid(axis='y', alpha=0.2, ls='--')

for ax in axes[1]:
    ax.set_xlabel('Training window end year', fontsize=10)

fig.suptitle(
    'Beta stability across estimation windows (2010 – end year)\n'
    'Left: volume-weighted sector β by country  |  Right: group-level global β',
    fontsize=11, y=1.02)

plt.tight_layout(h_pad=3.5, w_pad=3.0)
plt.savefig(out + 'G_rolling_betas.png', dpi=300, bbox_inches='tight')
plt.close()
print('Salvo: G_rolling_betas.png')

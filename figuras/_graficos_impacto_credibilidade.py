"""
Impacto CBAM por produto ponderado pela credibilidade do modelo.

Para cada produto:
  R²_p = corr(delta_pred, delta_obs)²  — calculado com todos os exportadores
          in the v2 validation period (2023-2025). Measures how much price
          explains share competition in that specific product.

  Impacto bruto     = delta_share_pct/100 × euro_exportado_base  (M€)
  Impacto ajustado  = R²_p × impacto bruto

The bar of each product is split into:
  ■ solid part   = adjusted impact (where we have evidence of the mechanism)
  □ parte hachura  = parte incerta (outros fatores dominam)
"""
import csv, math, sys
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import rcParams

sys.stdout.reconfigure(encoding='utf-8')

import os; root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(chr(92), '/')
out  = root + '/figuras_geradas/'
base = root + '/outputs'

rcParams['font.family'] = 'sans-serif'

COR_FA = '#2c6e9e'
COR_AL = '#c0392b'

CENARIO    = '75/tCO2'
TARIFA     = 'MFN'
PAIS_FOCO  = 'BR'
MIN_EXP    = 5    # min exportadores para calcular R²_p

# ── R²_p by product (v2 validation, all exporters) ────────────────────
def pearson_r(x, y):
    n = len(x)
    if n < 3: return float('nan')
    mx, my = sum(x)/n, sum(y)/n
    num = sum((a-mx)*(b-my) for a,b in zip(x,y))
    dx  = sum((a-mx)**2 for a in x)**0.5
    dy  = sum((b-my)**2 for b in y)**0.5
    return num/(dx*dy) if dx*dy > 0 else float('nan')

def compute_r2_by_product(setor):
    path = f'{base}/{setor}_brasil_e_argentina_individual_post_tax_j3_v2/5c_validacao_delta_dados.csv'
    by_prod = defaultdict(lambda: {'pred':[], 'obs':[]})
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            prod = row['product'].strip()
            try:
                obs  = float(row['delta_log_dv_obs'])
                pred = float(row['delta_log_dv_pred'])
            except: continue
            if not (math.isfinite(obs) and math.isfinite(pred)): continue
            by_prod[prod]['pred'].append(pred)
            by_prod[prod]['obs'].append(obs)
    r2 = {}
    for prod, d in by_prod.items():
        if len(d['pred']) < MIN_EXP: continue
        r = pearson_r(d['pred'], d['obs'])
        r2[prod] = max(r**2, 0) if math.isfinite(r) else 0.0
    return r2

# ── Base exported value (BR) ─────────────────────────────────────────────────
def load_exports(setor):
    path = f'{base}/{setor}_brasil_e_argentina_individual_post_tax_j3_v2/28_analise_share_vol_base.csv'
    exp = {}
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['exporter'].strip() == PAIS_FOCO:
                prod = row['product'].strip()
                try: exp[prod] = float(row['euro_exportado'])
                except: pass
    return exp

# ── Simulated CBAM impact (BR, base scenario) ─────────────────────────────────
def load_cbam_impact(setor):
    path = f'{base}/{setor}_brasil_e_argentina_individual_post_tax_j3_v2/14_cbam_resumo_product.csv'
    imp = {}
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if (row['exporter'].strip() == PAIS_FOCO and
                row['cenario_carbono'].strip() == CENARIO and
                row['cenario_tarifa'].strip() == TARIFA):
                prod = row['product'].strip()
                try:
                    pct = float(row['delta_share_pct'])   # % change in share
                    imp[prod] = pct / 100.0               # decimal
                except: pass
    return imp

# ── Plot ──────────────────────────────────────────────────────────────────────
setores_cfg = [
    ('ferro_aco', 'Iron & Steel', COR_FA),
    ('aluminio',  'Aluminium',    COR_AL),
]

fig, axes = plt.subplots(1, 2, figsize=(15, 7), sharey=False)

for ax, (setor, nome, cor) in zip(axes, setores_cfg):
    r2_map  = compute_r2_by_product(setor)
    exp_map = load_exports(setor)
    imp_map = load_cbam_impact(setor)

    rows = []
    for prod in imp_map:
        if prod not in exp_map: continue
        eur     = exp_map[prod] / 1e6          # M€
        pct     = imp_map[prod]                 # delta share como decimal
        imp_bruto = pct * eur                   # M€, negativo = perda
        r2      = r2_map.get(prod, float('nan'))
        if math.isnan(r2): continue
        imp_adj = r2 * imp_bruto

        rows.append({
            'prod':      prod,
            'eur':       eur,
            'imp_bruto': imp_bruto,
            'imp_adj':   imp_adj,
            'r2':        r2,
        })

    if not rows: continue

    # Sort by raw impact (most negative first)
    rows.sort(key=lambda x: x['imp_bruto'])

    prods     = [r['prod']      for r in rows]
    imp_bruto = [r['imp_bruto'] for r in rows]
    imp_adj   = [r['imp_adj']   for r in rows]
    r2_vals   = [r['r2']        for r in rows]
    eur_vals  = [r['eur']       for r in rows]

    y_pos = range(len(rows))

    # Total bar (raw impact), transparent
    ax.barh(list(y_pos), imp_bruto,
            color=cor, alpha=0.18, edgecolor=cor, linewidth=0.5,
            label='Raw impact (simulated)', zorder=2)

    # Adjusted bar (R²_p × impact), solid
    ax.barh(list(y_pos), imp_adj,
            color=cor, alpha=0.80, edgecolor='none',
            label=f'Adjusted impact (× R²)', zorder=3)

    # Annotations
    x_max = max(abs(v) for v in imp_bruto) if imp_bruto else 1
    for i, (ib, ia, r2, eur) in enumerate(zip(imp_bruto, imp_adj, r2_vals, eur_vals)):
        # R² on the right
        ax.text(x_max * 0.02, i,
                f'R²={r2:.2f}',
                va='center', fontsize=6.8, color='#444444')
        # Base (EUR mn exported) on the left
        ax.text(-x_max * 0.02, i,
                f'€{eur:.1f}M',
                va='center', ha='right', fontsize=6.5, color='#777777')

    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(prods, fontsize=8)
    ax.axvline(0, color='#aaaaaa', lw=0.8)
    ax.set_xlabel('Simulated impact on exports to the EU (EUR mn)', fontsize=9.5)

    # Totais no canto
    total_bruto = sum(imp_bruto)
    total_adj   = sum(imp_adj)
    ax.text(0.98, 0.98,
            f'Total bruto:    {total_bruto:+.1f} M€\n'
            f'Total ajustado: {total_adj:+.1f} M€\n'
            f'Mean R² factor: {sum(r2_vals)/len(r2_vals):.2f}',
            transform=ax.transAxes, fontsize=8.5,
            ha='right', va='top',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                      edgecolor='#cccccc', alpha=0.92))

    ax.set_title(f'{nome} — Brazil\nCBAM impact {CENARIO} {TARIFA}',
                 fontsize=11, fontweight='bold', color=cor, pad=8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(labelsize=8)
    ax.grid(axis='x', alpha=0.15, ls='--')

    bruto_p = mpatches.Patch(facecolor=cor, alpha=0.18,
                              edgecolor=cor, label='Raw impact (simul.)')
    adj_p   = mpatches.Patch(facecolor=cor, alpha=0.80,
                              label='R²-adjusted (price mechanism confirmed)')
    ax.legend(handles=[bruto_p, adj_p], fontsize=7.5,
              loc='lower right', framealpha=0.9)

fig.suptitle(
    f'Brazil — impacto CBAM bruto vs. ajustado pela credibilidade do modelo por produto\n'
    f'Adjustment: R²_product = fraction of the share change explained by relative price '
    f'(validation 2023–2025)',
    fontsize=11, y=1.01)

plt.tight_layout(w_pad=4.0)
plt.savefig(out + 'G_impacto_credibilidade.png', dpi=300, bbox_inches='tight')
plt.close()
print('Saved: G_impacto_credibilidade.png')

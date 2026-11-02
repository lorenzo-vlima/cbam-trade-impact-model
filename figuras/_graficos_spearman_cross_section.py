"""
Within-product cross-sectional Spearman rank correlations.

LOGIC:
  For each product × year there are ~30-50 exporting countries to the EU.
  The model predicts which country should gain the most share (the one with the lowest
  relative price). The test asks: is the *order* of countries by predicted share
  bate com a *ordem* pelo share observado?

  Spearman rho > 0 significa: sim, o ranking de quem ganha/perde share
  correct, even if the predicted size is imprecise.

DADOS: modelo completo v2 (2010–2025), anos de teste 2023, 2024, 2025.
  By product: we compute rho for each year separately and take the mean.
  At least 5 exporters per product×year.
"""
import csv, math, sys
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import rcParams
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

import os; root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(chr(92), '/')
out  = root + '/figuras_geradas/'
base = root + '/outputs'

rcParams['font.family'] = 'sans-serif'

COR_FA = '#2c6e9e'
COR_AL = '#c0392b'
MIN_EXP = 5   # minimum number of exporters per product×year

# ── Volume weights (to weight the importance of each product) ──────────────
def load_vol_weights(setor):
    path = f'{base}/{setor}_brasil_e_argentina_individual_post_tax_j3_v2/28_analise_share_vol_base.csv'
    w = {}
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            prod = row['product'].strip()
            ton  = float(row['ton_total_mercado'])
            w[prod] = w.get(prod, 0) + ton
    total = sum(w.values())
    return {p: v/total for p, v in w.items()}

# ── Spearman ──────────────────────────────────────────────────────────────────
def spearman(x, y):
    """Spearman rho between x (predicted) and y (observed)."""
    n = len(x)
    if n < 3:
        return float('nan')
    def ranks(v):
        s = sorted(range(n), key=lambda i: v[i])
        r = [0] * n
        for rank, i in enumerate(s):
            r[i] = rank + 1
        return r
    rx, ry = ranks(x), ranks(y)
    d2 = sum((a - b)**2 for a, b in zip(rx, ry))
    return 1 - 6*d2 / (n*(n**2 - 1))

# ── Load v2 data (all exporters, 2023-2025) ───────────────────────
def load_val_v2(setor):
    """
    Retorna dict: { (product, year): {'pred': [...], 'obs': [...]} }
    """
    path = f'{base}/{setor}_brasil_e_argentina_individual_post_tax_j3_v2/5c_validacao_delta_dados.csv'
    data = defaultdict(lambda: {'pred': [], 'obs': []})
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            prod = row['product'].strip()
            yr   = row['year'].strip()
            try:
                obs  = float(row['delta_log_dv_obs'])
                pred = float(row['delta_log_dv_pred'])
            except Exception:
                continue
            if not (math.isfinite(obs) and math.isfinite(pred)):
                continue
            data[(prod, yr)]['pred'].append(pred)
            data[(prod, yr)]['obs'].append(obs)
    return data

# ── Aggregate rho by product (mean over years with enough data) ─────────────
def aggregate_by_product(data):
    """
    For each product, computes rho for each available year (if n >= MIN_EXP)
    and returns the mean rho, the number of years and the mean n per year.
    """
    prod_years = defaultdict(dict)
    for (prod, yr), vals in data.items():
        if len(vals['pred']) >= MIN_EXP:
            rs = spearman(vals['pred'], vals['obs'])
            if math.isfinite(rs):
                prod_years[prod][yr] = {'rs': rs, 'n': len(vals['pred'])}

    results = []
    for prod, yr_dict in prod_years.items():
        rs_list = [v['rs'] for v in yr_dict.values()]
        n_list  = [v['n']  for v in yr_dict.values()]
        results.append({
            'prod':    prod,
            'rs_mean': sum(rs_list) / len(rs_list),
            'n_anos':  len(rs_list),
            'n_exp':   sum(n_list) / len(n_list),   # mean exporters/year
            'rs_min':  min(rs_list),
            'rs_max':  max(rs_list),
        })
    return results

# ── Plot ──────────────────────────────────────────────────────────────────────
setores_cfg = [
    ('ferro_aco', 'Iron & Steel', COR_FA),
    ('aluminio',  'Aluminium',    COR_AL),
]

fig, axes = plt.subplots(1, 2, figsize=(14, 7), sharey=False)

for ax, (setor, nome, cor) in zip(axes, setores_cfg):
    weights = load_vol_weights(setor)
    data    = load_val_v2(setor)
    results = aggregate_by_product(data)

    # Add vol share and sort by rho
    for r in results:
        r['vol'] = weights.get(r['prod'], 0) * 100
    results.sort(key=lambda x: x['rs_mean'])

    prods    = [r['prod']    for r in results]
    rs_vals  = [r['rs_mean'] for r in results]
    n_anos   = [r['n_anos']  for r in results]
    n_exp    = [r['n_exp']   for r in results]
    vols     = [r['vol']     for r in results]
    rs_mins  = [r['rs_min']  for r in results]
    rs_maxs  = [r['rs_max']  for r in results]

    y_pos = range(len(prods))

    # Bars with opacity proportional to volume
    vol_max = max(vols) if max(vols) > 0 else 1
    for i, (rs, vol) in enumerate(zip(rs_vals, vols)):
        alpha = 0.30 + 0.65 * (vol / vol_max) ** 0.5
        ax.barh(i, rs, color=cor, alpha=alpha, edgecolor='white',
                linewidth=0.4, zorder=3)

    # Min-max range across years (if more than 1 year is available)
    for i, (rs, rmin, rmax, na) in enumerate(zip(rs_vals, rs_mins, rs_maxs, n_anos)):
        if na > 1:
            ax.plot([rmin, rmax], [i, i], color='#444444', lw=1.8,
                    solid_capstyle='round', zorder=4, alpha=0.55)
            ax.plot([rmin], [i], marker='|', color='#444444', markersize=5,
                    zorder=5, alpha=0.55)
            ax.plot([rmax], [i], marker='|', color='#444444', markersize=5,
                    zorder=5, alpha=0.55)

    # Annotations: mean rho + info
    for i, (rs, n_a, ne, vol) in enumerate(zip(rs_vals, n_anos, n_exp, vols)):
        ax.text(rs + 0.012, i, f'{rs:.2f}', va='center', fontsize=7.5,
                color='#222222', fontweight='bold')
        # on the left: mean exporters and vol%
        info = f'n≈{ne:.0f}'
        if vol > 0.5:
            info += f'  {vol:.1f}%'
        ax.text(-0.015, i, info, va='center', ha='right', fontsize=6.8,
                color='#555555')

    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(prods, fontsize=8)
    ax.set_xlim(-0.22, 1.08)
    ax.axvline(0,   color='#888888', lw=0.8, ls='--')
    for ref in [0.3, 0.5, 0.7]:
        ax.axvline(ref, color='#e0e0e0', lw=0.6, ls=':')

    # Summary statistics
    pct_pos  = sum(1 for r in rs_vals if r > 0) / len(rs_vals) * 100
    mean_rs  = sum(rs_vals) / len(rs_vals)
    ax.text(0.98, 0.02,
            f'{len(rs_vals)} produtos | {pct_pos:.0f}% ρ>0\n'
            f'mean ρ = {mean_rs:.3f}',
            transform=ax.transAxes, fontsize=8.5, ha='right', va='bottom',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                      edgecolor='#cccccc', alpha=0.92))

    ax.set_title(
        f'{nome}\n'
        f'Cross-country Spearman ρ, by product\n'
        f'(modelo 2010–2025, teste 2023–2025, n≥{MIN_EXP} exportadores/ano)',
        fontsize=10.5, fontweight='bold', color=cor, pad=8)
    ax.set_xlabel('Spearman ρ  (predicted vs. actual ranking across countries)',
                  fontsize=9.5)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(labelsize=8)
    ax.grid(axis='x', alpha=0.15, ls='--')

    # Legenda
    big   = mpatches.Patch(facecolor=cor, alpha=0.90, label='Alto volume exportado')
    small = mpatches.Patch(facecolor=cor, alpha=0.30, label='Low exported volume')
    line  = plt.Line2D([0],[0], color='#444444', lw=1.8, label='Range 2023–2025')
    ax.legend(handles=[big, small, line], fontsize=7.5,
              loc='lower right', framealpha=0.9)

fig.suptitle(
    'Cross-sectional identification: within each product, do countries with\n'
    'the largest predicted price advantage gain more share? (2023–2025 test)',
    fontsize=11.5, y=1.01)

plt.tight_layout(w_pad=4.0)
plt.savefig(out + 'G_spearman_cross_section.png', dpi=300, bbox_inches='tight')
plt.close()
print('Saved: G_spearman_cross_section.png')

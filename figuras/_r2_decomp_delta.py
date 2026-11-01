"""
R² decomposition for share VARIATION (first differences).

Decomposes Var(Δlog share) into three components:

  Δlog(share_{i,p,t}) = β × Δlog(price_rel_{i,p,t})   [price]
                       + Δγ_{p,t}                        [demand trend]
                       + Δε                              [residual]

Where:
  - β × Δlog(price_rel): price competition mechanism (what CBAM activates)
  - Δγ_{p,t}: change in product×year FE = mean Δlog(share) across all
               exporters in product p at year t (common demand shock)
  - FE_{i×p} drops out in first differences (time-invariant → Δ = 0)

Contrast with level model (Table 4 in thesis):
  Level:     FEs explain ~87-90%, price ~12%, residual ~3-10%
  Variation: FE_{i×p} = 0, demand trend = ?, price = ?, residual = ?

Sectors: ferro_aco, aluminio, cimento
Uses v2 model betas (estimated 2010-2025).
"""
import csv, math, sys
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import rcParams

sys.stdout.reconfigure(encoding='utf-8')

root = 'C:/Users/loren/OneDrive/Documentos/TCC CBAM/Projeto R/Versão Claude code/MODELO_OFICIAL'
out  = root + '/figuras_geradas/'
cfg  = root + '/config'
bdir = root + '/outputs'

rcParams['font.family'] = 'sans-serif'

WINSOR_PCT = 0.01
MIN_EXP    = 5

# ── Helpers ───────────────────────────────────────────────────────────────────
def pearson_r(x, y):
    n = len(x)
    if n < 3: return float('nan')
    mx, my = sum(x)/n, sum(y)/n
    num = sum((a-mx)*(b-my) for a,b in zip(x,y))
    sdx = sum((a-mx)**2 for a in x)**0.5
    sdy = sum((b-my)**2 for b in y)**0.5
    return num/(sdx*sdy) if sdx*sdy > 0 else float('nan')

def r2(x, y):
    r = pearson_r(x, y)
    return r**2 if math.isfinite(r) else float('nan')

def r2_multivariate(xs_list, y):
    """R² of y ~ x1 + x2 + ... via OLS (normal equations)."""
    n = len(y)
    if n < len(xs_list) + 2: return float('nan')
    # add intercept
    X = [[1.0] + [xs[i] for xs in xs_list] for i in range(n)]
    k = len(X[0])
    # XtX and Xty
    XtX = [[sum(X[i][a]*X[i][b] for i in range(n)) for b in range(k)] for a in range(k)]
    Xty = [sum(X[i][a]*y[i] for i in range(n)) for a in range(k)]
    # solve via Gaussian elimination
    aug = [XtX[i][:] + [Xty[i]] for i in range(k)]
    for col in range(k):
        pivot = max(range(col, k), key=lambda r: abs(aug[r][col]))
        aug[col], aug[pivot] = aug[pivot], aug[col]
        if abs(aug[col][col]) < 1e-12: return float('nan')
        for row in range(k):
            if row == col: continue
            factor = aug[row][col] / aug[col][col]
            for c in range(col, k+1):
                aug[row][c] -= factor * aug[col][c]
    coef = [aug[i][k] / aug[i][i] for i in range(k)]
    # fitted and R²
    fitted = [sum(coef[a]*X[i][a] for a in range(k)) for i in range(n)]
    ss_res = sum((y[i]-fitted[i])**2 for i in range(n))
    ss_tot = sum((y[i]-sum(y)/n)**2 for i in range(n))
    return 1 - ss_res/ss_tot if ss_tot > 0 else float('nan')

# ── Data loading ──────────────────────────────────────────────────────────────
def load_panel(csv_path):
    raw = defaultdict(list)
    with open(csv_path, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter=';'):
            try:
                prod  = str(row['product']).strip()
                yr    = int(float(row['year']))
                ton   = float(row['ton'])
                price = float(row['price'])
                exp   = row['exporter'].strip()
                if ton > 1 and price > 0:
                    raw[(prod, yr)].append({'exp': exp, 'ton': ton, 'price': price})
            except: pass

    all_pr = []
    panel  = {}
    for (prod, yr), rows in raw.items():
        total_ton  = sum(r['ton']            for r in rows)
        total_euro = sum(r['price']*r['ton'] for r in rows)
        if total_ton <= 0: continue
        entries = []
        for r in rows:
            ton_loo  = total_ton  - r['ton']
            euro_loo = total_euro - r['price']*r['ton']
            if ton_loo <= 0: continue
            pr    = r['price'] / (euro_loo/ton_loo)
            share = r['ton']   / total_ton
            entries.append({'exp': r['exp'], 'ton': r['ton'],
                            'price_rel': pr, 'share': share})
            all_pr.append(pr)
        if entries:
            panel[(prod, yr)] = entries

    # winsorize
    all_pr.sort()
    p99 = all_pr[int(len(all_pr)*(1-WINSOR_PCT))]
    for entries in panel.values():
        for e in entries:
            e['price_rel'] = min(e['price_rel'], p99)
    return panel

def load_betas(setor):
    path = f'{bdir}/{setor}_brasil_e_argentina_individual_post_tax_j3_v2/8_tabela_betas_grupos.csv'
    betas = {}
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            prod = row['product'].strip()
            try: betas[prod] = float(row['beta_base'])
            except: pass
    return betas

# ── Compute deltas ────────────────────────────────────────────────────────────
def compute_deltas(panel, betas):
    """
    For each consecutive year pair per product, compute:
      delta_obs   = Δlog(share)
      delta_price = β × Δlog(price_rel)
    Returns list of dicts.
    """
    rows = []
    prods = set(p for (p, yr) in panel)

    for prod in prods:
        beta = betas.get(prod)
        if beta is None: continue

        yr_data = {}
        for (p, yr), entries in panel.items():
            if p != prod: continue
            yr_data[yr] = {e['exp']: e for e in entries}

        years = sorted(yr_data)
        for i in range(1, len(years)):
            yr_prev, yr_curr = years[i-1], years[i]
            common = set(yr_data[yr_prev]) & set(yr_data[yr_curr])
            if len(common) < MIN_EXP: continue

            for exp in common:
                prev = yr_data[yr_prev][exp]
                curr = yr_data[yr_curr][exp]
                if prev['share'] <= 0 or curr['share'] <= 0: continue
                if prev['price_rel'] <= 0 or curr['price_rel'] <= 0: continue

                d_obs   = math.log(curr['share']     / prev['share'])
                d_price = math.log(curr['price_rel'] / prev['price_rel'])
                d_pred  = beta * d_price

                if not all(math.isfinite(v) for v in [d_obs, d_price, d_pred]):
                    continue
                rows.append({'prod': prod, 'yr': yr_curr, 'exp': exp,
                             'delta_obs': d_obs, 'delta_pred': d_pred})
    return rows

# ── Demand trend component: Δγ_{p,t} = mean(Δlog share) within prod×yr ───────
def add_demand_trend(rows):
    """Adds 'demand_trend' = mean Δlog(share) across all exporters in (prod, yr)."""
    means = defaultdict(list)
    for r in rows:
        means[(r['prod'], r['yr'])].append(r['delta_obs'])
    for r in rows:
        vals = means[(r['prod'], r['yr'])]
        r['demand_trend'] = sum(vals)/len(vals)
    return rows

# ── R² decomposition ──────────────────────────────────────────────────────────
def decompose(rows):
    y      = [r['delta_obs']    for r in rows]
    x_pr   = [r['delta_pred']   for r in rows]
    x_dem  = [r['demand_trend'] for r in rows]

    r2_price  = r2(x_pr,  y)
    r2_demand = r2(x_dem, y)
    r2_both   = r2_multivariate([x_pr, x_dem], y)
    r2_resid  = 1 - r2_both if math.isfinite(r2_both) else float('nan')

    return {
        'n':         len(y),
        'r2_price':  r2_price,
        'r2_demand': r2_demand,
        'r2_both':   r2_both,
        'r2_resid':  r2_resid,
    }

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
setores_cfg = [
    ('ferro_aco', 'Iron & Steel', '#2c6e9e',
     f'{cfg}/Base_de_dados_final_Ferro.csv'),
    ('aluminio',  'Aluminium',    '#c0392b',
     f'{cfg}/Base_de_dados_final_Aluminio.csv'),
    ('cimento',   'Cement',       '#27ae60',
     f'{cfg}/Base_de_dados_final_Cimento.csv'),
]

results = {}

print(f'\n{"="*65}')
print(f'R² Decomposition — Share VARIATION (first differences)')
print(f'Δlog(share) = β×Δlog(price_rel) + Δγ(p,t) + residual')
print(f'{"="*65}')
print(f'{"Sector":<14} {"N":>6}  {"Price":>8}  {"Demand":>8}  {"Both":>8}  {"Residual":>9}')
print(f'{"-"*65}')

for setor, nome, cor, data_path in setores_cfg:
    panel = load_panel(data_path)
    betas = load_betas(setor)
    rows  = compute_deltas(panel, betas)
    rows  = add_demand_trend(rows)
    dec   = decompose(rows)
    results[setor] = {'nome': nome, 'cor': cor, **dec}

    print(f'{nome:<14} {dec["n"]:>6}  '
          f'{dec["r2_price"]*100:>7.1f}%  '
          f'{dec["r2_demand"]*100:>7.1f}%  '
          f'{dec["r2_both"]*100:>7.1f}%  '
          f'{dec["r2_resid"]*100:>8.1f}%')

print(f'{"="*65}')
print('\nNote: R²_price + R²_demand ≠ R²_both (components not orthogonal)')
print('      FE_{i×p} drops to zero in first differences (time-invariant)')

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5))

setores  = [s for s in results]
nomes    = [results[s]['nome'] for s in setores]
cores    = [results[s]['cor']  for s in setores]
n_sec    = len(setores)
x        = range(n_sec)
width    = 0.20

components = [
    ('r2_price',  'Price  (β × Δ log price_rel)',      0.85),
    ('r2_demand', 'Demand trend  (Δγ_{p,t})',           0.55),
    ('r2_both',   'Price + Demand trend (combined)',     1.00),
    ('r2_resid',  'Residual  (1 − R²_both)',             0.30),
]
comp_colors = ['#2980b9', '#e67e22', '#8e44ad', '#bdc3c7']

offsets = [-1.5*width, -0.5*width, 0.5*width, 1.5*width]

for (key, label, _), col, offset in zip(components, comp_colors, offsets):
    vals = [results[s][key]*100 for s in setores]
    bars = ax.bar([xi + offset for xi in x], vals,
                  width=width, color=col, alpha=0.85,
                  edgecolor='white', linewidth=0.5, label=label, zorder=3)
    for bar, val in zip(bars, vals):
        if math.isfinite(val) and val > 1:
            ax.text(bar.get_x() + bar.get_width()/2,
                    bar.get_height() + 0.5,
                    f'{val:.1f}%', ha='center', va='bottom',
                    fontsize=7.5, fontweight='bold', color='#333')

ax.set_xticks(list(x))
ax.set_xticklabels(nomes, fontsize=11)
ax.set_ylabel('Share of variation in Δ log(share) explained (%)', fontsize=10)
ax.set_ylim(0, 115)
ax.axhline(100, color='#ccc', lw=0.7, ls='--')
ax.legend(fontsize=8.5, loc='upper right', framealpha=0.95)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.tick_params(labelsize=10)
ax.grid(axis='y', alpha=0.15, ls='--')

ax.set_title(
    'R² decomposition: share variation model\n'
    'Δ log(share) = β×Δ log(price_rel)  +  Δγ(product×year)  +  residual\n'
    'FE(exporter×product) drops out in first differences',
    fontsize=11, fontweight='bold', pad=10)

plt.tight_layout()
plt.savefig(out + 'G_r2_decomp_delta.png', dpi=300, bbox_inches='tight')
plt.close()
print('\nSaved: G_r2_decomp_delta.png')

# ── CSV ───────────────────────────────────────────────────────────────────────
import csv as csv_mod
with open(out + 'r2_decomp_delta.csv', 'w', newline='', encoding='utf-8') as f:
    fields = ['setor', 'nome', 'n', 'r2_price', 'r2_demand', 'r2_both', 'r2_resid']
    w = csv_mod.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for s, d in results.items():
        w.writerow({
            'setor': s, 'nome': d['nome'], 'n': d['n'],
            'r2_price':  round(d['r2_price'],  4),
            'r2_demand': round(d['r2_demand'], 4),
            'r2_both':   round(d['r2_both'],   4),
            'r2_resid':  round(d['r2_resid'],  4),
        })
print('Saved: r2_decomp_delta.csv')

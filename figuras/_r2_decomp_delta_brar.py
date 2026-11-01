"""
R² decomposition for share VARIATION — Brazil and Argentina only.

Same framework as _r2_decomp_delta.py but:
  - Uses country-specific betas (beta_sim_BR, beta_sim_AR)
  - Filters observations to BR and AR only
  - Demand trend Δγ_{p,t} still computed from ALL exporters
    (it represents the common product×year shock, not country-specific)

Δlog(share_{i,p,t}) = β_i × Δlog(price_rel_{i,p,t})   [price — country-specific β]
                     + Δγ_{p,t}                          [common demand trend]
                     + Δε                                [residual]

Sectors: ferro_aco, aluminio, cimento
Countries: BR, AR
"""
import csv, math, sys
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib import rcParams

sys.stdout.reconfigure(encoding='utf-8')

root = 'C:/Users/loren/OneDrive/Documentos/TCC CBAM/Projeto R/Versão Claude code/MODELO_OFICIAL'
out  = root + '/figuras_geradas/'
cfg  = root + '/config'
bdir = root + '/outputs'

rcParams['font.family'] = 'sans-serif'

WINSOR_PCT = 0.01
MIN_EXP    = 5
COUNTRIES  = ['BR', 'AR']

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
    n = len(y)
    if n < len(xs_list) + 2: return float('nan')
    X = [[1.0] + [xs[i] for xs in xs_list] for i in range(n)]
    k = len(X[0])
    XtX = [[sum(X[i][a]*X[i][b] for i in range(n)) for b in range(k)] for a in range(k)]
    Xty = [sum(X[i][a]*y[i] for i in range(n)) for a in range(k)]
    aug = [XtX[i][:] + [Xty[i]] for i in range(k)]
    for col in range(k):
        pivot = max(range(col, k), key=lambda r: abs(aug[r][col]))
        aug[col], aug[pivot] = aug[pivot], aug[col]
        if abs(aug[col][col]) < 1e-12: return float('nan')
        for row in range(k):
            if row == col: continue
            f = aug[row][col] / aug[col][col]
            for c in range(col, k+1):
                aug[row][c] -= f * aug[col][c]
    coef = [aug[i][k] / aug[i][i] for i in range(k)]
    fitted = [sum(coef[a]*X[i][a] for a in range(k)) for i in range(n)]
    ss_res = sum((y[i]-fitted[i])**2 for i in range(n))
    ss_tot = sum((y[i]-sum(y)/n)**2 for i in range(n))
    return 1 - ss_res/ss_tot if ss_tot > 0 else float('nan')

# ── Panel loading (all exporters, for demand trend) ───────────────────────────
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

    all_pr.sort()
    p99 = all_pr[int(len(all_pr)*(1-WINSOR_PCT))]
    for entries in panel.values():
        for e in entries:
            e['price_rel'] = min(e['price_rel'], p99)
    return panel

# ── Country-specific betas ─────────────────────────────────────────────────────
def load_betas_country(setor):
    """Returns {prod -> {'BR': beta_sim_BR, 'AR': beta_sim_AR, 'global': beta_base}}"""
    path = f'{bdir}/{setor}_brasil_e_argentina_individual_post_tax_j3_v2/8_tabela_betas_grupos.csv'
    betas = {}
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            prod = row['product'].strip()
            try:
                betas[prod] = {
                    'BR':     float(row['beta_sim_BR']),
                    'AR':     float(row['beta_sim_AR']),
                    'global': float(row['beta_base']),
                }
            except: pass
    return betas

# ── Compute deltas for all exporters (needed for demand trend) ─────────────────
def compute_all_deltas(panel, betas_country):
    """
    Computes Δlog(share) and Δlog(price_rel) for ALL exporters.
    For BR/AR uses country-specific beta; others use global.
    Returns list of dicts with prod, yr, exp, delta_obs, delta_pred.
    """
    rows = []
    prods = set(p for (p, yr) in panel)

    for prod in prods:
        bd = betas_country.get(prod)
        if bd is None: continue

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
                beta    = bd.get(exp, bd['global'])
                d_pred  = beta * d_price

                if not all(math.isfinite(v) for v in [d_obs, d_price, d_pred]):
                    continue
                rows.append({'prod': prod, 'yr': yr_curr, 'exp': exp,
                             'delta_obs': d_obs, 'delta_pred': d_pred})
    return rows

# ── Add demand trend from all exporters ───────────────────────────────────────
def add_demand_trend(rows):
    means = defaultdict(list)
    for r in rows:
        means[(r['prod'], r['yr'])].append(r['delta_obs'])
    for r in rows:
        vals = means[(r['prod'], r['yr'])]
        r['demand_trend'] = sum(vals)/len(vals)
    return rows

# ── Decomposition ─────────────────────────────────────────────────────────────
def decompose(rows):
    y      = [r['delta_obs']    for r in rows]
    x_pr   = [r['delta_pred']   for r in rows]
    x_dem  = [r['demand_trend'] for r in rows]
    r2_price  = r2(x_pr,  y)
    r2_demand = r2(x_dem, y)
    r2_both   = r2_multivariate([x_pr, x_dem], y)
    r2_resid  = 1 - r2_both if math.isfinite(r2_both) else float('nan')
    return {'n': len(y), 'r2_price': r2_price,
            'r2_demand': r2_demand, 'r2_both': r2_both, 'r2_resid': r2_resid}

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

all_results = {}   # {setor -> {country -> decomp}}

print(f'\n{"="*70}')
print(f'R² Decomposition — Share VARIATION — Brazil and Argentina')
print(f'Country-specific β  |  Δγ(p,t) from all exporters')
print(f'{"="*70}')

for setor, nome, cor, data_path in setores_cfg:
    panel  = load_panel(data_path)
    betas  = load_betas_country(setor)
    rows_all = compute_all_deltas(panel, betas)
    rows_all = add_demand_trend(rows_all)

    all_results[setor] = {'nome': nome, 'cor': cor}

    print(f'\n── {nome} ──')
    print(f'{"Country":<10} {"N":>5}  {"Price β_i":>10}  {"Demand":>8}  {"Both":>8}  {"Residual":>9}')
    print(f'  {"(β_sim_i × Δprice)":>28}  {"(Δγ_pt)":>8}')
    print(f'  {"-"*58}')

    for country in COUNTRIES:
        sub = [r for r in rows_all if r['exp'] == country]
        if len(sub) < 5:
            print(f'  {country:<8}  insufficient observations')
            continue
        dec = decompose(sub)
        all_results[setor][country] = dec

        print(f'  {country:<8} {dec["n"]:>5}  '
              f'{dec["r2_price"]*100:>9.1f}%  '
              f'{dec["r2_demand"]*100:>7.1f}%  '
              f'{dec["r2_both"]*100:>7.1f}%  '
              f'{dec["r2_resid"]*100:>8.1f}%')

print(f'\n{"="*70}')

# ── Plot — grouped bars, incremental decomposition ────────────────────────────
# Stacking uses incremental contributions so bars always sum to 100%:
#   Price:              r2_price          (unique + shared, estimated first)
#   Additional demand:  r2_both-r2_price  (what demand adds on top of price)
#   Residual:           1 - r2_both
#
# Sum = r2_price + (r2_both-r2_price) + (1-r2_both) = 1 ✓

COR_BR = '#2c6e9e'
COR_AR = '#e67e22'
COL_PRICE  = '#3498db'
COL_DEMAND = '#95a5a6'
COL_RESID  = '#dfe6e9'

sector_order = [
    ('ferro_aco', 'Iron & Steel'),
    ('aluminio',  'Aluminium'),
    ('cimento',   'Cement'),
]

# Build row list
row_labels, row_data, row_colors = [], [], []
for setor, nome in sector_order:
    sec = all_results.get(setor, {})
    for country in COUNTRIES:
        if country not in sec: continue
        label = f'{"Brazil" if country=="BR" else "Argentina"} — {nome}'
        row_labels.append(label)
        row_data.append(sec[country])
        row_colors.append(COR_BR if country == 'BR' else COR_AR)

n_rows = len(row_labels)
fig, ax = plt.subplots(figsize=(11, 0.75 * n_rows + 2.2))

for i, (label, d, ccountry) in enumerate(zip(row_labels, row_data, row_colors)):
    p   = d['r2_price'] * 100
    b   = d['r2_both']  * 100
    add = max(b - p, 0)    # incremental demand contribution (≥ 0)
    rs  = 100 - b          # residual

    # stacked bars — always sum to 100%
    ax.barh(i, p,   left=0,     height=0.55, color=COL_PRICE,
            alpha=0.90, edgecolor='white', linewidth=0.4)
    ax.barh(i, add, left=p,     height=0.55, color=COL_DEMAND,
            alpha=0.80, edgecolor='white', linewidth=0.4)
    ax.barh(i, rs,  left=p+add, height=0.55, color=COL_RESID,
            alpha=0.90, edgecolor='white', linewidth=0.4)

    # value labels
    if p > 2.5:
        ax.text(p/2, i, f'{p:.1f}%', ha='center', va='center',
                fontsize=7.5, color='white', fontweight='bold')
    if add > 2.5:
        ax.text(p + add/2, i, f'+{add:.1f}%', ha='center', va='center',
                fontsize=7, color='white')
    ax.text(p + add + rs/2, i, f'{rs:.1f}%', ha='center', va='center',
            fontsize=7.5, color='#555')
    ax.text(102, i, f'N={d["n"]}', va='center', fontsize=7.5, color='#888')

# separator lines between sectors
sector_sizes = {s: sum(1 for c in COUNTRIES if c in all_results.get(s,{}))
                for s,_ in sector_order}
cum = 0
for setor, _ in sector_order[:-1]:
    cum += sector_sizes.get(setor, 0)
    ax.axhline(cum - 0.5, color='#ccc', lw=1.0)

ax.set_yticks(range(n_rows))
ax.set_yticklabels(row_labels, fontsize=9.5)
ax.set_xlim(0, 112)
ax.axvline(100, color='#aaa', lw=0.8, ls='--')
ax.set_xlabel('Share of Δ log(share) variation explained (%)', fontsize=10)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.tick_params(labelsize=9)
ax.grid(axis='x', alpha=0.12, ls='--')

handles = [
    plt.Rectangle((0,0),1,1, color=COL_PRICE,  alpha=0.90,
                  label='Price  (β_i × Δ log price_rel)'),
    plt.Rectangle((0,0),1,1, color=COL_DEMAND, alpha=0.80,
                  label='Demand trend  (incremental addition of Δγ_{p,t})'),
    plt.Rectangle((0,0),1,1, color=COL_RESID,  alpha=0.90,
                  label='Residual  (1 − R²_combined)'),
]
ax.legend(handles=handles, fontsize=8.5, loc='lower right',
          framealpha=0.95, ncol=1)

ax.set_title(
    'R² decomposition: share variation model — Brazil and Argentina\n'
    'Δ log(share) = β_i × Δ log(price_rel) + Δγ(p,t) + residual  |  country-specific β\n'
    'Bars sum to 100% (incremental contributions)',
    fontsize=10.5, fontweight='bold', pad=10)

plt.tight_layout()
plt.savefig(out + 'G_r2_decomp_delta_brar.png', dpi=300, bbox_inches='tight')
plt.close()
print('\nSaved: G_r2_decomp_delta_brar.png')

# ── CSV ───────────────────────────────────────────────────────────────────────
import csv as csv_mod
rows_out = []
for setor, d in all_results.items():
    for country in COUNTRIES:
        if country not in d: continue
        rows_out.append({
            'setor': setor, 'nome': d['nome'], 'country': country,
            'n':          d[country]['n'],
            'r2_price':   round(d[country]['r2_price'],  4),
            'r2_demand':  round(d[country]['r2_demand'], 4),
            'r2_both':    round(d[country]['r2_both'],   4),
            'r2_resid':   round(d[country]['r2_resid'],  4),
        })

with open(out + 'r2_decomp_delta_brar.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv_mod.DictWriter(f, fieldnames=rows_out[0].keys())
    w.writeheader(); w.writerows(rows_out)
print('Saved: r2_decomp_delta_brar.csv')

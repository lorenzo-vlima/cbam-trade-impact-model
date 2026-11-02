"""
Two charts:

1. G_impacto_vol_credibilidade.png
   Igual ao anterior mas em mil toneladas.
   Transparent bar = raw impact; solid bar = impact × R²_product.

2. G_oos_por_r2.png
   OOS scatter estratificado por R²_produto.
   Left panel  = products with HIGH R²_p (price dominates)
   Painel direito   = produtos com R²_p BAIXO (outros fatores dominam)
   Mostra que o modelo acerta exatamente onde deveria acertar.
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

CENARIO   = '75/tCO2'
TARIFA    = 'MFN'
PAIS_FOCO = 'BR'
MIN_EXP   = 5

# ── Helpers ───────────────────────────────────────────────────────────────────
def pearson_r(x, y):
    n = len(x)
    if n < 3: return float('nan')
    mx, my = sum(x)/n, sum(y)/n
    num = sum((a-mx)*(b-my) for a,b in zip(x,y))
    dx  = sum((a-mx)**2 for a in x)**0.5
    dy  = sum((b-my)**2 for b in y)**0.5
    return num/(dx*dy) if dx*dy > 0 else float('nan')

def spearman_r(x, y):
    n = len(x)
    if n < 3: return float('nan')
    def ranks(v):
        s = sorted(range(n), key=lambda i: v[i])
        r = [0]*n
        for rank, i in enumerate(s): r[i] = rank+1
        return r
    rx, ry = ranks(x), ranks(y)
    d2 = sum((a-b)**2 for a,b in zip(rx,ry))
    return 1 - 6*d2/(n*(n**2-1))

# ── R²_produto ────────────────────────────────────────────────────────────────
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

# ── Base data ────────────────────────────────────────────────────────────────
def load_base(setor):
    path = f'{base}/{setor}_brasil_e_argentina_individual_post_tax_j3_v2/28_analise_share_vol_base.csv'
    d = {}
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['exporter'].strip() == PAIS_FOCO:
                prod = row['product'].strip()
                try:
                    d[prod] = {
                        'ton':  float(row['ton_pais']),
                        'eur':  float(row['euro_exportado']),
                    }
                except: pass
    return d

def load_cbam(setor):
    path = f'{base}/{setor}_brasil_e_argentina_individual_post_tax_j3_v2/14_cbam_resumo_product.csv'
    imp = {}
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if (row['exporter'].strip() == PAIS_FOCO and
                row['cenario_carbono'].strip() == CENARIO and
                row['cenario_tarifa'].strip() == TARIFA):
                prod = row['product'].strip()
                try: imp[prod] = float(row['delta_share_pct']) / 100.0
                except: pass
    return imp

def load_val_all(setor):
    """Loads all exporters for the OOS scatter."""
    path = f'{base}/{setor}_brasil_e_argentina_individual_post_tax_j3_v2/5c_validacao_delta_dados.csv'
    rows = []
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            prod = row['product'].strip()
            try:
                obs  = float(row['delta_log_dv_obs'])
                pred = float(row['delta_log_dv_pred'])
            except: continue
            if not (math.isfinite(obs) and math.isfinite(pred)): continue
            rows.append({'prod': prod, 'obs': obs, 'pred': pred})
    return rows

setores_cfg = [
    ('ferro_aco', 'Iron & Steel', COR_FA),
    ('aluminio',  'Aluminium',    COR_AL),
]

# ══════════════════════════════════════════════════════════════════════════════
# CHART 1 — Impact by volume (thousand ton)
# ══════════════════════════════════════════════════════════════════════════════
fig1, axes1 = plt.subplots(1, 2, figsize=(15, 7))

for ax, (setor, nome, cor) in zip(axes1, setores_cfg):
    r2_map  = compute_r2_by_product(setor)
    base_map = load_base(setor)
    imp_map  = load_cbam(setor)

    rows = []
    for prod in imp_map:
        if prod not in base_map: continue
        ton   = base_map[prod]['ton'] / 1e3        # mil ton
        pct   = imp_map[prod]
        ib    = pct * ton                           # mil ton, negativo = perda
        r2    = r2_map.get(prod, float('nan'))
        if math.isnan(r2): continue
        rows.append({'prod': prod, 'ton': ton, 'ib': ib,
                     'ia': r2*ib, 'r2': r2})

    rows.sort(key=lambda x: x['ib'])
    y_pos = range(len(rows))

    for i, r in enumerate(rows):
        alpha_base = 0.30 + 0.55 * (r['ton'] / max(x['ton'] for x in rows))**0.5
        ax.barh(i, r['ib'], color=cor, alpha=0.18,
                edgecolor=cor, linewidth=0.5, zorder=2)
        ax.barh(i, r['ia'], color=cor, alpha=min(alpha_base + 0.2, 0.90),
                edgecolor='none', zorder=3)

    x_max = max(abs(r['ib']) for r in rows) if rows else 1
    for i, r in enumerate(rows):
        ax.text(x_max*0.02,  i, f"R²={r['r2']:.2f}",
                va='center', fontsize=6.8, color='#444')
        ax.text(-x_max*0.02, i, f"{r['ton']:.0f}kt",
                va='center', ha='right', fontsize=6.5, color='#777')

    ax.set_yticks(list(y_pos))
    ax.set_yticklabels([r['prod'] for r in rows], fontsize=8)
    ax.axvline(0, color='#aaa', lw=0.8)
    ax.set_xlabel('Change in exported volume (thousand ton)', fontsize=9.5)

    tot_b = sum(r['ib'] for r in rows)
    tot_a = sum(r['ia'] for r in rows)
    ax.text(0.98, 0.98,
            f'Total bruto:    {tot_b:+.1f} kt\n'
            f'Total ajustado: {tot_a:+.1f} kt\n'
            f'Mean R²: {sum(r["r2"] for r in rows)/len(rows):.2f}',
            transform=ax.transAxes, fontsize=8.5, ha='right', va='top',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                      edgecolor='#ccc', alpha=0.92))

    ax.set_title(f'{nome} — Brazil\nCBAM impact {CENARIO} {TARIFA}',
                 fontsize=11, fontweight='bold', color=cor)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='x', alpha=0.15, ls='--')

    p1 = mpatches.Patch(facecolor=cor, alpha=0.18, edgecolor=cor,
                        label='Simulated raw impact')
    p2 = mpatches.Patch(facecolor=cor, alpha=0.75,
                        label='Ajustado × R² (mecanismo confirmado)')
    ax.legend(handles=[p1, p2], fontsize=7.5, loc='lower right', framealpha=0.9)

fig1.suptitle(
    'Brazil — impacto CBAM em volume (mil ton): bruto vs. ajustado por R²_produto\n'
    f'Scenario {CENARIO} {TARIFA}  |  R²_product = fraction of the share change '
    'explained by price (validation 2023–2025)',
    fontsize=10.5, y=1.01)
plt.tight_layout(w_pad=4.0)
plt.savefig(out + 'G_impacto_vol_credibilidade.png', dpi=300, bbox_inches='tight')
plt.close()
print('Saved: G_impacto_vol_credibilidade.png')


# ══════════════════════════════════════════════════════════════════════════════
# CHART 2 — OOS scatter stratified by R²_product
# ══════════════════════════════════════════════════════════════════════════════
fig2, axes2 = plt.subplots(2, 2, figsize=(12, 10))

for row_idx, (setor, nome, cor) in enumerate(setores_cfg):
    r2_map = compute_r2_by_product(setor)
    val    = load_val_all(setor)

    # Enrich with R²
    val_r2 = [v for v in val if v['prod'] in r2_map]
    for v in val_r2:
        v['r2'] = r2_map[v['prod']]

    if not val_r2: continue

    # Mediana de R² como corte
    median_r2 = sorted(v['r2'] for v in val_r2)[len(val_r2)//2]

    high = [v for v in val_r2 if v['r2'] >= median_r2]
    low  = [v for v in val_r2 if v['r2'] <  median_r2]

    for col_idx, (subset, label, r2_desc) in enumerate([
        (high, f'R²_p high  (≥ {median_r2:.2f})', 'price is a relevant driver'),
        (low,  f'R²_p baixo (< {median_r2:.2f})', 'outros fatores dominam'),
    ]):
        ax = axes2[row_idx][col_idx]
        if not subset: continue

        obs  = [v['obs']  for v in subset]
        pred = [v['pred'] for v in subset]
        r2s  = [v['r2']   for v in subset]

        lim = min(max(abs(v) for v in obs+pred) * 1.15, 8)
        ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)

        ax.plot([-lim,lim],[-lim,lim], color='#aaa', lw=1.0, ls='--',
                zorder=1, alpha=0.7)
        ax.axhline(0, color='#ddd', lw=0.6)
        ax.axvline(0, color='#ddd', lw=0.6)
        ax.fill_between([-lim,0], 0,-lim, alpha=0.04, color='green')
        ax.fill_between([0, lim], 0, lim, alpha=0.04, color='green')

        # Scatter with size proportional to R²_p
        sizes = [20 + 80*r2 for r2 in r2s]
        sc = ax.scatter(pred, obs, s=sizes, c=r2s, cmap='Blues',
                        vmin=0, vmax=1, alpha=0.65,
                        edgecolors='#555', linewidths=0.3, zorder=3)

        r   = pearson_r(pred, obs)
        rho = spearman_r(pred, obs)
        hit = sum(1 for o,p in zip(obs,pred) if (o>0)==(p>0))/len(obs)*100

        ax.text(0.04, 0.97,
                f'r = {r:.2f}   ρ = {rho:.2f}\nhit = {hit:.0f}%   N = {len(obs)}',
                transform=ax.transAxes, fontsize=9, color=cor,
                va='top', fontweight='bold')

        ax.set_title(f'{nome}\n{label}\n({r2_desc})',
                     fontsize=9.5, fontweight='bold', color=cor)
        ax.set_xlabel('Δ log(share) previsto', fontsize=9)
        ax.set_ylabel('Δ log(share) observado', fontsize=9)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(labelsize=8)

        plt.colorbar(sc, ax=ax, label='R²_produto', fraction=0.03, pad=0.02)

fig2.suptitle(
    'OOS stratified by R²_product: the model gets it right where price is the driver\n'
    '(validation 2023–2025, model 2010–2025; cut at the median of R²_product)',
    fontsize=11, y=1.01)
plt.tight_layout(h_pad=3.5, w_pad=3.0)
plt.savefig(out + 'G_oos_por_r2.png', dpi=300, bbox_inches='tight')
plt.close()
print('Saved: G_oos_por_r2.png')

"""
Teste de validação em anos com mercado estável.

Lógica:
  Em anos onde as importações totais da UE num produto mal mudaram,
  qualquer redistribuição de share entre fornecedores é quase pura
  substituição — menos ruído de choque de demanda agregada.
  O modelo de preço relativo deveria funcionar melhor nesses anos.

Procedimento:
  1. Carrega dados brutos (2010-2025) e calcula importações totais UE
     por produto×ano.
  2. Calcula variação anual (Δ%) do mercado total por produto.
  3. Cruza com o arquivo de validação OOS do modelo v2 (2023-2025).
  4. Classifica produto×ano por quartil de estabilidade do mercado.
  5. Compara métricas OOS (Pearson r, Spearman rho, hit rate) entre
     anos de mercado estável vs. instável.

Outputs:
  G_stable_market_scatter.png  — scatter por quartil de estabilidade
  G_stable_market_metrics.png  — métricas vs. variação do mercado
  stable_market_results.csv    — tabela de métricas por grupo
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
base = root + '/outputs'

rcParams['font.family'] = 'sans-serif'

COR_FA  = '#2c6e9e'
COR_AL  = '#c0392b'

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

def hit_rate(obs, pred):
    if not obs: return float('nan')
    return sum(1 for o,p in zip(obs,pred) if (o>0)==(p>0)) / len(obs)

# ── Passo 1: importações totais UE por produto×ano ────────────────────────────
def load_total_imports(csv_path):
    """Soma ton de todos os exportadores por produto×ano."""
    totals = defaultdict(float)
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            try:
                prod = str(row['product']).strip()
                yr   = int(float(row['year']))
                ton  = float(row['ton'])
                if ton > 0:
                    totals[(prod, yr)] += ton
            except: pass
    return totals

# ── Passo 2: variação anual do mercado total ──────────────────────────────────
def compute_market_change(totals):
    """
    Para cada (produto, ano), calcula |Δ%| em relação ao ano anterior.
    Retorna dict (prod, yr) -> abs_pct_change
    """
    # organiza por produto
    by_prod = defaultdict(dict)
    for (prod, yr), ton in totals.items():
        by_prod[prod][yr] = ton

    changes = {}
    for prod, yr_dict in by_prod.items():
        years = sorted(yr_dict.keys())
        for i, yr in enumerate(years[1:], 1):
            prev = yr_dict[years[i-1]]
            curr = yr_dict[yr]
            if prev > 0:
                pct = abs((curr - prev) / prev)
                changes[(prod, yr)] = pct
    return changes

# ── Passo 3: validação OOS do modelo v2 ───────────────────────────────────────
def load_val(setor):
    path = f'{base}/{setor}_brasil_e_argentina_individual_post_tax_j3_v2/5c_validacao_delta_dados.csv'
    rows = []
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            prod = row['product'].strip()
            yr   = int(float(row['year']))
            try:
                obs  = float(row['delta_log_dv_obs'])
                pred = float(row['delta_log_dv_pred'])
            except: continue
            if not (math.isfinite(obs) and math.isfinite(pred)): continue
            rows.append({'prod': prod, 'yr': yr, 'obs': obs, 'pred': pred})
    return rows

# ── Passo 4: métricas por grupo de estabilidade ───────────────────────────────
def metrics_by_stability(val_rows, changes, n_bins=4):
    """
    Classifica cada observação pelo quartil de estabilidade do seu produto×ano
    e calcula métricas por quartil.
    """
    # Enriquece com change
    enriched = []
    for r in val_rows:
        chg = changes.get((r['prod'], r['yr']), None)
        if chg is not None:
            enriched.append({**r, 'chg': chg})

    if not enriched:
        return [], []

    # Quartis de variação (0 = mais estável, 3 = mais volátil)
    chg_vals = sorted(set(r['chg'] for r in enriched))
    n = len(chg_vals)
    quartile_cuts = [chg_vals[int(n * q / n_bins)] for q in range(1, n_bins)]

    def get_bin(chg):
        for i, cut in enumerate(quartile_cuts):
            if chg <= cut:
                return i
        return n_bins - 1

    for r in enriched:
        r['bin'] = get_bin(r['chg'])

    # Métricas por bin
    bin_metrics = []
    for b in range(n_bins):
        subset = [r for r in enriched if r['bin'] == b]
        obs  = [r['obs']  for r in subset]
        pred = [r['pred'] for r in subset]
        chgs = [r['chg']  for r in subset]

        if len(obs) < 5:
            continue

        r_val = pearson_r(pred, obs)
        rho   = spearman_r(pred, obs)
        hit   = hit_rate(obs, pred)
        med_chg = sorted(chgs)[len(chgs)//2]

        bin_metrics.append({
            'bin':     b,
            'label':   f'Q{b+1}',
            'n':       len(obs),
            'r':       r_val,
            'rho':     rho,
            'hit':     hit,
            'med_chg': med_chg,
            'obs':     obs,
            'pred':    pred,
        })

    return enriched, bin_metrics

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
setores_cfg = [
    ('ferro_aco', 'Iron & Steel', COR_FA,
     f'{cfg}/Base_de_dados_final_Ferro.csv'),
    ('aluminio',  'Aluminium',    COR_AL,
     f'{cfg}/Base_de_dados_final_Aluminio.csv'),
]

fig = plt.figure(figsize=(15, 11))
gs  = gridspec.GridSpec(2, 4, figure=fig, hspace=0.45, wspace=0.35)

all_results = []

for row_idx, (setor, nome, cor, data_path) in enumerate(setores_cfg):

    totals  = load_total_imports(data_path)
    changes = compute_market_change(totals)
    val     = load_val(setor)
    enriched, bin_metrics = metrics_by_stability(val, changes, n_bins=4)

    if not bin_metrics:
        continue

    print(f"\n{'='*50}")
    print(f"{nome}")
    print(f"{'='*50}")
    print(f"{'Quartil':<8} {'N':>5} {'Med Δ%':>8} {'r':>7} {'rho':>7} {'hit':>7}")
    print('-'*50)
    for m in bin_metrics:
        label = f"Q{m['bin']+1} ({'mais estável' if m['bin']==0 else 'mais volátil' if m['bin']==3 else ''})"
        print(f"  {label:<16} {m['n']:>5} {m['med_chg']*100:>7.1f}%"
              f"  {m['r']:>6.3f}  {m['rho']:>6.3f}  {m['hit']*100:>6.1f}%")
        all_results.append({
            'setor': setor, 'quartil': m['bin']+1,
            'n': m['n'], 'med_chg_pct': round(m['med_chg']*100, 2),
            'r': round(m['r'], 4), 'rho': round(m['rho'], 4),
            'hit': round(m['hit']*100, 2),
        })

    # ── Scatter por quartil ──
    for q_idx, m in enumerate(bin_metrics):
        ax = fig.add_subplot(gs[row_idx, q_idx])

        obs, pred = m['obs'], m['pred']
        lim = min(max(abs(v) for v in obs+pred) * 1.15, 7)
        ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)

        ax.plot([-lim,lim],[-lim,lim], color='#aaa', lw=0.8, ls='--', zorder=1)
        ax.axhline(0, color='#eee', lw=0.5); ax.axvline(0, color='#eee', lw=0.5)
        ax.fill_between([-lim,0],0,-lim, alpha=0.04, color='green')
        ax.fill_between([0,lim],0, lim, alpha=0.04, color='green')

        ax.scatter(pred, obs, s=18, color=cor,
                   alpha=0.55, edgecolors='none', zorder=3)

        # Linha de tendência
        if len(pred) > 3:
            n = len(pred)
            mx, my = sum(pred)/n, sum(obs)/n
            slope = sum((p-mx)*(o-my) for p,o in zip(pred,obs)) / \
                    sum((p-mx)**2 for p in pred) if sum((p-mx)**2 for p in pred)>0 else 0
            intercept = my - slope * mx
            xs = [-lim, lim]
            ys = [slope*x + intercept for x in xs]
            ax.plot(xs, ys, color=cor, lw=1.5, alpha=0.8, zorder=4)

        ax.text(0.05, 0.97,
                f'r={m["r"]:.2f}  ρ={m["rho"]:.2f}\nhit={m["hit"]*100:.0f}%  N={m["n"]}',
                transform=ax.transAxes, fontsize=7.5, color=cor,
                va='top', fontweight='bold')

        stability_label = (
            'mais estável' if m['bin'] == 0 else
            'mais volátil' if m['bin'] == 3 else ''
        )
        ax.set_title(
            f'{nome}  Q{m["bin"]+1}\n'
            f'Δ mercado ≈ {m["med_chg"]*100:.1f}%  {stability_label}',
            fontsize=8.5, color=cor, fontweight='bold')

        if q_idx == 0:
            ax.set_ylabel('Δ log(share) obs.', fontsize=8)
        if row_idx == 1:
            ax.set_xlabel('Δ log(share) pred.', fontsize=8)

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(labelsize=7)

fig.suptitle(
    'Validação OOS estratificada por estabilidade do mercado total da UE\n'
    'Q1 = produto×ano com mercado mais estável (menos choque de demanda)\n'
    'Q4 = produto×ano com maior variação no mercado total',
    fontsize=11, y=1.01)

plt.savefig(out + 'G_stable_market_scatter.png', dpi=300, bbox_inches='tight')
plt.close()
print(f'\nSalvo: G_stable_market_scatter.png')

# ── Gráfico de métricas vs. estabilidade ──────────────────────────────────────
fig2, axes2 = plt.subplots(1, 3, figsize=(13, 4.5))
metrics_labels = [('r', 'Pearson r'), ('rho', 'Spearman ρ'), ('hit', 'Hit rate (%)')]

for ax, (metric, label) in zip(axes2, metrics_labels):
    for setor, nome, cor, _ in setores_cfg:
        subset = [r for r in all_results if r['setor'] == setor]
        if not subset: continue
        xs = [r['med_chg_pct'] for r in subset]
        ys = [r[metric] for r in subset]
        qs = [r['quartil'] for r in subset]

        ax.plot(xs, ys, color=cor, lw=2, marker='o', markersize=8,
                label=nome, zorder=3)
        for x, y, q in zip(xs, ys, qs):
            ax.annotate(f'Q{q}', (x, y), xytext=(4, 4),
                        textcoords='offset points', fontsize=7.5,
                        color=cor, alpha=0.8)

    ax.set_xlabel('Variação mediana do mercado total UE (%)', fontsize=9.5)
    ax.set_ylabel(label, fontsize=9.5)
    ax.set_title(f'{label} vs. volatilidade do mercado', fontsize=10, fontweight='bold')
    ax.legend(fontsize=8, framealpha=0.9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(alpha=0.15, ls='--')
    ax.tick_params(labelsize=8)

fig2.suptitle(
    'Performance do modelo em função da estabilidade do mercado total\n'
    'Hipótese: em mercados estáveis, variação de share = pura substituição por preço',
    fontsize=11, y=1.01)

plt.tight_layout()
plt.savefig(out + 'G_stable_market_metrics.png', dpi=300, bbox_inches='tight')
plt.close()
print('Salvo: G_stable_market_metrics.png')

# ── CSV de resultados ─────────────────────────────────────────────────────────
import csv as csv_mod
with open(out + 'stable_market_results.csv', 'w', newline='',
          encoding='utf-8') as f:
    w = csv_mod.DictWriter(f, fieldnames=all_results[0].keys())
    w.writeheader(); w.writerows(all_results)
print('Salvo: stable_market_results.csv')

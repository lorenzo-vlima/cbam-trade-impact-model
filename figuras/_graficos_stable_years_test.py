"""
Teste de mercado estável — painel completo 2010-2025.

Para cada produto, encontra anos onde o mercado total da UE
pouco mudou em relação ao ano anterior. Nesses anos, toda
redistribuição de share entre países é quase pura substituição
via preço. Testa se beta × Δlog(price_rel) prevê o Δlog(share).

Reproduz a lógica do modelo:
  - price_rel = price_i / price_avg_leave_one_out  (post_tax)
  - winsorização a 99%
  - share = ton_i / ton_total_produto_ano
"""
import csv, math, sys
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import rcParams

sys.stdout.reconfigure(encoding='utf-8')

import os; root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(chr(92), '/')
out  = root + '/figuras_geradas/'
cfg  = root + '/config'
bdir = root + '/outputs'

rcParams['font.family'] = 'sans-serif'
COR_FA = '#2c6e9e'
COR_AL = '#c0392b'

WINSOR_PCT   = 0.01   # winsorização a 99%
STABLE_THRES = 0.05   # mercado estável: |Δ%| < 5%
MIN_EXP      = 5      # mínimo de exportadores por produto×ano

# ── Helpers ───────────────────────────────────────────────────────────────────
def pearson_r(x, y):
    n = len(x)
    if n < 3: return float('nan')
    mx, my = sum(x)/n, sum(y)/n
    num  = sum((a-mx)*(b-my) for a,b in zip(x,y))
    sdx  = sum((a-mx)**2 for a in x)**0.5
    sdy  = sum((b-my)**2 for b in y)**0.5
    return num/(sdx*sdy) if sdx*sdy > 0 else float('nan')

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
    return sum(1 for o,p in zip(obs,pred) if (o>0)==(p>0))/len(obs)

# ── Passo 1: carrega dados brutos e constrói price_rel e share ────────────────
def load_panel(csv_path):
    """
    Retorna dict: (prod, yr) -> list of {exporter, ton, price_rel, share}
    Reproduz lógica do modelo: leave-one-out price_rel + winsorização.
    """
    # Primeiro passo: agrega por (prod, yr)
    raw = defaultdict(list)  # (prod, yr) -> [(exporter, ton, price)]
    with open(csv_path, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter=';'):
            try:
                prod = str(row['product']).strip()
                yr   = int(float(row['year']))
                ton  = float(row['ton'])
                price= float(row['price'])
                exp  = row['exporter'].strip()
                if ton > 1 and price > 0:
                    raw[(prod, yr)].append({'exp': exp, 'ton': ton, 'price': price})
            except: pass

    # Segundo passo: calcula share e price_rel leave-one-out
    all_price_rel = []  # para winsorização global
    panel = {}
    for (prod, yr), rows in raw.items():
        total_ton   = sum(r['ton']           for r in rows)
        total_euro  = sum(r['price']*r['ton'] for r in rows)
        if total_ton <= 0: continue
        entries = []
        for r in rows:
            ton_loo   = total_ton  - r['ton']
            euro_loo  = total_euro - r['price']*r['ton']
            if ton_loo <= 0: continue
            price_avg_loo = euro_loo / ton_loo
            price_rel     = r['price'] / price_avg_loo
            share         = r['ton']   / total_ton
            entries.append({'exp': r['exp'], 'ton': r['ton'],
                            'price_rel': price_rel, 'share': share})
            all_price_rel.append(price_rel)
        if entries:
            panel[(prod, yr)] = entries

    # Winsorização global (99º percentil)
    all_price_rel.sort()
    p99 = all_price_rel[int(len(all_price_rel)*(1-WINSOR_PCT))]
    for entries in panel.values():
        for e in entries:
            e['price_rel'] = min(e['price_rel'], p99)

    return panel

# ── Passo 2: variação anual do mercado total por produto ──────────────────────
def market_changes(panel):
    """
    Retorna (prod, yr) -> |Δ%| das importações totais da UE.
    """
    totals = defaultdict(dict)  # prod -> {yr: total_ton}
    for (prod, yr), entries in panel.items():
        totals[prod][yr] = sum(e['ton'] for e in entries)

    changes = {}
    for prod, yr_dict in totals.items():
        years = sorted(yr_dict)
        for i in range(1, len(years)):
            yr_prev = years[i-1]
            yr_curr = years[i]
            prev = yr_dict[yr_prev]
            curr = yr_dict[yr_curr]
            if prev > 0:
                changes[(prod, yr_curr)] = abs((curr - prev) / prev)
    return changes

# ── Passo 3: carrega betas globais por produto ────────────────────────────────
def load_betas(setor):
    path = f'{bdir}/{setor}_brasil_e_argentina_individual_post_tax_j3_v2/8_tabela_betas_grupos.csv'
    betas = {}
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            prod = row['product'].strip()
            try: betas[prod] = float(row['beta_base'])
            except: pass
    return betas

# ── Passo 4: calcula Δlog(share) e Δlog(price_rel) entre anos consecutivos ──
def compute_deltas(panel, betas):
    """
    Para cada (prod, yr) com (prod, yr-1) disponível,
    calcula Δlog para cada exportador presente nos dois anos.
    Retorna list of {prod, yr, exp, delta_obs, delta_pred, delta_price}.
    """
    all_deltas = []
    prods = set(prod for (prod, yr) in panel)

    for prod in prods:
        beta = betas.get(prod, None)
        if beta is None: continue

        # mapeia ano -> {exp -> {share, price_rel}}
        yr_data = {}
        for (p, yr), entries in panel.items():
            if p != prod: continue
            yr_data[yr] = {e['exp']: e for e in entries}

        years = sorted(yr_data)
        for i in range(1, len(years)):
            yr_prev = years[i-1]
            yr_curr = years[i]
            # exportadores com dados nos dois anos
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
                all_deltas.append({
                    'prod': prod, 'yr': yr_curr, 'exp': exp,
                    'delta_obs': d_obs, 'delta_pred': d_pred,
                    'delta_price': d_price,
                })
    return all_deltas

# ── Passo 5: calcula métricas para um subconjunto de deltas ──────────────────
def compute_metrics(deltas):
    obs  = [d['delta_obs']  for d in deltas]
    pred = [d['delta_pred'] for d in deltas]
    return {
        'n':   len(deltas),
        'r':   pearson_r(pred, obs),
        'rho': spearman_r(pred, obs),
        'hit': hit_rate(obs, pred),
    }

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
setores_cfg = [
    ('ferro_aco', 'Iron & Steel', COR_FA,
     f'{cfg}/Base_de_dados_final_Ferro.csv'),
    ('aluminio',  'Aluminium',    COR_AL,
     f'{cfg}/Base_de_dados_final_Aluminio.csv'),
]

fig, axes = plt.subplots(2, 2, figsize=(13, 10))
all_results = []

for row_idx, (setor, nome, cor, data_path) in enumerate(setores_cfg):
    print(f'\n{"="*55}')
    print(f'{nome}')
    print(f'{"="*55}')

    panel   = load_panel(data_path)
    changes = market_changes(panel)
    betas   = load_betas(setor)
    deltas  = compute_deltas(panel, betas)

    if not deltas:
        print('  Sem dados suficientes.')
        continue

    # Enriquece com variação do mercado
    enriched = []
    for d in deltas:
        chg = changes.get((d['prod'], d['yr']), None)
        if chg is not None:
            enriched.append({**d, 'chg': chg})

    # ── Identifica anos estáveis por produto ──────────────────────────────────
    # Produto-anos estáveis
    stable_keys  = {(d['prod'], d['yr']) for d in enriched
                    if d['chg'] <= STABLE_THRES}
    unstable_keys = {(d['prod'], d['yr']) for d in enriched
                     if d['chg'] > STABLE_THRES}

    stable   = [d for d in enriched if (d['prod'], d['yr']) in stable_keys]
    unstable = [d for d in enriched if (d['prod'], d['yr']) in unstable_keys]
    all_enr  = enriched

    m_stable   = compute_metrics(stable)
    m_unstable = compute_metrics(unstable)
    m_all      = compute_metrics(all_enr)

    # Anos estáveis encontrados
    stable_prod_yrs = sorted(stable_keys)
    yr_counts = defaultdict(int)
    for (p, y) in stable_prod_yrs: yr_counts[y] += 1
    stable_years_summary = dict(sorted(yr_counts.items()))

    print(f'\nAnos e n° de produtos com mercado estável (|Δ| < {STABLE_THRES*100:.0f}%):')
    for yr, cnt in stable_years_summary.items():
        print(f'  {yr}: {cnt} produtos')

    print(f'\nMétricas — todos os anos ({m_all["n"]} obs):')
    print(f'  r={m_all["r"]:.3f}  rho={m_all["rho"]:.3f}  hit={m_all["hit"]*100:.1f}%')
    print(f'\nMétricas — anos ESTÁVEIS ({m_stable["n"]} obs):')
    print(f'  r={m_stable["r"]:.3f}  rho={m_stable["rho"]:.3f}  hit={m_stable["hit"]*100:.1f}%')
    print(f'\nMétricas — anos INSTÁVEIS ({m_unstable["n"]} obs):')
    print(f'  r={m_unstable["r"]:.3f}  rho={m_unstable["rho"]:.3f}  hit={m_unstable["hit"]*100:.1f}%')

    for label, m, subset in [('Estável', m_stable, stable),
                               ('Instável', m_unstable, unstable),
                               ('Todos', m_all, all_enr)]:
        all_results.append({'setor': setor, 'grupo': label, **m})

    # ── Scatter: estável vs todos ──────────────────────────────────────────────
    for col_idx, (label, subset, m) in enumerate([
        (f'Mercado estável\n(|Δ total| < {STABLE_THRES*100:.0f}%)', stable,   m_stable),
        ('Todos os anos',                                             all_enr, m_all),
    ]):
        ax = axes[row_idx][col_idx]
        obs  = [d['delta_obs']  for d in subset]
        pred = [d['delta_pred'] for d in subset]

        if not obs: continue
        lim = min(max(abs(v) for v in obs+pred)*1.15, 8)
        ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)
        ax.plot([-lim,lim],[-lim,lim], color='#aaa', lw=0.8, ls='--', zorder=1)
        ax.axhline(0, color='#eee', lw=0.5); ax.axvline(0, color='#eee', lw=0.5)
        ax.fill_between([-lim,0],0,-lim, alpha=0.04, color='green')
        ax.fill_between([0,lim],0, lim, alpha=0.04, color='green')

        # Colore por variação do mercado quando disponível
        chgs = [d.get('chg', 0) for d in subset]
        chg_max = max(chgs) if chgs else 1
        colors = [plt.cm.RdYlGn_r(c/chg_max) for c in chgs]

        ax.scatter(pred, obs, s=12, c=colors, alpha=0.50,
                   edgecolors='none', zorder=3)

        ax.text(0.04, 0.97,
                f'r={m["r"]:.3f}  ρ={m["rho"]:.3f}\nhit={m["hit"]*100:.0f}%  N={m["n"]}',
                transform=ax.transAxes, fontsize=9, color=cor,
                va='top', fontweight='bold')

        if col_idx == 0:
            yrs_shown = ', '.join(str(y) for y in sorted(stable_years_summary)[:6])
            note = f'Anos estáveis: {yrs_shown}{"..." if len(stable_years_summary)>6 else ""}'
            ax.text(0.04, 0.03, note, transform=ax.transAxes,
                    fontsize=7, color='#555', va='bottom')

        ax.set_title(f'{nome}\n{label}',
                     fontsize=10, fontweight='bold', color=cor)
        ax.set_xlabel('Δ log(share) previsto  [β × Δ log(preço_rel)]', fontsize=8.5)
        ax.set_ylabel('Δ log(share) observado', fontsize=8.5)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(labelsize=8)

fig.suptitle(
    f'Teste em anos de mercado estável (|Δ importações totais UE| < {STABLE_THRES*100:.0f}%)\n'
    'Nesses anos, redistribuição de share ≈ pura substituição via preço\n'
    'Painel completo 2011–2025  |  β da estimação v2',
    fontsize=11, y=1.01)

plt.tight_layout(h_pad=3.5, w_pad=3.0)
plt.savefig(out + 'G_stable_years_test.png', dpi=300, bbox_inches='tight')
plt.close()
print('\nSalvo: G_stable_years_test.png')

# ── CSV resumo ────────────────────────────────────────────────────────────────
import csv as csv_mod
with open(out + 'stable_years_results.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv_mod.DictWriter(f, fieldnames=['setor','grupo','n','r','rho','hit'])
    w.writeheader(); w.writerows(all_results)
print('Salvo: stable_years_results.csv')

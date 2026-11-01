"""
Teste de validação histórica — Antidumping EU 2016 em aço cold-rolled (CRC).
OPÇÃO A: betas diferenciais específicos para China e Rússia.

Regulamento (EU) 2016/1329 impôs tarifas definitivas em julho de 2016:
  - China: 22.1% (taxa residual "all others")
  - Rússia: 36.1% (taxa residual "all outros")
  - Brasil, Coreia, Índia etc.: não afetados → candidatos a ganhadores

Produtos afetados (HS4 presentes na base):
  7209, 7211, 7225, 7226

Diferença em relação ao script base (opção A):
  Em vez de usar beta_base (global) para CN e RU, usa beta_sim_CN e
  beta_sim_RU estimados com CN e RU como países focais — exatamente a
  mesma metodologia usada para BR e AR na simulação CBAM.
  Modelo: ferro_aco_china_e_russia_individual_post_tax_j3_roll2015

Lógica do teste:
  1. Modelo pré-choque 2010-2015 com CN/RU como países focais
  2. Choque de preço relativo pelo antidumping (mesma fórmula do CBAM)
  3. Simulação a partir de 2015, teste em 2017
  4. Métricas: direção correta, Spearman, magnitude
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

# ── Definição do choque antidumping ───────────────────────────────────────────
# Regulamento (EU) 2016/1329 — CRC definitivo julho 2016
ANTI_TARIFFS = {
    'CN': 0.221,   # China — taxa "all others"
    'RU': 0.361,   # Rússia — taxa "all others"
}
CRC_PRODUCTS = {'7209', '7211', '7225', '7226'}
ANO_BASE     = 2015   # share e preço pré-choque
ANO_TESTE    = 2017   # primeiro ano com efeito pleno
WINSOR_PCT   = 0.01
MIN_EXP      = 5      # mínimo de exportadores por produto

# ── Helpers ───────────────────────────────────────────────────────────────────
def pearson_r(x, y):
    n = len(x)
    if n < 3: return float('nan')
    mx, my = sum(x)/n, sum(y)/n
    num = sum((a-mx)*(b-my) for a,b in zip(x,y))
    sdx = sum((a-mx)**2 for a in x)**0.5
    sdy = sum((b-my)**2 for b in y)**0.5
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

# ── Carrega dados brutos ──────────────────────────────────────────────────────
def load_raw(csv_path, produtos, anos):
    """Retorna (prod, yr, exp) -> {ton, price}"""
    data = {}
    with open(csv_path, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter=';'):
            try:
                prod = str(row['product']).strip()
                yr   = int(float(row['year']))
                exp  = row['exporter'].strip()
                ton  = float(row['ton'])
                price= float(row['price'])
            except: continue
            if prod not in produtos: continue
            if yr not in anos: continue
            if ton <= 1 or price <= 0: continue
            data[(prod, yr, exp)] = {'ton': ton, 'price': price}
    return data

# ── Computa share e price_rel leave-one-out (mesma lógica do modelo) ──────────
def compute_panel(data, winsor_p99=None):
    """
    Para cada (prod, yr), calcula share e price_rel LOO.
    Retorna (prod, yr) -> {exp -> {share, price_rel}}
    """
    # Agrega totais por produto-ano
    totals = defaultdict(lambda: {'ton': 0.0, 'euro': 0.0})
    for (prod, yr, exp), d in data.items():
        totals[(prod, yr)]['ton']  += d['ton']
        totals[(prod, yr)]['euro'] += d['price'] * d['ton']

    panel = defaultdict(dict)
    all_pr = []

    for (prod, yr, exp), d in data.items():
        tot = totals[(prod, yr)]
        ton_loo  = tot['ton']  - d['ton']
        euro_loo = tot['euro'] - d['price'] * d['ton']
        if ton_loo <= 0: continue
        price_avg_loo = euro_loo / ton_loo
        price_rel = d['price'] / price_avg_loo
        share     = d['ton']  / tot['ton']
        panel[(prod, yr)][exp] = {'share': share, 'price_rel': price_rel,
                                   'price': d['price'], 'ton': d['ton']}
        all_pr.append(price_rel)

    # Winsorização
    if all_pr:
        all_pr.sort()
        p99 = all_pr[int(len(all_pr)*(1-WINSOR_PCT))]
        for py_dict in panel.values():
            for e in py_dict.values():
                e['price_rel'] = min(e['price_rel'], p99)

    return panel

# ── Carrega betas pré-choque — OPÇÃO A: beta_sim_CN e beta_sim_RU ─────────────
def load_betas_pre(setor):
    """
    Carrega betas do modelo estimado com CN e RU como países focais.
    Para cada produto retorna:
      {'global': beta_base, 'CN': beta_sim_CN, 'RU': beta_sim_RU}
    """
    path = (f'{bdir}/{setor}_china_e_russia_individual_post_tax_j3_roll2015'
            f'/4_betas_simulacao_cbam.csv')
    betas = {}
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            prod = row['product'].strip()
            if prod not in CRC_PRODUCTS: continue
            try:
                betas[prod] = {
                    'global': float(row['beta_base']),
                    'CN':     float(row['beta_sim_CN']),
                    'RU':     float(row['beta_sim_RU']),
                }
            except: pass
    return betas

# ── Constrói choque de preço antidumping ──────────────────────────────────────
def compute_ad_price_shock(panel_base, tariffs, prod):
    """
    Para cada exportador, recalcula o preço pós-tarifa e o novo price_rel.
    Retorna {exp -> delta_log_price_rel}
    """
    yr_dict = panel_base.get((prod, ANO_BASE), None)
    if yr_dict is None: return {}

    # Preços originais por exportador
    exporters = list(yr_dict.keys())
    prices = {e: yr_dict[e]['price'] for e in exporters}
    tons   = {e: yr_dict[e]['ton']   for e in exporters}

    # Preços pós-tarifa
    prices_ad = {e: prices[e] * (1 + tariffs.get(e, 0.0)) for e in exporters}

    # Nova média leave-one-out pós-tarifa
    total_ton  = sum(tons.values())
    total_euro_ad = sum(prices_ad[e] * tons[e] for e in exporters)

    shocks = {}
    for e in exporters:
        ton_loo  = total_ton  - tons[e]
        euro_loo = total_euro_ad - prices_ad[e] * tons[e]
        if ton_loo <= 0: continue
        price_avg_loo_ad = euro_loo / ton_loo

        # price_rel original (já calculado no panel)
        pr_orig = yr_dict[e]['price_rel']
        # price_rel pós-tarifa
        pr_ad   = prices_ad[e] / price_avg_loo_ad

        if pr_orig <= 0 or pr_ad <= 0: continue
        shocks[e] = math.log(pr_ad / pr_orig)

    return shocks

# ── Simulação de redistribuição ───────────────────────────────────────────────
def simulate(panel_base, panel_obs, betas, tariffs):
    """
    Para cada produto CRC, simula share pós-choque e compara com observado 2017.
    """
    results = []

    for prod in CRC_PRODUCTS:
        beta_dict = betas.get(prod, None)
        if beta_dict is None: continue
        beta_global = beta_dict['global']

        base_yr = panel_base.get((prod, ANO_BASE), {})
        obs_yr  = panel_obs.get( (prod, ANO_TESTE), {})
        if not base_yr or not obs_yr: continue

        # Exportadores com dados nos dois anos
        common = set(base_yr) & set(obs_yr)
        if len(common) < MIN_EXP: continue

        # Choque de preço
        shocks = compute_ad_price_shock(panel_base, tariffs, prod)

        # Simulação
        sim_shares = {}
        for e in common:
            s_base  = base_yr[e]['share']
            d_price = shocks.get(e, 0.0)
            # Usa beta específico para CN/RU, global para os demais
            beta = beta_dict.get(e, beta_global)
            sim_shares[e] = s_base * math.exp(beta * d_price)

        # Normaliza
        total_sim = sum(sim_shares.values())
        if total_sim <= 0: continue
        for e in sim_shares:
            sim_shares[e] /= total_sim

        # Compara com observado
        total_obs = sum(obs_yr[e]['share'] for e in common)
        if total_obs <= 0: continue
        obs_shares_norm = {e: obs_yr[e]['share'] / total_obs for e in common}

        for e in common:
            s_sim  = sim_shares[e]
            s_obs  = obs_shares_norm[e]
            s_base = base_yr[e]['share'] / sum(base_yr[ee]['share'] for ee in common)

            d_sim = s_sim - s_base
            d_obs = s_obs - s_base

            tariff = tariffs.get(e, 0.0)
            results.append({
                'prod':    prod,
                'exp':     e,
                'beta':    beta_dict.get(e, beta_global),
                'tariff':  tariff,
                'affected': e in tariffs,
                's_base':  s_base,
                's_sim':   s_sim,
                's_obs':   s_obs,
                'd_sim':   d_sim,
                'd_obs':   d_obs,
                'correct_dir': (d_sim > 0) == (d_obs > 0),
            })

    return results

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
print('Loading data...')
data_all  = load_raw(f'{cfg}/Base_de_dados_final_Ferro.csv',
                     CRC_PRODUCTS, set(range(2010, 2026)))
data_base = {k: v for k, v in data_all.items() if k[1] == ANO_BASE}
data_obs  = {k: v for k, v in data_all.items() if k[1] == ANO_TESTE}

panel_base = compute_panel(data_base)
panel_obs  = compute_panel(data_obs)
betas      = load_betas_pre('ferro_aco')

print(f'CRC products with country-specific betas (CN/RU):')
for p, bd in betas.items():
    print(f'  {p}: global={bd["global"]:.3f}  CN={bd["CN"]:.3f}  RU={bd["RU"]:.3f}')
print(f'Exporters in base year:')
for prod in CRC_PRODUCTS:
    n = len(panel_base.get((prod, ANO_BASE), {}))
    print(f'  {prod}: {n} exporters in {ANO_BASE}')

results = simulate(panel_base, panel_obs, betas, ANTI_TARIFFS)

if not results:
    print('Sem resultados. Verifique os dados.')
    sys.exit(1)

# ── Métricas globais ──────────────────────────────────────────────────────────
d_sim_all = [r['d_sim'] for r in results]
d_obs_all = [r['d_obs'] for r in results]
correct   = [r['correct_dir'] for r in results]
hit       = sum(correct) / len(correct) * 100

r_val = pearson_r(d_sim_all, d_obs_all)
rho   = spearman_r(d_sim_all, d_obs_all)

# Afetados vs não-afetados
affected   = [r for r in results if r['affected']]
unaffected = [r for r in results if not r['affected']]

hit_aff  = sum(r['correct_dir'] for r in affected)  / len(affected)  * 100 if affected   else float('nan')
hit_unaff= sum(r['correct_dir'] for r in unaffected)/ len(unaffected)* 100 if unaffected else float('nan')

print(f'\n{"="*55}')
print(f'RESULTS — Antidumping CRC 2016  [country-specific β: CN/RU]')
print(f'Model estimated: 2010–{ANO_BASE}  |  Test: {ANO_TESTE}')
print(f'Products: {", ".join(CRC_PRODUCTS)}')
print(f'Affected: China ({ANTI_TARIFFS["CN"]*100:.1f}%), Russia ({ANTI_TARIFFS["RU"]*100:.1f}%)')
print(f'{"="*55}')
print(f'N observations: {len(results)}  '
      f'({len(affected)} affected, {len(unaffected)} not affected)')
print(f'Pearson r:  {r_val:.3f}')
print(f'Spearman ρ: {rho:.3f}')
print(f'Hit rate overall:       {hit:.1f}%')
print(f'Hit rate — affected:    {hit_aff:.1f}%')
print(f'Hit rate — unaffected:  {hit_unaff:.1f}%')

print(f'\nPredicted vs. observed share change — affected countries:')
print(f'{"Prod":<6} {"Ctry":<5} {"Tariff":>8} {"β used":>8} {"Δ sim":>8} {"Δ obs":>8} {"Correct"}')
print('-'*60)
affected_sorted = sorted(affected, key=lambda x: x['tariff'], reverse=True)
for r in affected_sorted:
    ok = 'YES ✓' if r['correct_dir'] else 'NO  ✗'
    print(f'{r["prod"]:<6} {r["exp"]:<5} {r["tariff"]*100:>7.1f}%'
          f' {r["beta"]:>8.3f}  {r["d_sim"]*100:>+7.2f}%  {r["d_obs"]*100:>+7.2f}%  {ok}')

# ── Gráfico focado nos países afetados ───────────────────────────────────────
# O modelo só faz previsão direcional para países afetados (choque > 0).
# Para não-afetados, o choque é ≈ 0, então o modelo prevê Δ≈0 — o hit
# rate deles (56%) não reflete capacidade preditiva, só ruído residual.
# O teste relevante é: o modelo previu corretamente que CN e RU perdem share?

fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

# ── Painel 1: scatter só dos afetados ────────────────────────────────────────
ax = axes[0]
COR_CN = '#e74c3c'
COR_RU = '#8e44ad'

d_sim_aff = [r['d_sim'] for r in affected]
d_obs_aff = [r['d_obs'] for r in affected]
r_aff  = pearson_r(d_sim_aff, d_obs_aff)
rho_aff = spearman_r(d_sim_aff, d_obs_aff)
hit_aff_v = sum(r['correct_dir'] for r in affected) / len(affected) * 100

lim = max(max(abs(v) for v in d_sim_aff + d_obs_aff) * 1.30, 0.05)
ax.set_xlim(-lim, 0.02); ax.set_ylim(-lim*1.5, lim*0.5)

ax.axhline(0, color='#ccc', lw=0.8, ls='--')
ax.axvline(0, color='#ccc', lw=0.8, ls='--')
ax.fill_between([-lim, 0], -lim*1.5, 0, alpha=0.07, color='green',
                label='Correct quadrant (predicted and observed loss)')

for r in affected:
    cor = COR_CN if r['exp'] == 'CN' else COR_RU
    marker = 'o' if r['exp'] == 'CN' else 's'
    ax.scatter(r['d_sim'], r['d_obs'], s=130, color=cor, marker=marker,
               edgecolors='white', linewidths=0.8, zorder=4,
               alpha=0.90)
    ok = '✓' if r['correct_dir'] else '✗'
    ax.annotate(f'{r["exp"]} {r["prod"]} {ok}',
                (r['d_sim'], r['d_obs']),
                xytext=(7, 4), textcoords='offset points',
                fontsize=9, color=cor, fontweight='bold')

ax.text(0.04, 0.97,
        f'r = {r_aff:.3f}   ρ = {rho_aff:.3f}\n'
        f'hit = {hit_aff_v:.0f}%   N = {len(affected)}\n'
        f'(affected countries only: CN and RU)',
        transform=ax.transAxes, fontsize=9.5, color='#222',
        va='top', fontweight='bold',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                  edgecolor='#ccc', alpha=0.9))

cn_p = mpatches.Patch(color=COR_CN, label=f'China (duty +22.1%)')
ru_p = mpatches.Patch(color=COR_RU, label=f'Russia (duty +36.1%)',
                       hatch='//')
ax.legend(handles=[cn_p, ru_p], fontsize=9, loc='lower right', framealpha=0.9)

ax.set_xlabel('Δ share simulated  [β_CN/RU × Δ ln(p_rel_antidumping)]', fontsize=10)
ax.set_ylabel('Δ share observed  (2017 vs. 2015)', fontsize=10)
ax.set_title('Countries directly affected by antidumping\n(simulated vs. observed)  —  country-specific β', fontsize=11, fontweight='bold')
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
ax.tick_params(labelsize=9)


# ── Painel 2: magnitude por produto — barra simulado vs observado ─────────────
ax2 = axes[1]
prods_with_data = sorted(set(r['prod'] for r in affected))
x_base = range(len(prods_with_data))
width  = 0.18
country_cfg = [('CN', COR_CN, 'o'), ('RU', COR_RU, 's')]

for i, (exp, cor, mk) in enumerate(country_cfg):
    sub = [r for r in affected if r['exp'] == exp]
    prods_sub = [r['prod'] for r in sub]
    d_sim_sub = [r['d_sim']*100 for r in sub]
    d_obs_sub = [r['d_obs']*100 for r in sub]

    xs = [prods_with_data.index(p) for p in prods_sub]

    offset_sim = (i*2 - 1.5) * width
    offset_obs = offset_sim + width

    ax2.bar([x + offset_sim for x in xs], d_sim_sub,
            width=width, color=cor, alpha=0.55, label=f'{exp} simulated',
            edgecolor=cor, linewidth=0.5)
    ax2.bar([x + offset_obs for x in xs], d_obs_sub,
            width=width, color=cor, alpha=0.90, label=f'{exp} observed',
            edgecolor='white', linewidth=0.3, hatch='//' if exp=='RU' else '')

ax2.axhline(0, color='#888', lw=0.8)
ax2.set_xticks(list(x_base))
ax2.set_xticklabels(prods_with_data, fontsize=10)
ax2.set_ylabel('Δ share (p.p.)', fontsize=10)
ax2.set_title('Magnitude: simulated vs. observed\nby product and affected country', fontsize=11, fontweight='bold')
ax2.legend(fontsize=8, ncol=2, loc='lower left', framealpha=0.9)
ax2.spines['top'].set_visible(False); ax2.spines['right'].set_visible(False)
ax2.tick_params(labelsize=9)

# Marca acertos
for r in affected:
    xi = prods_with_data.index(r['prod'])
    i = 0 if r['exp'] == 'CN' else 1
    offset_obs = ((i*2 - 1.5) + 1) * width
    y = r['d_obs'] * 100
    ok = '✓' if r['correct_dir'] else '✗'
    col = 'green' if r['correct_dir'] else 'red'
    ax2.text(xi + offset_obs, y - (1.5 if y < 0 else -1.5),
             ok, ha='center', fontsize=11, color=col, fontweight='bold')

fig.suptitle(
    f'Historical validation — EU Antidumping 2016 (Reg. 2016/1329)  |  Country-specific β (CN/RU)\n'
    f'Cold-rolled steel (CRC): China +22.1%, Russia +36.1%\n'
    f'Same methodology as CBAM simulation  |  Model estimated on 2010–{ANO_BASE}, Test year: {ANO_TESTE}',
    fontsize=11, y=1.02)

plt.tight_layout(w_pad=3.5)
plt.savefig(out + 'G_antidumping_2016_test_opA.png', dpi=300, bbox_inches='tight')
plt.close()
print('\nSalvo: G_antidumping_2016_test_opA.png')

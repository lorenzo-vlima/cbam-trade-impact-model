"""
Computa betas e volumes por grupo a partir dos CSVs de output do modelo.
Fonte:
  - 8_tabela_betas_grupos.csv  → beta_sim_BR, beta_sim_AR, beta_base por produto + grupo
  - 28_analise_share_vol_base.csv → ton_pais por (exporter, product)  [base = últimos 3 anos]
"""
import csv, sys
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

import os
base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'outputs')

SETORES = {
    'aluminio':  'aluminio_brasil_e_argentina_individual_post_tax_j3_v2',
    'ferro_aco': 'ferro_aco_brasil_e_argentina_individual_post_tax_j3_v2',
    'cimento':   'cimento_brasil_e_argentina_individual_post_tax_j3_v2',
}

def read_csv(path):
    with open(path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

def safe_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def weighted_avg(values_weights):
    """values_weights: list of (value, weight); ignores None values."""
    total_w = sum(w for v, w in values_weights if v is not None)
    if total_w == 0:
        return None
    return sum(v * w for v, w in values_weights if v is not None) / total_w

# ─── Calcula para cada setor ──────────────────────────────────────────────────
for setor, folder in SETORES.items():
    print(f'\n{"="*60}')
    print(f'SETOR: {setor.upper()}')
    print(f'{"="*60}')

    betas_path = f'{base}/{folder}/8_tabela_betas_grupos.csv'
    vol_path   = f'{base}/{folder}/28_analise_share_vol_base.csv'

    betas_rows = read_csv(betas_path)
    vol_rows   = read_csv(vol_path)

    # Volumes por (exporter, product)
    vol = {}
    for r in vol_rows:
        vol[(r['exporter'], r['product'])] = safe_float(r['ton_pais']) or 0.0

    # Volumes total de mercado por product (para pesos quando país não tem exportação)
    mkt_vol = {}
    for r in vol_rows:
        mkt_vol[r['product']] = safe_float(r['ton_total_mercado']) or 0.0

    # Produtos por grupo
    grupos = defaultdict(list)  # grupo_num → list of row dicts
    for r in betas_rows:
        grupos[int(r['grupo'])].append(r)

    # Totais de volume por país (para % de grupo)
    total_BR = sum(v for (exp, _), v in vol.items() if exp == 'BR')
    total_AR = sum(v for (exp, _), v in vol.items() if exp == 'AR')

    print(f'  Total tons BR: {total_BR:,.0f}  |  Total tons AR: {total_AR:,.0f}')
    print()

    results = {}
    for g_num in sorted(grupos.keys()):
        rows = grupos[g_num]
        g_label = rows[0]['grupo_label']

        # Volumes por produto neste grupo
        vols_BR = {r['product']: vol.get(('BR', r['product']), 0.0) for r in rows}
        vols_AR = {r['product']: vol.get(('AR', r['product']), 0.0) for r in rows}
        vols_mkt = {r['product']: mkt_vol.get(r['product'], 0.0) for r in rows}

        tot_BR  = sum(vols_BR.values())
        tot_AR  = sum(vols_AR.values())
        tot_mkt = sum(vols_mkt.values())

        # Volume % do total exportado pelo país
        pct_BR = (tot_BR / total_BR * 100) if total_BR > 0 else 0.0
        pct_AR = (tot_AR / total_AR * 100) if total_AR > 0 else 0.0

        # Beta BR — ponderado por volume BR (ou mkt se sem exportação)
        if tot_BR > 0:
            b_BR = weighted_avg([(safe_float(r['beta_sim_BR']), vols_BR[r['product']]) for r in rows])
            b_BR_label = 'vol-weighted BR'
        else:
            b_BR = weighted_avg([(safe_float(r['beta_sim_BR']), vols_mkt[r['product']]) for r in rows])
            b_BR_label = 'mkt-weighted (sem exp BR)'

        # Beta AR — ponderado por volume AR (ou mkt se sem exportação)
        if tot_AR > 0:
            b_AR = weighted_avg([(safe_float(r['beta_sim_AR']), vols_AR[r['product']]) for r in rows])
            b_AR_label = 'vol-weighted AR'
        else:
            b_AR = weighted_avg([(safe_float(r['beta_sim_AR']), vols_mkt[r['product']]) for r in rows])
            b_AR_label = 'mkt-weighted (sem exp AR)'

        # Beta global — ponderado por volume de mercado
        b_glb = weighted_avg([(safe_float(r['beta_base']), vols_mkt[r['product']]) for r in rows])

        results[g_num] = {
            'label':  g_label,
            'b_BR':   b_BR,
            'b_AR':   b_AR,
            'b_glb':  b_glb,
            'pct_BR': pct_BR,
            'pct_AR': pct_AR,
            'n_prod': len(rows),
        }

        print(f'  Grupo {g_num}: {g_label}  (n={len(rows)} produtos)')
        print(f'    vol BR: {pct_BR:5.1f}%  vol AR: {pct_AR:5.1f}%')
        print(f'    β_BR:  {b_BR:7.3f}  [{b_BR_label}]')
        print(f'    β_AR:  {b_AR:7.3f}  [{b_AR_label}]')
        print(f'    β_glb: {b_glb:7.3f}  [mkt-weighted]')
        print()

print('\n\n=== CÓDIGO PYTHON (para _graficos_secao1.py) ===\n')

# Re-executa e imprime o código formatado
for setor, folder in SETORES.items():
    betas_rows = read_csv(f'{base}/{folder}/8_tabela_betas_grupos.csv')
    vol_rows   = read_csv(f'{base}/{folder}/28_analise_share_vol_base.csv')

    vol = {}
    for r in vol_rows:
        vol[(r['exporter'], r['product'])] = safe_float(r['ton_pais']) or 0.0
    mkt_vol = {}
    for r in vol_rows:
        mkt_vol[r['product']] = safe_float(r['ton_total_mercado']) or 0.0

    grupos = defaultdict(list)
    for r in betas_rows:
        grupos[int(r['grupo'])].append(r)

    total_BR = sum(v for (exp, _), v in vol.items() if exp == 'BR')
    total_AR = sum(v for (exp, _), v in vol.items() if exp == 'AR')

    print(f'grupos_{setor[:2].upper() if setor=="ferro_aco" else setor[:2].upper()} = [')
    for g_num in sorted(grupos.keys()):
        rows = grupos[g_num]
        g_label = rows[0]['grupo_label']
        vols_BR  = {r['product']: vol.get(('BR', r['product']), 0.0) for r in rows}
        vols_AR  = {r['product']: vol.get(('AR', r['product']), 0.0) for r in rows}
        vols_mkt = {r['product']: mkt_vol.get(r['product'], 0.0) for r in rows}
        tot_BR  = sum(vols_BR.values())
        tot_AR  = sum(vols_AR.values())
        tot_mkt = sum(vols_mkt.values())
        pct_BR  = (tot_BR / total_BR * 100) if total_BR > 0 else 0.0
        pct_AR  = (tot_AR / total_AR * 100) if total_AR > 0 else 0.0
        b_BR = weighted_avg([(safe_float(r['beta_sim_BR']), vols_BR[r['product']]) for r in rows]) if tot_BR > 0 else \
               weighted_avg([(safe_float(r['beta_sim_BR']), vols_mkt[r['product']]) for r in rows])
        b_AR = weighted_avg([(safe_float(r['beta_sim_AR']), vols_AR[r['product']]) for r in rows]) if tot_AR > 0 else \
               weighted_avg([(safe_float(r['beta_sim_AR']), vols_mkt[r['product']]) for r in rows])
        b_glb = weighted_avg([(safe_float(r['beta_base']), vols_mkt[r['product']]) for r in rows])
        print(f"    ('{g_label}', {b_BR:.3f}, {b_AR:.3f}, {b_glb:.3f}, {pct_BR:.1f}, {pct_AR:.1f}),")
    print(']\n')

"""
Correção de betas positivos por shrinkage censurado.

Para produtos onde beta_sim > 0 (diferencial positivo contra a teoria),
aplica censura do beta bruto em zero ANTES do shrinkage:

    beta_corrigido = (1 - w) * beta_global

Em vez de:
    beta_sim = w * beta_BR + (1-w) * beta_global   [com beta_BR > 0]

Resultado: valor negativo, menos elástico que o global (mais próximo de zero),
consistente com a hipótese de que o diferencial país-específico é no máximo zero.
"""

import csv, sys, math
sys.stdout.reconfigure(encoding='utf-8')

root = 'C:/Users/loren/OneDrive/Documentos/TCC CBAM/Projeto R/Versão Claude code/MODELO_OFICIAL'

setores = [
    'ferro_aco_brasil_e_argentina_individual_post_tax_j3',
    'aluminio_brasil_e_argentina_individual_post_tax_j3',
    'cimento_brasil_e_argentina_individual_post_tax_j3',
]

for pasta in setores:
    path_in  = root + f'/modelos/01_ppml_share/outputs/{pasta}/4_betas_simulacao_cbam.csv'
    path_out = root + f'/modelos/01_ppml_share/outputs/{pasta}/4_betas_simulacao_corrigido.csv'

    rows_in = []
    with open(path_in, encoding='latin-1') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows_in.append(dict(row))

    correcoes = []
    rows_out = []
    for row in rows_in:
        row = dict(row)
        prod       = row['product'].strip()
        beta_base  = float(row['beta_base'])

        for pais in ['BR', 'AR']:
            col_sim  = f'beta_sim_{pais}'
            col_w    = f'w_{pais}'
            col_raw  = f'beta_{pais}'
            col_fonte = f'fonte_{pais}'
            if col_sim not in row or not row[col_sim].strip():
                continue

            b_sim = float(row[col_sim])
            w     = float(row[col_w]) if row[col_w].strip() else 0.0
            b_raw = float(row[col_raw]) if row.get(col_raw,'').strip() else b_sim

            if b_sim > 0:
                b_corr = (1 - w) * beta_base
                row[col_sim]  = str(b_corr)
                row[col_fonte] = f'censurado (beta_raw={b_raw:.3f}>0; corr={(1-w):.3f}*global)'
                correcoes.append((pasta.split('_')[0] + '_' + pasta.split('_')[1] if '_' in pasta else pasta[:10], prod, pais, b_sim, b_corr, w, beta_base))

        rows_out.append(row)

    with open(path_out, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    print(f'Salvo: {path_out.split("/outputs/")[1]}')

print()
if correcoes:
    print('Correções aplicadas:')
    print(f'  {"Setor":<10} {"Produto":<10} {"País":<5} {"beta_sim_orig":>14} {"beta_corrigido":>14} {"w":>6} {"global":>8}')
    print('  ' + '-' * 65)
    for s, p, pa, bo, bc, w, bg in correcoes:
        print(f'  {s:<10} {p:<10} {pa:<5} {bo:>14.4f} {bc:>14.4f} {w:>6.3f} {bg:>8.4f}')
else:
    print('Nenhuma correção necessária.')

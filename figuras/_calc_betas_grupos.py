import csv, sys, math
sys.stdout.reconfigure(encoding='utf-8')

import os; root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(chr(92), '/')
grupos = {
    '260112':'Primarios', '7201':'Primarios', '7202':'Primarios',
    '7203':'Primarios', '7205':'Primarios',
    '7206':'Semiacabados e planos', '7207':'Semiacabados e planos',
    '7208':'Semiacabados e planos', '7209':'Semiacabados e planos',
    '7210':'Semiacabados e planos', '7211':'Semiacabados e planos',
    '7212':'Semiacabados e planos', '7218':'Semiacabados e planos',
    '7219':'Semiacabados e planos', '7220':'Semiacabados e planos',
    '7221':'Semiacabados e planos', '7225':'Semiacabados e planos',
    '7226':'Semiacabados e planos',
    '7213':'Longos e tubulares', '7214':'Longos e tubulares',
    '7215':'Longos e tubulares', '7216':'Longos e tubulares',
    '7217':'Longos e tubulares', '7222':'Longos e tubulares',
    '7223':'Longos e tubulares', '7224':'Longos e tubulares',
    '7227':'Longos e tubulares', '7228':'Longos e tubulares',
    '7229':'Longos e tubulares', '7301':'Longos e tubulares',
    '7302':'Longos e tubulares', '730300':'Longos e tubulares',
    '7304':'Longos e tubulares', '7305':'Longos e tubulares',
    '7306':'Longos e tubulares', '7307':'Longos e tubulares',
    '7308':'Longos e tubulares', '730900':'Longos e tubulares',
    '7310':'Longos e tubulares', '731100':'Longos e tubulares',
    '7318':'Longos e tubulares', '7326':'Longos e tubulares',
    '7601':'Primario e semi-acabado', '7603':'Primario e semi-acabado',
    '7604':'Primario e semi-acabado',
    '7605':'Laminados e tubulares', '7606':'Laminados e tubulares',
    '7607':'Laminados e tubulares', '7608':'Laminados e tubulares',
    '760900':'Laminados e tubulares',
    '7610':'Manufaturados e acabados', '761100':'Manufaturados e acabados',
    '7612':'Manufaturados e acabados', '761300':'Manufaturados e acabados',
    '7614':'Manufaturados e acabados', '7616':'Manufaturados e acabados',
    '252310':'Clinquer',
    '252321':'Cimento Portland', '252329':'Cimento Portland',
    '252330':'Cimentos especiais', '252390':'Cimentos especiais',
    '250700':'Argila',
}

setores = [
    ('ferro_aco', 'Ferro e Aco',  'Base_de_dados_final_Ferro.csv',    ';'),
    ('aluminio',  'Aluminio',     'Base_de_dados_final_Aluminio.csv', ';'),
    ('cimento',   'Cimento',      'Base_de_dados_final_Cimento.csv',  ';'),
]

ANOS_BASE = {2023, 2024, 2025}

def wmean(lst):
    if not lst:
        return float('nan')
    sw = sum(w for _, w in lst)
    if sw == 0:
        return float('nan')
    return sum(v * w for v, w in lst) / sw

for setor, nome, arq_base, sep_base in setores:
    pasta = setor + '_brasil_e_argentina_individual_post_tax_j3_v2'
    beta_path = root + '/outputs/' + pasta + '/4_betas_simulacao_cbam.csv'
    base_path = root + '/config/' + arq_base

    betas = {}
    with open(beta_path, encoding='latin-1') as f:
        reader = csv.DictReader(f)
        for row in reader:
            prod = row['product'].strip()
            try:
                betas[prod] = {
                    'beta_global':  float(row['beta_base']),
                    'beta_BR': float(row['beta_sim_BR']) if row.get('beta_sim_BR','').strip() else None,
                    'beta_AR': float(row['beta_sim_AR']) if row.get('beta_sim_AR','').strip() else None,
                    'w_BR': float(row['w_BR']) if row.get('w_BR','').strip() else None,
                    'w_AR': float(row['w_AR']) if row.get('w_AR','').strip() else None,
                    'fonte_BR': row.get('fonte_BR','').strip(),
                    'fonte_AR': row.get('fonte_AR','').strip(),
                }
            except:
                pass

    vol_br = {}
    eur_br = {}
    with open(base_path, encoding='latin-1') as f:
        reader = csv.DictReader(f, delimiter=sep_base)
        for row in reader:
            try:
                year = int(row['year'])
                exp  = row['exporter'].strip()
                prod = row['product'].strip()
                ton  = float(row['ton'].replace(',', '.')) if row['ton'].strip() else 0
                eur  = float(row['euro'].replace(',', '.')) if row['euro'].strip() else 0
            except:
                continue
            if year in ANOS_BASE and exp == 'BR':
                vol_br[prod] = vol_br.get(prod, 0) + ton
                eur_br[prod] = eur_br.get(prod, 0) + eur

    grupo_data = {}
    for prod, b in betas.items():
        g = grupos.get(prod, 'Outros')
        if g not in grupo_data:
            grupo_data[g] = {'bg': [], 'bBR': [], 'bAR': [], 'wBR': [], 'wAR': [], 'ton': 0, 'eur': 0}
        gd = grupo_data[g]
        w = vol_br.get(prod, 0)
        ww = w if w > 0 else 1
        gd['bg'].append((b['beta_global'], ww))
        if b['beta_BR'] is not None and math.isfinite(b['beta_BR']):
            gd['bBR'].append((b['beta_BR'], ww))
        if b['beta_AR'] is not None and math.isfinite(b['beta_AR']):
            gd['bAR'].append((b['beta_AR'], ww))
        if b['w_BR'] is not None and math.isfinite(b['w_BR']):
            gd['wBR'].append((b['w_BR'], ww))
        if b['w_AR'] is not None and math.isfinite(b['w_AR']):
            gd['wAR'].append((b['w_AR'], ww))
        gd['ton'] += vol_br.get(prod, 0)
        gd['eur'] += eur_br.get(prod, 0)

    total_ton = sum(v['ton'] for v in grupo_data.values())
    total_eur = sum(v['eur'] for v in grupo_data.values())

    print('\n' + '=' * 68)
    print('  ' + nome)
    print('=' * 68)
    print('  {:28s} {:>9} {:>9} {:>9} {:>7} {:>7}'.format(
        'Grupo', 'b_global', 'b_sim_BR', 'b_sim_AR', 'ton_BR%', 'eur_BR%'))
    print('  ' + '-' * 72)

    for g, gd in sorted(grupo_data.items()):
        bg  = wmean(gd['bg'])
        bBR = wmean(gd['bBR'])
        bAR = wmean(gd['bAR'])
        wBR = wmean(gd['wBR']) if gd['wBR'] else float('nan')
        tp  = gd['ton'] / total_ton * 100 if total_ton > 0 else 0
        ep  = gd['eur'] / total_eur * 100 if total_eur > 0 else 0

        def fmt(v):
            return '{:>9.3f}'.format(v) if math.isfinite(v) else '      n/d'

        print('  {:28s} {} {} {}  {:>6.1f}% {:>6.1f}%  [w_BR={:.2f}]'.format(
            g, fmt(bg), fmt(bBR), fmt(bAR), tp, ep,
            wBR if math.isfinite(wBR) else 0))

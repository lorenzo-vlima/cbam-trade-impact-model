"""
Out-of-sample validation scatter — train 2010-2018, test 2019.
"""
import csv, math, sys
import matplotlib.pyplot as plt
from matplotlib import rcParams

sys.stdout.reconfigure(encoding='utf-8')

import os; root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(chr(92), '/')
out  = root + '/figuras_geradas/'

rcParams['font.family'] = 'sans-serif'

COR_FA = '#2c6e9e'
COR_AL = '#c0392b'
COR_AR = '#e67e22'

setores = [
    ('ferro_aco', 'Iron & Steel', COR_FA),
    ('aluminio',  'Aluminium',    COR_AL),
]

v = '_brasil_e_argentina_individual_post_tax_j3_2019test'

fig, axes = plt.subplots(1, 2, figsize=(11, 5.5), sharey=False)

for ax, (setor, nome, cor) in zip(axes, setores):
    path = f'{root}/modelos/01_ppml_share/outputs/{setor}{v}/5c_validacao_delta_dados.csv'

    obs_BR, pred_BR, sign_BR, prod_BR = [], [], [], []
    obs_AR, pred_AR, sign_AR, prod_AR = [], [], [], []

    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            exp = row['exporter'].strip()
            if exp not in ('BR', 'AR'):
                continue
            try:
                o  = float(row['delta_log_dv_obs'])
                p  = float(row['delta_log_dv_pred'])
                s  = row['sign_correct'].strip().upper() == 'TRUE'
                pr = row['product'].strip()
            except Exception:
                continue
            if not (math.isfinite(o) and math.isfinite(p)):
                continue
            if exp == 'BR':
                obs_BR.append(o); pred_BR.append(p)
                sign_BR.append(s); prod_BR.append(pr)
            else:
                obs_AR.append(o); pred_AR.append(p)
                sign_AR.append(s); prod_AR.append(pr)

    all_vals = obs_BR + pred_BR + obs_AR + pred_AR
    if not all_vals:
        continue
    lim = min(max(abs(v) for v in all_vals) * 1.15, 8)

    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)

    ax.plot([-lim, lim], [-lim, lim], color='#aaaaaa',
            linewidth=1.0, linestyle='--', zorder=1, label='45°')
    ax.axhline(0, color='#dddddd', linewidth=0.6)
    ax.axvline(0, color='#dddddd', linewidth=0.6)

    ax.fill_between([-lim, 0],  0, -lim, alpha=0.05, color='green')
    ax.fill_between([0,  lim],  0,  lim, alpha=0.05, color='green')

    def split(obs, pred, sign, prods):
        oc  = [o for o,s in zip(obs,sign) if s]
        pc  = [p for p,s in zip(pred,sign) if s]
        prc = [pr for pr,s in zip(prods,sign) if s]
        oe  = [o for o,s in zip(obs,sign) if not s]
        pe  = [p for p,s in zip(pred,sign) if not s]
        pre = [pr for pr,s in zip(prods,sign) if not s]
        return oc, pc, prc, oe, pe, pre

    # ── Brazil ──
    oc, pc, prc, oe, pe, pre = split(obs_BR, pred_BR, sign_BR, prod_BR)
    ax.scatter(pc, oc, s=60, color=cor, alpha=0.85, zorder=3,
               edgecolors='white', linewidths=0.5,
               label=f'BR correct ({len(oc)}/{len(obs_BR)})')
    ax.scatter(pe, oe, s=60, color=cor, alpha=0.30, zorder=3,
               marker='x', linewidths=1.3,
               label=f'BR incorrect ({len(oe)}/{len(obs_BR)})')
    for xi, yi, pr in zip(pc + pe, oc + oe, prc + pre):
        ax.annotate(pr, (xi, yi), textcoords='offset points', xytext=(4, 3),
                    fontsize=7, color=cor, alpha=0.80, clip_on=True)

    # ── Argentina ──
    if obs_AR:
        oc2, pc2, prc2, oe2, pe2, pre2 = split(obs_AR, pred_AR, sign_AR, prod_AR)
        ax.scatter(pc2, oc2, s=60, color=COR_AR, alpha=0.85, zorder=3,
                   edgecolors='white', linewidths=0.5,
                   label=f'AR correct ({len(oc2)}/{len(obs_AR)})')
        ax.scatter(pe2, oe2, s=60, color=COR_AR, alpha=0.30, zorder=3,
                   marker='x', linewidths=1.3,
                   label=f'AR incorrect ({len(oe2)}/{len(obs_AR)})')
        for xi, yi, pr in zip(pc2 + pe2, oc2 + oe2, prc2 + pre2):
            ax.annotate(pr, (xi, yi), textcoords='offset points', xytext=(4, 3),
                        fontsize=7, color=COR_AR, alpha=0.80, clip_on=True)

    # ── Stats ──
    def corr(obs, pred):
        n = len(obs)
        if n < 3: return float('nan')
        mo, mp = sum(obs)/n, sum(pred)/n
        cov  = sum((o-mo)*(p-mp) for o,p in zip(obs,pred))/n
        sd_o = (sum((o-mo)**2 for o in obs)/n)**0.5
        sd_p = (sum((p-mp)**2 for p in pred)/n)**0.5
        return cov/(sd_o*sd_p) if sd_o*sd_p > 0 else float('nan')

    r_br   = corr(obs_BR, pred_BR)
    hit_br = sum(sign_BR)/len(sign_BR)*100 if sign_BR else 0
    ax.text(0.04, 0.97, f'BR: r={r_br:.2f}  hit={hit_br:.0f}%  N={len(obs_BR)}',
            transform=ax.transAxes, fontsize=9, color=cor,
            va='top', fontweight='bold')

    if obs_AR:
        r_ar   = corr(obs_AR, pred_AR)
        hit_ar = sum(sign_AR)/len(sign_AR)*100
        ax.text(0.04, 0.88, f'AR: r={r_ar:.2f}  hit={hit_ar:.0f}%  N={len(obs_AR)}',
                transform=ax.transAxes, fontsize=9, color=COR_AR,
                va='top', fontweight='bold')

    ax.set_xlabel('Δ log(share) predicted', fontsize=11)
    ax.set_ylabel('Δ log(share) realized', fontsize=11)
    ax.set_title(nome, fontsize=13, fontweight='bold', color=cor)
    ax.legend(fontsize=8, loc='lower right', framealpha=0.9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(labelsize=9)

fig.suptitle(
    'Out-of-sample validation: predicted vs. realized market share change\n'
    '(Brazil and Argentina; trained 2010–2018, tested on 2019)',
    fontsize=11, y=1.03)

plt.tight_layout(w_pad=3.0)
plt.savefig(out + 'G2_validacao_oos_2019test.png', dpi=300, bbox_inches='tight')
plt.close()
print('Saved: G2_validacao_oos_2019test.png')

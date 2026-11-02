"""
Iron & Steel summary — v2: adds market-share change to the volume vs value lines.
v1 (G_sim_FA_resumo.png) is kept intact.
"""
import csv, sys
import matplotlib.pyplot as plt
from matplotlib import rcParams

sys.stdout.reconfigure(encoding='utf-8')
import os; root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(chr(92), '/')
# Run folder = <sector>_<RUN>_<TAG>. RUN is NOME in rodar_modelo.R; override with the
# environment variables CBAM_RUN / CBAM_TAG if your runs are named differently.
RUN = os.environ.get('CBAM_RUN', 'brazil_and_argentina')
TAG = os.environ.get('CBAM_TAG', 'individual_post_tax_j3_v2')
out  = root + '/figuras_geradas/'
os.makedirs(out, exist_ok=True)
base = root + '/outputs'
rcParams['font.family'] = 'sans-serif'

path = f'{base}/ferro_aco_{RUN}_{TAG}/13_cbam_resumo_pais.csv'
rows = list(csv.DictReader(open(path, encoding='utf-8')))

carb = [75, 95, 115]
def serie(exp, tarifa, col):
    d = {int(float(r['preco_carbono_eur'])): float(r[col]) for r in rows
         if r['exporter']==exp and r['cenario_tarifa']==tarifa}
    return [d[c] for c in carb]

COR_SHARE = '#7f8c8d'
COR_TON   = '#2c6e9e'
COR_EUR   = '#c0392b'

fig, axes = plt.subplots(1, 2, figsize=(13.0, 4.6), sharey=True)

for ax, exp, nome in zip(axes, ['BR','AR'], ['Brazil','Argentina']):
    metrics = [
        ('variacao_relativa_pct', COR_SHARE, 'Market share', 'D'),
        ('delta_ton_pct',         COR_TON,   'Volume (ton)', 'o'),
        ('delta_euro_pct',        COR_EUR,   'Value (€)',    's'),
    ]
    # Brazil: stacked columns (volume above, share/value below) — works well.
    place_map = {
        'delta_ton_pct':         'top',
        'variacao_relativa_pct': 'bottom',
        'delta_euro_pct':        'below2',
    }
    for col, cor, lbl, mk in metrics:
        mfn = serie(exp, 'MFN', col)
        mer = serie(exp, 'Mercosul', col)
        ax.plot(carb, mfn, color=cor, lw=2.2, marker=mk, ms=7,
                label=f'{lbl} — MFN')
        ax.plot(carb, mer, color=cor, lw=1.6, marker=mk, ms=5,
                ls='--', alpha=0.65, label=f'{lbl} — Mercosur')

        if exp == 'BR':
            place = place_map[col]
            for idx, (xv, ym, ye) in enumerate(zip(carb, mfn, mer)):
                # higher value on top row, lower on bottom row
                top = (ym, 1.0) if ym >= ye else (ye, 0.65)
                bot = (ye, 0.65) if ym >= ye else (ym, 1.0)
                anchor = max(ym, ye)
                if idx == 0:
                    # volume & share handled together in a left column below;
                    # only value (red) is drawn laterally here
                    if col != 'delta_euro_pct':
                        continue
                    for (val, al), dy in zip([top, bot], [6, -6]):
                        ax.annotate(f'{val:.1f}', (xv, anchor), xytext=(-7, dy),
                                    textcoords='offset points', fontsize=8.5,
                                    color=cor, ha='right', va='center', alpha=al,
                                    fontweight='bold' if al == 1.0 else 'normal')
                elif idx == 2:      # right lateral
                    for (val, al), dy in zip([top, bot], [6, -6]):
                        ax.annotate(f'{val:.1f}', (xv, anchor), xytext=(7, dy),
                                    textcoords='offset points', fontsize=8.5,
                                    color=cor, ha='left', va='center', alpha=al,
                                    fontweight='bold' if al == 1.0 else 'normal')
                else:               # middle: compact vertical column
                    pairs = sorted([(ym, 1.0), (ye, 0.65)], key=lambda t: t[0],
                                   reverse=True)
                    if place == 'top':
                        anchor = max(ym, ye); offs = (18, 8); va = 'bottom'
                    else:
                        anchor = min(ym, ye); offs = (-8, -18); va = 'top'
                    for (val, al), dyo in zip(pairs, offs):
                        ax.annotate(f'{val:.1f}', (xv, anchor), xytext=(0, dyo),
                                    textcoords='offset points', fontsize=8.5,
                                    color=cor, ha='center', va=va, alpha=al,
                                    fontweight='bold' if al == 1.0 else 'normal')

    # Brazil scenario 0 (75): volume & share as a single left-stacked column
    # order top->bottom: volume MFN, volume Mercosur, share MFN, share Mercosur
    if exp == 'BR':
        Sb = {c: {'MFN': serie('BR','MFN',c), 'Mer': serie('BR','Mercosul',c)}
              for c, _, _, _ in metrics}
        i = 0
        col_order = [
            ('delta_ton_pct',         'MFN', COR_TON,   1.0),
            ('delta_ton_pct',         'Mer', COR_TON,   0.65),
            ('variacao_relativa_pct', 'MFN', COR_SHARE, 1.0),
            ('variacao_relativa_pct', 'Mer', COR_SHARE, 0.65),
        ]
        y0 = max(Sb[c][r][i] for c, r, _, _ in col_order) + 0.3
        for k, (c, r, cc, al) in enumerate(col_order):
            ax.annotate(f'{Sb[c][r][i]:.1f}', (carb[i], y0),
                        xytext=(-9, 8 - k*11), textcoords='offset points',
                        fontsize=8.5, color=cc, ha='right', va='center',
                        fontweight='bold' if al == 1.0 else 'normal', alpha=al)

    # Argentina: custom per-scenario placement, after lines are drawn
    if exp == 'AR':
        S = {col: {'MFN': serie('AR','MFN',col), 'Mer': serie('AR','Mercosul',col)}
             for col, _, _, _ in metrics}
        cor_share, cor_ton, cor_eur = COR_SHARE, COR_TON, COR_EUR

        # ----- scenario 0 (75): stacked one below the other, LEFT of points ---
        # top->bottom: value Mer, volume Mer, volume MFN, value MFN
        i = 0
        col_order = [
            ('delta_euro_pct', 'Mer', cor_eur, 0.6),
            ('delta_ton_pct',  'Mer', cor_ton, 0.6),
            ('delta_ton_pct',  'MFN', cor_ton, 1.0),
            ('delta_euro_pct', 'MFN', cor_eur, 1.0),
        ]
        yvals = [S[c][r][i] for c, r, _, _ in col_order]
        y0 = max(yvals) + 0.4
        for k, (c, r, cc, al) in enumerate(col_order):
            ax.annotate(f'{S[c][r][i]:.1f}', (carb[i], y0),
                        xytext=(-24, 6 - k*11), textcoords='offset points',
                        fontsize=8.5, color=cc, ha='right', va='center',
                        fontweight='bold' if al == 1.0 else 'normal', alpha=al)
        # market share at 75 -> just left of its own points
        for r, al in [('Mer',0.6),('MFN',1.0)]:
            yv = S['variacao_relativa_pct'][r][i]
            ax.annotate(f'{yv:.1f}', (carb[i], yv), xytext=(-8, 0),
                        textcoords='offset points', fontsize=8.5,
                        color=cor_share, ha='right', va='center',
                        fontweight='bold' if al==1.0 else 'normal', alpha=al)

        # ----- scenario 1 (95): reds above, blues below; share split ---------
        i = 1
        for r, al, dy in [('Mer',0.6,24),('MFN',1.0,17)]:
            yv = S['delta_euro_pct'][r][i]
            ax.annotate(f'{yv:.1f}', (carb[i], yv), xytext=(0, dy),
                        textcoords='offset points', fontsize=8.5,
                        color=cor_eur, ha='center', va='bottom',
                        fontweight='bold' if al==1.0 else 'normal', alpha=al)
        # volume (blue): both below; order inverted -> Mercosur first, then MFN
        blue_anchor = min(S['delta_ton_pct']['MFN'][i],
                          S['delta_ton_pct']['Mer'][i])
        for r, al, dy in [('Mer',0.6,-9),('MFN',1.0,-18)]:
            yv = S['delta_ton_pct'][r][i]
            ax.annotate(f'{yv:.1f}', (carb[i], blue_anchor), xytext=(0, dy),
                        textcoords='offset points', fontsize=8.5,
                        color=cor_ton, ha='center', va='top',
                        fontweight='bold' if al==1.0 else 'normal', alpha=al)
        ax.annotate(f"{S['variacao_relativa_pct']['Mer'][i]:.1f}",
                    (carb[i], S['variacao_relativa_pct']['Mer'][i]),
                    xytext=(0, 11), textcoords='offset points', fontsize=8.5,
                    color=cor_share, ha='center', va='bottom', alpha=0.6)
        ax.annotate(f"{S['variacao_relativa_pct']['MFN'][i]:.1f}",
                    (carb[i], S['variacao_relativa_pct']['MFN'][i]),
                    xytext=(0, -11), textcoords='offset points', fontsize=8.5,
                    color=cor_share, ha='center', va='top', fontweight='bold')

        # ----- scenario 2 (115): right of points, each pair stacked by value -
        i = 2
        for c, cc in [('variacao_relativa_pct',cor_share),
                      ('delta_ton_pct',cor_ton),
                      ('delta_euro_pct',cor_eur)]:
            vmfn = S[c]['MFN'][i]; vmer = S[c]['Mer'][i]
            # higher value on top row, lower on bottom row
            top = ('MFN',1.0,vmfn) if vmfn >= vmer else ('Mer',0.6,vmer)
            bot = ('Mer',0.6,vmer) if vmfn >= vmer else ('MFN',1.0,vmfn)
            anchor = max(vmfn, vmer)
            for (r, al, val), dy in zip([top, bot], [7, -7]):
                ax.annotate(f'{val:.1f}', (carb[i], anchor), xytext=(7, dy),
                            textcoords='offset points', fontsize=8.5,
                            color=cc, ha='left', va='center',
                            fontweight='bold' if al==1.0 else 'normal', alpha=al)

    ax.axhline(0, color='#ccc', lw=0.8)
    ax.set_title(nome, fontsize=14, fontweight='bold',
                 color=COR_TON if exp=='BR' else '#e67e22')
    ax.set_xlabel('Carbon price (€/tCO₂)', fontsize=12)
    ax.set_xticks(carb)
    ax.set_xlim(carb[0]-12, carb[-1]+12)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', alpha=0.15, ls='--')
    ax.tick_params(labelsize=11.5)
    ax.set_ylim(bottom=-10.5, top=1.2)

axes[0].set_ylabel('Change in EU exports (%)', fontsize=12)
axes[0].legend(fontsize=9.5, loc='lower left', framealpha=0.95, ncol=1)

fig.suptitle(
    'Iron & Steel — CBAM impact on Brazilian and Argentine EU exports',
    fontsize=14, fontweight='bold', y=1.0)

plt.tight_layout()
plt.savefig(out + 'G_sim_FA_resumo_v3.png', dpi=300, bbox_inches='tight')
plt.close()
print('Saved: G_sim_FA_resumo_v3.png')

"""
Iron & Steel summary — v2: adds market-share change to the volume vs value lines.
v1 (G_sim_FA_resumo.png) is kept intact.
"""
import csv, sys
import matplotlib.pyplot as plt
from matplotlib import rcParams

sys.stdout.reconfigure(encoding='utf-8')
root = 'C:/Users/loren/OneDrive/Documentos/TCC CBAM/Projeto R/Versão Claude code/MODELO_OFICIAL'
out  = root + '/figuras_geradas/'
base = root + '/outputs'
rcParams['font.family'] = 'sans-serif'

path = f'{base}/ferro_aco_brasil_e_argentina_individual_post_tax_j3_v2/13_cbam_resumo_pais.csv'
rows = list(csv.DictReader(open(path, encoding='utf-8')))

carb = [75, 95, 115]
def serie(exp, tarifa, col):
    d = {int(float(r['preco_carbono_eur'])): float(r[col]) for r in rows
         if r['exporter']==exp and r['cenario_tarifa']==tarifa}
    return [d[c] for c in carb]

COR_SHARE = '#7f8c8d'
COR_TON   = '#2c6e9e'
COR_EUR   = '#c0392b'

fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.8), sharey=True)

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
            for xv, ym, ye in zip(carb, mfn, mer):
                pairs = sorted([(ym, 1.0), (ye, 0.65)], key=lambda t: t[0],
                               reverse=True)
                if place == 'top':
                    anchor = max(ym, ye); offs = (24, 12); va = 'bottom'
                else:
                    anchor = min(ym, ye); offs = (-12, -24); va = 'top'
                for (val, al), dyo in zip(pairs, offs):
                    ax.annotate(f'{val:.1f}', (xv, anchor), xytext=(0, dyo),
                                textcoords='offset points', fontsize=7.2,
                                color=cor, ha='center', va=va, alpha=al,
                                fontweight='bold' if al == 1.0 else 'normal')
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
                        fontsize=7.0, color=cc, ha='right', va='center',
                        fontweight='bold' if al == 1.0 else 'normal', alpha=al)
        # market share at 75 -> just left of its own points
        for r, al in [('Mer',0.6),('MFN',1.0)]:
            yv = S['variacao_relativa_pct'][r][i]
            ax.annotate(f'{yv:.1f}', (carb[i], yv), xytext=(-8, 0),
                        textcoords='offset points', fontsize=7.0,
                        color=cor_share, ha='right', va='center',
                        fontweight='bold' if al==1.0 else 'normal', alpha=al)

        # ----- scenario 1 (95): reds above, blues below; share split ---------
        i = 1
        for r, al, dy in [('Mer',0.6,22),('MFN',1.0,11)]:
            yv = S['delta_euro_pct'][r][i]
            ax.annotate(f'{yv:.1f}', (carb[i], yv), xytext=(0, dy),
                        textcoords='offset points', fontsize=7.0,
                        color=cor_eur, ha='center', va='bottom',
                        fontweight='bold' if al==1.0 else 'normal', alpha=al)
        # volume (blue): both below, stacked clearly (values nearly identical)
        blue_anchor = min(S['delta_ton_pct']['MFN'][i],
                          S['delta_ton_pct']['Mer'][i])
        for r, al, dy in [('MFN',1.0,-13),('Mer',0.6,-26)]:
            yv = S['delta_ton_pct'][r][i]
            ax.annotate(f'{yv:.1f}', (carb[i], blue_anchor), xytext=(0, dy),
                        textcoords='offset points', fontsize=7.0,
                        color=cor_ton, ha='center', va='top',
                        fontweight='bold' if al==1.0 else 'normal', alpha=al)
        ax.annotate(f"{S['variacao_relativa_pct']['Mer'][i]:.1f}",
                    (carb[i], S['variacao_relativa_pct']['Mer'][i]),
                    xytext=(0, 11), textcoords='offset points', fontsize=7.0,
                    color=cor_share, ha='center', va='bottom', alpha=0.6)
        ax.annotate(f"{S['variacao_relativa_pct']['MFN'][i]:.1f}",
                    (carb[i], S['variacao_relativa_pct']['MFN'][i]),
                    xytext=(0, -11), textcoords='offset points', fontsize=7.0,
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
                            textcoords='offset points', fontsize=7.0,
                            color=cc, ha='left', va='center',
                            fontweight='bold' if al==1.0 else 'normal', alpha=al)

    ax.axhline(0, color='#ccc', lw=0.8)
    ax.set_title(nome, fontsize=13, fontweight='bold',
                 color=COR_TON if exp=='BR' else '#e67e22')
    ax.set_xlabel('Carbon price (€/tCO₂)', fontsize=10.5)
    ax.set_xticks(carb)
    ax.set_xlim(carb[0]-12, carb[-1]+12)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', alpha=0.15, ls='--')
    ax.tick_params(labelsize=9.5)

axes[0].set_ylabel('Change in EU exports (%)', fontsize=10.5)
axes[0].legend(fontsize=7.8, loc='lower left', framealpha=0.95, ncol=1)

fig.suptitle(
    'Iron & Steel — CBAM impact on Brazilian and Argentine EU exports',
    fontsize=12.5, fontweight='bold', y=1.01)

plt.tight_layout()
plt.savefig(out + 'G_sim_FA_resumo_v2.png', dpi=300, bbox_inches='tight')
plt.close()
print('Saved: G_sim_FA_resumo_v2.png')

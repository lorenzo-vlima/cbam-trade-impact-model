import csv, math, sys
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

import os; root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(chr(92), '/')
# ── Paleta ────────────────────────────────────────────────────────────────────
COR_FA  = '#2c6e9e'   # azul ferro
COR_AL  = '#c0392b'   # vermelho aluminio
COR_CI  = '#27ae60'   # verde cimento
COR_GLB = '#888888'   # cinza global

# ══════════════════════════════════════════════════════════════════════════════
# CHART 1 — Dot plot: β by product group
# ══════════════════════════════════════════════════════════════════════════════

# Data (excluding FA primaries as an artefact; using the global β for that group)
# setor, grupo_label, beta_BR, beta_global, ton_pct, cor
pontos = [
    # Iron & Steel
    ('Iron & Steel', 'Primaries\n(ore/pig iron)',   -0.184, -0.184, 80.6, COR_FA, True),
    ('Iron & Steel', 'Semiacabados\ne planos',       -4.447, -2.763, 16.5, COR_FA, False),
    ('Iron & Steel', 'Longos e\ntubulares',          -1.420, -1.248,  2.9, COR_FA, False),
    # Aluminium
    ('Aluminium',    'Primary and\nsemi-finished',     -5.259, -0.472, 88.8, COR_AL, False),
    ('Aluminium',    'Laminados e\ntubulares',       -5.314, -1.174, 10.3, COR_AL, False),
    ('Aluminium',    'Manufaturados\ne acabados',    -2.115, -1.112,  0.9, COR_AL, False),
]

fig, ax = plt.subplots(figsize=(10, 6))

y_labels = []
y_pos    = []

for i, (setor, grupo, bBR, bGlb, ton_pct, cor, usar_global) in enumerate(pontos):
    y = len(pontos) - i  # inverso para mais importante ficar em cima
    y_pos.append(y)
    y_labels.append(grupo)

    # Line connecting global to BR
    beta_plot = bGlb if usar_global else bBR
    ax.plot([bGlb, beta_plot], [y, y], color=cor, alpha=0.4, linewidth=1.5, zorder=1)

    # Ponto global (quadrado)
    ax.scatter(bGlb, y, s=120, color=cor, marker='s', alpha=0.5,
               zorder=3, linewidths=0.5, edgecolors='white')

    # BR point (circle), size proportional to volume
    size_br = 80 + ton_pct * 18
    ax.scatter(beta_plot, y, s=size_br, color=cor, marker='o',
               zorder=4, linewidths=0.8, edgecolors='white',
               label=setor if i in [0, 3] else '')

    # Volume annotation
    ax.annotate(f'{ton_pct:.0f}%', xy=(beta_plot, y),
                xytext=(6, 0), textcoords='offset points',
                fontsize=8, color=cor, va='center', alpha=0.85)

    # "Global β" note for FA primaries
    if usar_global:
        ax.annotate('(β global)', xy=(bGlb, y),
                    xytext=(-5, 8), textcoords='offset points',
                    fontsize=7, color='#555555', style='italic')

# Vertical line at zero
ax.axvline(0, color='#aaaaaa', linewidth=0.8, linestyle='--', zorder=0)

# Separator between sectors
ax.axhline(3.5, color='#dddddd', linewidth=0.8, linestyle='-', zorder=0)

# Sector labels
ax.text(-5.8, 5, 'Aluminium', fontsize=10, color=COR_AL,
        fontweight='bold', va='center', ha='right')
ax.text(-5.8, 2, 'Iron & Steel', fontsize=10, color=COR_FA,
        fontweight='bold', va='center', ha='right')

# Eixos
ax.set_yticks(y_pos)
ax.set_yticklabels(y_labels, fontsize=9)
ax.set_xlabel('Price elasticity (β)', fontsize=11)
ax.set_title('Estimated elasticities by product group: Brazil\n'
             '(circle size proportional to exported volume; square = global β)',
             fontsize=11, pad=12)
ax.set_xlim(-6.2, 1.0)

# Legenda manual
patch_br  = mpatches.Patch(color='#444444', label='● β Brazil (circle)')
patch_glb = mpatches.Patch(color='#888888', alpha=0.5, label='■ β global (quadrado)')
ax.legend(handles=[patch_br, patch_glb], fontsize=8,
          loc='lower right', framealpha=0.9)

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.grid(axis='x', alpha=0.25, linestyle='--')

plt.tight_layout()
out1 = root + '/_resultados_finais/G1_betas_grupos.png'
plt.savefig(out1, dpi=150, bbox_inches='tight')
plt.close()
print(f'Saved: {out1}')


# ══════════════════════════════════════════════════════════════════════════════
# CHART 2 — Out-of-sample scatter: Δpredicted × Δactual (BR and AR)
# ══════════════════════════════════════════════════════════════════════════════

setores_delta = [
    ('ferro_aco', 'Iron & Steel', COR_FA),
    ('aluminio',  'Aluminium',    COR_AL),
]

fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=False)

for ax, (setor, nome, cor) in zip(axes, setores_delta):
    pasta = setor + '_brasil_e_argentina_individual_post_tax_j3'
    path  = root + '/outputs/' + pasta + '/5c_validacao_delta_dados.csv'

    obs_BR, pred_BR, sign_BR = [], [], []
    obs_AR, pred_AR, sign_AR = [], [], []

    with open(path, encoding='latin-1') as f:
        reader = csv.DictReader(f)
        for row in reader:
            exp = row['exporter'].strip()
            if exp not in ('BR', 'AR'):
                continue
            try:
                o = float(row['delta_log_dv_obs'])
                p = float(row['delta_log_dv_pred'])
                s = row['sign_correct'].strip().upper() == 'TRUE'
            except:
                continue
            if not (math.isfinite(o) and math.isfinite(p)):
                continue
            if exp == 'BR':
                obs_BR.append(o); pred_BR.append(p); sign_BR.append(s)
            else:
                obs_AR.append(o); pred_AR.append(p); sign_AR.append(s)

    # Limites
    all_vals = obs_BR + pred_BR + obs_AR + pred_AR
    lim = max(abs(v) for v in all_vals) * 1.1
    lim = min(lim, 8)

    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)

    # 45° line
    ax.plot([-lim, lim], [-lim, lim], color='#aaaaaa',
            linewidth=1.0, linestyle='--', zorder=1, label='45°')
    ax.axhline(0, color='#dddddd', linewidth=0.6)
    ax.axvline(0, color='#dddddd', linewidth=0.6)

    # Quadrantes "acerto" (Q1 e Q3) em fundo claro
    ax.fill_between([-lim, 0], 0, -lim, alpha=0.04, color='green')
    ax.fill_between([0, lim],  0,  lim, alpha=0.04, color='green')

    # BR: sign hit and miss
    obs_c  = [o for o, s in zip(obs_BR, sign_BR) if s]
    pred_c = [p for p, s in zip(pred_BR, sign_BR) if s]
    obs_e  = [o for o, s in zip(obs_BR, sign_BR) if not s]
    pred_e = [p for p, s in zip(pred_BR, sign_BR) if not s]

    ax.scatter(pred_c, obs_c, s=45, color=cor, alpha=0.65,
               zorder=3, edgecolors='white', linewidths=0.4,
               label=f'BR acerta ({len(obs_c)}/{len(obs_BR)})')
    ax.scatter(pred_e, obs_e, s=45, color=cor, alpha=0.25,
               zorder=3, marker='x', linewidths=1.0,
               label=f'BR erra ({len(obs_e)}/{len(obs_BR)})')

    # AR
    if obs_AR:
        obs_c2  = [o for o, s in zip(obs_AR, sign_AR) if s]
        pred_c2 = [p for p, s in zip(pred_AR, sign_AR) if s]
        obs_e2  = [o for o, s in zip(obs_AR, sign_AR) if not s]
        pred_e2 = [p for p, s in zip(pred_AR, sign_AR) if not s]

        ax.scatter(pred_c2, obs_c2, s=45, color='#e67e22', alpha=0.65,
                   zorder=3, edgecolors='white', linewidths=0.4,
                   label=f'AR acerta ({len(obs_c2)}/{len(obs_AR)})')
        ax.scatter(pred_e2, obs_e2, s=45, color='#e67e22', alpha=0.25,
                   zorder=3, marker='x', linewidths=1.0,
                   label=f'AR erra ({len(obs_e2)}/{len(obs_AR)})')

    # BR correlation
    if len(obs_BR) > 2:
        mo = sum(obs_BR)/len(obs_BR)
        mp = sum(pred_BR)/len(pred_BR)
        cov = sum((o-mo)*(p-mp) for o,p in zip(obs_BR,pred_BR))/len(obs_BR)
        sd_o = (sum((o-mo)**2 for o in obs_BR)/len(obs_BR))**0.5
        sd_p = (sum((p-mp)**2 for p in pred_BR)/len(pred_BR))**0.5
        cor_br = cov/(sd_o*sd_p) if sd_o*sd_p > 0 else float('nan')
        n_br = len(obs_BR)
        hit_br = sum(sign_BR)/n_br*100
        ax.text(0.04, 0.97,
                f'BR: r={cor_br:.2f}  hit={hit_br:.0f}%  N={n_br}',
                transform=ax.transAxes, fontsize=8.5, color=cor,
                va='top', fontweight='bold')

    if obs_AR:
        mo2 = sum(obs_AR)/len(obs_AR)
        mp2 = sum(pred_AR)/len(pred_AR)
        cov2 = sum((o-mo2)*(p-mp2) for o,p in zip(obs_AR,pred_AR))/len(obs_AR)
        sd_o2 = (sum((o-mo2)**2 for o in obs_AR)/len(obs_AR))**0.5
        sd_p2 = (sum((p-mp2)**2 for p in pred_AR)/len(pred_AR))**0.5
        cor_ar = cov2/(sd_o2*sd_p2) if sd_o2*sd_p2 > 0 else float('nan')
        n_ar = len(obs_AR)
        hit_ar = sum(sign_AR)/n_ar*100
        ax.text(0.04, 0.89,
                f'AR: r={cor_ar:.2f}  hit={hit_ar:.0f}%  N={n_ar}',
                transform=ax.transAxes, fontsize=8.5, color='#e67e22',
                va='top', fontweight='bold')

    ax.set_xlabel('Δ log(share) previsto', fontsize=10)
    ax.set_ylabel('Δ log(share) realizado', fontsize=10)
    ax.set_title(nome, fontsize=12, fontweight='bold', color=cor)
    ax.legend(fontsize=7.5, loc='lower right', framealpha=0.9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

fig.suptitle('Out-of-sample validation: predicted vs. actual change in share\n'
             '(Brazil e Argentina, pooled 2023–2025; pontos nos quadrantes verdes = acerto de sinal)',
             fontsize=11, y=1.02)

plt.tight_layout()
out2 = root + '/_resultados_finais/G2_validacao_oos.png'
plt.savefig(out2, dpi=150, bbox_inches='tight')
plt.close()
print(f'Saved: {out2}')

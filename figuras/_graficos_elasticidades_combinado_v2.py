"""
V2 — Market-share price elasticities: Brazil vs Argentina, single figure.
Only Iron & Steel and Aluminium (no cement).
Country colours standardised across BOTH panels; distinct marker shapes.
Careful label placement to avoid overlap when BR and AR betas are close.
English.
"""
import sys
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from matplotlib import rcParams

sys.stdout.reconfigure(encoding='utf-8')

root = 'C:/Users/loren/OneDrive/Documentos/TCC CBAM/Projeto R/Versão Claude code/MODELO_OFICIAL'
out  = root + '/figuras_geradas/'

rcParams['font.family'] = 'sans-serif'
rcParams['font.size']   = 10

# Structure: (label, beta_BR, beta_AR, beta_global, vol_BR, vol_AR)
grupos_FA = [
    ('Long &\ntubular',           -1.352, -0.790, -1.512,  2.9, 95.0),
    ('Semi-finished\n& flat',     -3.482, -1.859, -2.303, 16.5,  5.0),
    ('Primaries\n(ore/pig iron)', -0.168, -0.187, -0.187, 80.6,  0.0),
]
grupos_AL = [
    ('Manufactured\n& finished',  -1.280, -1.129, -1.029,  0.9,  0.4),
    ('Rolled &\ntubular',         -1.515, -1.976, -1.123, 10.3,  0.7),
    ('Primary &\nsemi-finished',  -0.556, -0.334, -0.572, 88.8, 98.9),
]

# ── Standardised country colours (same in both panels) ────────────────────────
COR_BR = '#2c6e9e'   # blue circle
COR_AR = '#e67e22'   # orange triangle
COR_GL = '#888888'   # gray square
COR_FA_TITLE = '#2c6e9e'
COR_AL_TITLE = '#c0392b'

beta_setor_BR = {'FA': -0.749, 'AL': -0.662}
beta_setor_AR = {'FA': -0.844, 'AL': -0.349}
beta_setor_GL = {'FA': -1.635, 'AL': -0.769}

FS_TITLE=13; FS_XLABEL=11; FS_XTICK=9.5; FS_YTICK=10.5
FS_VOL=8.5; FS_BETA=8; FS_SET=8; FS_LEGEND=10; FS_NOTE=8.5
CLOSE_THR = 0.28   # if |b_br - b_ar| < this, offset labels horizontally
BETA_THR  = 0.10   # hide global label when within this of a country point
LBBOX = dict(boxstyle='round,pad=0.16', facecolor='white', edgecolor='none', alpha=0.92)


VOLBOX = dict(boxstyle='round,pad=0.10', facecolor='white', edgecolor='none', alpha=0.9)

def vol_annot(ax, val, yy, col, vol, side):
    """Volume % with a white tag, hugging the marker on the given side."""
    if vol <= 2.0:
        return
    ha = 'right' if side < 0 else 'left'
    ax.annotate(f'{vol:.0f}%', xy=(val, yy), xytext=(side, 0),
                textcoords='offset points', fontsize=FS_VOL, color=col,
                va='center', ha=ha, alpha=0.95, clip_on=False,
                zorder=9, bbox=VOLBOX)


def plot_panel(ax, grupos, setor_key, titulo, title_col, x_min, x_max):
    n = len(grupos)
    y_pos = list(range(n, 0, -1))

    # Labels hug their markers. Small offsets so each β sits right next to its
    # shape. Global normally just above its square; Brazil above its circle;
    # Argentina below its triangle. When Global and Brazil are horizontally
    # close, Global drops just BELOW its square to avoid the Brazil label.
    DY_GL = 0.20   # above square
    DY_BR = 0.20   # above circle
    DY_AR = -0.20  # below triangle
    for y, g in zip(y_pos, grupos):
        b_br, b_ar, b_gl = g[1], g[2], g[3]
        v_br, v_ar       = g[4], g[5]

        # connector line spanning all three points
        allb = [b_br, b_ar, b_gl]
        ax.plot([min(allb), max(allb)], [y, y],
                color='#cccccc', linewidth=1.4, zorder=1, alpha=0.8)

        # markers: Global behind, then Argentina, then Brazil on top
        ax.scatter(b_gl, y, s=85, color=COR_GL, marker='s',
                   zorder=3, linewidths=0.6, edgecolors='#666', alpha=0.85)
        ax.scatter(b_ar, y, s=max(80, 65 + v_ar*14), color=COR_AR, marker='^',
                   zorder=5, linewidths=1.2, edgecolors='white', alpha=0.95)
        ax.scatter(b_br, y, s=max(80, 65 + v_br*14), color=COR_BR, marker='o',
                   zorder=6, linewidths=1.2, edgecolors='white', alpha=0.95)

        # β labels — fixed rows, white tag behind each.
        # If Global and Brazil are horizontally close, nudge Global left and
        # Brazil right so the two top-row tags never collide.
        # scale-aware closeness: use a fraction of the panel x-range.
        # When close, right-anchor Global and left-anchor Brazil AND add a
        # generous horizontal gap so the two top-row tags clearly separate.
        xr = abs(x_max - x_min)
        gl_br_close = abs(b_gl - b_br) < 0.18 * xr
        # Global: normally just above its square. If close to Brazil, drop it
        # just BELOW the square — unless Argentina is also below-and-near (would
        # collide), in which case keep Global above but nudged aside.
        if abs(b_gl - b_br) > BETA_THR:
            ar_below_near = abs(b_gl - b_ar) < 0.10 * abs(x_max - x_min)
            if gl_br_close and not ar_below_near:
                ax.text(b_gl, y - DY_GL, f'{b_gl:.2f}', fontsize=FS_BETA - 0.5,
                        color='#666', ha='center', va='top', zorder=8,
                        clip_on=False, bbox=LBBOX)
            else:
                # above the square; shift right a touch if Brazil is just left
                gdx = 0.03 * abs(x_max - x_min) if gl_br_close else 0.0
                ax.text(b_gl + gdx, y + DY_GL, f'{b_gl:.2f}',
                        fontsize=FS_BETA - 0.5, color='#666', ha='center',
                        va='bottom', zorder=8, clip_on=False, bbox=LBBOX)
        #   Brazil just above its circle
        ax.text(b_br, y + DY_BR, f'{b_br:.2f}', fontsize=FS_BETA,
                color=COR_BR, ha='center', va='bottom', zorder=8,
                clip_on=False, bbox=LBBOX)
        #   Argentina always below the marker
        ax.text(b_ar, y + DY_AR, f'{b_ar:.2f}', fontsize=FS_BETA,
                color=COR_AR, ha='center', va='top', zorder=8,
                clip_on=False, bbox=LBBOX)

        # volume % tags — hug the marker: Brazil left, Argentina right
        vol_annot(ax, b_br, y, COR_BR, v_br, side=-13)
        vol_annot(ax, b_ar, y, COR_AR, v_ar, side=13)

    # sector betas as vertical lines
    b_sec_br = beta_setor_BR[setor_key]
    b_sec_ar = beta_setor_AR[setor_key]
    b_sec_gl = beta_setor_GL[setor_key]
    for bsec, col, ls, lw in [
        (b_sec_br, COR_BR, ':',  1.6),
        (b_sec_ar, COR_AR, '-.', 1.4),
        (b_sec_gl, COR_GL, '--', 1.1),
    ]:
        ax.axvline(bsec, color=col, linewidth=lw, linestyle=ls, alpha=0.6, zorder=0)
    # global sector-β label — placed to the LEFT of its (gray) line
    ax.text(b_sec_gl - 0.06, 0.34, f'{b_sec_gl:.3f}', fontsize=FS_SET,
            color=COR_GL, alpha=0.9, va='bottom', ha='right')

    # sector-β value labels: if the two lines are close, stack them at
    # different heights and push apart horizontally so they never collide
    sec_close = abs(b_sec_br - b_sec_ar) < 0.5
    if sec_close:
        # lower value on left-anchored, higher on right-anchored, different y
        left  = ('BR', b_sec_br) if b_sec_br <= b_sec_ar else ('AR', b_sec_ar)
        right = ('AR', b_sec_ar) if b_sec_br <= b_sec_ar else ('BR', b_sec_br)
        ax.text(left[1]  - 0.05, 0.52, f'{left[1]:.3f}', fontsize=FS_SET,
                color=(COR_BR if left[0]=='BR' else COR_AR), alpha=0.9,
                va='bottom', ha='right')
        ax.text(right[1] + 0.05, 0.30, f'{right[1]:.3f}', fontsize=FS_SET,
                color=(COR_BR if right[0]=='BR' else COR_AR), alpha=0.9,
                va='bottom', ha='left')
    else:
        ax.text(b_sec_br + 0.06, 0.34, f'{b_sec_br:.3f}', fontsize=FS_SET,
                color=COR_BR, alpha=0.9, va='bottom', ha='left')
        ax.text(b_sec_ar + 0.06, 0.34, f'{b_sec_ar:.3f}', fontsize=FS_SET,
                color=COR_AR, alpha=0.9, va='bottom', ha='left')

    ax.axvline(0, color='#cccccc', linewidth=0.8, linestyle='--', zorder=0)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([g[0] for g in grupos], fontsize=FS_YTICK)
    ax.set_title(titulo, fontsize=FS_TITLE, fontweight='bold', color=title_col, pad=10)
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(0.2, n + 0.95)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='x', alpha=0.18, linestyle='--')
    ax.tick_params(axis='x', labelsize=FS_XTICK)


# ── Figure ────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(11, 5.4),
                         gridspec_kw={'width_ratios': [1, 1]})

plot_panel(axes[0], grupos_FA, 'FA', 'Iron & Steel', COR_FA_TITLE, -4.3, 0.7)
plot_panel(axes[1], grupos_AL, 'AL', 'Aluminium',    COR_AL_TITLE, -2.6, 0.7)

for ax in axes:
    ax.set_xlabel('Market-share price elasticity (β)', fontsize=FS_XLABEL, labelpad=7)

# Legend
dot_br = mlines.Line2D([], [], color=COR_BR, marker='o', linestyle='None',
                       markersize=9, label='Brazil (circle, size ∝ export volume share 2023–25)')
dot_ar = mlines.Line2D([], [], color=COR_AR, marker='^', linestyle='None',
                       markersize=9, label='Argentina (triangle, size ∝ export volume share)')
dot_gl = mlines.Line2D([], [], color=COR_GL, marker='s', linestyle='None',
                       markersize=7, label='Global β (gray square)')
lin_br = mlines.Line2D([], [], color=COR_BR, linestyle=':',  linewidth=1.6,
                       label='Sector β — Brazil (dotted)')
lin_ar = mlines.Line2D([], [], color=COR_AR, linestyle='-.', linewidth=1.4,
                       label='Sector β — Argentina (dash-dot)')
lin_gl = mlines.Line2D([], [], color=COR_GL, linestyle='--', linewidth=1.1,
                       label='Sector β — Global (dashed)')
fig.legend(handles=[dot_br, dot_ar, dot_gl, lin_br, lin_ar, lin_gl],
           fontsize=FS_LEGEND, loc='lower center', ncol=3,
           bbox_to_anchor=(0.5, 0.0), framealpha=0.95)

note = ('Note: for each product group, β is shown for Brazil and Argentina. '
        'When the two are close, labels are placed side by side. '
        'Volume share (%) annotated next to the marker when > 2%.')
fig.text(0.01, -0.05, note, fontsize=FS_NOTE, color='#555', style='italic')

fig.suptitle('Market-share price elasticities by product group — Brazil vs. Argentina',
             fontsize=FS_TITLE, fontweight='bold', y=1.03)

plt.tight_layout(w_pad=3.0, rect=[0, 0.13, 1, 1])
plt.savefig(out + 'G1_elasticidades_combinado_v2.png', dpi=300, bbox_inches='tight')
plt.close()
print('Saved: G1_elasticidades_combinado_v2.png')

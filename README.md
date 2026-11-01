# CBAM-Trade-Impact-Model

**Undergraduate Thesis Research Project (TCC)**

Replication files for a thesis on how the EU's Carbon Border Adjustment
Mechanism (CBAM) reallocates import market share in **iron & steel, aluminium
and cement**, with a focus on Brazil and Argentina. The model is a PPML
market-share gravity model with sign-constrained shrinkage (v2).

The thesis asks about the first of the two outcomes the EU expects from CBAM,
a change in the supplier basket. Emission factors are held fixed in every
scenario, so each simulated change is the effect of pure reallocation, with no
technological response by exporters. The second outcome (greener technology)
is not modelled.

Language: code comments are mostly in Portuguese; documentation and the
dashboard are in English.

## Summary of results

Reference scenario: EUR 95/tCO2, MFN tariff, iron & steel.

| Group | Base share of EU imports | Simulated share |
|---|---|---|
| EU / EEA / Switzerland (exempt) | 63.3% | 68.2% |
| 11-country basket (taxed exporters) | 28.5% | 23.0% |
| Others (long tail) | 8.2% | 8.9% |

Brazil loses about 2.7% of its iron & steel volume, against roughly 30% to 50%
for Russia, India, Turkey and China. Cement has a very weak price mechanism,
so its results are the least reliable. The exempt bloc's "gain" is a
consequence of share renormalisation, not an estimated supply response.

## Root files

- `main_v2.R`: the official model. Configuration (product, countries, scenarios) is at the top.
- `rodar_modelo.R`: runner. Set `PRODUTO`, `PAISES` and `NOME`, then run it.
- `analise_realocacao_verde.R`: isolates pure reallocation (fixed technology): aggregate change in embedded emissions, average carbon intensity of the basket before/after, and whether dirtier exporters lose more share.
- `analise_realocacao_cesta.csv`, `analise_realocacao_paises.csv`: outputs of the script above.
- `extrair_dashboard.R`: consolidates the model outputs into the JSON embedded in the dashboard.
- `LICENSE`: MIT.

## scripts folder

R pipeline sourced in order by `main_v2.R`:

- `00_tracking.R`: sample tracking after each filter.
- `01_limpeza.R`: cleaning, prices, leave-one-out relative price, market share.
- `02_modelo.R`: PPML estimation with `exporter x product` and `product x year` fixed effects.
- `03_paises.R`: country-specific elasticities with shrinkage toward the sector elasticity.
- `04_validacao.R`, `04b_validacao_delta.R`: out-of-sample validation (train to 2022, test 2025), levels and changes.
- `05_grupos.R`: elasticities by processing stage (uses `config/*_grupos.R`).
- `06_robustez_paises.R`: robustness against a basket-restricted model.
- `07_simulacao_cbam.R`: 6 scenarios (3 carbon prices x MFN/Mercosul), with competitive renormalisation of shares.
- `08_projecao_cbam.R`: cumulative projection 2026 to 2028.
- `09_analise.R`: impact tables, charts, emissions and goodness of fit.
- `helper_grupos.R`: grouping helper.

## helpers folder

- `funcoes_modelo_v2.R`: country-elasticity shrinkage with the sign constraint (official). `funcoes_modelo.R` is the unconstrained v1.
- `10_auditoria_betas.R`: audit of the estimated elasticities.
- `11_gof_modelo.R`: explained variation, fixed effects vs. price.

## config folder

- `Base_de_dados_final_Ferro.csv`, `..._Aluminio.csv`, `..._Cimento.csv`: bilateral trade data (volume, value, price, tariff) by exporter and HS product, 2008 to 2025.
- `Base_fatores_ferro_ajustada.csv`, `..._aluminio_...`, `..._cimento_...`: emission factors by exporter and product, with the CBAM phase-in factors for 2026 to 2028. Only non-EU exporters are covered, plus a rest-of-world fallback.
- `ferro_aco_grupos.R`, `aluminio_grupos.R`, `cimento_grupos.R`: product-to-group mappings.

## figuras folder

38 Python scripts that build the thesis figures. They read from `outputs/` and
write to `figuras_geradas/`. They locate the repository from their own path,
so run them from the repository root, for example:

```bash
python figuras/_graf_sim_FA_resumo_v3.py
```

Main figures:

- Elasticities by country and group: `_graficos_elasticidades_combinado_v2.py`
- Out-of-sample validation: `_graficos_validacao_2025.py`, `_graficos_validacao_2019test.py`
- Explained variation, levels vs. changes: `_graf_r2_mesclado.py`, `_r2_decomp_delta.py`
- Iron & steel impact summary: `_graf_sim_FA_resumo_v3.py`
- Aluminium impact summary and decomposition: `_graf_sim_AL_resumo_v2.py`, `_graf_sim_AL_decomp.py`, `_graf_sim_AL_mercosul.py`
- Brazil and Argentina bubble charts: `_graf_bubble_brar.py`, `_graf_bubble_AL.py`
- Stability and placebo tests: `_graficos_rolling_betas.py`, `_graficos_stable_years_test.py`, `_graficos_stable_market_test.py`
- Anti-dumping 2016 validation: `_teste_antidumping_2016.py`

## dashboard folder

`cbam_manifest.html` is a single self-contained interactive page (data
embedded; only web fonts are fetched). It shows, by sector, carbon price and
tariff regime: the market overview before/after, a per-country view with
product-level drill-down, and the pure-reallocation comparison across sectors.
Open it in a browser.

## Folders not tracked here

`outputs/` (model results per run, about 60 MB) and `figuras_geradas/`
(generated figures and tables, about 18 MB) are regenerated by running the
code and are git-ignored.

## How to replicate

1. Install R 4.5 with `tidyverse`, `fixest`, `broom`, `ggplot2`, `janitor`
   (and `jsonlite` for the dashboard export). Python 3 with `matplotlib` for
   the figures.
2. Edit the three lines at the top of `rodar_modelo.R`:

   ```r
   PRODUTO <- "aluminio"          # "ferro_aco" | "aluminio" | "cimento"
   PAISES  <- c("BR", "AR", "CN") # focal countries (ISO-2)
   NOME    <- "my_run"            # suffix of the output folder
   ```

3. From the repository root run `Rscript rodar_modelo.R`. Results go to
   `outputs/<product>_<name>_individual_post_tax_j3_v2/`. A run with an
   11-country basket takes about 10 to 15 minutes.

## Data

Trade data and emission factors in `config/` are the inputs used for the
thesis. Check the terms of the original sources before reusing them.

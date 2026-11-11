# CBAM-Trade-Impact-Model

**CBAM and Export Competitiveness: Market Share Elasticity Estimates and Simulations for Brazil and Argentina**

Lorenzo Viana Lima and Flávio Tosi Feijó. The paper is in `paper/`.

Replication files for a paper on how the EU's Carbon Border Adjustment
Mechanism (CBAM) affects the competitiveness of Brazilian and Argentine
exports in **iron & steel, aluminium and cement**. A structural gravity model
estimated by PPML with fixed effects gives market-share price elasticities at
the individual product level (trade flows from more than 150 countries to the
EU, 2010 to 2025). These elasticities feed CBAM cost simulations under three
carbon prices and two tariff regimes (MFN and Mercosul).

## Method

- **Estimator:** PPML (`fixest::fepois`) on market share, with
  `exporter x product` and `product x year` fixed effects.
- **Price variable:** post-tariff unit price relative to the leave-one-out
  average price of competitors.
- **Country elasticities:** shrunk towards the sector-wide elasticity. The v2
  model adds a sign constraint: a country estimate with the wrong (positive)
  sign is censored at zero before shrinkage.
- **Simulation:** CBAM cost = product-level emission factor x carbon price is
  added to the price of each non-exempt exporter. Shares of all exporters are
  renormalised to sum to one. EU/EEA/Switzerland are exempt.
- **Scenarios:** carbon price of EUR 75, 95 and 115 per tCO2, under MFN and
  Mercosul tariffs (6 per sector).
- **Validation:** out-of-sample test (train to 2022, test 2025), explained
  variation split between fixed effects and price, and a historical test with
  the 2016 EU anti-dumping duties on cold-rolled steel.

## Repository layout

```
paper/           the paper (PDF)
CONFIGURATION.md every option, every fixed choice, and why (read this next)
DATA.md          data sources: database, version, extraction and treatment
main_v2.R        official model; configuration at the top
rodar_modelo.R   runner: set PRODUTO / PAISES / NOME and run
scripts/         pipeline 00 to 09 (+ 04b), sourced in order by main_v2.R
helpers/         shrinkage with sign constraint, goodness of fit, beta audit
config/          trade data, emission factors, product-to-group mappings
figuras/         Python scripts for the paper figures
outputs/         model results per run (generated, git-ignored)
```

### scripts and helpers

- `00_tracking.R`: sample tracking after each filter.
- `01_limpeza.R`: cleaning, prices, leave-one-out relative price, market share.
- `02_modelo.R`: PPML estimation.
- `03_paises.R`: country-specific elasticities with shrinkage.
- `04_validacao.R`, `04b_validacao_delta.R`: out-of-sample validation (levels and changes).
- `05_grupos.R`: elasticities by processing stage (uses `config/*_grupos.R`).
- `06_robustez_paises.R`: robustness against a model restricted to the focal countries.
- `07_simulacao_cbam.R`: 6 scenarios with competitive renormalisation of shares.
- `08_projecao_cbam.R`: cumulative projection 2026 to 2028.
- `09_analise.R`: impact tables, charts, emissions, goodness of fit.
- `helpers/funcoes_modelo_v2.R`: shrinkage with the sign constraint.

### config

- `Base_de_dados_final_{Ferro,Aluminio,Cimento}.csv`: bilateral trade data (volume, value, price, tariff) by exporter and HS product.
- `Base_fatores_*_ajustada.csv`: emission factors by exporter and product, with the CBAM phase-in factors for 2026 to 2028. Non-EU exporters plus a rest-of-world fallback.
- `*_grupos.R`: product-to-group mappings.

## How to replicate

**Requirements.** R 4.5 with `tidyverse`, `fixest`, `broom`, `ggplot2` and
`janitor` (missing packages install on first run). Python 3 with `matplotlib`
for the figures. Run everything from the repository root.

### 1. Main model runs

Set the three lines at the top of `rodar_modelo.R` and run it, once per sector:

```r
PRODUTO <- "ferro_aco"          # "ferro_aco" | "aluminio" | "cimento"
PAISES  <- c("BR", "AR")        # focal countries (ISO-2)
NOME    <- "brazil_and_argentina" # any name you like (see "Run folders" below)
```

```bash
Rscript rodar_modelo.R
```

Repeat for `aluminio` and `cimento`. A run takes a few minutes.

**Every option is documented in [`CONFIGURATION.md`](CONFIGURATION.md)**: what
it does, its default, whether the paper uses it, and the reason the paper gives.
The table below is only a summary of the options that change the output folder.

**Run folders.** Results go to
`outputs/<product>_<NOME>_<mode>_<price_model>_j<window>_<suffix>/`, for
example `outputs/ferro_aco_brazil_and_argentina_individual_post_tax_j3_v2/`.
The parts after `<NOME>` come from the configuration at the top of
`main_v2.R`:

| Option | Default | Notes |
|---|---|---|
| `modo_grupo` | `"individual"` | The only implemented mode: each focal country gets its own elasticity (Equation 3 of the paper). |
| `price_model` | `"post_tax"` | `"post_tax"` adds the ad valorem tariff to the price (the paper); any other value, e.g. `"pre_tax"`, leaves the price without the tariff. Set it with `PRICE_MODEL` in `rodar_modelo.R`. |
| `janela_base` | `3` | Years averaged for the base shares (the `j3` in the folder name). |
| `sufixo_output` | `"v2"` | Set it with `SUFIXO` in `rodar_modelo.R`. |

The figure scripts look for the folders of the default configuration, with
`NOME` set to `brazil_and_argentina`. If you used another name or options, tell
the scripts through environment variables instead of renaming folders:

```bash
CBAM_RUN=my_run CBAM_TAG=individual_pre_tax_j3_v2 python figuras/_graf_sim_FA_resumo_v3.py
```

That is bash syntax. In Windows PowerShell set them first, for example
`$env:CBAM_RUN = "my_run"; $env:CBAM_TAG = "individual_pre_tax_j3_v2"`, then run the script.

`CBAM_RUN` is the `NOME` you used and `CBAM_TAG` is everything after it in the
folder name.

### 2. Historical test (anti-dumping 2016) — optional

This step is an extra check and is not needed for the main results. Skip it
unless you want Figures 8 and 9, which need two extra runs of iron & steel on
data up to 2015. In `rodar_modelo.R` set `ANO_CORTE <- 2015` and
`SUFIXO <- "roll2015"`, then run it twice:

| `PAISES` | `NOME` |
|---|---|
| `c("BR", "AR")` | `"brazil_and_argentina"` |
| `c("CN", "RU")` | `"china_and_russia"` |

### 3. Figures

The scripts read from `outputs/` and write PNGs to `figuras_geradas/`.

| Figure in the paper | Script | Needs |
|---|---|---|
| 1. R² decomposition (share changes) | `_r2_decomp_delta.py` | step 1, all three sectors |
| 2 and 3. Elasticities, Brazil and Argentina | `_graficos_secao1_paises_v2.py` | none (values embedded) |
| 4. Impact scenarios, iron & steel | `_graf_sim_FA_resumo_v3.py` | step 1, `ferro_aco` |
| 5 and 10. Impact by product, Brazil and Argentina | `_graf_bubble_separado.py` | step 1, `ferro_aco` |
| 6. Impact scenarios, aluminium | `_graf_sim_AL_resumo_v2.py` | step 1, `aluminio` |
| 8. Historical validation, global elasticities (optional) | `_teste_antidumping_2016.py` | step 2 |
| 9. Historical validation, country-specific elasticities (optional) | `_teste_antidumping_2016_opA.py` | step 2 |
| 11. Tariffs vs. CBAM cost, aluminium | `_graf_AL_tarifa_vs_cbam.py` | none (values embedded) |
| Table 4. Explanatory power | `_graficos_secao1.py` | none (values embedded) |

For example: `python figuras/_graf_sim_FA_resumo_v3.py`.

Scripts marked "values embedded" use numbers taken from the model outputs and
typed into the script; they do not read `outputs/`. The histogram of relative
prices (Figure 7) and the panel-diagnostic and robustness tables (Tables 2, 3,
5 and 6) are not generated by scripts in this repository.

## Language

Documentation, code comments, console messages and chart text are in English.
File names, CSV column names and variable names keep their original Portuguese
identifiers (for example `cenario_carbono`, `13_cbam_resumo_pais.csv`).

## Data

The inputs in `config/` are processed series built from Eurostat (trade), the ITC
Market Access Map (tariffs) and the European Commission's default emission values
(Regulation (EU) 2025/2621). [`DATA.md`](DATA.md) documents each source: database,
version and access date, what was extracted, how it was treated, the structure of
the files, and what is not in this repository. Check the terms of each source
before reusing the data.

## License

Code is released under the MIT License (see `LICENSE`). The paper in `paper/`
is not covered by that license.

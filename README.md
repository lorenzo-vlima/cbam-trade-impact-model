# CBAM Trade Impact Model

A PPML market-share gravity model of how the EU's **Carbon Border Adjustment
Mechanism (CBAM)** reallocates import market share across exporters in three
covered sectors: **iron & steel, aluminium and cement**. The focus is on
Brazil and Argentina, benchmarked against the largest non-EU exporters.

Undergraduate thesis project (TCC). Code in R (estimation and simulation) and
Python (thesis figures), plus a standalone interactive dashboard.

## Research question

The EU expects two outcomes from CBAM: (1) the supplier basket changes, and
(2) exporters adopt greener technology. This project isolates **outcome 1**.
Emission factors are held fixed in every scenario, so every simulated change
in volume or embedded emissions is the effect of *pure reallocation*, with no
technological response by exporters. That gives a clean benchmark against
which any observed decarbonisation can later be compared.

## Method

- **Estimator:** Poisson pseudo-maximum likelihood (PPML, `fixest::fepois`) on
  market share, with `exporter x product` and `product x year` fixed effects.
- **Price variable:** post-tariff unit price relative to the leave-one-out
  average price of competitors, so a country is never compared with itself.
- **Country elasticities:** country-specific price elasticities are shrunk
  towards the sector-wide elasticity. The v2 model adds a **sign constraint**:
  if a country estimate has the wrong (positive) sign it is censored at zero
  before shrinkage.
- **Simulation:** CBAM cost = product-level emission factor x carbon price is
  added to each non-exempt exporter's price. Shares of all exporters are then
  renormalised to sum to one, so one exporter's loss is another's gain.
  EU/EEA/Switzerland are exempt (cost = 0).
- **Scenarios:** 3 carbon prices (EUR 75, 95, 115 per tCO2) x 2 tariff regimes
  (MFN, Mercosul) = 6 scenarios per sector.
- **Validation:** out-of-sample test (train up to 2022, test 2025), a
  decomposition of explained variation into fixed effects vs. price, and a
  robustness check against a basket-restricted model.

## Main findings (reference scenario: EUR 95/tCO2, MFN)

- Exporters subject to CBAM lose share; the exempt EU/EEA/Swiss bloc and the
  long tail of other exporters absorb it (e.g. iron & steel: EU/EEA/CH goes
  from 63.3% to 68.2% of the import market).
- Brazil's loss in iron & steel is small (about -2.7% of volume) compared with
  the largest losers (Russia, India, Turkey, China, roughly -30% to -50%).
- Cement has a very weak price mechanism (very low price R2), so its results
  are much less reliable than steel and aluminium.
- **Limitation:** the "gain" of the exempt bloc is an accounting consequence of
  share renormalisation, not an estimated supply response. The model also
  assumes full cost pass-through and a fixed market size, and the emission
  factor file contains no EU producers. See the thesis for the full discussion.

## Repository layout

```
main_v2.R                     official model (edit config at the top)
rodar_modelo.R                runner: set PRODUTO / PAISES / NOME and run
scripts/                      pipeline 00-09 (+ 04b)
helpers/                      model functions (shrinkage), GoF, beta audit
config/                       raw trade data, emission factors, product groups
analise_realocacao_verde.R    pure-reallocation vs. green-technology analysis
extrair_dashboard.R           consolidates results into JSON for the dashboard
figuras/                      Python scripts that build the thesis figures
dashboard/cbam_manifest.html  standalone interactive dashboard
outputs/                      model results per run (generated, git-ignored)
```

## How to run

Requirements: R 4.5 with `tidyverse`, `fixest`, `broom`, `ggplot2`, `janitor`
(and `jsonlite` for the dashboard export). Missing packages install themselves
on first run.

1. Set the three lines at the top of `rodar_modelo.R`:

   ```r
   PRODUTO <- "aluminio"          # "ferro_aco" | "aluminio" | "cimento"
   PAISES  <- c("BR", "AR", "CN") # focal countries (ISO-2)
   NOME    <- "my_run"            # suffix of the output folder
   ```

2. From the repository root:

   ```bash
   Rscript rodar_modelo.R
   ```

Results are written to `outputs/<product>_<name>_individual_post_tax_j3_v2/`.
A full run with a basket of about 11 countries takes roughly 10-15 minutes.

To regenerate a figure (Python):

```bash
python figuras/_graf_sim_FA_resumo_v3.py
```

## Dashboard

`dashboard/cbam_manifest.html` is a single self-contained file (data embedded;
only web fonts are loaded from Google Fonts). Open it in a browser to explore
by sector, carbon price and tariff regime: market overview before/after, a
per-country view with product-level drill-down, and the reallocation vs.
green-technology comparison across sectors.

## Note on the sector share fix

The sector share of a country is aggregated at volume level (sum of the
country's volume across products divided by the sum of total EU volume in the
sector), not by adding product-level shares. Percentage changes were never
affected; only the reported share level was.

## Data

The trade data and emission factors in `config/` are the inputs used for the
thesis. Check the terms of the original sources before reusing them.

## License

Code is released under the MIT License (see `LICENSE`).

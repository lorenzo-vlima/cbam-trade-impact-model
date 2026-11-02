# Configuration reference and methodological choices

This document explains every option of the model, every choice fixed inside
the code, what the paper used, and why. It is written so that someone can
reproduce the paper's numbers and also understand what changes if they change
an option.

**Status labels used below**

- **Paper**: the option is used in the paper, with the value shown.
- **Available**: implemented and working, but the paper does not use it (or
  does not discuss it).
- **Inert**: the variable exists in the configuration but nothing in the code
  reads it.

Where the paper gives a reason, it is cited by section. Where it does not, this
document says so instead of inventing one. The paper is in `paper/`.

Contents

1. [How to change an option](#1-how-to-change-an-option)
2. [Options in `main_v2.R`](#2-options-in-main_v2r)
3. [Choices fixed in the code](#3-choices-fixed-in-the-code)
4. [Input data](#4-input-data)
5. [Output files](#5-output-files)
6. [Replication checkpoints](#6-replication-checkpoints)
7. [What this repository does not reproduce](#7-what-this-repository-does-not-reproduce)
8. [Known differences and limitations](#8-known-differences-and-limitations)

---

## 1. How to change an option

There are two ways, and they do the same thing.

**Through the runner (recommended).** `rodar_modelo.R` rewrites a few lines of
`main_v2.R` in a temporary copy and runs it, so `main_v2.R` is never edited.
It controls:

| Runner variable | Overrides in `main_v2.R` | Default |
|---|---|---|
| `PRODUTO` | `produto_ativo` | `"ferro_aco"` |
| `PAISES` | `paises_grupo` | `c("BR", "AR")` |
| `NOME` | `nome_grupo` | `"brazil_and_argentina"` |
| `PRICE_MODEL` | `price_model` | `NULL` (keeps `"post_tax"`) |
| `ANO_CORTE` | `ano_corte`, and also `ano_val_treino` (= `ANO_CORTE - 2`) and `ano_val_teste` (= `ANO_CORTE`) | `NULL` (keeps 2025, 2022, 2025) |
| `SUFIXO` | `sufixo_output` | `NULL` (keeps `"v2"`) |

**By editing `main_v2.R`.** Every option in section 2 can be edited in the
block marked `CONFIGURATION — EDIT ONLY HERE`. Run it from the repository root
(`Rscript main_v2.R`), or through the runner, which still applies its own
overrides on top.

Each run writes to

```
outputs/<produto_ativo>_<nome_grupo>_<modo_grupo>_<price_model>_j<janela_base>_<sufixo_output>/
```

for example `outputs/ferro_aco_brazil_and_argentina_individual_post_tax_j3_v2/`.
The figure scripts rebuild this name from `NOME` and the part after it; see
"Run folders" in the README.

---

## 2. Options in `main_v2.R`

### 2.1 What is run

#### `produto_ativo` — **Paper**: all three sectors, one run each
Sector to estimate: `"ferro_aco"` (iron & steel), `"aluminio"` (aluminium) or
`"cimento"` (cement). It selects the trade-data file, the emission-factor file
and the product-group mapping (`config/<sector>_grupos.R`).
The paper analyses the three sectors (62 products: 42 iron & steel, 14
aluminium, 6 cement; Table 1). Each sector is estimated separately, so there is
one run per sector.

#### `paises_grupo` — **Paper**: `c("BR", "AR")`
The focal countries: the ones that get their own price elasticity and are
simulated individually. Use ISO 3166 alpha-2 codes as they appear in the trade
data (`BR`, `AR`, `CN`, `RU`, ...).
The paper's focal countries are Brazil and Argentina. You can pass any other
countries, for example the basket of main exporters used in `analysis/`.
A country with no exports in the base window (the last `janela_base` years)
has no rows in the simulation tables, and no warning is printed. For example,
Belarus is in the cement estimation sample (19 observations) but has no cement
exports to the EU after 2022, so it does not appear in the cement simulation.

#### `nome_grupo` — **Available** (only a label)
Free text used in the output folder name and in chart subtitles. It has no
effect on the estimation. The default is `brazil_and_argentina`.

#### `modo_grupo` — **Paper**: `"individual"` (the only implemented mode)
How the focal countries enter the model. `"individual"` gives **each** focal
country its own differential from the global elasticity, estimated together in
one joint model. This is Equation (3) of the paper (Section 3.2.2): the
effective elasticity of country *j* in product *p* is the global elasticity
plus a country-specific differential, and each differential is weighted by its
own precision (Equation 4).

The paper uses individual mode because its question is about Brazil and
Argentina **separately**: results, elasticities and simulations are reported
per country (Figures 2 to 6), and a country with a poorly estimated
differential has to fall back on the global elasticity without dragging the
other one with it.

**Aggregated mode does not exist in this code.** The configuration check used
to accept `"agregado"`, but no part of the pipeline implemented it, so choosing
it silently ran the individual model. The check now only accepts
`"individual"` and stops with an error otherwise. The paper does not describe
an aggregated mode.

#### `price_model` — **Paper**: `"post_tax"`
Which price is used. With `"post_tax"` the unit price (CIF value per ton) is
multiplied by one plus the ad valorem tariff, giving the price actually paid by
the EU importer. With any other value (for example `"pre_tax"`) the CIF price is
used as it is.

The paper uses the post-tax price (Equation 2, Section 3.2.2): the CIF price
"does not cover the import taxation cost", so the tariff is added to
approximate the effective price paid by importers (Section 3.1.2). It is also
what makes the Mercosul–EU scenario possible, because that scenario works by
setting the tariff to zero (Section 3.3.2).

> The `pre_tax` variant is **not validated**. The Mercosul scenario in
> `07_simulacao_cbam.R` divides the price by one plus the tariff to remove the
> tariff, which assumes the tariff is already in the price. With a pre-tax
> price that division would remove a tariff that was never added. Use
> `pre_tax` only to look at the MFN scenarios, if at all. See section 8.

#### `sufixo_output` — **Available** (only a label)
Last part of the output folder name, default `"v2"` (the sign-constrained model,
see 3.2). It exists so that runs with different data cuts can live side by side;
the anti-dumping test uses `"roll2015"`.

### 2.2 Sample

The filters below are applied in this order in `scripts/01_limpeza.R`, and
`outputs/<run>/00_sample_tracking.csv` records the number of observations after
each one.

#### `ano_inicio` and `ano_corte` — **Paper**: 2010 and 2025
First and last year of the sample. `ano_corte` is also the end of the window
used to average base shares (see `janela_base`).
The paper's sample is yearly data from 2010 to 2025. The data go back to 2002,
but the paper starts in 2010 "to ensure that punctually relevant events like
the 2008 crisis would not have an impact on the model" (Section 3.1.1).
Changing `ano_corte` moves the whole analysis; it is what the 2015 anti-dumping
test does.

#### `filtro_vol` — **Paper**: 1 (ton)
Observations with volume not above this value are removed. Together with a
fixed `ton >= 1` in the same line, the effect is to keep only observations
**strictly above** 1 ton at the default.
The paper removes observations with less than 1 ton "as this would generate
exaggerated prices that could have an artificial impact in the modelling with
no real volume significance" (Section 3.1.4).

#### `filtro_euros` — **Paper**: 0 (euro)
Observations with value not above this are removed. At 0 this only drops
observations with no value. It is the "prices equal to or lower than zero"
filter of Section 3.1.4: a zero value would produce a non-positive price.

#### `min_anos_obs` — **Paper**: 5
An exporter–product pair must appear in at least this many distinct years to
stay in the sample. This is the "singleton" filter.
The paper keeps "only countries that exported at least 1 ton of the analysed
product for at least 5 years", to exclude "extreme punctual exports" and to
make sure there are no singletons in the fixed-effects structure
(Section 3.1.4). Together with the volume filter, this is what takes the number of exporters
from 235 in the raw aluminium file to the 114 of Table 1 (81 for cement and 159
for iron & steel).

#### `min_obs` — **Inert**
Defined (value 5) but never read by any script. Changing it does nothing.

#### `share_min_pais` — **Available**, not used (`NULL`)
If set to a number, drops exporter–product pairs whose average market share is
below it, **except** the focal countries. The paper does not use a minimum
share filter, so it stays `NULL`.

#### `winsor_price_rel` — **Paper**: 0.01 (top 1%)
Relative prices above the `1 - winsor_price_rel` quantile are set to that
quantile. The quantile is computed over the whole sector (all products and
years together), only on the upper tail, and on the relative price before the
logarithm.
The paper winsorises "at the top 1% of its distribution" to limit the influence
of outliers, "typically associated with small or sporadic exporters"
(Section 3.2.2). Set it to `NULL` to turn winsorisation off.

### 2.3 Estimation

#### `usar_peso_tempo` and `half_life` — **Available**, not used (`FALSE`, 5)
When `usar_peso_tempo` is `TRUE`, each observation gets a weight
`exp(-ln(2) / half_life * (last year - year))`, so recent years count more and
the weight halves every `half_life` years. When `FALSE` all weights are 1.
The paper does not discuss time weighting; its model is unweighted.

#### `z_critico` — **Available** (affects diagnostics only)
Critical value for 95% confidence intervals (1.96). It is used to draw the
confidence bars in the beta audit and stability charts and to flag significance
in the robustness comparison. It does **not** enter the shrinkage weights or the
simulation.

### 2.4 Validation

#### `ano_val_treino` and `ano_val_teste` — **Available**; not reported as such in the paper
Training end and test year of the out-of-sample validation in
`04_validacao.R` (train to 2022, test 2025 by default), and the base and test
years of the change-based validation in `04b_validacao_delta.R` (base window
ending in 2022, test years 2023 to 2025).
The final paper does not report this exercise. Its validation is the
anti-dumping test (Section 4.1, Annex F), which is a separate procedure
(`figuras/_teste_antidumping_2016*.py`). These scripts are kept because they
produce the `5*_validacao*` files and are part of the pipeline. If you set
`ANO_CORTE` through the runner, the validation years follow it automatically.

### 2.5 Simulation

#### `janela_base` — **Paper**: 3 (years)
Number of final years averaged to build base shares and base volumes
(`ano_corte - janela_base + 1` to `ano_corte`, that is 2023 to 2025). The same
window defines the volume weights used when combining product-level
elasticities into group and sector numbers.
The paper averages the three last years "to capture the structural trade
pattern of the recent years, avoiding punctual shocks in price and volume"
(Section 3.3.2). The `j3` in the output folder name is this option.

#### `premissa_agregacao` — **Paper**: `"media_simples"`
How emission factors are combined when the regulation is more detailed than the
product level used here: simple mean (`"media_simples"`) or the maximum
(`"maximo"`).
The paper uses the simple average of the constituent codes: CN8 codes inside an
HS6 product, and HS6 codes inside an HS4 product (Section 3.1.3). The maximum is
available as a conservative alternative that the paper does not use.

#### `fase_cbam` — **Paper**: `"factor_2026"` (see note)
Which column of the emission-factor file is the factor used in the six
scenarios. The file has `base_factor` and one column per year, `factor_2026`,
`factor_2027` and `factor_2028`, which are the base value with the regulation's
mark-up (10%, 20% and 30%; the file's ratios to the base value are exactly
1.10, 1.20 and 1.30).
The code uses `factor_2026`. The paper describes the mark-up schedule
(Section 3.1.3) but does not say which year's factor is applied to the three
carbon-price scenarios. If you want a different one, change this option.

#### `cenarios_carbono` — **Paper**: 75, 95 and 115 (EUR per tCO2)
The three carbon prices. The names (`baixo`, `medio`, `alto`) only appear in
labels, as `75/tCO2`, `95/tCO2`, `115/tCO2`.
The paper anchors 75 on the first quarterly price released by the European
Commission in 2026, and builds 95 and 115 "mostly as sensitivity tests" around
forecasts for 2027 and 2028 (Section 3.3.1). The charts that show only one
scenario (the pie charts, the per-product dumbbell and bubble charts) use the
**middle** price.

#### `cenarios_tarifa` — **Paper**: `"MFN"` and `"Mercosul"`
Tariff regimes crossed with the carbon prices, giving the six scenarios per
sector. In `"MFN"` each exporter keeps its tariff. In `"Mercosul"` the tariff of
the Mercosul exporters is set to zero, to represent the Mercosul–EU agreement
(Section 3.3.2).

#### `paises_mercosul` — **Paper**: `BR`, `AR`, `UY`, `PY`
The exporters that lose the tariff in the Mercosul scenario. Only Brazil and
Argentina appear in the paper's results; Uruguay and Paraguay are in the list
because they are Mercosul members and have no effect when they are not in the
trade data.

### 2.6 Cumulative projection

#### `projecao_anos` and `projecao_precos` — **Available**; not used in the paper
`08_projecao_cbam.R` simulates 2026, 2027 and 2028 in sequence, each year
starting from the previous year's simulated shares, using that year's emission
factor (`factor_2026` to `factor_2028`) and carbon price (75, 95 and 115 in
`projecao_precos`; the 2025 entry is the zero-price base). The paper does not
present a cumulative projection; its six scenarios are static and independent.
The outputs (`19_*`, `20_*`, `21_*` to `25_*`) are extras.

---

## 3. Choices fixed in the code

These are not options; changing them means editing the scripts. They are listed
so that nothing in the method is hidden.

### 3.1 Variables

- **Market share** = volume of an exporter in a product and year divided by the
  EU's total imported volume of that product in that year (`01_limpeza.R`;
  Section 3.1.1). Intra-EU flows are kept in the data (the exporters `DE`, `FR`,
  `NL`... are in the market), because shifts inside the bloc are a possible
  CBAM outcome.
- **Price** = value (euros, CIF) divided by volume (tons), times one plus the
  tariff when `price_model` is `"post_tax"`.
- **Relative price** = the exporter's price divided by the volume-weighted
  average price of all **other** exporters of that product in that year
  (leave-one-out), then winsorised and logged (Equation 2). The weights are
  volumes.
- **Tariff** is the effective ad valorem rate as a fraction (for example 0.037),
  in the input file. Observations without a tariff are dropped.

### 3.2 Estimation (`02_modelo.R`, `03_paises.R`)

- **Global elasticity by product**: PPML (`fixest::fepois`) of market share on
  the log relative price interacted with product, with exporter–product and
  product–year fixed effects. One elasticity per product.
- **Focal countries**: a second PPML, with the global elasticity entering as an
  offset, estimates for each focal country a differential per product (the
  interaction of the log relative price, the country dummy and the product).
- **Standard errors** are clustered two-way by exporter and by year
  (`cluster = ~exporter + year`) in the estimation scripts. See section 8 about
  how this compares with the wording in the paper.
- **Shrinkage** (Equation 4): the elasticity used in the simulation for focal
  country *j* is `w * (global + differential) + (1 - w) * global`, where the
  weight is `w = se_global^2 / (se_global^2 + se_differential^2)`. The
  more precisely the differential is estimated, the more it counts. If the
  differential has no standard error, `w = 0` and the global elasticity is used.
  The paper presents this as a precision-weighted shrinkage that avoids
  arbitrary significance thresholds (Section 3.2.2).
- **Sign constraint (v2)**: if the shrunk elasticity of a country comes out
  **positive**, the country's own elasticity is first set to zero, so the result
  is `(1 - w) * global`, still negative but less elastic than the global
  value. According to the notes in `main_v2.R`, with the paper's data this affects
  only iron ore (260112) for Brazil in iron & steel and calcined clay (250700)
  for Argentina in cement. The paper
  reports that no global elasticity was positive (Section 3.2.3); the constraint
  concerns country-level values.
- **Sector and group elasticities** are volume-weighted averages of the
  product-level ones, with each product weighted by its share of the sector's
  imports in the base window (footnote 9 of the paper). Groups are defined in
  `config/*_grupos.R` and match Annex E.

### 3.3 Simulation (`07_simulacao_cbam.R`)

- **CBAM cost per ton** = emission factor × carbon price. The paper's
  Equation 5 allows deducting a carbon price already paid in the country of
  origin; this is **not** deducted, "due to lack of consistent and comparable
  data across countries" (Section 3.3.1). When a country has no specific factor
  for a product, the regulation's rest-of-world value (`ROW` rows in the factor
  file) is used; if there is none, the cost is zero.
- **Exempt exporters** pay no CBAM cost: the 27 EU member states plus Iceland,
  Liechtenstein, Norway and Switzerland (the list `paises_isentos_cbam`, at the
  top of `07_simulacao_cbam.R`, repeated for the pie charts in
  `09_analise.R`). The United Kingdom is **not** exempt. The paper treats the
  EU countries and the exporters of Annex III of the regulation as exempt
  (Section 3.3.1).
- **New price** = base price + CBAM cost. In the Mercosul scenario the Mercosul
  exporters' base price first has the tariff removed.
- **Change in share** follows Equation 8: `base share × (exp(elasticity ×
  change in log relative price) − 1)`. The relative price is recomputed against
  the new leave-one-out average of **all** exporters, so competitors' CBAM costs
  matter too.
- **Elasticities used**: shrunk country elasticities for the focal countries and
  the global product elasticity for every other exporter.
- **Normalisation**: after simulation, shares of all exporters are rescaled so
  they sum to one within each product (market clearing, partial equilibrium;
  Section 3.3.2). This is why a loss by taxed exporters raises the share of the
  rest, including the exempt bloc.
- **Volume and value**: simulated volume = simulated share × the base total
  market of the product (held fixed). Value uses the **historical CIF price**
  without tariff, because the tariff goes to the EU treasury and the CBAM is a
  cost for the importer, not revenue lost by the exporter.
- **Sector-level share** of a country is aggregated in **volume** (sum of the
  country's volume across products over the sector's total EU volume), not by
  adding product shares.

### 3.4 Charts produced by the pipeline

Charts with one scenario use the middle carbon price and MFN. The dumbbell and
bubble charts of `09_analise.R` are drawn per focal country.

---

## 4. Input data

The model reads three pairs of files from `config/`, one per sector.

**Trade data**, `Base_de_dados_final_{Ferro,Aluminio,Cimento}.csv`
(semicolon-separated):

| Column | Meaning |
|---|---|
| `AUX` | key: exporter + product + year |
| `exporter` | ISO-2 code of the origin country |
| `product` | HS code (HS4, or HS6 for products the regulation lists at that level) |
| `year` | 2008 to 2025 (the model uses `ano_inicio` onwards) |
| `kg`, `ton` | imported volume (net kilograms and tons) |
| `euro` | imported value in euros (CIF) |
| `price` | euros per ton |
| `tariff` | effective ad valorem tariff, as a fraction |
| `dummy_eu` | 1 for the 27 EU member states and 0 otherwise; not read by any script |

**Emission factors**, `Base_fatores_{ferro,aluminio,cimento}_ajustada.csv`:
`exporter`, `product`, `description`, `base_factor`, `factor_2026`,
`factor_2027`, `factor_2028`, in tCO2e per ton of product. `ROW` is the
rest-of-world fallback.

**Product groups**, `{ferro_aco,aluminio,cimento}_grupos.R`: map each product to
a group (`grupo`, `grupo_label`). They define the groups of Annex E.

**Where the data come from** (Section 3.1 of the paper):

| Data | Source |
|---|---|
| Trade | Eurostat, "International trade of EU and non-EU countries since 2002 by HS2-4-6", downloaded in April 2026 |
| Tariffs | International Trade Centre, Market Access Map (MAcMap), May 2026; the lowest rate available to the importer (agreement, preference or MFN), and for HS4 products the simple average of the HS6 rates |
| Emission factors | Annex I of Regulation (EU) 2025/2620 (default values), with the regulation's mark-up |

The scripts that downloaded and merged these sources into the files above are
**not** in this repository; the files in `config/` are the result of that
preparation. Check the terms of the original sources before reusing them.

---

## 5. Output files

Everything is written to `outputs/<run>/`. The most useful files:

| File | Content | Used for |
|---|---|---|
| `00_sample_tracking.csv` | observations, exporters, products, years and tons after each filter | Table 1 of the paper |
| `4_betas_simulacao_cbam.csv` | per product: global elasticity (`beta_base`) and, for each focal country, its raw elasticity (`beta_X`), weight (`w_X`), simulation elasticity (`beta_sim_X`) and how it was formed (`fonte_X`) | anti-dumping test; the elasticities of the paper |
| `4c_*`, `4d_*`, `8_tabela_betas_grupos.csv` | elasticity tables by product, sector and group | source of the values shown in Figures 2 and 3 |
| `13_cbam_resumo_pais.csv` | per country, carbon price and tariff regime: base and simulated share, volume, value and changes | Figures 4 and 6 |
| `14_cbam_resumo_product.csv` | the same, per product | Figures 5 and 10 |
| `28_analise_share_vol_base.csv` | base share and volume per country and product | Figures 5 and 10 |
| `30_analise_betas.csv`, `30c_analise_beta_setor.csv` | product-level and sector elasticity with standard errors | Table 3, base model |
| `44_gof_modelo.csv` | R² of the model, of the fixed effects alone and the price contribution | Table 4 |
| `5*_validacao*` | out-of-sample and change-based validation | not in the final paper |
| `19_*` to `25_*` | cumulative projection 2026 to 2028 | not in the paper |
| `32_*` to `40_*` | standardised impact metrics, group share, emissions | extras |
| `41_*`, `43*_*` | audit of the elasticities and their stability over time | extras |

---

## 6. Replication checkpoints

If your runs reproduce these numbers, the pipeline and data are working as in
the paper. They come from a run for each sector with `PAISES = c("BR", "AR")`
and default options.

**Sample (Table 1)**

| | Exporters | Products | Observations (paper) | Observations (code) |
|---|---|---|---|---|
| Aluminium | 114 | 14 | 13,113 | **13,103** |
| Cement | 81 | 6 | 4,104 | 4,104 |
| Iron & steel | 159 | 42 | 38,726 | 38,726 |

The aluminium count differs by 10 observations (see section 8).

**Fit (Table 4)**

| | R² full model | R² fixed effects only | R² price |
|---|---|---|---|
| Aluminium | 0.906 | 0.782 | 0.123 |
| Cement | 0.916 | 0.721 | 0.195 |
| Iron & steel | 0.935 | 0.812 | 0.123 |

**Sector elasticity, base model (Table 3)**: aluminium −0.770 (se 0.227),
cement −1.309 (se 0.212), iron & steel −1.616 (se 0.394).

---

## 7. What this repository does not reproduce

These parts of the paper are **not** generated by code in this repository:

- Table 2 (panel diagnostics: RESET, Wooldridge, Hausman).
- Table 3 beyond its first row (the alternative models: OLS on the log of the
  share, price lagged one period, model without the product–year fixed effect,
  and the placebo with the future price).
- Figure 7 (histogram of relative prices) and Tables 5 to 7 (use of AI,
  alternative functional forms, HS codes and groups).
- The downloading and merging of the raw trade, tariff and emission data.

The alternative models in Table 3 and the diagnostics in Table 2 were run
outside this pipeline, so the elasticities there cannot be regenerated from
these files.

---

## 8. Known differences and limitations

1. **Clustering of standard errors.** The estimation scripts cluster two-way by
   exporter and year (`cluster = ~exporter + year`). The note under Tables 2 and
   3 of the paper says standard errors are clustered by exporter–product, and
   its footnote 7 reports robustness to clustering by exporter and to two-way
   clustering. The standard errors reproduced above (Table 3, 0.227, 0.212,
   0.394) are the ones this code produces. Check the wording against the code
   before citing either.
2. **Aluminium sample size.** Table 1 gives 13,113 observations; the code gives
   13,103 on the data in `config/`. The other two sectors match exactly, and the
   exporter and product counts match in all three. Whether this is a typo in the
   table or a difference in the data file has not been resolved.
3. **`pre_tax` is not a validated variant.** See `price_model` in section 2.1.
4. **`modo_grupo = "agregado"` is not implemented.** See section 2.1.
5. **`min_obs` does nothing.** See section 2.2.
6. **Focal countries can disappear.** A country with no exports in the base
   window has no rows in the simulation tables, and no warning is printed
   (Belarus in cement).
7. **Elasticities are short-run.** Prices enter contemporaneously only (the paper
   says so in Section 3.2.3), so the simulation does not capture slow
   adjustment.
8. **Partial equilibrium.** The market's total size is fixed; the "gain" of the
   exempt bloc in the simulation is a result of renormalising shares, not an
   estimated supply response. The emission-factor file has no EU producers, so
   the effect on emissions of the exempt bloc cannot be assessed.

# Configuration reference and methodological choices

This document explains every option of the model, every choice fixed inside the
code, what was used in the paper, and why. It is written so that the numbers
of the paper can be reproduced, and so that it is clear what changes when an
option is changed.

**Status labels used below**

- **In the paper**: the option is used in the paper, with the value shown.
- **Available**: implemented and working, but not used for the results of the
  paper.

Where a choice has a reason, it is given here together with the section of the
paper (`paper/`) that develops it.

Contents

1. [How to change an option](#1-how-to-change-an-option)
2. [Options in `main_v2.R`](#2-options-in-main_v2r)
3. [Choices fixed in the code](#3-choices-fixed-in-the-code)
4. [Input data](#4-input-data)
5. [Output files](#5-output-files)
6. [Replication checkpoints](#6-replication-checkpoints)
7. [What this repository does not reproduce](#7-what-this-repository-does-not-reproduce)
8. [Limitations](#8-limitations)

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

#### `produto_ativo` — in the paper: all three sectors, one run each
Sector to estimate: `"ferro_aco"` (iron & steel), `"aluminio"` (aluminium) or
`"cimento"` (cement). It selects the trade-data file, the emission-factor file
and the product-group mapping (`config/<sector>_grupos.R`).
The paper covers the three sectors (62 products: 42 iron & steel, 14
aluminium, 6 cement; Table 1 of the paper), and each one is estimated
separately, so there is one run per sector.

#### `paises_grupo` — in the paper: `c("BR", "AR")`
The focal countries: the ones that get their own price elasticity and are
simulated individually. Use ISO 3166 alpha-2 codes as they appear in the trade
data (`BR`, `AR`, `CN`, `RU`, ...). The focal countries of the paper are Brazil and Argentina. Any other countries
can be passed.
A country with no exports in the base window (the last `janela_base` years)
has no rows in the simulation tables, and no warning is printed. For example,
Belarus is in the cement estimation sample (19 observations) but has no cement
exports to the EU after 2022, so it does not appear in the cement simulation.

#### `nome_grupo` — available (only a label)
Free text used in the output folder name and in chart subtitles. It has no
effect on the estimation. The default is `brazil_and_argentina`.

#### `modo_grupo` — in the paper: `"individual"`
How the focal countries enter the model. The script was built to allow an
individual and an aggregated analysis. In the aggregated analysis the focal
countries would be pooled into a single artificial country, to analyse a bloc as
a whole. Only the individual analysis is implemented in this version, and it is
the one used in the paper: even for blocs, it was judged better to estimate each
country individually and analyse the results jointly. The configuration check
accepts only `"individual"`.

In individual mode **each** focal country gets its own differential from the
global elasticity, and all differentials are estimated together in one joint
model. This is Equation 3 of the paper (Section 3.2.2): the effective elasticity
of country *j* in product *p* is the global elasticity plus the country's
differential, and each differential is weighted by its own precision
(Equation 4). It is used because the question is about Brazil and Argentina **separately**:
elasticities, impacts and simulations are reported for each country (Figures 2
to 6), and a country whose differential is poorly estimated falls back on the
global elasticity without affecting the other.

#### `price_model` — in the paper: `"post_tax"`
Which price is used. With `"post_tax"` the unit price (CIF value per ton) is
multiplied by one plus the ad valorem tariff, giving the price the EU importer
actually pays. With any other value (for example `"pre_tax"`) the CIF price is
used as it is, and the tariff plays no role in the model.

The post-tax price is used (Equation 2, Section 3.2.2) because the CIF price
does not include the import duty, so the tariff is added to approximate the
effective price paid by importers (Section 3.1.2). It is also what makes the
Mercosul–EU scenario possible, because that scenario works by setting the
tariff to zero (Section 3.3.2). With `"pre_tax"` the tariff is not in the price,
so the MFN and Mercosul scenarios give the same result. This variant is not used in the paper.

#### `sufixo_output` — available (only a label)
Last part of the output folder name, default `"v2"` (the sign-constrained model,
see 3.2). It lets runs with different data cuts live side by side; the
anti-dumping test uses `"roll2015"`.

### 2.2 Sample

The filters below are applied in this order in `scripts/01_limpeza.R`, and
`outputs/<run>/00_sample_tracking.csv` records the number of observations after
each one.

#### `ano_inicio` and `ano_corte` — in the paper: 2010 and 2025
First and last year of the sample. `ano_corte` is also the end of the window
used to average base shares (see `janela_base`).
The sample is yearly data from 2010 to 2025. The data go back to 2002, but the
sample starts in 2010 so that events such as the 2008 crisis do not affect the
model (Section 3.1.1). Changing `ano_corte` moves the whole analysis; it is what the
2015 anti-dumping test does.

#### `filtro_vol` — in the paper: 1 (ton)
Observations with volume not above this value are removed. Together with a
fixed `ton >= 1` in the same line, the effect is to keep only observations
**strictly above** 1 ton at the default. Observations below 1 ton are removed because they generate exaggerated prices
that could artificially affect the estimation without any real volume behind
them (Section 3.1.4).

#### `filtro_euros` — in the paper: 0 (euro)
Observations with value not above this are removed. At 0 this only drops
observations with no value: a zero value would give a non-positive price
(Section 3.1.4).

#### `min_anos_obs` — in the paper: 5
An exporter–product pair must appear in at least this many distinct years to
stay in the sample. This is the "singleton" filter. Only exporters that sold at least 1 ton of the product to the EU in at least 5
years are kept, to exclude extreme one-off exports and to make sure there are
no singletons in the fixed-effects structure (Section 3.1.4). Together with the volume filter, this
takes the number of exporters from 235 in the raw aluminium file to the 114 of
Table 1 (81 for cement and 159 for iron & steel).

#### `share_min_pais` — available, not used (`NULL`)
If set to a number, drops exporter–product pairs whose average market share is
below it, **except** the focal countries.

#### `winsor_price_rel` — in the paper: 0.01 (top 1%)
Relative prices above the `1 - winsor_price_rel` quantile are set to that
quantile. The quantile is computed over the whole sector (all products and
years together), only on the upper tail, and on the relative price before the
logarithm. The top 1% is winsorised to limit the influence of outliers, which are
typically small or sporadic exporters (Section 3.2.2). Set it to `NULL` to turn
winsorisation off.

### 2.3 Estimation

#### `usar_peso_tempo` and `half_life` — available, not used (`FALSE`, 5)
When `usar_peso_tempo` is `TRUE`, each observation gets a weight
`exp(-ln(2) / half_life * (last year - year))`, so recent years count more and
the weight halves every `half_life` years. When `FALSE` all weights are 1, which is how the model is estimated in the
paper. The option exists to give more weight to the most recent data and reach
a standard average level of exports. It was preferred not to use it and to rely
only on the average of the last three years (`janela_base`).

#### `z_critico` — available (affects diagnostics only)
Critical value for 95% confidence intervals (1.96). It is used to draw the
confidence bars in the beta audit and stability charts and to flag significance
in the robustness comparison. It does **not** enter the shrinkage weights or the
simulation.

### 2.4 Validation

#### `ano_val_treino` and `ano_val_teste` — available
The out-of-sample validation tests whether the model performs well beyond the
estimation sample: the model is estimated with data up to a period *x* and
tries to predict the period after it. With the default values (`ano_val_treino = 2022`,
`ano_val_teste = 2025`), `04_validacao.R` re-estimates the model on data up to
2022, starts from the shares of 2022 and predicts the shares of 2025.
`04b_validacao_delta.R` tests whether the elasticities predict changes in
share: the base window is the last `janela_base` years up to `ano_val_treino`
(2020 to 2022) and the test years are 2023, 2024 and 2025. To train up to 2024
and predict 2025, set `ano_val_treino` to 2024. Both write the `5*_validacao*`
files.
The validation reported in the paper is the historical anti-dumping test
(Section 4.1, Annex F), a separate procedure
(`figuras/_teste_antidumping_2016*.py`). If you set `ANO_CORTE` through the
runner, the validation years follow it automatically.

### 2.5 Simulation

#### `janela_base` — in the paper: 3 (years)
Number of final years averaged to build base shares and base volumes
(`ano_corte - janela_base + 1` to `ano_corte`, that is 2023 to 2025). The same
window defines the volume weights used when combining product-level
elasticities into group and sector numbers. The last three years are averaged to capture the recent structural trade
pattern and avoid one-off shocks in price and volume (Section 3.3.2). The `j3` in the output folder name is this option.

#### `premissa_agregacao` — in the paper: `"media_simples"`
How emission factors are combined when the regulation is more detailed than the product level used here: simple mean (`"media_simples"`) or the maximum (`"maximo"`). The simple average of the constituent codes is used: CN8 codes inside an HS6
product, and HS6 codes inside an HS4 product (Section 3.1.3). The maximum gives
a conservative variant with higher costs.

#### `fase_cbam` — in the paper: `"factor_2026"`
Which column of the emission-factor file is the factor used in the six
scenarios. The file has `base_factor` and one column per year, `factor_2026`,
`factor_2027` and `factor_2028`, which are the base value with the regulation's
mark-up (10%, 20% and 30%; the file's ratios to the base value are exactly
1.10, 1.20 and 1.30). `factor_2026` is used in all six scenarios because it is the factor that
would apply in the short term. To use another year, change this option.

#### `cenarios_carbono` — in the paper: 75, 95 and 115 (EUR per tCO2)
The three carbon prices. The names (`baixo`, `medio`, `alto`) only appear in
labels, as `75/tCO2`, `95/tCO2`, `115/tCO2`. The 75 is anchored on the first quarterly price released by the European
Commission in 2026, and 95 and 115 are built mostly as sensitivity tests around
the forecasts for 2027 and 2028 (Section 3.3.1).
The charts that show only one scenario (the pie charts, the per-product
dumbbell and bubble charts) use the **middle** price.

#### `cenarios_tarifa` — in the paper: `"MFN"` and `"Mercosul"`
Tariff regimes crossed with the carbon prices, giving the six scenarios per
sector. In `"MFN"` each exporter keeps its tariff. In `"Mercosul"` the tariff of
the Mercosul exporters is set to zero, to represent the Mercosul–EU agreement
(Section 3.3.2).

#### `paises_mercosul` — in the paper: `BR`, `AR`, `UY`, `PY`
The exporters that lose the tariff in the Mercosul scenario. The results cover Brazil and Argentina; Uruguay and Paraguay are in the list because they are
Mercosul members, and they have no effect when they are not in the trade data.

### 2.6 Cumulative projection

#### `projecao_anos` and `projecao_precos` — available
`08_projecao_cbam.R` simulates 2026, 2027 and 2028 in sequence, each year
starting from the previous year's simulated shares, using that year's emission
factor (`factor_2026` to `factor_2028`) and carbon price (75, 95 and 115 in
`projecao_precos`; the 2025 entry is the zero-price base). The projection was
built because the emission factors are available up to 2028. It is not used in
the text of the paper, whose results are the six static, independent scenarios.
Its outputs (`19_*`, `20_*`, `21_*` to `25_*`) are extras.

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
  (`cluster = ~exporter + year`) in the estimation scripts.
- **Shrinkage** (Equation 4): the elasticity used in the simulation for focal
  country *j* is `w * (global + differential) + (1 - w) * global`, where the
  weight is `w = se_global^2 / (se_global^2 + se_differential^2)`. The
  more precisely the differential is estimated, the more it counts. If the
  differential has no standard error, `w = 0` and the global elasticity is used.
  A precision-weighted shrinkage is used so that the data decide continuously how
much country-specific information enters the simulation, with no arbitrary
significance threshold (Section 3.2.2).
- **Sign constraint (v2)**: if the shrunk elasticity of a country comes out
  **positive**, the country's own elasticity is first set to zero, so the result
  is `(1 - w) * global`, still negative but less elastic than the global
  value. With the data used here this affects only iron ore (260112) for Brazil in
  iron & steel and calcined clay (250700) for Argentina in cement. No global
  elasticity is positive (Section 3.2.3); the constraint concerns country-level
  values.
- **Sector and group elasticities** are volume-weighted averages of the
  product-level ones, with each product weighted by its share of the sector's
  imports in the base window. Groups are defined in `config/*_grupos.R` and
  correspond to Annex E of the paper.

### 3.3 Simulation (`07_simulacao_cbam.R`)

- **CBAM cost per ton** = emission factor × carbon price. No carbon price already paid in the country of origin is deducted (Equation 5
allows it), because there are no consistent and comparable data across
countries (Section 3.3.1). When a country has no specific factor for a product, the
  regulation's rest-of-world value (`ROW` rows in the factor file) is used; if
  there is none, the cost is zero.
- **Exempt exporters** pay no CBAM cost: the 27 EU member states plus Iceland,
  Liechtenstein, Norway and Switzerland (the list `paises_isentos_cbam`, at the
  top of `07_simulacao_cbam.R`, repeated for the pie charts in
  `09_analise.R`). The United Kingdom is **not** exempt (Section 3.3.1).
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

The model reads three pairs of files from `config/`, one per sector. Each
source, its version, how it was extracted and how it was treated are described in
[`DATA.md`](DATA.md).

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

| Data | Source |
|---|---|
| Trade | Eurostat, *International trade of EU and non-EU countries since 2002 by HS2-4-6* |
| Tariffs | International Trade Centre, Market Access Map (MAcMap) |
| Emission factors | Commission Implementing Regulation (EU) 2025/2621 (default values for the definitive period), with the regulation's mark-up |

The data were extracted and merged by hand, so there are no extraction scripts;
the raw downloads are not included.

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
| `5*_validacao*` | out-of-sample and change-based validation | diagnostics |
| `19_*` to `25_*` | cumulative projection 2026 to 2028 | extras |
| `32_*` to `40_*` | standardised impact metrics, group share, emissions | extras |
| `41_*`, `43*_*` | audit of the elasticities and their stability over time | extras |

---

## 6. Replication checkpoints

If your runs reproduce these numbers, the pipeline and data are working as in
the runs of the paper. They come from a run for each sector with `PAISES = c("BR", "AR")` and
default options.

**Sample (Table 1 of the paper)**

| | Exporters | Products | Observations |
|---|---|---|---|
| Aluminium | 114 | 14 | 13,103 |
| Cement | 81 | 6 | 4,104 |
| Iron & steel | 159 | 42 | 38,726 |

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

These parts of the paper are not generated by code in this repository:

- Table 2 (panel diagnostics: RESET, Wooldridge, Hausman).
- Table 3 beyond its first row (the alternative models: OLS on the log of the
  share, price lagged one period, model without the product–year fixed effect,
  and the placebo with the future price).
- Figure 7 (histogram of relative prices) and Tables 5 to 7 (use of AI,
  alternative functional forms, HS codes and groups).
- The downloading and merging of the raw trade, tariff and emission data (done
  by hand).

---

## 8. Limitations

1. **Focal countries can disappear.** A country with no exports in the base
   window has no rows in the simulation tables, and no warning is printed
   (Belarus in cement).
2. **Elasticities are short-run.** Prices enter contemporaneously only
   (Section 3.2.3), so the simulation does not capture slow adjustment.
3. **Partial equilibrium.** The market's total size is fixed; the "gain" of the
   exempt bloc in the simulation is a result of renormalising shares, not an
   estimated supply response.

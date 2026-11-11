# Data sources

This document says where each number in `config/` comes from, how it was obtained and treated before it reached this repository, and what the code does with it
afterwards. Section 3.1 of the paper (`paper/`) develops the same material.

Contents

1. [At a glance](#1-at-a-glance)
2. [Trade data](#2-trade-data)
3. [Tariff data](#3-tariff-data)
4. [Emission factors](#4-emission-factors)
5. [Product scope](#5-product-scope)
6. [Carbon price scenarios](#6-carbon-price-scenarios)
7. [From the sources to the files in `config/`](#7-from-the-sources-to-the-files-in-config)
8. [Limitations of the data](#8-limitations-of-the-data)
9. [What is not in this repository](#9-what-is-not-in-this-repository)
10. [References](#10-references)

---

## 1. At a glance

| Data | Provider | Database or document | Version and access |
|---|---|---|---|
| Bilateral trade: volume and value of EU imports by origin, product and year | Eurostat | *International trade of EU and non-EU countries since 2002 by HS2-4-6* (dataset `ds-059341`) | Dataset dated 17 April 2026; extracted in April 2026 (Section 3.1.1); reference accessed 24 May 2026 |
| Import tariffs: effective ad valorem rate by origin, product and year | International Trade Centre (ITC) | Market Access Map (MAcMap), <https://www.macmap.org/> | Extracted in May 2026 (Section 3.1.2); reference accessed 1 May 2026 |
| Embedded-emission default values | European Union | Commission Implementing Regulation (EU) 2025/2621 of 29 December 2025, default values for the definitive period | Accessed 7 June 2026 |
| Product list | European Union | Annex I of Regulation (EU) 2023/956 (the CBAM Regulation) | Accessed 24 May 2026 |
| Carbon price scenarios | European Commission; Reuters; ABN AMRO | see section 6 | see section 6 |

The three sector files in `config/` combine the first two rows (trade and
tariffs). The emission-factor files come from the third. The fourth defines which
products enter. The fifth is not a file: the carbon prices are options in
`main_v2.R`.

---

## 2. Trade data

**Source.** Eurostat, *International trade of EU and non-EU countries since
2002 by HS2-4-6* (`ds-059341`), the Eurostat database of EU trade by
Harmonised System (HS) product and partner country. Link:
<https://ec.europa.eu/eurostat/databrowser/product/view/ds-059341?category=ext_go.ext_go_detail>.

**What was taken** (Section 3.1.1):

- **Quantity**: net weight of imports, in kilograms.
- **Value**: value of imports, in euros.
- **Dimensions**: origin country (called *exporter* in the files), product (HS
  code) and year.
- **Period**: the database starts in 2002. The files here cover **2008 to
  2025**, and the analysis uses **2010 to 2025** (`ano_inicio`, `ano_corte`).
  The sample starts in 2010 so that the 2008 crisis does not affect the model.
- **Products**: the 62 products of the CBAM Regulation in the three sectors,
  at the HS4 level for most and the HS6 level for the products the Regulation
  lists that way (section 5).
- **Origins**: more than 200 countries and territories. **Intra-EU flows are
  kept**, because shifts of trade inside the bloc are a possible outcome of CBAM.
  This is why the EU member states appear as exporters in the files.

**Price.** Value divided by quantity, in euros per ton. The values are **CIF**
(cost, insurance and freight), so the price already carries freight and
insurance, which are treated as the gravity-model "frictions" other than tariffs
(Section 3.1.1). Tariffs are **not** included in the trade value; they
are added by the model (see `price_model` in `CONFIGURATION.md`).

**Market share.** Built from the data: volume of an exporter in a product and
year divided by total EU imported volume of that product in that year
(Section 3.1.1). It is the dependent variable of the model.

**Missing data.** Observations without data are not in the Eurostat download
(Section 3.1.4). Further filters (no tariff, non-positive price, less than 1 ton,
fewer than 5 years) are applied in the code and are described in
`CONFIGURATION.md`, section 2.2.

**Also cited, not a model input.** Eurostat's *Extra-EU trade by partner*
(`ext_lt_maineu`, dated 19 March 2026, accessed 27 May 2026) appears in the
introduction of the paper as the source of the total trade of Brazil and
Argentina with the EU in 2025 (87.1 and 17.4 billion). It is context for the
paper and is not read by any script.

---

## 3. Tariff data

**Source.** ITC Market Access Map, <https://www.macmap.org/> (Section 3.1.2).

**What was taken.**

- The **effective ad valorem tariff** applied by the EU to each origin, product
  and year.
- It is the **lowest rate available** to the importer, whether it comes from a
  trade agreement, a preference scheme or the base Most-Favoured-Nation (MFN)
  rate.
- For products defined at the HS4 level, the tariff is the **simple average of
  the HS6 codes** that compose it.
- It is stored as a fraction (a 3.7% tariff is `0.037`).

**Use in the model.** The tariff turns the CIF price into an approximation of the
price the EU importer actually pays, because the CIF value does not include the
import duty (Section 3.1.2). It is also what the Mercosul scenario removes.

**Gaps.** Tariff availability varies across origins and years. Origins with no
tariff data are excluded, because without it the effective price cannot be
built (Section 3.1.4).

**Terms of use.** The tariff series is redistributed in this repository as part
of the `tariff` column. Check the ITC terms for Market Access Map before
reusing it.

---

## 4. Emission factors

**Source.** Commission Implementing Regulation (EU) 2025/2621 of 29 December
2025, which establishes the default values for the definitive period of the
CBAM. The Commission publishes the values at
<https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-legislation-and-guidance_en>.

**What the values are** (Section 3.1.3):

- Embedded emissions, in **tonnes of CO2 equivalent per tonne of product**,
  covering direct emissions (scope 1) and the emissions from the energy used in
  production (scope 2).
- They are **specific to each product and country of origin** for the main
  exporting countries. For other origins the Regulation gives a **fallback
  value**, set so that emissions are not underestimated. In the file this is the
  `ROW` row.
- They were determined from data collected during the transitional period
  (2023 to 2025). They apply when the importer does not submit verified
  installation-level emissions, and are treated as an approximation of real emissions.
- The Regulation adds a **mark-up** to the 2025 baseline values, rising by 10
  percentage points a year: **10% in 2026, 20% in 2027, 30% in 2028**. A review
  of the whole system is foreseen for 2027.
- They are published at the **CN8 level** (HS6 plus two national digits).

**How they were adapted.** Where the Regulation is more detailed than the
product level of the analysis, the factor is the simple average of the
constituent codes: CN8 codes inside an HS6 product, HS6 codes inside an HS4
product.

**What is in the file.** `Base_fatores_*_ajustada.csv` has one row per
exporter, product and regulation line, with the columns `base_factor` (2025
value) and `factor_2026`, `factor_2027`, `factor_2028` (with the mark-up; the
file's ratios to the base value are 1.10, 1.20 and 1.30). A product can have
several rows per exporter, one for each regulation line under it (for example
the several ferro-alloys inside HS 7202). The code averages them to one value
per exporter and product (`premissa_agregacao = "media_simples"`). The file does
not contain the EU member states: they are treated as having a zero factor in
the code.

**Which factor is used.** In the six scenarios `factor_2026` is used, the base
value with the 2026 mark-up (`fase_cbam`), because it is the factor that would
apply in the short term.

**No deduction of carbon already paid.** The Regulation lets importers deduct a
carbon price already paid in the country of origin. This is not applied, because there are no consistent and comparable data across countries
(Section 3.3.1).

---

## 5. Product scope

The products are those of **Annex I of Regulation (EU) 2023/956** in the three
sectors (Section 3.1.1), in total **62**:

| Sector | Products | HS chapters |
|---|---|---|
| Iron & steel | 42 | 72, 73 and iron ore (HS 2601) |
| Aluminium | 14 | 76 |
| Cement | 6 | 25 |

Most are identified at the HS4 level; the products the Regulation lists more
finely are kept at HS6 (for example `260112`, `730300`, `252310`, `250700`). The
complete list, with descriptions and the product group of each, is in Annex E of
the paper. The groups are coded in `config/*_grupos.R`.

---

## 6. Carbon price scenarios

The three carbon prices (EUR per tonne of CO2) are options in `main_v2.R`
(`cenarios_carbono`), not files. They are anchored as follows (Section 3.3.1):

| Scenario | Value | Anchor |
|---|---|---|
| Low | 75 | First quarterly CBAM certificate price released by the European Commission in 2026 (*Price of CBAM certificates*, 6 May 2026) |
| Middle | 95 | Sensitivity test around the forecast for 2027 (Reuters, 30 January 2026; Altaghlibi and Gentile, ABN AMRO, 16 September 2025) |
| High | 115 | Sensitivity test around the forecast for 2028 (same sources) |

One average price per year is used, because the analysis is yearly. The
Commission publishes the certificate price quarterly in 2026 and weekly from
2027.

---

## 7. From the sources to the files in `config/`

### Trade files: `Base_de_dados_final_{Ferro,Aluminio,Cimento}.csv`

Semicolon-separated; one row per exporter, product and year.

| Column | Content | Check |
|---|---|---|
| `AUX` | key made of exporter code, product and year | |
| `exporter` | ISO 3166 alpha-2 code of the origin | |
| `product` | HS code (HS4, or HS6 for the finer products) | |
| `year` | 2008 to 2025 | |
| `kg` | net weight in kilograms | |
| `euro` | value in euros (CIF) | |
| `ton` | volume in tons | equals `kg / 1000` in all rows but four (iron & steel) |
| `price` | euros per ton | equals `euro / ton` in every row with volume |
| `tariff` | effective ad valorem tariff, as a fraction | 0 to 0.08125 |
| `dummy_eu` | 1 for the 27 EU member states | not read by any script |

| Sector | Rows | Exporters | Products |
|---|---|---|---|
| Iron & steel | 58,987 | 240 | 42 |
| Aluminium | 21,636 | 235 | 14 |
| Cement | 6,836 | 174 | 6 |

The first line of the cement file writes the key column as `aux` in lower case
and the other files as `AUX`; no script reads it.

### Emission-factor files: `Base_fatores_{ferro,aluminio,cimento}_ajustada.csv`

| Sector | Rows | Origins (including `ROW`) | Products |
|---|---|---|---|
| Iron & steel | 6,452 | 48 | 42 |
| Aluminium | 1,628 | 68 | 14 |
| Cement | 338 | 101 | 6 |

### Group files: `*_grupos.R`

Map each product to a group and give the group a label. The groups correspond to
those of Annex E of the paper (the labels are worded slightly differently).

### Where treatment happens

| Treatment | Where |
|---|---|
| Intra-EU flows kept, volume and value taken from Eurostat | by hand, before this repository |
| Effective tariff, with the HS4 average of the HS6 rates | by hand, before this repository (column `tariff`) |
| Emission factors expressed at CN8 or finer lines, with the mark-up columns | by hand, before this repository |
| Averaging of the emission-factor lines to one value per exporter and product | the code, `07_simulacao_cbam.R` (`premissa_agregacao`) |
| Filters on year, volume, value, tariff and years of presence | the code, `01_limpeza.R` |
| Price with tariff, relative price, market share | the code, `01_limpeza.R` |
| Winsorisation of the relative price | the code, `01_limpeza.R` |

---

## 8. Limitations of the data

- **Tariff gaps.** Tariff data are not available for every origin and year, which
  is why origins without them are dropped (Section 3.1.2 and 3.1.4).
- **Default values are an approximation.** They are not installation-level
  emissions, and they carry a mark-up that the EU may revise after the 2027
  review (Section 3.1.3).
- **Aggregation.** Products are grouped at HS4 or HS6 level, so there is
  heterogeneity inside them. An exporter's average price can move because of a
  change in the mix of products, not only because of a price change
  (Section 3.2.3).
- **Short sample.** The analysis covers 2010 to 2025 only, by design.
- **No foreign carbon price deduction.** See section 4.

---

## 9. What is not in this repository

- **Extraction and merging scripts.** The files in `config/` are the result of
  preparing the sources above. The Eurostat and MAcMap data were downloaded and
  merged with the emission factors by hand, so there are no extraction scripts.
- **The raw downloads.** Neither the Eurostat nor the MAcMap original files are
  included.
- **A single combined source.** Each source is updated by its provider over
  time. The versions in section 1 are the ones used for the paper; a new download
  can produce slightly different numbers.

To rebuild the files, start from the sources in section 1, apply the treatments
of sections 2 to 4, and compare the result with the descriptive numbers in
section 7 and with Table 1 of the paper.

**Terms of use.** Each provider has its own terms. This repository includes
processed series derived from Eurostat, MAcMap and the Commission's default
values; check the terms of each before reusing or redistributing them.

---

## 10. References

References for the data sources, as in the paper.

- EUROPEAN UNION. *Regulation (EU) 2023/956* (CBAM Regulation). 10 May 2023.
  <https://eur-lex.europa.eu/eli/reg/2023/956/oj>. Accessed 24 May 2026.
- EUROPEAN UNION. *Commission Implementing Regulation (EU) 2025/2621*
  (default values). 29 December 2025. Published with the CBAM legislation and
  guidance of the European Commission,
  <https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-legislation-and-guidance_en>.
  Accessed 7 June 2026.
- EUROSTAT. *International trade of EU and non-EU countries since 2002 by
  HS2-4-6* (ds-059341). 17 April 2026.
  <https://ec.europa.eu/eurostat/databrowser/product/view/ds-059341?category=ext_go.ext_go_detail>.
  Accessed 24 May 2026.
- EUROSTAT. *Extra-EU trade by partner* (ext_lt_maineu). 19 March 2026.
  <https://ec.europa.eu/eurostat/databrowser/view/ext_lt_maineu/default/table?lang=en&category=ext_go.ext_go_agg.ext_go_lti.ext_go_lti_ext>.
  Accessed 27 May 2026.
- INTERNATIONAL TRADE CENTRE (ITC). *Market Access Map: improving transparency
  in international trade and market access*. <https://www.macmap.org/>.
  Accessed 1 May 2026.
- EUROPEAN COMMISSION. *Price of CBAM certificates*. 6 May 2026.
  <https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/price-cbam-certificates_en>.
  Accessed 6 June 2026.
- TWIDALE, Susanna. *Analyst EU carbon price forecasts edge up in volatile start
  to the year*. Reuters, 30 January 2026.
  <https://www.reuters.com/sustainability/climate-energy/analyst-eu-carbon-price-forecasts-edge-up-volatile-start-year-2026-01-30/>.
- ALTAGHLIBI, Moutaz; GENTILE, Giovanni. *Scenarios shaping EU ETS prices*.
  ABN AMRO, 16 September 2025.
  <https://www.abnamro.com/research/en/our-research/esg-economist-scenarios-shaping-eu-ets-prices>.
  Accessed 7 June 2026.

############################################
# extrair_dashboard.R
# ----------------------------------------
# Consolidates the results of the 3 "cesta_padrao" runs
# (ferro_aco, aluminio, cimento) into a single JSON file to
# feed an interactive HTML dashboard.
#
# Does NOT re-run the PPML model/simulation (heavy). It only reuses
# 01_limpeza.R (generic cleaning, independent of paises_grupo
# when share_min_pais = NULL) to rebuild the cleaned "df"
# and compute the pie block (basket / EU-EEA-CH / Others),
# which the official pipeline does not save to CSV.
############################################

pkgs <- c("tidyverse", "jsonlite")
for (p in pkgs) if (!require(p, character.only = TRUE)) install.packages(p)
invisible(lapply(pkgs, library, character.only = TRUE))

dir_scripts <- "scripts"
dir_config  <- "config"

paises_isentos_cbam <- c(
  "AT","BE","BG","CY","CZ","DE","DK","EE","ES","FI",
  "FR","GR","HR","HU","IE","IT","LT","LU","LV","MT",
  "NL","PL","PT","RO","SE","SI","SK",
  "IS","LI","NO","CH"
)

setores <- list(
  ferro_aco = list(
    paises = c("RU","UA","BR","CA","CN","TR","GB","IN","KR","TW","AR"),
    dir_out = "outputs/ferro_aco_cesta_padrao_individual_post_tax_j3_v2",
    label = "Iron & Steel"
  ),
  aluminio = list(
    paises = c("RU","CN","GB","MZ","AE","TR","BH","IN","CA","EG","BR","AR"),
    dir_out = "outputs/aluminio_cesta_padrao_individual_post_tax_j3_v2",
    label = "Aluminium"
  ),
  cimento = list(
    paises = c("TR","UA","GB","BR","US","DZ","CN","EG","TN","BY","AR"),
    dir_out = "outputs/cimento_cesta_padrao_individual_post_tax_j3_v2",
    label = "Cement"
  )
)

# Fixed config from main_v2.R (independent of paises_grupo)
ano_inicio <- 2010
ano_corte  <- 2025
filtro_vol <- 1
filtro_euros <- 0
min_anos_obs <- 5
share_min_pais <- NULL
price_model <- "post_tax"
winsor_price_rel <- 0.01
janela_base <- 3
anos_base <- seq(ano_corte - janela_base + 1, ano_corte)

# the "registrar" function is used inside 01_limpeza.R (tracking), no-op stub
registrar <- function(...) invisible(NULL)

resultado_geral <- list()

for (nome_setor in names(setores)) {

  cfg <- setores[[nome_setor]]
  produto_ativo <- nome_setor
  paises_grupo  <- cfg$paises

  cat("== ", nome_setor, " ==\n")

  # ---- 0. Product group labels (config/<sector>_grupos.R) ----
  grupo_map <- NULL
  source(file.path(dir_config, paste0(nome_setor, "_grupos.R")), encoding = "UTF-8")
  produto_labels <- setNames(as.list(grupo_map$grupo_label), grupo_map$product)

  # ---- 1. Rebuild the cleaned df (identical to the one used in the official pipeline) ----
  source(file.path(dir_scripts, "01_limpeza.R"))

  # ---- 2. Base ton by exporter (annual mean, 2023-2025 window) ----
  ton_base_exportador <- df %>%
    filter(year %in% anos_base) %>%
    group_by(exporter) %>%
    summarise(ton = sum(ton, na.rm = TRUE) / length(anos_base), .groups = "drop")

  ton_mercado_total <- sum(ton_base_exportador$ton)

  categorizar <- function(exp) {
    case_when(
      exp %in% paises_grupo        ~ exp,
      exp %in% paises_isentos_cbam ~ "UE_EEE_CH",
      TRUE                         ~ "Outros"
    )
  }

  base_categ <- ton_base_exportador %>%
    mutate(categoria = categorizar(exporter)) %>%
    group_by(categoria) %>%
    summarise(ton = sum(ton, na.rm = TRUE), .groups = "drop") %>%
    mutate(share_pct = ton / sum(ton) * 100)

  # fixed base ton for EU/Others (also used in the simulated scenarios)
  ton_ue_base     <- base_categ$ton[base_categ$categoria == "UE_EEE_CH"]
  ton_outros_base <- base_categ$ton[base_categ$categoria == "Outros"]
  if (length(ton_ue_base) == 0) ton_ue_base <- 0
  if (length(ton_outros_base) == 0) ton_outros_base <- 0

  # ---- 3. Read summary by country x scenario (13_cbam_resumo_pais.csv) ----
  resumo_pais <- read.csv(file.path(cfg$dir_out, "13_cbam_resumo_pais.csv"),
                           stringsAsFactors = FALSE)
  emissoes    <- read.csv(file.path(cfg$dir_out, "40_emissoes_resumo.csv"),
                           stringsAsFactors = FALSE)
  gof         <- read.csv(file.path(cfg$dir_out, "44_gof_modelo.csv"),
                           stringsAsFactors = FALSE)
  produtos_raw <- read.csv(file.path(cfg$dir_out, "39b_emissoes_impacto.csv"),
                            stringsAsFactors = FALSE)

  resumo_pais <- resumo_pais %>%
    left_join(
      emissoes %>% select(exporter, cenario_carbono, cenario_tarifa,
                           delta_emissoes_pct, delta_emissoes_total),
      by = c("exporter", "cenario_carbono", "cenario_tarifa")
    )

  cenarios <- resumo_pais %>%
    distinct(cenario_carbono, cenario_tarifa) %>%
    arrange(cenario_carbono, cenario_tarifa)

  # ---- 4. Simulated pie by scenario ----
  pizza_por_cenario <- pmap(cenarios, function(cenario_carbono, cenario_tarifa) {
    linha <- resumo_pais %>%
      filter(cenario_carbono == !!cenario_carbono, cenario_tarifa == !!cenario_tarifa)

    categs_grupo <- linha %>%
      transmute(categoria = exporter, ton = ton_sim_total)

    categs <- bind_rows(
      categs_grupo,
      tibble(categoria = "UE_EEE_CH", ton = ton_ue_base),
      tibble(categoria = "Outros",    ton = ton_outros_base)
    ) %>%
      mutate(share_pct = ton / sum(ton) * 100)

    list(
      cenario_carbono = as.character(cenario_carbono),
      cenario_tarifa  = as.character(cenario_tarifa),
      categorias = setNames(as.list(round(categs$share_pct, 4)), categs$categoria)
    )
  })

  # ---- 5. Build list by country x scenario for the dashboard ----
  paises_dados <- resumo_pais %>%
    transmute(
      exporter, cenario_carbono = as.character(cenario_carbono),
      cenario_tarifa = as.character(cenario_tarifa),
      preco_carbono_eur, share_base_pct = share_base_total * 100,
      share_sim_pct = share_sim_total * 100,
      delta_share_pp = delta_share_pp_total * 100,
      variacao_relativa_pct, delta_ton_pct, delta_euro_pct,
      delta_emissoes_pct,
      ton_base_total, euro_base_total
    )

  # ---- 6. Product detail (drill-down by country) ----
  produtos_dados <- produtos_raw %>%
    transmute(
      exporter, product = as.character(product),
      grupo_label = map_chr(as.character(product), function(p) {
        val <- produto_labels[[p]]
        if (is.null(val)) "Outro" else val
      }),
      cenario_carbono = as.character(cenario_carbono),
      cenario_tarifa  = as.character(cenario_tarifa),
      share_base_pct  = share_base * 100,
      share_sim_pct   = share_simulado * 100,
      delta_share_pp  = delta_share_pp * 100,
      delta_ton_pct   = if_else(ton_base > 0, delta_ton / ton_base * 100, NA_real_),
      delta_euro_pct  = if_else(euro_base > 0, delta_euro / euro_base * 100, NA_real_),
      delta_emissoes_pct = if_else(emissoes_base_tco2 > 0,
                                    delta_emissoes_tco2 / emissoes_base_tco2 * 100, NA_real_),
      fator_emissao, beta_usado, ton_base
    )

  # ---- 7. Pure reallocation (fixed technology) x green technology ----
  realoc_cesta <- produtos_raw %>%
    group_by(cenario_carbono, cenario_tarifa) %>%
    summarise(
      emissoes_base = sum(emissoes_base_tco2, na.rm = TRUE),
      emissoes_sim  = sum(emissoes_sim_tco2,  na.rm = TRUE),
      ton_base_tot  = sum(ton_base,      na.rm = TRUE),
      ton_sim_tot   = sum(ton_simulado,  na.rm = TRUE),
      intens_antes  = sum(fator_emissao * ton_base,     na.rm = TRUE) / ton_base_tot,
      intens_depois = sum(fator_emissao * ton_simulado, na.rm = TRUE) / ton_sim_tot,
      .groups = "drop"
    ) %>%
    transmute(
      cenario_carbono = as.character(cenario_carbono),
      cenario_tarifa  = as.character(cenario_tarifa),
      delta_emissoes_pct = (emissoes_sim - emissoes_base) / emissoes_base * 100,
      intens_antes, intens_depois,
      delta_intens_pct = (intens_depois - intens_antes) / intens_antes * 100
    )

  paises_greening <- produtos_raw %>%
    group_by(exporter, cenario_carbono, cenario_tarifa) %>%
    summarise(
      fator_emissao_pond = sum(fator_emissao * ton_base, na.rm = TRUE) / sum(ton_base, na.rm = TRUE),
      beta_pond           = sum(beta_usado   * ton_base, na.rm = TRUE) / sum(ton_base, na.rm = TRUE),
      .groups = "drop"
    ) %>%
    mutate(cenario_carbono = as.character(cenario_carbono),
           cenario_tarifa  = as.character(cenario_tarifa)) %>%
    left_join(
      paises_dados %>% select(exporter, cenario_carbono, cenario_tarifa, delta_share_pp, share_base_pct),
      by = c("exporter", "cenario_carbono", "cenario_tarifa")
    ) %>%
    filter(!is.na(fator_emissao_pond), !is.na(delta_share_pp))

  correlacoes <- paises_greening %>%
    group_by(cenario_carbono, cenario_tarifa) %>%
    summarise(
      r = suppressWarnings(as.numeric(cor(fator_emissao_pond, delta_share_pp))),
      n = n(),
      .groups = "drop"
    )

  resultado_geral[[nome_setor]] <- list(
    label = cfg$label,
    paises_grupo = paises_grupo,
    isentos_cbam = paises_isentos_cbam,
    ton_mercado_total = ton_mercado_total,
    pizza_base = setNames(as.list(round(base_categ$share_pct, 4)), base_categ$categoria),
    pizza_simulada = pizza_por_cenario,
    gof = list(
      r2_fe_only = gof$r2_fe_only[1],
      r2_total = gof$r2_total[1],
      r2_price_marginal = gof$r2_price_marginal[1],
      n_obs = gof$n_obs[1],
      n_produtos = gof$n_produtos[1]
    ),
    paises = paises_dados,
    produtos = produtos_dados,
    realocacao = list(
      cesta = realoc_cesta,
      paises = paises_greening,
      correlacoes = correlacoes
    )
  )
}

write_json(resultado_geral, "dashboard_data.json", auto_unbox = TRUE, pretty = TRUE, na = "null")
cat("\nSaved: dashboard_data.json\n")

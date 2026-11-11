############################################
# 07_simulacao_cbam.R
# ----------------------------------------
# Simulation of the CBAM impact on the
# market share of the countries in paises_grupo.
#
# Produces 6 scenarios = 3 carbon price levels
# × 2 regimes de tarifa (MFN | Mercosul).
#
# Competitive normalisation:
#   simulated shares of ALL exporters
#   are normalised by product so that they sum to 1.
#   - paises_grupo: uses beta_sim (shrinkage)
#   - others:       use beta_base (global)
#   Guarantees accounting and economic consistency:
#   if BR gains share, someone loses.
#
# Depende de: 01_limpeza.R, 02_modelo.R,
#             03_paises.R
############################################

cat("[ 07 ] CBAM simulation — 6 scenarios...\n")

# ── Countries exempt from CBAM (cost = 0) ───────────────────────────────────────
paises_isentos_cbam <- c(
  "AT","BE","BG","CY","CZ","DE","DK","EE","ES","FI",
  "FR","GR","HR","HU","IE","IT","LT","LU","LV","MT",
  "NL","PL","PT","RO","SE","SI","SK",
  "IS","LI","NO","CH"
)

# ── 1. Load emission factors — all countries ─────────────────────────

arquivo_fatores <- switch(produto_ativo,
                          "aluminio"  = file.path(dir_config, "Base_fatores_aluminio_ajustada.csv"),
                          "ferro_aco" = file.path(dir_config, "Base_fatores_ferro_ajustada.csv"),
                          "cimento"   = file.path(dir_config, "Base_fatores_cimento_ajustada.csv"),
                          stop("produto_ativo invalido: ", produto_ativo)
)

fatores_raw <- read.csv(file = arquivo_fatores, header = TRUE, sep = ";") %>%
  mutate(
    product     = as.character(product),
    base_factor = as.numeric(base_factor),
    factor_2026 = as.numeric(factor_2026),
    factor_2027 = as.numeric(factor_2027),
    factor_2028 = as.numeric(factor_2028)
  )

fn_agregar <- if (premissa_agregacao == "maximo") max else mean

# ROW factor by product (fallback)
fatores_row <- fatores_raw %>%
  filter(exporter == "ROW", !is.na(.data[[fase_cbam]])) %>%
  group_by(product) %>%
  summarise(fator_row = fn_agregar(.data[[fase_cbam]], na.rm = TRUE),
            .groups = "drop")

# Aggregated factors by country × product (all countries)
fatores_todos <- fatores_raw %>%
  filter(exporter != "ROW", !is.na(.data[[fase_cbam]])) %>%
  group_by(exporter, product) %>%
  summarise(fator_emissao = fn_agregar(.data[[fase_cbam]], na.rm = TRUE),
            .groups = "drop")

# ── 2. Model pairs with factors (paises_grupo only) ────────────────────────────

pares_modelo <- df %>%
  filter(exporter %in% paises_grupo) %>%
  distinct(exporter, product)

produtos_grupo <- unique(pares_modelo$product)

fatores_grupo <- pares_modelo %>%
  left_join(fatores_todos, by = c("exporter", "product")) %>%
  left_join(fatores_row,   by = "product") %>%
  mutate(
    fonte_fator   = case_when(
      !is.na(fator_emissao) ~ "especifico",
      !is.na(fator_row)     ~ "ROW",
      TRUE                  ~ "ausente"
    ),
    fator_emissao = coalesce(fator_emissao, fator_row)
  ) %>%
  select(-fator_row)

registrar(fatores_grupo, "07", "10. model pairs with emission factor",
          note = paste0(
            "specific: ", sum(fatores_grupo$fonte_fator == "especifico"),
            " | ROW: ",     sum(fatores_grupo$fonte_fator == "ROW"),
            " | missing: ", sum(fatores_grupo$fonte_fator == "ausente")
          ))

cat(sprintf(
  "  Fatores grupo — especifico: %d | ROW: %d | ausente: %d\n",
  sum(fatores_grupo$fonte_fator == "especifico"),
  sum(fatores_grupo$fonte_fator == "ROW"),
  sum(fatores_grupo$fonte_fator == "ausente")
))

# ── 3. Function: compute delta_log_price ──────────────────────────────────────
# Returns delta_log_price for ALL exporters in the panel
# (not only paises_grupo), needed for competitive normalisation.

calcular_price_rel_2026 <- function(cenario_tarifa, fase, preco_co2) {
  
  fatores_fase <- fatores_raw %>%
    filter(exporter != "ROW", !is.na(.data[[fase]])) %>%
    group_by(exporter, product) %>%
    summarise(fator = fn_agregar(.data[[fase]], na.rm = TRUE),
              .groups = "drop")
  
  fatores_row_fase <- fatores_raw %>%
    filter(exporter == "ROW", !is.na(.data[[fase]])) %>%
    group_by(product) %>%
    summarise(fator_row = fn_agregar(.data[[fase]], na.rm = TRUE),
              .groups = "drop")
  
  df_base <- df %>%
    filter(year %in% anos_base,
           product %in% produtos_grupo,
           !is.na(ton), !is.na(price)) %>%
    group_by(exporter, product) %>%
    summarise(
      price         = weighted.mean(price,        ton, na.rm = TRUE),
      tariff        = weighted.mean(tariff,        ton, na.rm = TRUE),
      log_price_rel = weighted.mean(log_price_rel, ton, na.rm = TRUE),
      ton           = mean(ton, na.rm = TRUE),
      .groups = "drop"
    ) %>%
    left_join(fatores_fase,     by = c("exporter", "product")) %>%
    left_join(fatores_row_fase, by = "product") %>%
    mutate(
      fator_final = coalesce(fator, fator_row),
      custo_cbam  = case_when(
        exporter %in% paises_isentos_cbam ~ 0,
        is.na(fator_final)                ~ 0,
        TRUE                              ~ fator_final * preco_co2
      ),
      preco_base_2026 = case_when(
        # the tariff is only in the price when price_model is "post_tax"
        cenario_tarifa == "Mercosul" & exporter %in% paises_mercosul &
          price_model == "post_tax" ~
          price / (1 + tariff),
        TRUE ~ price
      ),
      preco_2026 = preco_base_2026 + custo_cbam
    ) %>%
    filter(!is.na(preco_2026))
  
  # Totals by product (all exporters)
  df_total_produto <- df_base %>%
    group_by(product) %>%
    summarise(
      ton_total_2026  = sum(ton,              na.rm = TRUE),
      euro_total_2026 = sum(preco_2026 * ton, na.rm = TRUE),
      .groups = "drop"
    )
  
  # Totals by country × product
  df_total_pais <- df_base %>%
    group_by(exporter, product) %>%
    summarise(
      ton_pais        = sum(ton,              na.rm = TRUE),
      euro_pais_2026  = sum(preco_2026 * ton, na.rm = TRUE),
      preco_pais_2026 = weighted.mean(preco_2026,    ton, na.rm = TRUE),
      log_pr_2025     = weighted.mean(log_price_rel, ton, na.rm = TRUE),
      .groups = "drop"
    )
  
  # LOO for ALL exporters
  todos_exportadores <- unique(df_total_pais$exporter)
  
  resultado <- map_dfr(todos_exportadores, function(pais) {
    df_total_pais %>%
      filter(exporter == pais) %>%
      left_join(df_total_produto, by = "product") %>%
      left_join(
        df_total_pais %>%
          filter(exporter == pais) %>%
          select(product, ton_pais_loo = ton_pais,
                 euro_pais_loo = euro_pais_2026),
        by = "product"
      ) %>%
      mutate(
        ton_loo_2026       = ton_total_2026  - ton_pais_loo,
        euro_loo_2026      = euro_total_2026 - euro_pais_loo,
        price_avg_loo_2026 = if_else(
          ton_loo_2026 > 0,
          euro_loo_2026 / ton_loo_2026,
          NA_real_
        ),
        price_rel_2026  = preco_pais_2026 / price_avg_loo_2026,
        delta_log_price = log(price_rel_2026) - log_pr_2025,
        exporter        = pais
      ) %>%
      filter(!is.na(delta_log_price)) %>%
      select(exporter, product,
             preco_pais_2026, price_avg_loo_2026,
             log_price_rel_2025 = log_pr_2025,
             price_rel_2026, delta_log_price)
  })
  
  resultado
}

# ── 4. Reference shares — ALL exporters ──────────────────────────

anos_base <- seq(ano_corte - janela_base + 1, ano_corte)

# Shares for paises_grupo (with specific beta_sim)
shares_ref_grupo <- df %>%
  filter(year %in% anos_base, exporter %in% paises_grupo) %>%
  group_by(exporter, product) %>%
  summarise(share_base = mean(share, na.rm = TRUE), .groups = "drop")

# Shares for all exporters (for normalisation)
shares_ref_todos <- df %>%
  filter(year %in% anos_base, product %in% produtos_grupo) %>%
  group_by(exporter, product) %>%
  summarise(share_base = mean(share, na.rm = TRUE), .groups = "drop")

# Keeps shares_ref for compatibility with 08
shares_ref <- shares_ref_grupo

registrar(shares_ref_todos, "07", "11. reference shares (all exporters)",
          note = paste0("window: ", paste(anos_base, collapse = "-")))

cat(sprintf("  Reference shares: mean of %d year(s) (%d–%d)\n",
            janela_base, min(anos_base), max(anos_base)))
cat(sprintf("  Exporters with base share: %d\n",
            n_distinct(shares_ref_todos$exporter)))

# ── 5. Betas in long format (paises_grupo) ──────────────────────────────────

betas_long <- map_dfr(paises_grupo, function(cod) {
  betas_simulacao %>%
    select(
      product,
      beta_sim   = all_of(paste0("beta_sim_", cod)),
      fonte_beta = all_of(paste0("fonte_",    cod))
    ) %>%
    mutate(exporter = cod)
})

# ── 6. Compute impact — 6-scenario grid with normalisation ───────────────────

grid_cenarios <- expand_grid(
  nome_carbono = names(cenarios_carbono),
  tarifa       = cenarios_tarifa
)

resultados_cenarios <- pmap_dfr(grid_cenarios, function(nome_carbono, tarifa) {
  
  preco_co2 <- cenarios_carbono[nome_carbono]
  
  # delta_log_price for all exporters
  price_rel_todos <- calcular_price_rel_2026(tarifa, fase_cbam, preco_co2)
  
  # beta_base by product (for the rest of the world)
  beta_base_prod <- betas_simulacao %>% select(product, beta_base)
  
  # Simulated shares for ALL exporters
  shares_sim_todos <- shares_ref_todos %>%
    left_join(price_rel_todos, by = c("exporter", "product")) %>%
    left_join(beta_base_prod,  by = "product") %>%
    left_join(betas_long %>% select(exporter, product, beta_sim),
              by = c("exporter", "product")) %>%
    mutate(
      beta_usado    = coalesce(beta_sim, beta_base),
      share_sim_raw = if_else(
        !is.na(delta_log_price),
        pmax(share_base * exp(beta_usado * delta_log_price), 0),
        share_base
      )
    ) %>%
    # Normalise by product: shares sum to 1
    group_by(product) %>%
    mutate(
      soma_sim       = sum(share_sim_raw, na.rm = TRUE),
      share_simulado = if_else(soma_sim > 0,
                               share_sim_raw / soma_sim,
                               share_base)
    ) %>%
    ungroup() %>%
    select(exporter, product, share_base, share_simulado,
           delta_log_price, beta_usado)
  
  # Final result: paises_grupo only, with complete metadata
  sim <- shares_sim_todos %>%
    filter(exporter %in% paises_grupo) %>%
    left_join(betas_long, by = c("exporter", "product")) %>%
    left_join(
      fatores_grupo %>% select(exporter, product, fator_emissao, fonte_fator),
      by = c("exporter", "product")
    ) %>%
    left_join(
      price_rel_todos %>% select(exporter, product,
                                 log_price_rel_2025, price_rel_2026,
                                 preco_pais_2026, price_avg_loo_2026),
      by = c("exporter", "product")
    ) %>%
    filter(!is.na(share_base)) %>%
    mutate(
      cenario_carbono   = nome_carbono,
      cenario_tarifa    = tarifa,
      preco_carbono_eur = preco_co2,
      custo_cbam_ton    = coalesce(fator_emissao, 0) * preco_co2,
      delta_share_pp    = share_simulado - share_base,
      delta_share_pct   = (share_simulado / share_base - 1) * 100
    )
  
  sim
})

# Convert to factor
resultados_cenarios <- resultados_cenarios %>%
  mutate(
    cenario_carbono = factor(cenario_carbono,
                             levels = names(cenarios_carbono),
                             labels = paste0(cenarios_carbono, "/tCO2")),
    cenario_tarifa  = factor(cenario_tarifa,
                             levels = cenarios_tarifa)
  )

registrar_resumo(nrow(resultados_cenarios), "07",
                 "12. simulation results (all combinations)",
                 n_exp  = n_distinct(resultados_cenarios$exporter),
                 n_prod = n_distinct(resultados_cenarios$product),
                 note   = paste0(length(cenarios_carbono), " carbon × ",
                                 length(cenarios_tarifa),
                                 " tariff | normalised shares"))

cat(sprintf("  Scenarios computed: %d × %d = %d\n",
            length(cenarios_carbono), length(cenarios_tarifa),
            length(cenarios_carbono) * length(cenarios_tarifa)))

# ── 7. Resumos ────────────────────────────────────────────────────────────────

resumo_pais <- resultados_cenarios %>%
  group_by(exporter, cenario_carbono, cenario_tarifa, preco_carbono_eur) %>%
  summarise(
    n_products            = n(),
    custo_cbam_medio      = weighted.mean(custo_cbam_ton,  share_base, na.rm = TRUE),
    delta_log_price_medio = weighted.mean(delta_log_price, share_base, na.rm = TRUE),
    # Do NOT use sum(share): adding shares of different products makes no sense.
    # The correct sector share is aggregated at LEVEL (volume), see the block below,
    # where it is computed from ton_base_total / total sector market.
    .groups = "drop"
  )

# ── Volume and revenue: converts share → ton/EUR using the base market ─────────────
volume_mercado_07 <- df %>%
  filter(year %in% anos_base, product %in% produtos_grupo) %>%
  group_by(product) %>%
  summarise(
    ton_total_mercado = sum(ton, na.rm = TRUE) / length(anos_base),
    .groups = "drop"
  )

preco_cif_07 <- df %>%
  filter(year %in% anos_base, exporter %in% paises_grupo) %>%
  group_by(exporter, product) %>%
  summarise(
    preco_CIF = sum(euro, na.rm = TRUE) / sum(ton, na.rm = TRUE),
    ton_base  = sum(ton,  na.rm = TRUE) / length(anos_base),
    .groups   = "drop"
  )

# Total sector market (sum of the volume of ALL sector products),
# usado como denominador do share setorial correto.
mercado_setorial_total <- sum(volume_mercado_07$ton_total_mercado, na.rm = TRUE)

ton_euro_pais <- resultados_cenarios %>%
  left_join(volume_mercado_07, by = "product") %>%
  left_join(preco_cif_07,      by = c("exporter", "product")) %>%
  mutate(
    ton_sim    = share_simulado * ton_total_mercado,
    delta_ton  = ton_sim - ton_base,
    euro_base  = ton_base * preco_CIF,
    euro_sim   = ton_sim  * preco_CIF,
    delta_euro = euro_sim - euro_base
  ) %>%
  group_by(exporter, cenario_carbono, cenario_tarifa) %>%
  summarise(
    ton_base_total   = sum(ton_base,   na.rm = TRUE),
    ton_sim_total    = sum(ton_sim,    na.rm = TRUE),
    delta_ton_total  = sum(delta_ton,  na.rm = TRUE),
    euro_base_total  = sum(euro_base,  na.rm = TRUE),
    delta_euro_total = sum(delta_euro, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  mutate(
    delta_ton_pct  = if_else(ton_base_total  > 0,
                             delta_ton_total  / ton_base_total  * 100, NA_real_),
    delta_euro_pct = if_else(euro_base_total > 0,
                             delta_euro_total / euro_base_total * 100, NA_real_),
    # ── CORRECT SECTOR SHARE (volume) ──
    # country share of the TOTAL sector volume imported by the EU.
    # Level aggregation: country ton sum / market ton sum.
    share_base_total      = ton_base_total / mercado_setorial_total,
    share_sim_total       = ton_sim_total  / mercado_setorial_total,
    delta_share_pp_total  = share_sim_total - share_base_total,
    variacao_relativa_pct = if_else(share_base_total > 0,
                             delta_share_pp_total / share_base_total * 100, NA_real_)
  )

resumo_pais <- resumo_pais %>%
  left_join(ton_euro_pais, by = c("exporter", "cenario_carbono", "cenario_tarifa"))

resumo_product <- resultados_cenarios %>%
  select(exporter, product, cenario_carbono, cenario_tarifa, preco_carbono_eur,
         fonte_fator, fator_emissao, custo_cbam_ton, delta_log_price,
         log_price_rel_2025, price_rel_2026,
         beta_sim, fonte_beta, share_base, share_simulado,
         delta_share_pp, delta_share_pct)

# ── 8. Print summary table ─────────────────────────────────────────────────

setor_label <- toupper(produto_ativo)

cat("\n", rep("=", 70), "\n", sep = "")
cat("  SIMULACAO CBAM —", setor_label,
    "| Grupo:", nome_grupo, "\n")
cat(rep("=", 70), "\n\n", sep = "")

cat("TABLE: Aggregate impact by country × carbon × tariff\n")
cat(rep("-", 70), "\n", sep = "")
resumo_pais %>%
  mutate(
    `share_base (%)`  = round(share_base_total * 100,    3),
    `Δshare (pp)`     = round(delta_share_pp_total * 100, 3),
    `Δshare (%)`      = round(variacao_relativa_pct,      2),
    `Δton (k t)`    = round(delta_ton_total  / 1e3,     1),
    `Δton (%)`        = round(delta_ton_pct,               2),
    `ΔEUR (EUR mn)`     = round(delta_euro_total / 1e6,      2),
    `ΔEUR (%)`        = round(delta_euro_pct,               2)
  ) %>%
  select(exporter, cenario_carbono, cenario_tarifa,
         `share_base (%)`, `Δshare (pp)`, `Δshare (%)`,
         `Δton (k t)`, `Δton (%)`, `ΔEUR (EUR mn)`, `ΔEUR (%)`) %>%
  arrange(exporter, cenario_tarifa, cenario_carbono) %>%
  print(n = Inf)

# ── 9. Exportar ───────────────────────────────────────────────────────────────

write_csv(resumo_pais,    file.path(dir_output, "13_cbam_resumo_pais.csv"))
write_csv(resumo_product, file.path(dir_output, "14_cbam_resumo_product.csv"))

# ── 10. Charts ──────────────────────────────────────────────────────────────

cores_carbono <- setNames(
  c("#4DAF4A", "#FF7F00", "#E41A1C"),
  paste0(cenarios_carbono, "/tCO2")
)
cenario_medio <- levels(resultados_cenarios$cenario_carbono)[2]

# Plot 1: relative change — all 6 scenarios by country
p1 <- resumo_pais %>%
  ggplot(aes(x = cenario_carbono, y = variacao_relativa_pct,
             fill = cenario_carbono, alpha = cenario_tarifa)) +
  geom_col(position = position_dodge(width = 0.7), width = 0.6) +
  geom_hline(yintercept = 0, linetype = "dashed", colour = "grey40") +
  facet_wrap(~exporter) +
  scale_fill_manual(values = cores_carbono, name = "Carbon") +
  scale_alpha_manual(values = c("MFN" = 1, "Mercosul" = 0.5), name = "Tariff") +
  scale_y_continuous(labels = function(x) paste0(x, "%")) +
  labs(
    title    = paste("CBAM impact —", setor_label, "| 6 scenarios"),
    subtitle = paste("Group:", nome_grupo, "| Fase:", fase_cbam,
                     "| Opaco = MFN | Transparente = Mercosul"),
    x = "Carbon scenario", y = "Relative change in share (%)"
  ) +
  theme_minimal(base_size = 12) +
  theme(strip.text = element_text(face = "bold"),
        plot.title = element_text(face = "bold"),
        panel.grid.major.x = element_blank(),
        legend.position = "bottom")

ggsave(file.path(dir_output, "15_cbam_6cenarios_pais.png"),
       p1, width = min(24, max(10, 4 * length(paises_grupo))), height = 5, dpi = 150)

# Plot 2: change by product — middle scenario, MFN vs Mercosul
source(file.path(dir_scripts, "helper_grupos.R"))

# Sector-wide summary (shown at the top of the chart)
resumo_setor <- resultados_cenarios %>%
  filter(cenario_carbono == cenario_medio) %>%
  group_by(exporter, cenario_tarifa) %>%
  summarise(
    delta_share_pct = weighted.mean(delta_share_pct, share_base, na.rm = TRUE),
    share_base      = sum(share_base, na.rm = TRUE),
    .groups         = "drop"
  ) %>%
  mutate(
    product     = "[Setor]",
    grupo       = 0L,
    grupo_label = "Setor",
    is_resumo   = TRUE
  )

df_p2_base <- resultados_cenarios %>%
  filter(cenario_carbono == cenario_medio) %>%
  preparar_plot_grupos(
    col_produto = "product",
    col_valor   = "delta_share_pct",
    col_peso    = "share_base",
    cols_resumo = c("exporter", "cenario_tarifa")
  )

# Extract levels before bind_rows
levels_produto <- levels(df_p2_base$product)

resumo_setor <- resultados_cenarios %>%
  filter(cenario_carbono == cenario_medio) %>%
  group_by(exporter, cenario_tarifa) %>%
  summarise(
    delta_share_pct = weighted.mean(delta_share_pct, share_base, na.rm = TRUE),
    share_base      = sum(share_base, na.rm = TRUE),
    .groups         = "drop"
  ) %>%
  mutate(
    product     = "[Setor]",
    grupo       = 0L,
    grupo_label = "Setor",
    is_resumo   = TRUE
  )

df_p2 <- df_p2_base %>%
  bind_rows(resumo_setor) %>%
  mutate(
    product = factor(product,
                     levels = c("[Setor]", levels_produto))
  )

p2 <- df_p2 %>%
  ggplot(aes(x = delta_share_pct, y = product,
             colour = cenario_tarifa, shape = cenario_tarifa,
             size = is_resumo)) +
  geom_vline(xintercept = 0, linetype = "dashed", colour = "grey40") +
  geom_point(alpha = 0.85, position = position_dodge(width = 0.4)) +
  facet_wrap(~exporter) +
  scale_colour_manual(values = c("MFN" = "#E41A1C", "Mercosul" = "#4DAF4A"),
                      name = "Tariff") +
  scale_shape_manual(values = c("MFN" = 16, "Mercosul" = 17), name = "Tariff") +
  scale_size_manual(values = c("TRUE" = 4.5, "FALSE" = 2.5), guide = "none") +
  scale_x_continuous(labels = function(x) paste0(x, "%")) +
  labs(
    title    = paste(setor_label, ": MFN vs Mercosul —", cenario_medio),
    subtitle = "By product group | Larger points = group weighted mean | [Sector] = overall mean",
    x = "Change in share (%)", y = NULL
  ) +
  theme_minimal(base_size = 12) +
  theme(
    plot.title = element_text(face = "bold"),
    legend.position = "bottom",
    axis.text.y = element_text(
      face = ifelse(grepl("^\\[", as.character(levels(df_p2$product))),
                    "bold", "plain")
    )
  )

ggsave(file.path(dir_output, "16_cbam_mfn_vs_mercosul_produto.png"),
       p2, width = min(24, max(11, 5 * length(paises_grupo))), height = 6, dpi = 150)

# ── 10b. Charts by metric (share pp | share % | ton | ton % | EUR | EUR %) ─

w_plt <- min(24, max(10, 4 * length(paises_grupo)))   # largura base

.bar_metrica <- function(y_col, y_lab, tit, fmt = identity) {
  resumo_pais %>%
    ggplot(aes(x = cenario_carbono, y = .data[[y_col]],
               fill = cenario_carbono, alpha = cenario_tarifa)) +
    geom_col(position = position_dodge(width = 0.7), width = 0.6) +
    geom_hline(yintercept = 0, linetype = "dashed", colour = "grey40") +
    facet_wrap(~exporter) +
    scale_fill_manual(values = cores_carbono, name = "Carbon") +
    scale_alpha_manual(values = c("MFN" = 1, "Mercosul" = 0.5), name = "Tariff") +
    scale_y_continuous(labels = fmt) +
    labs(
      title    = paste("CBAM:", setor_label, "—", tit),
      subtitle = paste("Group:", nome_grupo,
                       "| Opaco = MFN | Transparente = Mercosul"),
      x = "Carbon scenario", y = y_lab
    ) +
    theme_minimal(base_size = 12) +
    theme(strip.text = element_text(face = "bold"),
          plot.title = element_text(face = "bold"),
          panel.grid.major.x = element_blank(),
          legend.position = "bottom")
}

# — prepare intermediate columns in resumo_pais for the plots —
resumo_pais <- resumo_pais %>%
  mutate(
    delta_share_pp_pct  = delta_share_pp_total * 100,   # pp → % for display
    delta_ton_mil       = delta_ton_total  / 1e3,
    delta_eur_mi        = delta_euro_total / 1e6
  )

# Plot A — Δshare (pp)
pA <- .bar_metrica("delta_share_pp_pct",  "Δ share (pp)",
                   "Change in market share (pp)",
                   fmt = function(x) paste0(sprintf("%.2f", x), " pp"))
ggsave(file.path(dir_output, "15b_cbam_delta_share_pp.png"),
       pA, width = w_plt, height = 5, dpi = 150)

# Plot B — Δshare (%)
pB <- .bar_metrica("variacao_relativa_pct", "Δ share (%)",
                   "Relative change in market share (%)",
                   fmt = function(x) paste0(x, "%"))
ggsave(file.path(dir_output, "15c_cbam_delta_share_pct.png"),
       pB, width = w_plt, height = 5, dpi = 150)

# Plot C — Δton (k t)
pC <- .bar_metrica("delta_ton_mil", "Δ volume (thousand t)",
                   "Change in volume (thousand tonnes)",
                   fmt = function(x) paste0(x, " k t"))
ggsave(file.path(dir_output, "15d_cbam_delta_ton_mil.png"),
       pC, width = w_plt, height = 5, dpi = 150)

# Plot D — Δton (%)
pD <- .bar_metrica("delta_ton_pct", "Δ volume (%)",
                   "Relative change in volume (%)",
                   fmt = function(x) paste0(x, "%"))
ggsave(file.path(dir_output, "15e_cbam_delta_ton_pct.png"),
       pD, width = w_plt, height = 5, dpi = 150)

# Plot E — ΔEUR (EUR mn)
pE <- .bar_metrica("delta_eur_mi", "Δ revenue (EUR mn)",
                   "Change in export revenue (EUR mn)",
                   fmt = function(x) paste0(x, " mn EUR"))
ggsave(file.path(dir_output, "15f_cbam_delta_eur_mi.png"),
       pE, width = w_plt, height = 5, dpi = 150)

# Plot F — ΔEUR (%)
pF <- .bar_metrica("delta_euro_pct", "Δ revenue (%)",
                   "Relative change in export revenue (%)",
                   fmt = function(x) paste0(x, "%"))
ggsave(file.path(dir_output, "15g_cbam_delta_eur_pct.png"),
       pF, width = w_plt, height = 5, dpi = 150)

# Plot G — Combined: Δshare % | Δton % | ΔEUR % (facet by metric)
resumo_long <- resumo_pais %>%
  select(exporter, cenario_carbono, cenario_tarifa,
         `Δ share (%)` = variacao_relativa_pct,
         `Δ volume (%)` = delta_ton_pct,
         `Δ revenue (%)` = delta_euro_pct) %>%
  tidyr::pivot_longer(
    cols      = c(`Δ share (%)`, `Δ volume (%)`, `Δ revenue (%)`),
    names_to  = "metric",
    values_to = "value"
  ) %>%
  mutate(metric = factor(metric,
                          levels = c("Δ share (%)", "Δ volume (%)", "Δ revenue (%)")))

pG <- resumo_long %>%
  ggplot(aes(x = cenario_carbono, y = value,
             fill = cenario_carbono, alpha = cenario_tarifa)) +
  geom_col(position = position_dodge(width = 0.7), width = 0.6) +
  geom_hline(yintercept = 0, linetype = "dashed", colour = "grey40") +
  facet_grid(metric ~ exporter, scales = "free_y") +
  scale_fill_manual(values = cores_carbono, name = "Carbon") +
  scale_alpha_manual(values = c("MFN" = 1, "Mercosul" = 0.5), name = "Tariff") +
  scale_y_continuous(labels = function(x) paste0(x, "%")) +
  labs(
    title    = paste("CBAM:", setor_label, "— Comparative impacts (%)"),
    subtitle = paste("Group:", nome_grupo,
                     "| Rows: share | volume | revenue | Opaque = MFN | Transparent = Mercosul"),
    x = "Carbon scenario", y = "Change (%)"
  ) +
  theme_minimal(base_size = 11) +
  theme(strip.text      = element_text(face = "bold"),
        strip.text.y    = element_text(angle = 0),
        plot.title      = element_text(face = "bold"),
        panel.grid.major.x = element_blank(),
        legend.position = "bottom")

ggsave(file.path(dir_output, "15h_cbam_impactos_combinados_pct.png"),
       pG,
       width  = min(24, max(12, 4 * length(paises_grupo))),
       height = 8, dpi = 150)

cat(sprintf("  [10b] Charts by metric saved (15b–15h) in: %s\n", dir_output))

# ── 11. Salvar RDS ────────────────────────────────────────────────────────────

saveRDS(resultados_cenarios, file.path(dir_output, "17_cbam_resultados_cenarios.rds"))
saveRDS(resumo_pais,         file.path(dir_output, "18_cbam_resumo_pais.rds"))
saveRDS(resumo_product,      file.path(dir_output, "18_cbam_resumo_product.rds"))

cat("[ 07 ] OK — outputs em:", dir_output, "\n\n")
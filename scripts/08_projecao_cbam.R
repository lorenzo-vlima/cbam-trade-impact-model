############################################
# 08_projecao_cbam.R
# ----------------------------------------
# Cumulative projection of the CBAM impact
# de 2026 a 2028.
#
# Competitive normalisation:
#   each year, simulated shares of ALL
#   exporters are normalised by product.
#   - paises_grupo: uses beta_sim (shrinkage)
#   - others:       use beta_base (global)
#   Guarantees that shares sum to 1 at each iteration.
#
# Depende de: 07_simulacao_cbam.R
############################################

cat("[ 08 ] Cumulative CBAM projection 2026-2028...\n")

# ── Main function: projection for one tariff scenario ─────────────────────

rodar_projecao <- function(cenario_tarifa) {
  
  cat(sprintf("  Running projection — tariff: %s\n", cenario_tarifa))
  
  # Initial share = share observed in the base window (all exporters)
  share_atual <- shares_ref_todos %>%
    rename(share = share_base)
  
  # Base beta by product (for the rest of the world)
  beta_base_prod <- betas_simulacao %>% select(product, beta_base)
  
  resultados_anos <- list()
  
  for (i in seq_len(nrow(projecao_anos))) {
    
    ano_proj  <- projecao_anos$ano[i]
    fase_proj <- projecao_anos$fase[i]
    preco_co2 <- projecao_precos[as.character(ano_proj)]
    
    # delta_log_price for all exporters
    price_rel_todos <- calcular_price_rel_2026(cenario_tarifa, fase_proj, preco_co2)
    
    # Simulate shares for all exporters with normalisation
    shares_sim_todos <- share_atual %>%
      left_join(price_rel_todos, by = c("exporter", "product")) %>%
      left_join(beta_base_prod,  by = "product") %>%
      left_join(betas_long %>% select(exporter, product, beta_sim),
                by = c("exporter", "product")) %>%
      mutate(
        beta_usado    = coalesce(beta_sim, beta_base),
        share_sim_raw = if_else(
          !is.na(delta_log_price),
          pmax(share * exp(beta_usado * delta_log_price), 0),
          share
        )
      ) %>%
      group_by(product) %>%
      mutate(
        soma_sim       = sum(share_sim_raw, na.rm = TRUE),
        share_simulado = if_else(soma_sim > 0,
                                 share_sim_raw / soma_sim,
                                 share)
      ) %>%
      ungroup()
    
    # Result for the year: paises_grupo only, with metadata
    resultado_ano <- shares_sim_todos %>%
      filter(exporter %in% paises_grupo) %>%
      left_join(betas_long, by = c("exporter", "product")) %>%
      left_join(
        fatores_grupo %>% select(exporter, product, fator_emissao, fonte_fator),
        by = c("exporter", "product")
      ) %>%
      mutate(
        ano               = ano_proj,
        cenario_tarifa    = cenario_tarifa,
        fase              = fase_proj,
        preco_carbono_eur = preco_co2,
        custo_cbam_ton    = coalesce(fator_emissao, 0) * preco_co2,
        share_anterior    = share,
        delta_share_pp    = share_simulado - share_anterior,
        delta_share_pct   = (share_simulado / share_anterior - 1) * 100
      ) %>%
      filter(!is.na(share_anterior))
    
    resultados_anos[[i]] <- resultado_ano
    
    # Simulated share of ALL becomes the base of the next year
    share_atual <- shares_sim_todos %>%
      select(exporter, product, share = share_simulado)
    
    cat(sprintf("    %d (fase: %s, CO2: EUR %d): OK\n",
                ano_proj, fase_proj, preco_co2))
  }
  
  bind_rows(resultados_anos)
}

# ── Run for all tariff scenarios ───────────────────────────────────

projecao_completa <- map_dfr(cenarios_tarifa, rodar_projecao)

# ── Summary by country × year × tariff ───────────────────────────────────────────

# Aggregation 1: sum of shares (original metric, kept for compatibility)
projecao_pais <- projecao_completa %>%
  group_by(exporter, ano, cenario_tarifa, preco_carbono_eur) %>%
  summarise(
    share_anterior_total  = sum(share_anterior,  na.rm = TRUE),
    share_simulado_total  = sum(share_simulado,  na.rm = TRUE),
    delta_share_pp_total  = sum(delta_share_pp,  na.rm = TRUE),
    custo_cbam_medio      = weighted.mean(custo_cbam_ton, share_anterior,
                                          na.rm = TRUE),
    .groups = "drop"
  ) %>%
  mutate(
    variacao_relativa_pct = delta_share_pp_total / share_anterior_total * 100
  )

# ── Aggregation 2: weighted by market volume (correct metric) ────────────
#
# Logic in two steps:
#   1. Each product share changes according to the simulation
#   2. Rebuilds the country volume:
#      volume_p = share_p × TotalImports_p  (fixed total market = partial equilibrium)
#   Change: (Σ_p volume_p_sim - Σ_p volume_p_base) / Σ_p volume_p_base
#
# This automatically weights by the market size of each product,
# with no arbitrary choice of weights. It yields a number interpretable as:
# "the total volume exported by the country in the sector fell by X%."

projecao_pais_vol <- projecao_completa %>%
  # Total market by product (fixed at the base, partial-equilibrium assumption)
  left_join(volume_mercado_07, by = "product") %>%
  # Base CIF price by country × product (to compute the change in EUR)
  left_join(
    preco_cif_07 %>% select(exporter, product, preco_CIF),
    by = c("exporter", "product")
  ) %>%
  filter(!is.na(ton_total_mercado), ton_total_mercado > 0) %>%
  mutate(
    # Rebuilt volume: share × total market
    ton_anterior_p  = share_anterior * ton_total_mercado,
    ton_simulado_p  = share_simulado * ton_total_mercado,
    delta_ton_p     = ton_simulado_p - ton_anterior_p,
    # Rebuilt value (base CIF price, no price update)
    euro_anterior_p = ton_anterior_p * coalesce(preco_CIF, 0),
    euro_simulado_p = ton_simulado_p * coalesce(preco_CIF, 0)
  ) %>%
  group_by(exporter, ano, cenario_tarifa, preco_carbono_eur) %>%
  summarise(
    ton_base_total    = sum(ton_anterior_p,  na.rm = TRUE),
    ton_sim_total     = sum(ton_simulado_p,  na.rm = TRUE),
    delta_ton_total   = sum(delta_ton_p,     na.rm = TRUE),
    euro_base_total   = sum(euro_anterior_p, na.rm = TRUE),
    euro_sim_total    = sum(euro_simulado_p, na.rm = TRUE),
    n_produtos        = n(),
    .groups           = "drop"
  ) %>%
  mutate(
    variacao_ton_pct  = delta_ton_total / ton_base_total  * 100,
    variacao_euro_pct = (euro_sim_total - euro_base_total) / euro_base_total * 100
  )

cat("\n  Comparison: sum of shares vs. volume-weighted (MFN):\n")
comp <- projecao_pais %>%
  select(exporter, ano, cenario_tarifa, var_share = variacao_relativa_pct) %>%
  left_join(
    projecao_pais_vol %>% select(exporter, ano, cenario_tarifa, var_vol = variacao_ton_pct),
    by = c("exporter", "ano", "cenario_tarifa")
  ) %>%
  filter(cenario_tarifa == "MFN") %>%
  mutate(across(c(var_share, var_vol), ~ round(.x, 2)))
print(as.data.frame(comp))

# ── Imprimir ──────────────────────────────────────────────────────────────────

cat("\n", rep("=", 70), "\n", sep = "")
cat("  CUMULATIVE CBAM PROJECTION — 2026–2028\n")
cat(rep("=", 70), "\n\n", sep = "")

projecao_pais %>%
  arrange(exporter, cenario_tarifa, ano) %>%
  mutate(across(c(share_anterior_total, share_simulado_total),
                ~round(. * 100, 4)),
         across(c(variacao_relativa_pct, custo_cbam_medio), ~round(., 2))) %>%
  print(n = Inf)

# ── Exportar ──────────────────────────────────────────────────────────────────

write_csv(projecao_completa, file.path(dir_output, "19_cbam_projecao_cumulativa.csv"))
write_csv(projecao_pais,     file.path(dir_output, "20_cbam_projecao_pais.csv"))

# ── Charts ──────────────────────────────────────────────────────────────────

cores_tarifa <- c("MFN" = "#E41A1C", "Mercosul" = "#4DAF4A")

p_proj1 <- projecao_pais %>%
  ggplot(aes(x = ano, y = share_simulado_total * 100,
             colour = cenario_tarifa, linetype = cenario_tarifa)) +
  geom_line(linewidth = 1.2) +
  geom_point(size = 3) +
  geom_hline(
    data = shares_ref_grupo %>%
      group_by(exporter) %>%
      summarise(share_base = sum(share_base, na.rm = TRUE)),
    aes(yintercept = share_base * 100),
    linetype = "dotted", colour = "grey50", linewidth = 0.8
  ) +
  facet_wrap(~exporter, scales = "free_y") +
  scale_colour_manual(values = cores_tarifa, name = "Tarifa") +
  scale_linetype_manual(values = c("MFN" = "solid", "Mercosul" = "dashed"),
                        name = "Tarifa") +
  scale_x_continuous(breaks = projecao_anos$ano) +
  labs(
    title    = paste("Cumulative CBAM projection —", toupper(produto_ativo)),
    subtitle = paste("Total share in the EU | Group:", nome_grupo,
                     "| Dotted line = base", ano_corte),
    x = "Year", y = "Total share (%)",
    caption  = paste("CO2 prices:", paste(names(projecao_precos),
                                          projecao_precos, sep = "=",
                                          collapse = " | "), "EUR/tCO2")
  ) +
  theme_minimal(base_size = 12) +
  theme(strip.text = element_text(face = "bold"),
        plot.title = element_text(face = "bold"),
        legend.position = "bottom")

ggsave(file.path(dir_output, "21_cbam_projecao_share_pais.png"),
       p_proj1, width = min(24, max(10, 4 * length(paises_grupo))), height = 5, dpi = 150)

p_proj2 <- projecao_pais %>%
  ggplot(aes(x = ano, y = variacao_relativa_pct,
             colour = cenario_tarifa, linetype = cenario_tarifa)) +
  geom_line(linewidth = 1.2) +
  geom_point(size = 3) +
  geom_hline(yintercept = 0, linetype = "dashed", colour = "grey40") +
  facet_wrap(~exporter) +
  scale_colour_manual(values = cores_tarifa, name = "Tarifa") +
  scale_linetype_manual(values = c("MFN" = "solid", "Mercosul" = "dashed"),
                        name = "Tarifa") +
  scale_x_continuous(breaks = projecao_anos$ano) +
  scale_y_continuous(labels = function(x) paste0(x, "%")) +
  labs(
    title    = paste("Cumulative change in share —", toupper(produto_ativo)),
    subtitle = paste("Group:", nome_grupo,
                     "| Each year starts from the previous simulated share"),
    x = "Year", y = "Relative change in share (%)"
  ) +
  theme_minimal(base_size = 12) +
  theme(strip.text = element_text(face = "bold"),
        plot.title = element_text(face = "bold"),
        legend.position = "bottom")

ggsave(file.path(dir_output, "22_cbam_projecao_variacao_pais.png"),
       p_proj2, width = min(24, max(10, 4 * length(paises_grupo))), height = 5, dpi = 150)

# ── Weighted volume chart ──────────────────────────────────────────────────
p_proj_vol <- projecao_pais_vol %>%
  ggplot(aes(x = ano, y = variacao_ton_pct,
             colour = cenario_tarifa, linetype = cenario_tarifa)) +
  geom_line(linewidth = 1.2) +
  geom_point(size = 3) +
  geom_hline(yintercept = 0, linetype = "dashed", colour = "grey40") +
  facet_wrap(~exporter) +
  scale_colour_manual(values = cores_tarifa, name = "Tarifa") +
  scale_linetype_manual(values = c("MFN" = "solid", "Mercosul" = "dashed"),
                        name = "Tarifa") +
  scale_x_continuous(breaks = projecao_anos$ano) +
  scale_y_continuous(labels = function(x) paste0(x, "%")) +
  labs(
    title    = paste("Cumulative change in volume (ton) —", toupper(produto_ativo)),
    subtitle = paste("Aggregation weighted by total market by product",
                     "| Partial equilibrium (TotalImports_p fixed at the base)"),
    x = "Year", y = "Change in volume exported to the EU (%)"
  ) +
  theme_minimal(base_size = 12) +
  theme(strip.text = element_text(face = "bold"),
        plot.title = element_text(face = "bold"),
        legend.position = "bottom")

ggsave(file.path(dir_output, "22b_cbam_projecao_variacao_volume.png"),
       p_proj_vol, width = min(24, max(10, 4 * length(paises_grupo))), height = 5, dpi = 150)

source(file.path(dir_scripts, "helper_grupos.R"))

dados_heatmap_raw <- projecao_completa %>%
  filter(cenario_tarifa == cenarios_tarifa[1])

if (nrow(dados_heatmap_raw) > 0) {
  
  dados_heatmap <- dados_heatmap_raw %>%
    preparar_plot_grupos(
      col_produto = "product",
      col_valor   = "delta_share_pct",
      col_peso    = "share_anterior",
      cols_resumo = c("exporter", "ano")
    )
  
  p_proj3 <- dados_heatmap %>%
    ggplot(aes(x = factor(ano), y = product, fill = delta_share_pct)) +
    geom_tile(colour = "white", linewidth = 0.5) +
    geom_text(aes(label    = sprintf("%.1f%%", delta_share_pct),
                  fontface = if_else(is_resumo, "bold", "plain")),
              size = 2.8) +
    facet_wrap(~exporter) +
    scale_fill_gradient2(low = "#E41A1C", mid = "white", high = "#4DAF4A",
                         midpoint = 0, name = "Δ share (%)") +
    labs(
      title    = paste("Heatmap — Δ share by product and year —",
                       toupper(produto_ativo)),
      subtitle = paste("Tariff:", cenarios_tarifa[1], "| Group:", nome_grupo,
                       "| Bold = group summary (share-weighted mean)"),
      x = "Year", y = NULL
    ) +
    theme_minimal(base_size = 11) +
    theme(
      plot.title = element_text(face = "bold"),
      legend.position = "right",
      axis.text.y = element_text(
        face = ifelse(grepl("^\\[", as.character(levels(dados_heatmap$product))),
                      "bold", "plain")
      )
    )
  
  ggsave(file.path(dir_output, "23_cbam_projecao_heatmap_produto.png"),
         p_proj3, width = min(24, max(12, 5 * length(paises_grupo))), height = 7,
         dpi = 150)
}

# ── Salvar RDS e CSVs ─────────────────────────────────────────────────────────

saveRDS(projecao_completa,  file.path(dir_output, "24_cbam_projecao_cumulativa.rds"))
saveRDS(projecao_pais,      file.path(dir_output, "25_cbam_projecao_pais.rds"))
saveRDS(projecao_pais_vol,  file.path(dir_output, "25b_cbam_projecao_vol.rds"))

write_csv(projecao_pais_vol, file.path(dir_output, "20b_cbam_projecao_vol.csv"))

cat("  Saved: 20b_cbam_projecao_vol.csv  (volume-weighted aggregation)\n")
cat("  Saved: 22b_cbam_projecao_variacao_volume.png\n")
cat("[ 08 ] OK — outputs em:", dir_output, "\n\n")
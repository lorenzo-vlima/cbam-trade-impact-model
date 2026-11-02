############################################
# 09_analise.R — Unified CBAM impact analysis
# ----------------------------------------
# Works for all models (share and volume):
# all produce share_base and share_simulado via 07.
#
# Produz:
#   1. Emission factors
#   2. Base prices
#   3. Market share + base volume
#   4. Custo CBAM
#   5. Betas + distribution
#   6. Standardised metrics (6 unified columns)
#   7. Pie charts (share before/after)
#   7b. Dumbbell + bubble charts (by product)
#   8. Group share before/after
#   9. Impact on emissions
#
# Depende de: 01_limpeza.R, 03_paises.R, 07_simulacao_cbam.R
############################################

cat("[ 09 ] Analysis and context of the results...\n")

setor_label <- toupper(produto_ativo)
cenario_ref <- levels(resultados_cenarios$cenario_carbono)[2]

# ── Total market volume (basis to convert share → ton) ─────────────────

volume_total <- df %>%
  filter(year %in% anos_base) %>%
  group_by(product) %>%
  summarise(
    ton_total_mercado  = sum(ton,  na.rm = TRUE) / length(anos_base),
    euro_total_mercado = sum(euro, na.rm = TRUE) / length(anos_base),
    .groups = "drop"
  )

# ── 1. Emission factors — global vs group ───────────────────────────────────

cat("\n[ 1 ] Emission factors\n")

fator_global <- fatores_raw %>%
  filter(exporter != "ROW", !is.na(.data[[fase_cbam]])) %>%
  left_join(
    df %>%
      filter(year %in% anos_base) %>%
      group_by(exporter, product) %>%
      summarise(ton = sum(ton, na.rm = TRUE), .groups = "drop"),
    by = c("exporter", "product")
  ) %>%
  group_by(product) %>%
  summarise(
    fator_global = weighted.mean(.data[[fase_cbam]], ton, na.rm = TRUE),
    .groups = "drop"
  )

fator_grupo_tab <- fatores_grupo %>%
  select(exporter, product, fator_emissao, fonte_fator) %>%
  left_join(fator_global, by = "product") %>%
  mutate(diferenca_vs_mercado_pct = (fator_emissao / fator_global - 1) * 100)

cat("  Emission factors by country and product (phase:", fase_cbam, ")\n")
print(fator_grupo_tab %>% arrange(product, exporter), n = Inf)

write.csv(fator_grupo_tab,
          file.path(dir_output, "26_analise_fatores_emissao.csv"), row.names = FALSE)

# ── 2. Base prices — global vs group ─────────────────────────────────────────

cat("\n[ 2 ] Base prices (", paste(anos_base, collapse = "-"), ")\n")

preco_global <- df %>%
  filter(year %in% anos_base) %>%
  group_by(product) %>%
  summarise(
    preco_global = sum(euro, na.rm = TRUE) / sum(ton, na.rm = TRUE),
    .groups = "drop"
  )

precos_grupo <- df %>%
  filter(year %in% anos_base, exporter %in% paises_grupo) %>%
  group_by(exporter, product) %>%
  summarise(
    preco_pais      = sum(euro, na.rm = TRUE) / sum(ton, na.rm = TRUE),
    price_rel_medio = weighted.mean(price_rel, ton, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  left_join(preco_global, by = "product") %>%
  mutate(diferenca_pct = (preco_pais / preco_global - 1) * 100)

cat("  Base prices by country and product (EUR/ton)\n")
print(precos_grupo %>% arrange(product, exporter), n = Inf)

write.csv(precos_grupo,
          file.path(dir_output, "27_analise_precos_base.csv"), row.names = FALSE)

# ── 3. Base market share + base volume ────────────────────────────────────────

cat("\n[ 3 ] Market share and base volume\n")

share_vol <- df %>%
  filter(year %in% anos_base, exporter %in% paises_grupo) %>%
  group_by(exporter, product) %>%
  summarise(ton_pais = sum(ton, na.rm = TRUE) / length(anos_base),
            .groups = "drop") %>%
  left_join(volume_total %>% select(product, ton_total_mercado), by = "product") %>%
  left_join(precos_grupo %>% select(exporter, product, preco_pais), by = c("exporter", "product")) %>%
  mutate(
    share_vol      = ton_pais / ton_total_mercado,
    euro_exportado = ton_pais * preco_pais
  )

cat("  Share and volume by country and product\n")
print(share_vol %>% arrange(product, exporter) %>%
        mutate(share_vol = round(share_vol * 100, 3)), n = Inf)

share_acumulado_vol <- share_vol %>%
  group_by(exporter) %>%
  summarise(
    ton_total_exportado = sum(ton_pais, na.rm = TRUE),
    ton_mercado_total   = sum(ton_total_mercado, na.rm = TRUE),
    share_total_mercado = ton_total_exportado / ton_mercado_total,
    .groups = "drop"
  )

cat("\n  Total group share in the market:\n")
share_acumulado_vol %>%
  mutate(share_total_mercado = round(share_total_mercado * 100, 2)) %>%
  print()

write.csv(share_vol,
          file.path(dir_output, "28_analise_share_vol_base.csv"), row.names = FALSE)

# ── 4. Potential CBAM cost by product ───────────────────────────────────────

cat("\n[ 4 ] Custo CBAM potencial\n")

custo_cbam_tab <- fator_grupo_tab %>%
  left_join(precos_grupo %>% select(exporter, product, preco_pais),
            by = c("exporter", "product")) %>%
  cross_join(tibble(cenario   = names(cenarios_carbono),
                    preco_co2 = cenarios_carbono)) %>%
  mutate(
    custo_cbam_ton = fator_emissao * preco_co2,
    pct_preco      = custo_cbam_ton / preco_pais * 100
  ) %>%
  arrange(exporter, product, cenario)

write.csv(custo_cbam_tab,
          file.path(dir_output, "29_analise_custo_cbam.csv"), row.names = FALSE)

# ── 5. Betas — global vs simulated + distribution ──────────────────────────────

cat("\n[ 5 ] Betas e shrinkage\n")

cols_w      <- paste0("w_",        paises_grupo)
cols_beta   <- paste0("beta_",     paises_grupo)
cols_sim    <- paste0("beta_sim_", paises_grupo)
cols_fonte  <- paste0("fonte_",    paises_grupo)

betas_tab <- betas_simulacao %>%
  select(product, beta_base, se_base,
         any_of(c(cols_w, cols_beta, cols_sim, cols_fonte))) %>%
  arrange(product)

print(betas_tab, n = Inf)
write.csv(betas_tab, file.path(dir_output, "30_analise_betas.csv"), row.names = FALSE)

# Aggregate sector beta
beta_setor <- betas_simulacao %>%
  left_join(
    df %>% filter(year %in% anos_base) %>%
      group_by(product) %>%
      summarise(ton_produto = sum(ton, na.rm = TRUE), .groups = "drop"),
    by = "product"
  ) %>%
  summarise(
    beta_setor  = weighted.mean(beta_base, ton_produto, na.rm = TRUE),
    se_setor    = weighted.mean(se_base,   ton_produto, na.rm = TRUE),
    n_produtos  = n()
  )

cat(sprintf("\n  Aggregate sector beta: %.4f (se: %.4f, N=%d)\n",
            beta_setor$beta_setor, beta_setor$se_setor, beta_setor$n_produtos))

write.csv(beta_setor, file.path(dir_output, "30c_analise_beta_setor.csv"), row.names = FALSE)

# ── 6. Standardised metrics — 6 unified columns ──────────────────────────
#
# Note: preco_CIF = historical euro/ton of the exporter.
# The tariff goes to the EU treasury; CBAM is a cost for the importer.
# The exporter always receives the recorded CIF value, regardless of the regime.

cat("\n[ 6 ] Standardised metrics (share + volume + euros)\n")

# Historical CIF price (the same for both MFN and Mercosul scenarios)
precos_grupo_cif <- df %>%
  filter(year %in% anos_base, exporter %in% paises_grupo) %>%
  group_by(exporter, product) %>%
  summarise(
    preco_CIF = sum(euro, na.rm = TRUE) / sum(ton, na.rm = TRUE),
    .groups   = "drop"
  )

# Base volume (annual mean over anos_base)
ton_base_vol <- df %>%
  filter(year %in% anos_base, exporter %in% paises_grupo) %>%
  group_by(exporter, product) %>%
  summarise(ton_base = sum(ton, na.rm = TRUE) / length(anos_base), .groups = "drop")

# Complete impact
impacto_monetario <- resultados_cenarios %>%
  left_join(volume_total,    by = "product") %>%
  left_join(ton_base_vol,    by = c("exporter", "product")) %>%
  left_join(precos_grupo_cif, by = c("exporter", "product")) %>%
  mutate(
    ton_simulado  = share_simulado * ton_total_mercado,
    delta_ton     = ton_simulado   - ton_base,
    euro_base     = ton_base       * preco_CIF,
    euro_simulado = ton_simulado   * preco_CIF,
    delta_euro    = euro_simulado  - euro_base
  )

# Standardised metrics by product × scenario
metricas_padrao <- impacto_monetario %>%
  mutate(
    delta_share_pp   = share_simulado - share_base,
    delta_share_pct  = if_else(share_base > 0,
                               (share_simulado / share_base - 1) * 100, NA_real_),
    delta_ton_pct    = if_else(ton_base > 0,
                               delta_ton / ton_base * 100, NA_real_),
    delta_euro_pct   = if_else(euro_base > 0,
                               delta_euro / euro_base * 100, NA_real_)
  ) %>%
  select(exporter, product, cenario_carbono, cenario_tarifa,
         share_base, share_simulado, delta_share_pp, delta_share_pct,
         ton_base, ton_simulado, delta_ton, delta_ton_pct,
         euro_base, euro_simulado, delta_euro, delta_euro_pct, preco_CIF)

# Total sector market (denominator of the correct sector share): sum of the
# volume of ALL sector products imported by the EU.
mercado_setorial_total_09 <- sum(volume_total$ton_total_mercado, na.rm = TRUE)

# Aggregate summary by country × scenario (all 6 metrics)
impacto_resumo <- impacto_monetario %>%
  group_by(exporter, cenario_carbono, cenario_tarifa) %>%
  summarise(
    ton_base_total    = sum(ton_base,       na.rm = TRUE),
    ton_sim_total     = sum(ton_simulado,   na.rm = TRUE),
    euro_base_total   = sum(euro_base,      na.rm = TRUE),
    euro_sim_total    = sum(euro_simulado,  na.rm = TRUE),
    .groups = "drop"
  ) %>%
  mutate(
    # CORRECT SECTOR SHARE (volume): aggregated at level, not a sum of shares
    share_base_total  = ton_base_total / mercado_setorial_total_09,
    share_sim_total   = ton_sim_total  / mercado_setorial_total_09,
    delta_share_pp    = share_sim_total - share_base_total,
    delta_share_pct   = if_else(share_base_total > 0,
                                (share_sim_total / share_base_total - 1) * 100, NA_real_),
    delta_ton         = ton_sim_total   - ton_base_total,
    delta_ton_pct     = if_else(ton_base_total > 0,
                                delta_ton / ton_base_total * 100, NA_real_),
    delta_euro        = euro_sim_total  - euro_base_total,
    delta_euro_pct    = if_else(euro_base_total > 0,
                                delta_euro / euro_base_total * 100, NA_real_)
  )

cat("  Impact by country × scenario (all metrics)\n")
impacto_resumo %>%
  mutate(
    share_base_total  = round(share_base_total * 100, 3),
    delta_share_pp    = round(delta_share_pp   * 100, 3),
    delta_share_pct   = round(delta_share_pct,  2),
    delta_ton         = round(delta_ton / 1e3,  1),
    delta_ton_pct     = round(delta_ton_pct,    2),
    delta_euro        = round(delta_euro / 1e6, 2),
    delta_euro_pct    = round(delta_euro_pct,   2)
  ) %>%
  select(exporter, cenario_carbono, cenario_tarifa,
         share_base_total, delta_share_pp, delta_share_pct,
         delta_ton, delta_ton_pct, delta_euro, delta_euro_pct) %>%
  rename(`share_base (%)` = share_base_total,
         `Δshare (pp)`    = delta_share_pp,
         `Δshare (%)`     = delta_share_pct,
         `Δton (k t)`   = delta_ton,
         `Δton (%)`       = delta_ton_pct,
         `ΔEUR (EUR mn)`    = delta_euro,
         `ΔEUR (%)`       = delta_euro_pct) %>%
  arrange(exporter, cenario_tarifa, cenario_carbono) %>%
  print(n = Inf)

# Bar chart — change in volume
cores_carbono <- setNames(c("#4DAF4A", "#FF7F00", "#E41A1C"),
                          levels(impacto_resumo$cenario_carbono))

p_vol <- impacto_resumo %>%
  ggplot(aes(x = cenario_carbono, y = delta_ton / 1e3,
             fill = cenario_carbono, alpha = cenario_tarifa)) +
  geom_col(position = position_dodge(width = 0.7), width = 0.6) +
  geom_hline(yintercept = 0, linetype = "dashed", colour = "grey40") +
  facet_wrap(~exporter) +
  scale_fill_manual(values = cores_carbono, name = "Carbono") +
  scale_alpha_manual(values = c("MFN" = 1, "Mercosul" = 0.5), name = "Tariff") +
  scale_y_continuous(labels = function(x) paste0(x, " mil t")) +
  labs(title    = paste("CBAM impact — Volume (ton) |", setor_label),
       subtitle = paste("Group:", nome_grupo, "| Opaque = MFN | Transparent = Mercosul"),
       x = "Carbon scenario", y = "Δ volume (thousand ton)") +
  theme_minimal(base_size = 12) +
  theme(strip.text = element_text(face = "bold"),
        plot.title = element_text(face = "bold"),
        panel.grid.major.x = element_blank(),
        legend.position = "bottom")

ggsave(file.path(dir_output, "31_impacto_volume.png"),
       p_vol, width = min(24, max(10, 4 * length(paises_grupo))), height = 5, dpi = 150)

# Bar chart — change in euros
p_euro <- impacto_resumo %>%
  ggplot(aes(x = cenario_carbono, y = delta_euro / 1e6,
             fill = cenario_carbono, alpha = cenario_tarifa)) +
  geom_col(position = position_dodge(width = 0.7), width = 0.6) +
  geom_hline(yintercept = 0, linetype = "dashed", colour = "grey40") +
  facet_wrap(~exporter) +
  scale_fill_manual(values = cores_carbono, name = "Carbono") +
  scale_alpha_manual(values = c("MFN" = 1, "Mercosul" = 0.5), name = "Tariff") +
  scale_y_continuous(labels = function(x) paste0(x, " mn EUR")) +
  labs(title    = paste("CBAM impact — Revenue (EUR) |", setor_label),
       subtitle = paste("Historical CIF price without tariff | Group:", nome_grupo),
       x = "Carbon scenario", y = "Δ revenue (EUR mn)",
       caption  = "Opaque = MFN | Transparent = Mercosul") +
  theme_minimal(base_size = 12) +
  theme(strip.text = element_text(face = "bold"),
        plot.title = element_text(face = "bold"),
        panel.grid.major.x = element_blank(),
        legend.position = "bottom")

ggsave(file.path(dir_output, "31b_impacto_euro.png"),
       p_euro, width = min(24, max(10, 4 * length(paises_grupo))), height = 5, dpi = 150)

write.csv(metricas_padrao,   file.path(dir_output, "32_metricas_padrao.csv"),          row.names = FALSE)
write.csv(impacto_resumo,    file.path(dir_output, "33_analise_impacto_resumo.csv"),   row.names = FALSE)
write.csv(impacto_monetario, file.path(dir_output, "34_impacto_produto.csv"),          row.names = FALSE)

# ── 7. Pie charts — share before and after ───────────────────────────────

cat("\n[ 7 ] Pie charts\n")

preparar_pizza <- function(shares_df, label_ano) {
  shares_df %>%
    mutate(ton_abs = share_col * ton_total_mercado) %>%
    group_by(exporter) %>%
    summarise(ton = sum(ton_abs, na.rm = TRUE), .groups = "drop") %>%
    mutate(
      categoria = case_when(
        exporter %in% paises_grupo        ~ exporter,
        exporter %in% paises_isentos_cbam ~ "UE/EEE/CH",
        TRUE                              ~ "Outros"
      )
    ) %>%
    group_by(categoria) %>%
    summarise(ton = sum(ton, na.rm = TRUE), .groups = "drop") %>%
    mutate(share_pct = ton / sum(ton) * 100, ano = label_ano)
}

shares_todos_base <- df %>%
  filter(year %in% anos_base) %>%
  left_join(volume_total %>% select(product, ton_total_mercado), by = "product") %>%
  group_by(exporter, product, ton_total_mercado) %>%
  summarise(ton = sum(ton, na.rm = TRUE) / length(anos_base), .groups = "drop") %>%
  mutate(share_col = ton / ton_total_mercado)

pizza_base <- preparar_pizza(shares_todos_base,
                             paste0("Base (", paste(anos_base, collapse = "-"), ")"))

shares_simulados <- resultados_cenarios %>%
  filter(cenario_carbono == cenario_ref,
         cenario_tarifa  == cenarios_tarifa[1]) %>%
  left_join(volume_total, by = "product") %>%
  mutate(share_col = share_simulado) %>%
  select(exporter, product, ton_total_mercado, share_col) %>%
  bind_rows(
    df %>%
      filter(year %in% anos_base, !exporter %in% paises_grupo) %>%
      left_join(volume_total %>% select(product, ton_total_mercado), by = "product") %>%
      group_by(exporter, product, ton_total_mercado) %>%
      summarise(ton = sum(ton, na.rm = TRUE) / length(anos_base), .groups = "drop") %>%
      mutate(share_col = ton / ton_total_mercado)
  )

pizza_sim <- preparar_pizza(shares_simulados,
                            paste0("Simulated (", cenario_ref, " MFN)"))

pizza_dados <- bind_rows(pizza_base, pizza_sim)

n_paises    <- length(paises_grupo)
cores_pais  <- setNames(scales::hue_pal()(n_paises), paises_grupo)
cores_pizza <- c(cores_pais, "UE/EEE/CH" = "#2171B5", "Outros" = "#BDBDBD")

p_pizza <- pizza_dados %>%
  mutate(
    categoria = factor(categoria, levels = c(paises_grupo, "UE/EEE/CH", "Outros")),
    label     = if_else(share_pct >= 2,
                        paste0(categoria, "\n", round(share_pct, 1), "%"), "")
  ) %>%
  ggplot(aes(x = "", y = share_pct, fill = categoria)) +
  geom_col(width = 1, colour = "white", linewidth = 0.5) +
  geom_text(aes(label = label),
            position = position_stack(vjust = 0.5),
            size = 3, fontface = "bold") +
  coord_polar(theta = "y") +
  facet_wrap(~ano) +
  scale_fill_manual(values = cores_pizza, name = NULL) +
  labs(
    title    = paste("Market distribution of", setor_label, "in the EU"),
    subtitle = paste("Imported volume (ton) | Group:", nome_grupo),
    caption  = paste("Simulated scenario:", cenario_ref, "| Tariff: MFN")
  ) +
  theme_void() +
  theme(plot.title      = element_text(face = "bold", hjust = 0.5),
        plot.subtitle   = element_text(hjust = 0.5),
        legend.position = "bottom",
        strip.text      = element_text(face = "bold", size = 12))

ggsave(file.path(dir_output, "35_pizza_share.png"),
       p_pizza, width = 12, height = 6, dpi = 150)

print(p_pizza)

# ── 7b. Charts by product — dumbbell and bubble ─────────────────────────────

cat("\n[ 7b ] Charts by product (dumbbell and bubble)\n")

metricas_ref <- metricas_padrao %>%
  filter(cenario_carbono == cenario_ref,
         cenario_tarifa  == "MFN")

# — Option A: Dumbbell chart — share before/after, points ordered by volume —

for (cod in paises_grupo) {
  df_dumb <- metricas_ref %>%
    filter(exporter == cod) %>%
    arrange(desc(ton_base)) %>%
    mutate(
      product = factor(product, levels = rev(product)),
      ganho   = delta_share_pp >= 0
    )

  if (nrow(df_dumb) == 0) next

  p_dumb <- ggplot(df_dumb) +
    geom_segment(aes(x    = share_base    * 100,
                     xend = share_simulado * 100,
                     y    = product, yend = product,
                     color = ganho),
                 linewidth = 1.4, alpha = 0.75) +
    geom_point(aes(x = share_base * 100, y = product, size = ton_base / 1e3),
               color = "gray55", alpha = 0.85) +
    geom_point(aes(x = share_simulado * 100, y = product,
                   size = ton_base / 1e3, color = ganho),
               alpha = 0.95) +
    scale_color_manual(values = c("TRUE" = "#2CA02C", "FALSE" = "#D62728"),
                       labels = c("TRUE" = "Gain", "FALSE" = "Loss"),
                       name   = NULL) +
    scale_size_continuous(name   = "Base volume\n(thousand ton)",
                          labels = scales::comma,
                          range  = c(2, 9)) +
    labs(
      title    = paste("CBAM impact by product —", cod, "|", setor_label),
      subtitle = paste("Grey dot = base share | Coloured dot = simulated share |",
                       cenario_ref, "| MFN"),
      x       = "Market share (%)", y = NULL,
      caption = "Products ordered by imported volume (largest → smallest)"
    ) +
    theme_minimal(base_size = 11) +
    theme(plot.title = element_text(face = "bold"),
          legend.position = "bottom")

  ggsave(file.path(dir_output, paste0("36_dumbbell_", tolower(cod), ".png")),
         p_dumb,
         width  = 10,
         height = min(48, max(5, nrow(df_dumb) * 0.38 + 2.5)),
         dpi    = 150)
}

# — Option B: Bubble chart — delta vs importance —

for (cod in paises_grupo) {
  df_bubble <- metricas_ref %>%
    filter(exporter == cod, !is.na(delta_share_pp), !is.na(ton_base)) %>%
    mutate(
      ganho      = delta_share_pp >= 0,
      abs_euro   = abs(delta_euro),
      label_prod = product
    )

  if (nrow(df_bubble) == 0) next

  p_bubble <- ggplot(df_bubble,
                     aes(x     = delta_share_pp * 100,
                         y     = ton_base / 1e3,
                         size  = abs_euro / 1e6,
                         color = ganho,
                         label = label_prod)) +
    geom_vline(xintercept = 0, linetype = "dashed", color = "gray40") +
    geom_point(alpha = 0.75) +
    geom_text(
      aes(label = label_prod),
      size          = 2.8,
      color         = "gray20",
      check_overlap = TRUE,
      nudge_y       = max(df_bubble$ton_base / 1e3, na.rm = TRUE) * 0.04
    ) +
    scale_color_manual(values = c("TRUE" = "#2CA02C", "FALSE" = "#D62728"),
                       labels = c("TRUE" = "Gain", "FALSE" = "Loss"),
                       name   = NULL) +
    scale_size_continuous(name   = "|Δ EUR| (EUR mn)",
                          range  = c(2, 16),
                          labels = scales::comma) +
    scale_x_continuous(labels = function(x) paste0(x, " pp")) +
    scale_y_continuous(labels = scales::comma) +
    labs(
      title    = paste("CBAM impact by product —", cod, "|", setor_label),
      subtitle = paste("X: change in share (pp) | Y: base volume |",
                       "Bubble: |Δ revenue| in EUR mn |", cenario_ref, "| MFN"),
      x       = "Change in market share (pp)",
      y       = "Base volume (thousand ton)",
      caption = "Larger bubbles = larger absolute impact in euros"
    ) +
    theme_minimal(base_size = 11) +
    theme(plot.title = element_text(face = "bold"),
          legend.position = "bottom")

  ggsave(file.path(dir_output, paste0("37_bubble_", tolower(cod), ".png")),
         p_bubble, width = 10, height = 7, dpi = 150)
}

# ── 8. Group share before and after ─────────────────────────────────────────

cat("\n[ 8 ] Group share before and after\n")

share_grupo_vol <- impacto_resumo %>%
  select(cenario_carbono, cenario_tarifa,
         share_base_total, share_sim_total,
         ton_base_total, ton_sim_total) %>%
  left_join(
    df %>% filter(year %in% anos_base) %>%
      group_by(product) %>%
      summarise(ton_mercado_prod = sum(ton, na.rm = TRUE) / length(anos_base), .groups = "drop") %>%
      summarise(ton_mercado = sum(ton_mercado_prod)),
    by = character()
  ) %>%
  mutate(
    share_grupo_base_pct = share_base_total * 100,
    share_grupo_sim_pct  = share_sim_total  * 100,
    delta_pp             = share_grupo_sim_pct - share_grupo_base_pct,
    delta_pct            = if_else(share_grupo_base_pct > 0,
                                   delta_pp / share_grupo_base_pct * 100, NA_real_)
  )

share_ue_base_pct <- pizza_base %>%
  filter(categoria == "UE/EEE/CH") %>%
  pull(share_pct)

cat(sprintf("  Base share of EU/EEA/CH (descriptive): %.2f%%\n", share_ue_base_pct))

cat("  Group share by scenario:\n")
share_grupo_vol %>%
  mutate(across(c(share_grupo_base_pct, share_grupo_sim_pct,
                  delta_pp, delta_pct), ~round(., 3))) %>%
  arrange(cenario_tarifa, cenario_carbono) %>%
  print(n = Inf)

p_share_grupo <- impacto_resumo %>%
  group_by(cenario_carbono, cenario_tarifa) %>%
  summarise(
    share_base_total = sum(share_base_total, na.rm = TRUE),
    share_sim_total  = sum(share_sim_total,  na.rm = TRUE),
    .groups = "drop"
  ) %>%
  pivot_longer(cols = c(share_base_total, share_sim_total),
               names_to = "momento", values_to = "share_pct") %>%
  mutate(
    share_pct = share_pct * 100,
    momento   = if_else(momento == "share_base_total",
                        paste0("Base (", paste(anos_base, collapse = "-"), ")"),
                        "Simulado")
  ) %>%
  ggplot(aes(x = cenario_carbono, y = share_pct,
             fill = momento, group = momento)) +
  geom_col(position = position_dodge(width = 0.7), width = 0.6) +
  facet_wrap(~cenario_tarifa) +
  scale_fill_manual(values = c("grey70", "#E41A1C"), name = NULL) +
  scale_y_continuous(labels = function(x) paste0(x, "%")) +
  labs(
    title    = paste("Group share in the EU market —", setor_label),
    subtitle = paste("Base vs. simulated | Group:", nome_grupo),
    x = "Carbon scenario", y = "Market share (%)"
  ) +
  theme_minimal(base_size = 12) +
  theme(strip.text = element_text(face = "bold"),
        plot.title = element_text(face = "bold"),
        panel.grid.major.x = element_blank(),
        legend.position = "bottom")

ggsave(file.path(dir_output, "38_share_grupo.png"),
       p_share_grupo, width = 10, height = 5, dpi = 150)
print(p_share_grupo)

write.csv(share_grupo_vol,
          file.path(dir_output, "38b_share_grupo.csv"), row.names = FALSE)

# ── 9. Emissions analysis ────────────────────────────────────────────────────

cat("\n[ 9 ] Emissions analysis\n")

source(file.path(dir_scripts, "helper_grupos.R"))

fatores_base_emissao <- fatores_raw %>%
  filter(exporter != "ROW", !is.na(base_factor)) %>%
  group_by(exporter, product) %>%
  summarise(fator_base = fn_agregar(base_factor, na.rm = TRUE), .groups = "drop")

fatores_row_base <- fatores_raw %>%
  filter(exporter == "ROW", !is.na(base_factor)) %>%
  group_by(product) %>%
  summarise(fator_row_base = fn_agregar(base_factor, na.rm = TRUE), .groups = "drop")

fatores_base_grupo <- pares_modelo %>%
  left_join(fatores_base_emissao, by = c("exporter", "product")) %>%
  left_join(fatores_row_base,     by = "product") %>%
  mutate(
    fonte_fator = case_when(
      !is.na(fator_base)     ~ "especifico",
      !is.na(fator_row_base) ~ "ROW",
      TRUE                   ~ "ausente"
    ),
    fator_base = coalesce(fator_base, fator_row_base)
  ) %>%
  select(-fator_row_base)

cat(sprintf("  Factor coverage: %d specific, %d ROW, %d missing\n",
            sum(fatores_base_grupo$fonte_fator == "especifico"),
            sum(fatores_base_grupo$fonte_fator == "ROW"),
            sum(fatores_base_grupo$fonte_fator == "ausente")))

if (any(fatores_base_grupo$fonte_fator == "ausente")) {
  cat("  WARNING: pairs without an emission factor, check fatores_raw.\n")
  print(fatores_base_grupo %>% filter(fonte_fator == "ausente") %>% select(exporter, product))
}

emissoes_impacto <- impacto_monetario %>%
  left_join(fatores_base_grupo %>% select(exporter, product, fator_base),
            by = c("exporter", "product")) %>%
  mutate(
    emissoes_base_tco2  = ton_base     * fator_base,
    emissoes_sim_tco2   = ton_simulado * fator_base,
    delta_emissoes_tco2 = emissoes_sim_tco2 - emissoes_base_tco2
  )

emissoes_resumo <- emissoes_impacto %>%
  group_by(exporter, cenario_carbono, cenario_tarifa) %>%
  summarise(
    emissoes_base_total  = sum(emissoes_base_tco2,  na.rm = TRUE),
    emissoes_sim_total   = sum(emissoes_sim_tco2,   na.rm = TRUE),
    delta_emissoes_total = sum(delta_emissoes_tco2, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  mutate(
    delta_emissoes_pct = if_else(emissoes_base_total > 0,
                                 delta_emissoes_total / emissoes_base_total * 100, NA_real_)
  )

cat("  Impact on emissions by country × scenario\n")
emissoes_resumo %>%
  mutate(
    emissoes_base_total  = round(emissoes_base_total  / 1e3, 1),
    emissoes_sim_total   = round(emissoes_sim_total   / 1e3, 1),
    delta_emissoes_total = round(delta_emissoes_total / 1e3, 1),
    delta_emissoes_pct   = round(delta_emissoes_pct, 2)
  ) %>%
  arrange(exporter, cenario_tarifa, cenario_carbono) %>%
  print(n = Inf)

p_emissoes <- emissoes_resumo %>%
  ggplot(aes(x = cenario_carbono, y = delta_emissoes_total / 1e3,
             fill = cenario_carbono, alpha = cenario_tarifa)) +
  geom_col(position = position_dodge(width = 0.7), width = 0.6) +
  geom_hline(yintercept = 0, linetype = "dashed", colour = "grey40") +
  facet_wrap(~exporter) +
  scale_fill_manual(
    values = setNames(c("#4DAF4A", "#FF7F00", "#E41A1C"),
                      levels(emissoes_resumo$cenario_carbono)),
    name = "Carbono"
  ) +
  scale_alpha_manual(
    values = setNames(c(1, 0.5), levels(emissoes_resumo$cenario_tarifa)),
    name = "Tariff"
  ) +
  scale_y_continuous(labels = function(x) paste0(x, " k tCO₂e")) +
  labs(
    title    = paste("Impact on emissions —", setor_label),
    subtitle = "Change in emissions embodied in exports (volume effect)",
    x = "Carbon scenario", y = "Δ emissions (thousand tCO₂e/year)",
    caption  = "Fixed base factor, volume effect | Opaque = MFN | Transparent = Mercosul"
  ) +
  theme_minimal(base_size = 12) +
  theme(strip.text = element_text(face = "bold"),
        plot.title = element_text(face = "bold"),
        panel.grid.major.x = element_blank(),
        legend.position = "bottom")

ggsave(file.path(dir_output, "39_impacto_emissoes.png"),
       p_emissoes,
       width  = min(24, max(10, 4 * length(paises_grupo))),
       height = 5, dpi = 150)

write.csv(emissoes_impacto, file.path(dir_output, "39b_emissoes_impacto.csv"), row.names = FALSE)
write.csv(emissoes_resumo,  file.path(dir_output, "40_emissoes_resumo.csv"),   row.names = FALSE)

# ── 10. GoF — goodness of fit and explanatory power of price ───────────────

source(file.path(dir_helpers, "11_gof_modelo.R"))

# ── 11. Beta audit ────────────────────────────────────────────────────

source(file.path(dir_helpers, "10_auditoria_betas.R"))

cat("[ 09 ] OK — outputs in:", dir_output, "\n\n")

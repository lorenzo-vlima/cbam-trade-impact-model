############################################
# helpers/10_auditoria_betas.R
# ----------------------------------------
# Quality audit of the estimated betas.
# Called at the end of 09_analise.R for any model.
#
# Required context (already in the environment):
#   betas_simulacao, df, anos_base, paises_grupo,
#   setor_label, dir_output, z_critico
#
# Produces:
#   41_auditoria_alertas.csv      — suspicious betas
#   41b_auditoria_betas.png       — dot plot with expected zone
#   42_auditoria_series.png       — log_price_rel vs share/DV series
#   43_auditoria_estabilidade.png — betas in 5-year windows
############################################

cat("\n[ 10 ] Beta quality audit...\n")

# Alert parameters
beta_sinal_errado <- 0          # beta > 0 is suspicious for commodities
beta_magnitude_max <- 8         # |beta| > 8 deserves attention
p_value_max <- 0.20             # p > 0.20 = weak empirical support
zona_esperada <- c(-5, -0.5)   # plausible range for commodities

# ── 1. Mean volume by product (basis for ordering) ──────────────────────────

ton_prod <- df %>%
  filter(year %in% anos_base) %>%
  group_by(product) %>%
  summarise(ton_base_prod = sum(ton, na.rm = TRUE) / length(anos_base), .groups = "drop")

betas_audit <- betas_simulacao %>%
  left_join(ton_prod, by = "product") %>%
  mutate(
    t_stat    = beta_base / se_base,
    p_value   = 2 * pnorm(-abs(t_stat)),
    ic_low    = beta_base - z_critico * se_base,
    ic_high   = beta_base + z_critico * se_base,
    alerta_sinal     = beta_base > beta_sinal_errado,
    alerta_magnitude = abs(beta_base) > beta_magnitude_max,
    alerta_p         = p_value > p_value_max,
    n_alertas        = as.integer(alerta_sinal) + as.integer(alerta_magnitude) + as.integer(alerta_p),
    gravidade        = case_when(
      n_alertas == 0 ~ "OK",
      n_alertas == 1 ~ "Warning",
      TRUE           ~ "Critical"
    )
  ) %>%
  arrange(desc(n_alertas), desc(ton_base_prod))

# Summary
n_alertas_total <- sum(betas_audit$n_alertas > 0, na.rm = TRUE)
n_sinal  <- sum(betas_audit$alerta_sinal,     na.rm = TRUE)
n_mag    <- sum(betas_audit$alerta_magnitude, na.rm = TRUE)
n_pval   <- sum(betas_audit$alerta_p,         na.rm = TRUE)

cat(sprintf("  Total de betas: %d | Alertas: %d | Sinal errado: %d | Magnitude: %d | p>0.20: %d\n",
            nrow(betas_audit), n_alertas_total, n_sinal, n_mag, n_pval))

if (n_alertas_total > 0) {
  cat("\n  === BETAS SUSPEITOS ===\n")
  betas_audit %>%
    filter(n_alertas > 0) %>%
    select(product, beta_base, se_base, t_stat, p_value,
           ton_base_prod, gravidade, alerta_sinal, alerta_magnitude, alerta_p) %>%
    mutate(across(c(beta_base, se_base, t_stat), ~round(., 4)),
           p_value      = round(p_value, 3),
           ton_base_prod = round(ton_base_prod / 1e3, 1)) %>%
    rename(`β` = beta_base, SE = se_base, `t` = t_stat, `p` = p_value,
           `ton (mil)` = ton_base_prod) %>%
    print(n = Inf)
}

write.csv(
  betas_audit %>%
    select(product, beta_base, se_base, t_stat, p_value, ic_low, ic_high,
           ton_base_prod, gravidade, alerta_sinal, alerta_magnitude, alerta_p, n_alertas),
  file.path(dir_output, "41_auditoria_alertas.csv"),
  row.names = FALSE
)

# ── 2. Dot plot of betas with expected zone ────────────────────────────────────

p_audit_betas <- betas_audit %>%
  mutate(
    product_f = factor(product, levels = rev(product[order(ton_base_prod)])),
    cor_ponto = case_when(
      gravidade == "Critical"  ~ "#D62728",
      gravidade == "Warning"  ~ "#FF7F0E",
      TRUE                   ~ "#1F77B4"
    )
  ) %>%
  ggplot(aes(x = beta_base, y = product_f)) +
  # Expected zone for commodities
  annotate("rect",
           xmin = zona_esperada[1], xmax = zona_esperada[2],
           ymin = -Inf, ymax = Inf,
           fill = "#4DAF4A", alpha = 0.08) +
  annotate("text",
           x = mean(zona_esperada), y = Inf,
           label = "Zona esperada\ncommodities",
           vjust = 1.3, size = 3, color = "#4DAF4A") +
  geom_vline(xintercept = 0, linetype = "dashed", color = "gray40") +
  # IC 95%
  geom_errorbarh(aes(xmin = ic_low, xmax = ic_high),
                 height = 0.25, alpha = 0.35,
                 color = betas_audit$cor_ponto[
                   match(betas_audit$product,
                         levels(betas_audit %>%
                                  arrange(desc(ton_base_prod)) %>%
                                  pull(product) %>%
                                  rev()))]) +
  # Points coloured by severity
  geom_point(aes(size = ton_base_prod / 1e3, color = gravidade), alpha = 0.9) +
  scale_color_manual(
    values = c("OK" = "#1F77B4", "Warning" = "#FF7F0E", "Critical" = "#D62728"),
    name   = "Diagnosis"
  ) +
  scale_size_continuous(name = "Base volume\n(thousand ton)", range = c(2, 8)) +
  labs(
    title    = paste("Beta audit —", setor_label),
    subtitle = sprintf("Green zone = expected range [%.1f, %.1f] | Size ∝ volume | N=%d alerts",
                       zona_esperada[1], zona_esperada[2], n_alertas_total),
    x = "β (price-demand elasticity)", y = NULL,
    caption = "Red = critical (≥2 alerts) | Orange = warning (1 alert) | Blue = OK"
  ) +
  theme_minimal(base_size = 11) +
  theme(plot.title      = element_text(face = "bold"),
        legend.position = "bottom",
        panel.grid.minor = element_blank())

ggsave(file.path(dir_output, "41b_auditoria_betas.png"),
       p_audit_betas,
       width  = 10,
       height = max(5, nrow(betas_audit) * 0.38 + 2),
       dpi    = 150)

# ── 3. Time series: log_price_rel vs DV (top-10 by volume) ───────────────

cat("\n  Time series for the top-10 products by volume...\n")

top_produtos <- ton_prod %>%
  arrange(desc(ton_base_prod)) %>%
  slice_head(n = 10) %>%
  pull(product)

# Detect the model DV (share or ton)
tem_share <- "share" %in% names(df)
dv_col    <- if (tem_share && !all(is.na(df$share))) "share" else "ton"
dv_label  <- if (dv_col == "share") "Market share" else "Volume (ton)"

series_df <- df %>%
  filter(product %in% top_produtos, exporter %in% paises_grupo,
         !is.na(log_price_rel), !is.na(.data[[dv_col]])) %>%
  select(exporter, product, year, log_price_rel, dv = all_of(dv_col))

if (nrow(series_df) > 0) {
  # Normalise DV for visual comparison on the same scale
  series_norm <- series_df %>%
    group_by(exporter, product) %>%
    mutate(
      dv_norm    = (dv - mean(dv, na.rm = TRUE)) /
                   pmax(sd(dv, na.rm = TRUE), 1e-10),
      price_norm = (log_price_rel - mean(log_price_rel, na.rm = TRUE)) /
                   pmax(sd(log_price_rel, na.rm = TRUE), 1e-10)
    ) %>%
    ungroup() %>%
    pivot_longer(cols = c(dv_norm, price_norm),
                 names_to  = "serie",
                 values_to = "value") %>%
    mutate(
      serie = if_else(serie == "price_norm", "log_price_rel (norm.)",
                      paste0(dv_label, " (norm.)")),
      produto_pais = paste0(product, " — ", exporter)
    )

  n_combos <- n_distinct(series_norm$produto_pais)

  # ncol grows with the number of combinations (product x country) to keep
  # the plot height within the 50" ggsave limit when paises_grupo
  # is large.
  ncol_series <- if (n_combos > 60) 6 else if (n_combos > 30) 4 else 2

  p_series <- series_norm %>%
    ggplot(aes(x = year, y = value, color = serie, group = serie)) +
    geom_line(linewidth = 0.8, alpha = 0.85) +
    geom_point(size = 1.5, alpha = 0.7) +
    geom_hline(yintercept = 0, linetype = "dotted", color = "gray60") +
    facet_wrap(~produto_pais, scales = "free_y", ncol = ncol_series) +
    scale_color_manual(
      values = c("#D62728", "#1F77B4"),
      name   = NULL
    ) +
    labs(
      title    = paste("Time series: relative price vs", dv_label, "—", setor_label),
      subtitle = "Normalised variables (z-score) for visual comparison | Moving in opposition → negative beta expected",
      x = NULL, y = "Standard deviations from the mean",
      caption  = paste("Top-10 products by volume | Countries:", paste(paises_grupo, collapse = ", "))
    ) +
    theme_minimal(base_size = 10) +
    theme(
      plot.title      = element_text(face = "bold"),
      legend.position = "bottom",
      strip.text      = element_text(face = "bold", size = 8),
      panel.grid.minor = element_blank()
    )

  ggsave(file.path(dir_output, "42_auditoria_series.png"),
         p_series,
         width  = min(49, max(14, ncol_series * 7)),
         height = min(49, max(8, ceiling(n_combos / ncol_series) * 3.5)),
         dpi    = 150)
  cat(sprintf("  Series generated: %d product × country combinations\n", n_combos))
} else {
  cat("  Warning: no data to plot the time series.\n")
}

# ── 4. Temporal stability, 5-year windows ──────────────────────────────

cat("\n  Estabilidade temporal do beta global...\n")

anos_disponiveis <- sort(unique(df$year))
janela_est       <- 5

if (length(anos_disponiveis) >= janela_est + 1) {

  # Determine the main regressor of the model
  regressor_col <- case_when(
    "d_log_price_rel"    %in% names(df) &&
      sum(!is.na(df$d_log_price_rel)) > 0     ~ "d_log_price_rel",
    "log_price_rel_lag"  %in% names(df) &&
      sum(!is.na(df$log_price_rel_lag)) > 0   ~ "log_price_rel_lag",
    TRUE                                       ~ "log_price_rel"
  )
  regressor_label <- switch(regressor_col,
    "d_log_price_rel"   = "Δlog_price_rel",
    "log_price_rel_lag" = "log_price_rel_lag",
    "log_price_rel"
  )

  anos_fim <- anos_disponiveis[anos_disponiveis >= min(anos_disponiveis) + janela_est - 1]

  betas_janela <- map_dfr(anos_fim, function(ano_fim) {
    ano_ini <- ano_fim - janela_est + 1
    df_jan  <- df %>%
      filter(year >= ano_ini, year <= ano_fim,
             !is.na(.data[[regressor_col]]),
             !is.na(.data[[dv_col]]))

    if (nrow(df_jan) < 20) return(NULL)

    tryCatch({
      fml <- as.formula(
        paste0(dv_col, " ~ ", regressor_col,
               ":factor(product) | exporter^product + product^year")
      )
      mod <- fepois(fml, data = df_jan,
                    cluster = ~exporter + year,
                    warn    = FALSE, notes = FALSE)

      tidy(mod) %>%
        filter(grepl(regressor_col, term)) %>%
        mutate(
          product  = str_trim(gsub(
            paste0(regressor_col, ":factor\\(product\\)|factor\\(product\\):"),
            "", term
          )),
          ano_ini  = ano_ini,
          ano_fim  = ano_fim,
          janela   = paste0(ano_ini, "–", ano_fim),
          beta_global = weighted.mean(estimate, 1 / std.error^2, na.rm = TRUE),
          se_global   = 1 / sqrt(sum(1 / std.error^2, na.rm = TRUE))
        ) %>%
        distinct(janela, ano_ini, ano_fim, beta_global, se_global) %>%
        slice(1)
    }, error = function(e) NULL)
  })

  if (!is.null(betas_janela) && nrow(betas_janela) > 1) {

    p_estab <- betas_janela %>%
      mutate(
        ic_low  = beta_global - z_critico * se_global,
        ic_high = beta_global + z_critico * se_global,
        janela  = factor(janela, levels = janela)
      ) %>%
      ggplot(aes(x = janela, y = beta_global)) +
      geom_hline(yintercept = 0, linetype = "dashed", color = "gray50") +
      annotate("rect",
               xmin = -Inf, xmax = Inf,
               ymin = zona_esperada[1], ymax = zona_esperada[2],
               fill = "#4DAF4A", alpha = 0.08) +
      geom_errorbar(aes(ymin = ic_low, ymax = ic_high),
                    width = 0.25, color = "#1F77B4", alpha = 0.5) +
      geom_line(group = 1, color = "#1F77B4", linewidth = 0.9) +
      geom_point(color = "#1F77B4", size = 3) +
      scale_y_continuous(breaks = scales::pretty_breaks(n = 6)) +
      labs(
        title    = paste("Temporal stability of the beta —", setor_label),
        subtitle = paste0("Precision-weighted global beta | Windows of ", janela_est,
                          " years | Regressor: ", regressor_label),
        x = paste0("Window (", janela_est, " years)"),
        y = "Global β (precision-weighted)",
        caption = "Green zone = expected range for commodities | Bars = 95% CI"
      ) +
      theme_minimal(base_size = 11) +
      theme(
        plot.title       = element_text(face = "bold"),
        axis.text.x      = element_text(angle = 35, hjust = 1),
        panel.grid.minor = element_blank()
      )

    ggsave(file.path(dir_output, "43_auditoria_estabilidade.png"),
           p_estab, width = 10, height = 5, dpi = 150)

    cat(sprintf("  Windows estimated: %d | Mean beta: %.4f | Range: [%.4f, %.4f]\n",
                nrow(betas_janela),
                mean(betas_janela$beta_global, na.rm = TRUE),
                min(betas_janela$beta_global,  na.rm = TRUE),
                max(betas_janela$beta_global,  na.rm = TRUE)))

    write.csv(betas_janela,
              file.path(dir_output, "43b_auditoria_estabilidade.csv"),
              row.names = FALSE)
  } else {
    cat("  Warning: too little data for temporal stability.\n")
  }
} else {
  cat(sprintf("  Warning: fewer than %d years available, temporal stability skipped.\n",
              janela_est + 1))
}

cat("[ 10 ] Auditoria OK\n")

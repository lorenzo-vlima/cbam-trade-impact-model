############################################
# 04_validacao.R — PPML share
# ----------------------------------------
# Genuine out-of-sample validation:
#   1. Re-estimates up to ano_val_treino
#   2. Predicts share for each year in anos_val_teste
#   3. Compares predicted vs. actual, by year and pooled
#
# Modos de uso:
#   Modo simples  : ano_val_treino = 2024, ano_val_teste = 2025
#   Multi-year mode: ano_val_treino = 2022, anos_val_teste = c(2023, 2024, 2025)
#
#   If anos_val_teste is not defined in the environment,
#   the script uses c(ano_val_teste) automatically.
#
# Depende de: 01_limpeza.R
# Produces: df_val, df_val_all (multi-year), metrics, charts
############################################

# ── Resolve which years to test ────────────────────────────────────────────────

anos_val_teste <- if (exists("anos_val_teste") && length(anos_val_teste) >= 1) {
  sort(unique(anos_val_teste))
} else {
  c(ano_val_teste)
}

multi_ano <- length(anos_val_teste) > 1
ano_pred  <- anos_val_teste[length(anos_val_teste)]   # last year (for compatibility)

if (multi_ano) {
  cat(sprintf("[ 04 ] Multi-year out-of-sample validation (%d → %s)...\n",
              ano_val_treino, paste(anos_val_teste, collapse = ", ")))
} else {
  cat("[ 04 ] Out-of-sample validation (", ano_val_treino, "→", ano_pred, ")...\n")
}

arquivo_price <- switch(produto_ativo,
  "aluminio"  = file.path(dir_config, "Base_de_dados_final_Aluminio.csv"),
  "ferro_aco" = file.path(dir_config, "Base_de_dados_final_Ferro.csv"),
  "cimento"   = file.path(dir_config, "Base_de_dados_final_Cimento.csv"),
  stop("invalid produto_ativo: ", produto_ativo)
)

# ── 1. Training up to ano_val_treino ──────────────────────────────────────────────

df_train <- preparar_pesos(
  df %>% filter(year >= ano_inicio, year <= ano_val_treino),
  usar_peso_tempo, half_life
)

for (cod in paises_grupo) {
  df_train[[paste0("d_", cod)]] <- if_else(df_train$exporter == cod, 1L, 0L)
}

cat("  Training obs:", nrow(df_train), "\n")

# ── 2. Estimate global (by product) ───────────────────────────────────────────

model_global_val <- tryCatch(
  fepois(
    share ~ log_price_rel:factor(product) | exporter^product + product^year,
    data    = df_train,
    weights = ~peso_tempo,
    cluster = ~exporter + year
  ),
  error = function(e) {
    cat("  Warning: global fepois did not converge —", conditionMessage(e), "\n"); NULL
  }
)
if (is.null(model_global_val)) {
  cat("[ 04 ] SKIPPED (global model not estimated)\n\n"); return(invisible(NULL))
}

beta_global_val <- extrair_betas_globais(model_global_val) %>%
  rename(beta_base = beta_global, se_base = se_global)

if (nrow(beta_global_val) == 0) {
  cat("  Warning: no global beta extracted.\n")
  cat("[ 04 ] PULADO\n\n"); return(invisible(NULL))
}

# ── 3. Estimate country differentials ─────────────────────────────────────────

termos_dif_val <- paste0(
  "log_price_rel:d_", paises_grupo, ":factor(product)",
  collapse = " + "
)

df_conj_val <- df_train %>%
  left_join(beta_global_val %>% select(product, beta_base), by = "product") %>%
  filter(!is.na(beta_base)) %>%
  mutate(offset_term = beta_base * log_price_rel)

formula_conj_val <- as.formula(paste(
  "share ~ offset(offset_term) +", termos_dif_val,
  "| exporter^product + product^year"
))

model_conj_val <- tryCatch(
  fepois(
    formula_conj_val,
    data    = df_conj_val,
    weights = ~peso_tempo,
    cluster = ~exporter + year
  ),
  error = function(e) {
    cat("  Warning: joint fepois did not converge —", conditionMessage(e), "\n"); NULL
  }
)

if (is.null(model_conj_val)) {
  cat("  Warning: using global betas only (no differentials).\n")
  coefs_val <- tibble(term = character(), estimate = numeric(), std.error = numeric())
} else {
  coefs_val <- tidy(model_conj_val)
}

betas_dif_val_list <- map(paises_grupo, function(cod) {
  coefs_val %>%
    filter(grepl(paste0("d_", cod), term)) %>%
    mutate(product = str_trim(gsub(
      paste0("log_price_rel:d_", cod, ":factor\\(product\\)|",
             "log_price_rel:factor\\(product\\)|:d_", cod),
      "", term
    ))) %>%
    select(product, estimate, std.error) %>%
    rename(
      !!paste0("beta_dif_", cod) := estimate,
      !!paste0("se_dif_",   cod) := std.error
    )
})

betas_val <- montar_betas_simulacao(
  df_train %>% distinct(product) %>% mutate(product = str_trim(as.character(product))),
  beta_global_val %>% rename(beta_global = beta_base, se_global = se_base),
  betas_dif_val_list, paises_grupo, z_critico
)

cat("  Validation betas:", nrow(betas_val), "products\n")

# ── 4. Load raw data for ALL test years ─────────────────────

df_raw_todos <- read.csv(file = arquivo_price, header = TRUE, sep = ";") %>%
  mutate(
    product = as.character(product),
    euro    = as.numeric(euro),
    ton     = as.numeric(ton),
    year    = as.numeric(year),
    tariff  = as.numeric(tariff),
    price   = if_else(ton > 0, euro / ton, NA_real_)
  ) %>%
  filter(year %in% anos_val_teste, !is.na(ton), !is.na(euro), !is.na(tariff),
         ton >= 0, euro >= 0)

if (nrow(df_raw_todos) == 0) {
  cat("  Warning: no data for anos_val_teste =",
      paste(anos_val_teste, collapse = ", "), ". Pulando.\n")
  cat("[ 04 ] PULADO\n\n")
  return(invisible(NULL))
}

if (price_model == "post_tax") {
  df_raw_todos <- df_raw_todos %>%
    mutate(price = price * (1 + tariff))
}

df_raw_todos <- df_raw_todos %>%
  mutate(euro_loo = if_else(price_model == "post_tax" & !is.na(price),
                             price * ton, euro)) %>%
  group_by(product, year) %>%
  mutate(
    total_ton_all  = sum(ton,      na.rm = TRUE),
    total_euro_all = sum(euro_loo, na.rm = TRUE),
    total_ton_loo  = total_ton_all  - ton,
    total_euro_loo = total_euro_all - euro_loo,
    price_avg_loo  = if_else(total_ton_loo > 0, total_euro_loo / total_ton_loo, NA_real_),
    share          = if_else(total_ton_all > 0, ton / total_ton_all, NA_real_),
    price_rel      = if_else(!is.na(price) & !is.na(price_avg_loo) & price_avg_loo > 0,
                             price / price_avg_loo, NA_real_),
    log_price_rel  = log(price_rel)
  ) %>%
  ungroup()

# ── 5. Starting base: always the last training year ────────────────────────

df_base <- df %>%
  filter(year == ano_val_treino, !is.na(log_price_rel), !is.na(share)) %>%
  select(exporter, product,
         log_price_rel_base = log_price_rel,
         share_base         = share)

# ── 6. Loop over test years ──────────────────────────────────────────────────

beta_global_medio <- mean(betas_val$beta_base, na.rm = TRUE)
cols_sim          <- paste0("beta_sim_", paises_grupo)
cores_grupo_val   <- setNames(scales::hue_pal()(length(paises_grupo)), paises_grupo)

resultados_val    <- list()
metricas_por_ano  <- list()

for (ano_t in anos_val_teste) {

  cat(sprintf("\n  ── Test year: %d ──\n", ano_t))

  df_pred_t <- df_raw_todos %>%
    filter(year == ano_t, !is.na(log_price_rel), !is.na(share)) %>%
    select(exporter, product,
           log_price_rel_pred = log_price_rel,
           share_real         = share)

  df_val_t <- df_base %>%
    inner_join(df_pred_t, by = c("exporter", "product"))

  cat("  Pairs for validation:", nrow(df_val_t), "\n")

  if (nrow(df_val_t) < 2) {
    cat("  Warning: fewer than 2 pairs. Skipping this year.\n")
    next
  }

  # Aplicar betas
  df_val_t <- df_val_t %>%
    left_join(betas_val %>% select(product, all_of(cols_sim)), by = "product") %>%
    mutate(beta_usado = beta_global_medio)

  for (cod in paises_grupo) {
    col <- paste0("beta_sim_", cod)
    df_val_t <- df_val_t %>%
      mutate(beta_usado = if_else(
        exporter == cod & !is.na(.data[[col]]),
        .data[[col]], beta_usado
      ))
  }

  df_val_t <- df_val_t %>%
    mutate(
      ano             = ano_t,
      delta_log_price = log_price_rel_pred - log_price_rel_base,
      share_pred      = pmin(share_base * exp(beta_usado * delta_log_price), 1),
      erro_abs        = abs(share_pred - share_real),
      erro_pct        = abs(share_pred - share_real) / share_real
    )

  resultados_val[[as.character(ano_t)]] <- df_val_t

  # ── Metrics for the year ───────────────────────────────────────────────────────
  mae_t    <- mean(df_val_t$erro_abs, na.rm = TRUE)
  mape_t   <- mean(df_val_t$erro_pct[is.finite(df_val_t$erro_pct)], na.rm = TRUE)
  n_t      <- sum(!is.na(df_val_t$share_pred) & !is.na(df_val_t$share_real))
  cor_t    <- if (n_t >= 2) cor(df_val_t$share_pred, df_val_t$share_real,
                                 use = "complete.obs") else NA_real_

  # Naive MAE: predict share_real = share_base (without applying beta)
  mae_naive_t  <- mean(abs(df_val_t$share_base - df_val_t$share_real), na.rm = TRUE)

  # Skill score: how much the model improves on the naive (>0 = better; =1 = perfect)
  skill_t      <- if (mae_naive_t > 0) 1 - mae_t / mae_naive_t else NA_real_

  # Relative MAE: error as % of the mean observed share
  share_medio_t  <- mean(df_val_t$share_real, na.rm = TRUE)
  mae_relativo_t <- if (share_medio_t > 0) mae_t / share_medio_t else NA_real_

  metricas_por_ano[[as.character(ano_t)]] <- tibble(
    ano          = ano_t,
    n            = n_t,
    cor          = cor_t,
    mae          = mae_t,
    mae_naive    = mae_naive_t,
    skill_score  = skill_t,       # 1 - MAE/MAE_naive  (>0 = melhor que naive)
    mae_relativo = mae_relativo_t, # MAE / mean_share  (<0.5 = reasonable)
    share_medio  = share_medio_t
  )

  cat(sprintf("  Cor: %s | MAE: %.6f | MAE naive: %.6f | Skill: %s | MAE/mean_share: %s\n",
              if (is.na(cor_t))   "NA" else round(cor_t, 4),
              mae_t,
              mae_naive_t,
              if (is.na(skill_t))      "NA" else sprintf("%.1f%%", skill_t * 100),
              if (is.na(mae_relativo_t)) "NA" else sprintf("%.1f%%", mae_relativo_t * 100)))

  for (cod in paises_grupo) {
    cat("\n  ---", cod, "---\n")
    df_val_t %>%
      filter(exporter == cod) %>%
      select(product, share_base, share_pred, share_real, erro_pct) %>%
      mutate(across(where(is.numeric), ~round(.x, 5))) %>%
      as_tibble() %>%
      print(n = Inf)
  }

  # Overall chart for the year
  cor_label_t <- if (is.na(cor_t)) "NA" else round(cor_t, 3)
  p_geral_t <- ggplot(df_val_t, aes(x = share_real, y = share_pred)) +
    geom_point(alpha = 0.3) +
    geom_abline(slope = 1, intercept = 0, col = "red", linetype = "dashed") +
    { if (n_t >= 3) geom_smooth(method = "lm", col = "steelblue", se = FALSE) } +
    labs(
      title    = paste("PPML share validation —", produto_ativo, "(", ano_t, ")"),
      subtitle = paste0("Cor: ", cor_label_t, " | MAPE: ", round(mape_t * 100, 1), "%"),
      x = paste("Actual share", ano_t),
      y = paste("Predicted share", ano_t)
    ) +
    theme_minimal()

  ggsave(file.path(dir_output, paste0("5_validacao_geral_", ano_t, ".png")),
         plot = p_geral_t, width = 8, height = 5, dpi = 150)

  # Top-30 chart for the year
  top30_t <- df_raw_todos %>%
    filter(year == ano_t, !is.na(share)) %>%
    group_by(exporter) %>%
    summarise(share_total = sum(share, na.rm = TRUE)) %>%
    slice_max(share_total, n = 30) %>%
    pull(exporter)

  df_val_plot_t <- df_val_t %>%
    mutate(
      destaque  = case_when(
        exporter %in% paises_grupo ~ exporter,
        exporter %in% top30_t      ~ "Top 30",
        TRUE                        ~ "Outros"
      ),
      alpha_val = if_else(destaque == "Outros", 0.15, 0.85),
      size_val  = case_when(
        exporter %in% paises_grupo ~ 3.5,
        exporter %in% top30_t      ~ 2.0,
        TRUE                        ~ 1.2
      )
    )

  cores_plot <- c(cores_grupo_val, "Top 30" = "#E8A020", "Outros" = "gray50")

  p_top30_t <- ggplot(df_val_plot_t,
                      aes(x = share_real, y = share_pred,
                          color = destaque, size = size_val, alpha = alpha_val)) +
    geom_point() +
    geom_abline(slope = 1, intercept = 0, col = "red", linetype = "dashed") +
    scale_color_manual(values = cores_plot) +
    scale_size_identity() +
    scale_alpha_identity() +
    labs(title    = paste("PPML share validation —", produto_ativo, "(", ano_t, ")"),
         subtitle = paste("Group:", nome_grupo),
         x = paste("Actual share", ano_t),
         y = paste("Predicted share", ano_t),
         color = NULL) +
    theme_minimal()

  ggsave(file.path(dir_output, paste0("6_validacao_top30_", ano_t, ".png")),
         plot = p_top30_t, width = 8, height = 5, dpi = 150)

  # Per-country charts for the year
  for (cod in paises_grupo) {
    df_val_pais_t <- df_val_t %>% filter(exporter == cod) %>% mutate(label = product)
    if (nrow(df_val_pais_t) == 0) next
    p_pais_t <- ggplot(df_val_pais_t, aes(x = share_real, y = share_pred, label = label)) +
      geom_point(color = cores_grupo_val[cod], size = 3) +
      geom_text(nudge_y = max(df_val_pais_t$share_real, na.rm = TRUE) * 0.02,
                size = 3, color = "gray30") +
      geom_abline(slope = 1, intercept = 0, col = "red", linetype = "dashed") +
      labs(title = paste("Validation —", cod, "(", ano_t, ")"),
           x = paste("Actual share", ano_t),
           y = paste("Predicted share", ano_t)) +
      theme_minimal()
    ggsave(file.path(dir_output,
                     paste0("7_validacao_", tolower(cod), "_", ano_t, ".png")),
           plot = p_pais_t, width = 7, height = 5, dpi = 150)
  }
}

# ── 7. Consolidar resultados ──────────────────────────────────────────────────

if (length(resultados_val) == 0) {
  cat("[ 04 ] SKIPPED (no year produced results)\n\n")
  return(invisible(NULL))
}

df_val_all <- bind_rows(resultados_val)
df_val     <- df_val_all %>% filter(ano == max(ano))   # compatibilidade legada

tab_metricas <- bind_rows(metricas_por_ano)

cat("\n  ══ Out-of-sample validation summary ══\n")
cat(sprintf("  Treino: %d–%d | Teste: %s\n",
            ano_inicio, ano_val_treino, paste(anos_val_teste, collapse = ", ")))
print(tab_metricas %>%
        mutate(
          cor          = round(cor, 3),
          mae          = round(mae, 6),
          mae_naive    = round(mae_naive, 6),
          skill_score  = paste0(round(skill_score  * 100, 1), "%"),
          mae_relativo = paste0(round(mae_relativo * 100, 1), "%"),
          share_medio  = round(share_medio, 6)
        ))

cat("\n  Interpretation:\n")
cat("    skill_score  > 0%  → model beats the naive (predicting the status quo)\n")
cat("    mae_relativo < 50% → error < half the mean share (reasonable)\n")
cat("    mae_relativo < 20% → error < 1/5 of the mean share (good)\n")

write.csv(tab_metricas,
          file.path(dir_output, "5b_validacao_metricas.csv"),
          row.names = FALSE)

# ── 8. Pooled chart (multi-year only) ────────────────────────────────────

if (multi_ano && nrow(tab_metricas) >= 2) {

  p_metricas <- tab_metricas %>%
    ggplot(aes(x = ano)) +
    geom_line(aes(y = cor, color = "Correlation"), linewidth = 1) +
    geom_point(aes(y = cor, color = "Correlation"), size = 3) +
    geom_line(aes(y = skill_score, color = "Skill score"), linewidth = 1, linetype = "dashed") +
    geom_point(aes(y = skill_score, color = "Skill score"), size = 3) +
    geom_hline(yintercept = 0, linetype = "dotted", color = "gray50") +
    scale_color_manual(values = c("Correlation" = "#1F77B4", "Skill score" = "#D62728")) +
    scale_x_continuous(breaks = anos_val_teste) +
    labs(
      title    = paste("Out-of-sample predictive quality —", produto_ativo),
      subtitle = paste0("Training up to ", ano_val_treino,
                        " | Forecast: ", paste(anos_val_teste, collapse = ", "),
                        " | Skill = 1 − MAE/MAE_naive"),
      x = "Test year", y = NULL, color = NULL
    ) +
    theme_minimal(base_size = 11) +
    theme(legend.position = "bottom")

  ggsave(file.path(dir_output, "5c_validacao_evolucao.png"),
         plot = p_metricas, width = 8, height = 5, dpi = 150)

  # Pooled scatter: all years together, coloured by year
  p_consolidado <- df_val_all %>%
    ggplot(aes(x = share_real, y = share_pred, color = factor(ano))) +
    geom_point(alpha = 0.25, size = 1.2) +
    geom_abline(slope = 1, intercept = 0, col = "black", linetype = "dashed") +
    facet_wrap(~ano, ncol = length(anos_val_teste)) +
    scale_color_brewer(palette = "Set1") +
    labs(
      title    = paste("Out-of-sample validation —", produto_ativo),
      subtitle = paste0("Training: ", ano_inicio, "–", ano_val_treino),
      x = "Actual share", y = "Predicted share", color = "Year"
    ) +
    theme_minimal(base_size = 10) +
    theme(legend.position = "none")

  ggsave(file.path(dir_output, "5d_validacao_consolidado.png"),
         plot = p_consolidado,
         width = 4 * length(anos_val_teste), height = 5, dpi = 150)
}

cat("[ 04 ] OK\n\n")

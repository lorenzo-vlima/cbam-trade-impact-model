############################################
# 04b_validacao_delta.R
# ----------------------------------------
# Additional validation: β as an elasticity
# of CHANGES (not of levels).
#
# Logic:
#   For each pair (exporter × product):
#     Δlog(DV)_obs  = log(DV_teste) - log(DV_base)
#     Δlog(DV)_pred = β_sim × Δlog(price_rel)
#
#   If β captures substitution well, the two
#   series should be positively correlated and
#   have a slope close to 1.
#
# Metrics:
#   cor       → does β get the direction right?
#   slope     → β bem calibrado em magnitude?
#   sign_acc  → % of pairs with the correct sign
#   mae_delta → mean error in Δlog
#
# DV deste script: share
#
# Depends (in memory): df, betas_simulacao,
#   paises_grupo, janela_base, ano_val_treino,
#   ano_val_teste, dir_output, produto_ativo
############################################

cat("[ 04b ] Delta validation — β as an elasticity of changes (share)...\n")

# ── Parameters ─────────────────────────────────────────────────────────────────
dv_col       <- "share"
min_dv_delta <- 0          # share > 0 is enough

anos_base_val  <- (ano_val_treino - janela_base + 1):ano_val_treino
anos_teste_val <- (ano_val_treino + 1):ano_val_teste

if (length(anos_teste_val) == 0) {
  cat("  [04b] No test year available — skipping.\n")
  cat("[ 04b ] OK\n")
} else {

cat(sprintf("  DV: %s | Base: %d–%d | Test: %d–%d\n",
            dv_col,
            min(anos_base_val), max(anos_base_val),
            min(anos_teste_val), max(anos_teste_val)))

# ── 1. Base period: ALL exporters with enough data ──────────────
base_df <- df %>%
  filter(year %in% anos_base_val,
         .data[[dv_col]] > min_dv_delta,
         price_rel > 0, is.finite(price_rel)) %>%
  group_by(exporter, product) %>%
  summarise(
    dv_base        = mean(.data[[dv_col]], na.rm = TRUE),
    price_rel_base = mean(price_rel,       na.rm = TRUE),
    n_base         = n(),
    .groups        = "drop"
  ) %>%
  filter(dv_base > 0, price_rel_base > 0, n_base >= 1)

cat(sprintf("  Exporters in base period: %d | Exp×prod pairs: %d\n",
            n_distinct(base_df$exporter), nrow(base_df)))

# ── 2. Test period: ALL exporters ───────────────────────────────────
test_df <- df %>%
  filter(year %in% anos_teste_val,
         .data[[dv_col]] > min_dv_delta,
         price_rel > 0, is.finite(price_rel)) %>%
  select(exporter, product, year,
         dv_obs         = all_of(dv_col),
         price_rel_test = price_rel)

# ── 3. Betas: focal = beta_sim_X; others = beta_base (global by product) ─────
#
# β was estimated with all exporters, so it makes sense to test it on all of them.
# Focal countries (paises_grupo) get the shrinkage-adjusted β.
# All others get the global β by product (beta_base).

beta_cols_disp <- intersect(paste0("beta_sim_", paises_grupo),
                             names(betas_simulacao))

# Betas of focal countries (shrinkage-adjusted)
beta_focal <- betas_simulacao %>%
  select(product, all_of(beta_cols_disp)) %>%
  pivot_longer(
    cols         = all_of(beta_cols_disp),
    names_to     = "exporter",
    names_prefix = "beta_sim_",
    values_to    = "beta_sim"
  ) %>%
  filter(!is.na(beta_sim)) %>%
  mutate(grupo_exporter = "focal")

# Betas of all other exporters (global beta)
exportadores_nao_focais <- setdiff(unique(base_df$exporter), paises_grupo)

beta_outros <- tidyr::expand_grid(
  betas_simulacao %>%
    select(product, beta_sim = beta_base) %>%
    filter(!is.na(beta_sim)),
  exporter = exportadores_nao_focais
) %>%
  mutate(grupo_exporter = "outros")

beta_long <- bind_rows(beta_focal, beta_outros)

# ── 4. Combinar e computar deltas ─────────────────────────────────────────────
delta_df <- test_df %>%
  left_join(base_df,   by = c("exporter", "product")) %>%
  left_join(beta_long, by = c("exporter", "product")) %>%
  filter(!is.na(dv_base), !is.na(price_rel_base), !is.na(beta_sim),
         dv_base > 0, price_rel_base > 0) %>%
  mutate(
    # Observed and predicted change (in logs)
    delta_log_dv_obs  = log(dv_obs)         - log(dv_base),
    delta_log_price   = log(price_rel_test)  - log(price_rel_base),
    delta_log_dv_pred = beta_sim * delta_log_price,

    # Residual and sign hit
    residuo      = delta_log_dv_obs - delta_log_dv_pred,
    sign_correct = sign(delta_log_dv_obs) == sign(delta_log_dv_pred)
  ) %>%
  filter(is.finite(delta_log_dv_obs),
         is.finite(delta_log_dv_pred),
         is.finite(residuo))

cat(sprintf("  Pairs used in delta validation: %d\n", nrow(delta_df)))

if (nrow(delta_df) < 4) {
  cat("  [04b] Insufficient data — skipping metrics.\n")
} else {

# ── 5. Metrics by year × country ────────────────────────────────────────────────
.calc_metricas_delta <- function(d) {
  n <- nrow(d)
  if (n < 3) return(tibble(n = n, cor = NA_real_, slope = NA_real_,
                            sign_acc = NA_real_, mae_delta = NA_real_))
  cor_v   <- cor(d$delta_log_dv_obs, d$delta_log_dv_pred)
  slope_v <- tryCatch(
    coef(lm(delta_log_dv_obs ~ delta_log_dv_pred, data = d))[[2]],
    error = function(e) NA_real_
  )
  tibble(
    n         = n,
    cor       = round(cor_v,                                            3),
    slope     = round(slope_v,                                          3),
    sign_acc  = round(mean(d$sign_correct, na.rm = TRUE) * 100,        1),
    mae_delta = round(mean(abs(d$residuo),  na.rm = TRUE),             4)
  )
}

# ── Metrics by group: overall, focal, others, and individual focal ──────────────

# Overall (all exporters) — by year + pooled
metricas_geral_ano <- delta_df %>%
  group_by(ano = as.character(year)) %>%
  group_modify(~ .calc_metricas_delta(.x)) %>%
  ungroup() %>%
  mutate(grupo = "geral")

metricas_geral_pool <- .calc_metricas_delta(delta_df) %>%
  mutate(ano = "pooled", grupo = "geral")

metricas_geral <- bind_rows(metricas_geral_ano, metricas_geral_pool)

# By focal group / others — by year + pooled
metricas_grupos_ano <- delta_df %>%
  group_by(ano = as.character(year), grupo = grupo_exporter) %>%
  group_modify(~ .calc_metricas_delta(.x)) %>%
  ungroup()

metricas_grupos_pool <- delta_df %>%
  group_by(grupo = grupo_exporter) %>%
  group_modify(~ .calc_metricas_delta(.x)) %>%
  ungroup() %>%
  mutate(ano = "pooled")

metricas_grupos <- bind_rows(metricas_grupos_ano, metricas_grupos_pool)

# By individual focal country
metricas_focais <- delta_df %>%
  filter(grupo_exporter == "focal") %>%
  group_by(ano = as.character(year), exporter) %>%
  group_modify(~ .calc_metricas_delta(.x)) %>%
  ungroup() %>%
  bind_rows(
    delta_df %>%
      filter(grupo_exporter == "focal") %>%
      group_by(exporter) %>%
      group_modify(~ .calc_metricas_delta(.x)) %>%
      ungroup() %>%
      mutate(ano = "pooled")
  ) %>%
  mutate(grupo = exporter)

metricas_total <- bind_rows(metricas_geral, metricas_grupos, metricas_focais) %>%
  mutate(setor = produto_ativo) %>%
  arrange(grupo, ano)

cat("\n  ── Delta metrics: all exporters ──\n")
cat("  [geral = all | focal = BR+AR | outros = rest]\n\n")
print(metricas_total, n = Inf)

cat("\n  Interpretation:\n")
cat("    cor > 0    → β captures the direction of share changes\n")
cat("    slope ≈ 1  → β bem calibrado em magnitude\n")
cat("    slope < 1  → β sobrestima a resposta (observado < previsto)\n")
cat("    slope > 1  → β subestima a resposta (observado > previsto)\n")
cat("    sign_acc   → % of pairs with the correct sign (> 50% = better than random)\n\n")

# ── 6. Scatter Δlog(obs) × Δlog(pred) ────────────────────────────────────────
lim_max <- delta_df %>%
  summarise(lim = max(abs(c(delta_log_dv_obs, delta_log_dv_pred)),
                      na.rm = TRUE) * 1.12) %>%
  pull(lim)
lim_max <- max(lim_max, 0.1)   # minimum so the chart does not collapse

ncol_p <- min(3, length(anos_teste_val))

# Classify exporters for the scatter: focal gets a label, others = grey
delta_plot_df <- delta_df %>%
  mutate(
    ano_label  = paste("Teste:", year),
    exp_label  = if_else(grupo_exporter == "focal", exporter, "outros"),
    pt_alpha   = if_else(grupo_exporter == "focal", 0.90, 0.25),
    pt_size    = if_else(grupo_exporter == "focal", 2.8,  1.2)
  )

cores_base <- c("#E41A1C", "#377EB8", "#4DAF4A", "#984EA3")
cores_scatter <- c(
  setNames(cores_base[seq_along(paises_grupo)], paises_grupo),
  outros = "grey60"
)

p_delta <- ggplot(delta_plot_df,
                  aes(x = delta_log_dv_pred, y = delta_log_dv_obs)) +
  geom_hline(yintercept = 0, colour = "grey75", linewidth = 0.4) +
  geom_vline(xintercept = 0, colour = "grey75", linewidth = 0.4) +
  geom_abline(slope = 1, intercept = 0,
              linetype = "dashed", colour = "grey30", linewidth = 0.8) +
  # Points: others in grey, focal ones coloured
  geom_point(data = ~ filter(.x, exp_label == "outros"),
             colour = "grey60", size = 1.2, alpha = 0.25) +
  geom_point(data = ~ filter(.x, exp_label != "outros"),
             aes(colour = exp_label), size = 2.8, alpha = 0.90) +
  # Product label for focal only
  geom_text(data = ~ filter(.x, exp_label != "outros"),
            aes(label = product, colour = exp_label),
            size = 1.9, vjust = -0.65, show.legend = FALSE) +
  # Overall regression (all)
  geom_smooth(method = "lm", formula = y ~ x, se = TRUE,
              colour = "black", linewidth = 0.8, alpha = 0.12,
              linetype = "solid") +
  # Focal regression
  geom_smooth(data = ~ filter(.x, exp_label != "outros"),
              aes(colour = exp_label, group = exp_label),
              method = "lm", formula = y ~ x, se = FALSE,
              linewidth = 0.7, linetype = "dotted") +
  scale_colour_manual(values = cores_scatter, name = "Country") +
  coord_cartesian(xlim = c(-lim_max, lim_max),
                  ylim = c(-lim_max, lim_max)) +
  facet_wrap(~ ano_label, ncol = ncol_p) +
  labs(
    title    = sprintf("Delta validation — %s (share): does β predict changes?",
                       toupper(produto_ativo)),
    subtitle = paste("Dashed = perfect calibration | Solid black = overall OLS",
                     "| Dotted = OLS by focal country"),
    x        = "Predicted Δlog(share)  [= β × Δlog(price_rel)]",
    y        = "Observed Δlog(share)",
    caption  = sprintf("Grey points = other exporters (global β) | Base: mean %d–%d",
                       min(anos_base_val), max(anos_base_val))
  ) +
  theme_minimal(base_size = 11) +
  theme(
    plot.title      = element_text(face = "bold", size = 12),
    plot.subtitle   = element_text(size = 9, colour = "grey40"),
    legend.position = "bottom",
    strip.text      = element_text(face = "bold")
  )

ggsave(file.path(dir_output, "5c_validacao_delta_scatter.png"),
       p_delta,
       width  = 5 * ncol_p + 1,
       height = 5,
       dpi    = 150)

# ── 7. Salvar CSVs ────────────────────────────────────────────────────────────
write.csv(
  metricas_total,
  file.path(dir_output, "5c_validacao_delta_metricas.csv"),
  row.names = FALSE
)

write.csv(
  delta_df %>%
    select(exporter, product, year,
           dv_obs, dv_base,
           price_rel_test, price_rel_base,
           beta_sim,
           delta_log_dv_obs, delta_log_price,
           delta_log_dv_pred, sign_correct),
  file.path(dir_output, "5c_validacao_delta_dados.csv"),
  row.names = FALSE
)

cat(sprintf("  Saved: 5c_validacao_delta_metricas.csv\n"))
cat(sprintf("  Saved: 5c_validacao_delta_scatter.png\n"))

}  # fim if nrow >= 4
}  # fim if length(anos_teste_val) > 0

cat("[ 04b ] OK\n")

############################################
# 02_modelo.R — PPML share
# ----------------------------------------
# DV      : share
# Regressor: log_price_rel
# FE      : exporter^product + product^year
# Method  : PPML (fepois)
#
# Produz: model_ppml, betas_modelo_global
############################################

cat("[ 02 ] Estimating PPML share model...\n")

df_model <- preparar_pesos(df, usar_peso_tempo, half_life)

# ── Main model ──────────────────────────────────────────────────────────

model_ppml <- fepois(
  share ~ log_price_rel | exporter^product + product^year,
  data    = df_model,
  weights = ~peso_tempo,
  cluster = ~exporter + year
)

cat("  PPML estimated. Obs:", model_ppml$nobs, "| Dropped:",
    nrow(df) - model_ppml$nobs, "\n")

registrar_resumo(model_ppml$nobs, "02", "06. obs in PPML model",
                 note = paste0("singletons: ", nrow(df) - model_ppml$nobs))

etable(model_ppml,
       tex  = TRUE,
       file = file.path(dir_output, "tabela_ppml.tex"))

# ── Visual diagnostics ────────────────────────────────────────────────────────

df_diag <- data.frame(
  fit = fitted(model_ppml),
  res = residuals(model_ppml, type = "response")
)

ggplot(df_diag, aes(x = fit, y = res)) +
  geom_point(alpha = 0.3) +
  geom_smooth(method = "loess", col = "red", se = FALSE) +
  geom_hline(yintercept = 0, linetype = "dashed") +
  labs(title = paste("PPML share diagnostics —", produto_ativo),
       x = "Fitted", y = "Residual (response)") +
  theme_minimal()

ggsave(file.path(dir_output, "1_diagnostico_ppml.png"),
       width = 8, height = 5, dpi = 150)

# ── Global betas by product ─────────────────────────────────────────────────

model_ppml_prod <- fepois(
  share ~ log_price_rel:factor(product) | exporter^product + product^year,
  data    = df_model,
  weights = ~peso_tempo,
  cluster = ~exporter + year
)

betas_modelo_global <- extrair_betas_globais(model_ppml_prod)

cat("  Betas by product:", nrow(betas_modelo_global), "\n")
cat("  Mean beta:", round(mean(betas_modelo_global$beta_global, na.rm = TRUE), 4), "\n")
print(betas_modelo_global, n = Inf)

cat("[ 02 ] OK\n\n")

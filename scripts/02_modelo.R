############################################
# 02_modelo.R — PPML share
# ----------------------------------------
# DV      : share
# Regressor: log_price_rel
# FE      : exporter^product + product^year
# Método  : PPML (fepois)
#
# Produz: model_ppml, betas_modelo_global
############################################

cat("[ 02 ] Estimando modelo PPML share...\n")

df_model <- preparar_pesos(df, usar_peso_tempo, half_life)

# ── Modelo principal ──────────────────────────────────────────────────────────

model_ppml <- fepois(
  share ~ log_price_rel | exporter^product + product^year,
  data    = df_model,
  weights = ~peso_tempo,
  cluster = ~exporter + year
)

cat("  PPML estimado. Obs:", model_ppml$nobs, "| Descartados:",
    nrow(df) - model_ppml$nobs, "\n")

registrar_resumo(model_ppml$nobs, "02", "06. obs no modelo PPML",
                 nota = paste0("singletons: ", nrow(df) - model_ppml$nobs))

etable(model_ppml,
       tex  = TRUE,
       file = file.path(dir_output, "tabela_ppml.tex"))

# ── Diagnóstico visual ────────────────────────────────────────────────────────

df_diag <- data.frame(
  fit = fitted(model_ppml),
  res = residuals(model_ppml, type = "response")
)

ggplot(df_diag, aes(x = fit, y = res)) +
  geom_point(alpha = 0.3) +
  geom_smooth(method = "loess", col = "red", se = FALSE) +
  geom_hline(yintercept = 0, linetype = "dashed") +
  labs(title = paste("Diagnóstico PPML share —", produto_ativo),
       x = "Ajustado", y = "Resíduo (resposta)") +
  theme_minimal()

ggsave(file.path(dir_output, "1_diagnostico_ppml.png"),
       width = 8, height = 5, dpi = 150)

# ── Betas globais por produto ─────────────────────────────────────────────────

model_ppml_prod <- fepois(
  share ~ log_price_rel:factor(product) | exporter^product + product^year,
  data    = df_model,
  weights = ~peso_tempo,
  cluster = ~exporter + year
)

betas_modelo_global <- extrair_betas_globais(model_ppml_prod)

cat("  Betas por produto:", nrow(betas_modelo_global), "\n")
cat("  Beta médio:", round(mean(betas_modelo_global$beta_global, na.rm = TRUE), 4), "\n")
print(betas_modelo_global, n = Inf)

cat("[ 02 ] OK\n\n")

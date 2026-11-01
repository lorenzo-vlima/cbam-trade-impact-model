############################################
# helpers/11_gof_modelo.R
# ----------------------------------------
# Métricas de qualidade do ajuste (GoF).
# Decomposição: quanto explicam os EFs,
# quanto acrescenta o preço, total.
#
# Contexto necessário (já no ambiente):
#   model_ppml + model_ppml_prod   (modelos PPML)
#   model_ols  + model_ols_prod    (modelos OLS)
#   df          (dados usados na estimação)
#   betas_simulacao, dir_output, setor_label
#
# Produz:
#   44_gof_modelo.csv     — métricas tabuladas
#   44b_gof_obs_pred.png  — scatter obs vs predito
#
# ── Decomposição reportada ───────────────────
#
#   r2_fe_only   — cor²(y, ŷ_FE)
#     Quanto os EFs sozinhos (sem preço) explicam.
#
#   r2_total     — cor²(y, ŷ_full)   [= cor² antigo]
#     Quanto o modelo completo (EFs + preço) explica.
#
#   r2_price_add — r2_total − r2_fe_only
#     Contribuição marginal do preço além dos EFs.
#
#   r2_within    — within pseudo-R² ou within R²
#     Quanto do resíduo dos EFs o preço explica
#     (métrica condicional, para comparação entre specs).
############################################

cat("\n[ 11 ] Métricas de qualidade do ajuste (GoF)...\n")

# ── 1. Identificar modelo disponível ──────────────────────────────────────────

if (exists("model_ppml_prod") && !is.null(model_ppml_prod)) {
  mod_prod  <- model_ppml_prod
  mod_simpl <- model_ppml
  is_ppml   <- TRUE
  tipo_str  <- "PPML (Poisson)"
  r2_tipo   <- "wpr2"
} else if (exists("model_ols_prod") && !is.null(model_ols_prod)) {
  mod_prod  <- model_ols_prod
  mod_simpl <- model_ols
  is_ppml   <- FALSE
  tipo_str  <- "OLS (log-linear)"
  r2_tipo   <- "wr2"
} else {
  cat("  Aviso: nenhum objeto de modelo encontrado — GoF pulado.\n")
  stop("GoF: objeto de modelo não encontrado.", call. = FALSE)
}

cat(sprintf("  Tipo: %s\n", tipo_str))

# ── 2. Observados e preditos — modelo completo ───────────────────────────────

y_obs  <- fitted(mod_prod) + residuals(mod_prod, type = "response")
y_pred <- fitted(mod_prod)

if (is_ppml) {
  mask_valid <- is.finite(y_obs) & is.finite(y_pred) & y_obs > 0 & y_pred > 0
} else {
  mask_valid <- is.finite(y_obs) & is.finite(y_pred)
}

r2_total <- cor(y_obs[mask_valid], y_pred[mask_valid], use = "complete.obs")^2

# ── 3. Predito FE-only — via decomposição do preditor linear ─────────────────
#
# Estratégia: em vez de re-estimar o modelo sem preço (o que gera problemas de
# alinhamento de observações nos modelos com lag/diff), decompõe-se o preditor
# linear do modelo já estimado:
#
#   PPML: ŷ_full = exp(FE + β·x)  →  ŷ_FE = ŷ_full · exp(−β·x) = ŷ / exp(β·x)
#   OLS:  ŷ_full = FE + β·x       →  ŷ_FE = ŷ_full − β·x
#
# Usa mod_prod (betas por produto), então y_obs e y_pred_fe têm
# exatamente o mesmo conjunto de observações — sem risco de desalinhamento.

r2_fe_only  <- NA_real_
r2_price_add <- NA_real_

X_prod <- tryCatch(model.matrix(mod_prod), error = function(e) NULL)
b_prod <- tryCatch(coef(mod_prod),         error = function(e) NULL)

if (!is.null(X_prod) && !is.null(b_prod) && length(b_prod) == ncol(X_prod)) {
  bx_prod <- as.vector(X_prod %*% b_prod)   # contribuição total do preço por obs.

  if (is_ppml) {
    # PPML: ŷ_FE = ŷ_full * exp(−β·x)   (escala resposta: contagens/volume)
    y_pred_fe <- y_pred * exp(-bx_prod)
    mfe <- is.finite(y_obs) & is.finite(y_pred_fe) & y_obs > 0 & y_pred_fe > 0
  } else {
    # OLS: ŷ_FE = ŷ_full − β·x           (escala log)
    y_pred_fe <- y_pred - bx_prod
    mfe <- is.finite(y_obs) & is.finite(y_pred_fe)
  }

  if (sum(mfe) > 10) {
    r2_fe_only   <- cor(y_obs[mfe], y_pred_fe[mfe], use = "complete.obs")^2
    r2_price_add <- r2_total - r2_fe_only
  }
} else {
  cat("  Aviso: model.matrix não disponível — r2_fe_only não calculado.\n")
}

# Dados para fallback wpr2 manual (estimação do modelo nulo-FE via log-lik)
dados_gof <- if (exists("df") && is.data.frame(df)) df else NULL
mod_null  <- NULL

# ── 4. Within R² (fixest automático, ou manual via log-lik) ───────────────────

r2_simpl_all <- tryCatch(r2(mod_simpl), error = function(e) NULL)
r2_prod_all  <- tryCatch(r2(mod_prod),  error = function(e) NULL)

r2_within_simpl <- if (!is.null(r2_simpl_all)) unname(r2_simpl_all[r2_tipo]) else NA_real_
r2_within_prod  <- if (!is.null(r2_prod_all))  unname(r2_prod_all[r2_tipo])  else NA_real_

r2_tipo_adj         <- paste0("wa", sub("^w", "", r2_tipo))
r2_within_simpl_adj <- if (!is.null(r2_simpl_all)) unname(r2_simpl_all[r2_tipo_adj]) else NA_real_
r2_within_prod_adj  <- if (!is.null(r2_prod_all))  unname(r2_prod_all[r2_tipo_adj])  else NA_real_

# Fallback manual via log-lik quando wpr2 é NA (EFs interados)
if (is_ppml && is.na(r2_within_simpl) && !is.null(mod_null)) {
  ll_full  <- tryCatch(as.numeric(logLik(mod_simpl)), error = function(e) NA_real_)
  ll_null  <- tryCatch(as.numeric(logLik(mod_null)),  error = function(e) NA_real_)

  if (!is.na(ll_full) && !is.na(ll_null) && ll_null != 0) {
    r2_within_simpl <- max(0, 1 - ll_full / ll_null)
  }

  ll_full_prod <- tryCatch(as.numeric(logLik(mod_prod)), error = function(e) NA_real_)
  if (!is.na(ll_full_prod) && !is.na(ll_null) && ll_null != 0) {
    r2_within_prod <- max(0, 1 - ll_full_prod / ll_null)
  }

  # Ajustado
  k_s <- length(coef(mod_simpl)); k_p <- length(coef(mod_prod))
  n_k <- nobs(mod_simpl)
  adj <- function(r, k, n) if (is.na(r) || n <= k+1) NA_real_ else 1-(1-r)*(n-1)/(n-k)
  r2_within_simpl_adj <- adj(r2_within_simpl, k_s, n_k)
  r2_within_prod_adj  <- adj(r2_within_prod,  k_p, n_k)
}

# ── 5. Relatório ──────────────────────────────────────────────────────────────

fmt_pct <- function(x) if (is.na(x)) "  NA  " else sprintf("%5.1f%%", x * 100)
fmt_na  <- function(x) if (is.na(x)) "NA" else sprintf("%.4f", x)

cat("\n  ══ Decomposição da variação explicada ══\n")
cat(sprintf("  EFs sozinhos (sem preço)  : %s  ← cor²(y, ŷ_FE)\n",
            fmt_pct(r2_fe_only)))
cat(sprintf("  EFs + preço (modelo full) : %s  ← cor²(y, ŷ_full)\n",
            fmt_pct(r2_total)))
cat(sprintf("  Contribuição marginal preço: %s  ← diferença\n",
            fmt_pct(r2_price_add)))

cat("\n  ══ Within R² (preço explica do resíduo dos EFs) ══\n")
cat(sprintf("  β único    (1 parâm.):        %s  da variação within-EF\n",
            fmt_pct(r2_within_simpl)))
cat(sprintf("  β produto  (N parâm., adj.):  %s  (limite superior)\n",
            fmt_pct(r2_within_prod_adj)))

cat("\n  → Leitura rápida:\n")
cat(sprintf("    • O modelo completo explica %.1f%% da variação total em %s.\n",
            ifelse(is.na(r2_total), 0, r2_total * 100),
            if(is_ppml) "volume/share" else "log(volume/share)"))
if (!is.na(r2_fe_only))
  cat(sprintf("    • Os EFs sozinhos já explicam %.1f%%; o preço acrescenta apenas %.1f%%.\n",
              r2_fe_only * 100, ifelse(is.na(r2_price_add), 0, r2_price_add * 100)))
cat(sprintf("    • Mas dentro do resíduo dos EFs, o preço explica %.1f%% (within R²).\n",
            ifelse(is.na(r2_within_simpl), 0, r2_within_simpl * 100)))

# ── 6. N ──────────────────────────────────────────────────────────────────────

n_obs      <- nobs(mod_prod)
n_produtos <- if (exists("betas_simulacao")) n_distinct(betas_simulacao$product) else NA_integer_
cat(sprintf("\n  N obs: %d | N produtos: %s\n",
            n_obs, ifelse(is.na(n_produtos), "?", as.character(n_produtos))))

# ── 7. Salvar CSV ─────────────────────────────────────────────────────────────

gof_tab <- tibble(
  setor                = setor_label,
  tipo_modelo          = tipo_str,
  n_obs                = n_obs,
  n_produtos           = n_produtos,
  r2_fe_only           = r2_fe_only,        # EFs sozinhos (cor²)
  r2_total             = r2_total,           # EFs + preço  (cor²)
  r2_price_marginal    = r2_price_add,       # contribuição marginal do preço
  r2_within_simpl      = r2_within_simpl,    # within: β único
  r2_within_simpl_adj  = r2_within_simpl_adj,
  r2_within_prod       = r2_within_prod,     # within: β por produto
  r2_within_prod_adj   = r2_within_prod_adj,
  metrica              = if (is_ppml) "wpr2 (within pseudo-R²)" else "wr2 (within R²)"
)

# Manter coluna legacy r2_cor_sq para compatibilidade com comparar_modelos.R
gof_tab <- gof_tab %>% mutate(r2_cor_sq = r2_total)

write.csv(gof_tab, file.path(dir_output, "44_gof_modelo.csv"), row.names = FALSE)

# ── 8. Scatter obs vs predito ─────────────────────────────────────────────────

dv_formula <- tryCatch(as.character(formula(mod_simpl)[[2]]), error = function(e) "DV")

set.seed(42)
n_plot <- min(sum(mask_valid), 5000)
idx    <- sample(which(mask_valid), n_plot)

df_scatter <- data.frame(obs = y_obs[idx], pred = y_pred[idx])

# Adiciona predito FE-only (via decomposição do preditor linear, já calculado)
df_scatter$pred_fe <- if (exists("y_pred_fe") && length(y_pred_fe) == length(y_obs)) {
  y_pred_fe[idx]
} else {
  NA_real_
}

p_obs_pred <- df_scatter %>%
  ggplot(aes(x = pred, y = obs)) +
  geom_point(alpha = 0.18, size = 1.0, color = "#1F77B4") +
  { if (!all(is.na(df_scatter$pred_fe)))
      list(geom_point(aes(x = pred_fe), alpha = 0.08, size = 0.8, color = "#9467BD"))
    else list() } +
  geom_abline(slope = 1, intercept = 0, color = "#D62728", linewidth = 0.9) +
  geom_smooth(method = "loess", se = FALSE,
              color = "#FF7F0E", linewidth = 0.7, linetype = "dashed") +
  { if (is_ppml) list(scale_x_log10(labels = scales::comma),
                      scale_y_log10(labels = scales::comma))
    else list() } +
  labs(
    title    = paste("Obs vs Predito —", setor_label),
    subtitle = sprintf(
      "EFs sozinhos: %s | EFs+preço: %s | Preço acrescenta: %s | Within: %s",
      fmt_pct(r2_fe_only), fmt_pct(r2_total),
      fmt_pct(r2_price_add), fmt_pct(r2_within_simpl)
    ),
    x = paste("Predito:", dv_formula), y = paste("Observado:", dv_formula),
    caption = paste(tipo_str, "| N =", scales::comma(n_plot), "pontos",
                    "| Azul=full | Roxo=FE-only | Vermelho=identidade")
  ) +
  theme_minimal(base_size = 11) +
  theme(plot.title    = element_text(face = "bold"),
        plot.subtitle = element_text(size = 7.5, color = "gray30"),
        plot.caption  = element_text(size = 7, color = "gray50"))

ggsave(file.path(dir_output, "44b_gof_obs_pred.png"),
       p_obs_pred, width = 8, height = 6, dpi = 150)

cat("  Salvo: 44_gof_modelo.csv | 44b_gof_obs_pred.png\n")
cat("[ 11 ] GoF OK\n")

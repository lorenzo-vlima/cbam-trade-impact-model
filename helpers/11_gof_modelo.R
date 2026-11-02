############################################
# helpers/11_gof_modelo.R
# ----------------------------------------
# Goodness-of-fit (GoF) metrics.
# Decomposition: how much the FEs explain,
# how much price adds, and the total.
#
# Required context (already in the environment):
#   model_ppml + model_ppml_prod   (PPML models)
#   model_ols  + model_ols_prod    (OLS models)
#   df          (data used in the estimation)
#   betas_simulacao, dir_output, setor_label
#
# Produces:
#   44_gof_modelo.csv     — tabulated metrics
#   44b_gof_obs_pred.png  — scatter observed vs predicted
#
# ── Reported decomposition ───────────────────
#
#   r2_fe_only   — cor²(y, ŷ_FE)
#     How much the FEs alone (without price) explain.
#
#   r2_total     — cor²(y, ŷ_full)   [= old cor²]
#     How much the full model (FEs + price) explains.
#
#   r2_price_add — r2_total − r2_fe_only
#     Marginal contribution of price beyond the FEs.
#
#   r2_within    — within pseudo-R² or within R²
#     How much of the FE residual price explains
#     (conditional metric, for comparison across specs).
############################################

cat("\n[ 11 ] Goodness-of-fit (GoF) metrics...\n")

# ── 1. Identify the available model ──────────────────────────────────────────

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
  cat("  Warning: no model object found, GoF skipped.\n")
  stop("GoF: model object not found.", call. = FALSE)
}

cat(sprintf("  Tipo: %s\n", tipo_str))

# ── 2. Observed and predicted — full model ───────────────────────────────

y_obs  <- fitted(mod_prod) + residuals(mod_prod, type = "response")
y_pred <- fitted(mod_prod)

if (is_ppml) {
  mask_valid <- is.finite(y_obs) & is.finite(y_pred) & y_obs > 0 & y_pred > 0
} else {
  mask_valid <- is.finite(y_obs) & is.finite(y_pred)
}

r2_total <- cor(y_obs[mask_valid], y_pred[mask_valid], use = "complete.obs")^2

# ── 3. FE-only prediction, via decomposition of the linear predictor ─────────────────
#
# Strategy: instead of re-estimating the model without price (which causes
# observation alignment problems in models with lag/diff), the linear
# predictor of the already-estimated model is decomposed:
#
#   PPML: ŷ_full = exp(FE + β·x)  →  ŷ_FE = ŷ_full · exp(−β·x) = ŷ / exp(β·x)
#   OLS:  ŷ_full = FE + β·x       →  ŷ_FE = ŷ_full − β·x
#
# Uses mod_prod (betas by product), so y_obs and y_pred_fe have
# exactly the same set of observations, with no misalignment risk.

r2_fe_only  <- NA_real_
r2_price_add <- NA_real_

X_prod <- tryCatch(model.matrix(mod_prod), error = function(e) NULL)
b_prod <- tryCatch(coef(mod_prod),         error = function(e) NULL)

if (!is.null(X_prod) && !is.null(b_prod) && length(b_prod) == ncol(X_prod)) {
  bx_prod <- as.vector(X_prod %*% b_prod)   # total price contribution per obs.

  if (is_ppml) {
    # PPML: ŷ_FE = ŷ_full * exp(−β·x)   (response scale: counts/volume)
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
  cat("  Warning: model.matrix unavailable, r2_fe_only not computed.\n")
}

# Data for the manual wpr2 fallback (null-FE model estimation via log-lik)
dados_gof <- if (exists("df") && is.data.frame(df)) df else NULL
mod_null  <- NULL

# ── 4. Within R² (automatic fixest, or manual via log-lik) ───────────────────

r2_simpl_all <- tryCatch(r2(mod_simpl), error = function(e) NULL)
r2_prod_all  <- tryCatch(r2(mod_prod),  error = function(e) NULL)

r2_within_simpl <- if (!is.null(r2_simpl_all)) unname(r2_simpl_all[r2_tipo]) else NA_real_
r2_within_prod  <- if (!is.null(r2_prod_all))  unname(r2_prod_all[r2_tipo])  else NA_real_

r2_tipo_adj         <- paste0("wa", sub("^w", "", r2_tipo))
r2_within_simpl_adj <- if (!is.null(r2_simpl_all)) unname(r2_simpl_all[r2_tipo_adj]) else NA_real_
r2_within_prod_adj  <- if (!is.null(r2_prod_all))  unname(r2_prod_all[r2_tipo_adj])  else NA_real_

# Manual fallback via log-lik when wpr2 is NA (interacted FEs)
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

# ── 5. Report ──────────────────────────────────────────────────────────────

fmt_pct <- function(x) if (is.na(x)) "  NA  " else sprintf("%5.1f%%", x * 100)
fmt_na  <- function(x) if (is.na(x)) "NA" else sprintf("%.4f", x)

cat("\n  ══ Decomposition of explained variation ══\n")
cat(sprintf("  FEs alone (no price)       : %s  ← cor²(y, ŷ_FE)\n",
            fmt_pct(r2_fe_only)))
cat(sprintf("  FEs + price (full model)  : %s  ← cor²(y, ŷ_full)\n",
            fmt_pct(r2_total)))
cat(sprintf("  Marginal price contribution: %s  ← difference\n",
            fmt_pct(r2_price_add)))

cat("\n  ══ Within R² (price explains the FE residual) ══\n")
cat(sprintf("  single β   (1 param.):        %s  of the within-FE variation\n",
            fmt_pct(r2_within_simpl)))
cat(sprintf("  β by product (N params, adj.): %s  (upper bound)\n",
            fmt_pct(r2_within_prod_adj)))

cat("\n  → Quick read:\n")
cat(sprintf("    • The full model explains %.1f%% of the total variation in %s.\n",
            ifelse(is.na(r2_total), 0, r2_total * 100),
            if(is_ppml) "volume/share" else "log(volume/share)"))
if (!is.na(r2_fe_only))
  cat(sprintf("    • The FEs alone already explain %.1f%%; price adds only %.1f%%.\n",
              r2_fe_only * 100, ifelse(is.na(r2_price_add), 0, r2_price_add * 100)))
cat(sprintf("    • But within the FE residual, price explains %.1f%% (within R²).\n",
            ifelse(is.na(r2_within_simpl), 0, r2_within_simpl * 100)))

# ── 6. N ──────────────────────────────────────────────────────────────────────

n_obs      <- nobs(mod_prod)
n_produtos <- if (exists("betas_simulacao")) n_distinct(betas_simulacao$product) else NA_integer_
cat(sprintf("\n  N obs: %d | N products: %s\n",
            n_obs, ifelse(is.na(n_produtos), "?", as.character(n_produtos))))

# ── 7. Save CSV ─────────────────────────────────────────────────────────────

gof_tab <- tibble(
  setor                = setor_label,
  tipo_modelo          = tipo_str,
  n_obs                = n_obs,
  n_produtos           = n_produtos,
  r2_fe_only           = r2_fe_only,        # EFs sozinhos (cor²)
  r2_total             = r2_total,           # FEs + price  (cor²)
  r2_price_marginal    = r2_price_add,       # marginal contribution of price
  r2_within_simpl      = r2_within_simpl,    # within: single β
  r2_within_simpl_adj  = r2_within_simpl_adj,
  r2_within_prod       = r2_within_prod,     # within: β by product
  r2_within_prod_adj   = r2_within_prod_adj,
  metrica              = if (is_ppml) "wpr2 (within pseudo-R²)" else "wr2 (within R²)"
)

# Keep the legacy r2_cor_sq column for compatibility with comparar_modelos.R
gof_tab <- gof_tab %>% mutate(r2_cor_sq = r2_total)

write.csv(gof_tab, file.path(dir_output, "44_gof_modelo.csv"), row.names = FALSE)

# ── 8. Scatter observed vs predicted ─────────────────────────────────────────────────

dv_formula <- tryCatch(as.character(formula(mod_simpl)[[2]]), error = function(e) "DV")

set.seed(42)
n_plot <- min(sum(mask_valid), 5000)
idx    <- sample(which(mask_valid), n_plot)

df_scatter <- data.frame(obs = y_obs[idx], pred = y_pred[idx])

# Add FE-only prediction (via decomposition of the linear predictor, already computed)
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
    title    = paste("Observed vs Predicted —", setor_label),
    subtitle = sprintf(
      "FEs alone: %s | FEs+price: %s | Price adds: %s | Within: %s",
      fmt_pct(r2_fe_only), fmt_pct(r2_total),
      fmt_pct(r2_price_add), fmt_pct(r2_within_simpl)
    ),
    x = paste("Predicted:", dv_formula), y = paste("Observed:", dv_formula),
    caption = paste(tipo_str, "| N =", scales::comma(n_plot), "points",
                    "| Azul=full | Roxo=FE-only | Vermelho=identidade")
  ) +
  theme_minimal(base_size = 11) +
  theme(plot.title    = element_text(face = "bold"),
        plot.subtitle = element_text(size = 7.5, color = "gray30"),
        plot.caption  = element_text(size = 7, color = "gray50"))

ggsave(file.path(dir_output, "44b_gof_obs_pred.png"),
       p_obs_pred, width = 8, height = 6, dpi = 150)

cat("  Saved: 44_gof_modelo.csv | 44b_gof_obs_pred.png\n")
cat("[ 11 ] GoF OK\n")

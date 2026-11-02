############################################
# helpers/funcoes_modelo.R
# ----------------------------------------
# Shared estimation functions.
# Used by all models in modelos/*/
############################################

# ── Formatting ────────────────────────────────────────────────────────────────

sig_label <- function(p) {
  case_when(p < 0.01 ~ "***", p < 0.05 ~ "**", p < 0.10 ~ "*", TRUE ~ "")
}

fmt_coef <- function(b, se) {
  if (is.na(b))  return("-")
  if (is.na(se)) return(paste0(round(b, 3), " (-)"))
  p   <- 2 * pnorm(-abs(b / se))
  sig <- sig_label(p)
  paste0(round(b, 3), sig, " (", round(se, 3), ")")
}

# ── Time weights ───────────────────────────────────────────────────────────

preparar_pesos <- function(dados, usar_peso_tempo, half_life) {
  if (usar_peso_tempo) {
    dados %>%
      mutate(peso_tempo = exp(-log(2) / half_life * (max(year) - year)))
  } else {
    dados %>%
      mutate(peso_tempo = 1)
  }
}

# ── Shrinkage ─────────────────────────────────────────────────────────────────
# w = se_global² / (se_global² + se_dif²)
# beta_sim = w × beta_cod + (1-w) × beta_global

calcular_shrinkage <- function(se_global, se_dif) {
  se_global^2 / (se_global^2 + se_dif^2)
}

# ── Extraction of global betas by product ─────────────────────────────────────
# Takes a fixest model with the log_price_rel:factor(product) interaction
# Returns a tibble with product, beta_global, se_global

extrair_betas_globais <- function(model, prefixo_termo = "log_price_rel:factor\\(product\\)") {
  tidy(model) %>%
    filter(grepl(paste0("^", prefixo_termo), term)) %>%
    mutate(product = str_trim(gsub(prefixo_termo, "", term))) %>%
    select(product, beta_global = estimate, se_global = std.error) %>%
    mutate(product = str_trim(as.character(product)))
}

# ── Building betas_simulacao with shrinkage ─────────────────────────────────
# Takes: todos_produtos, betas_globais, list of betas_dif by country,
#         paises_grupo, z_critico
# Returns: betas_simulacao with columns beta_base, beta_dif_X, beta_X,
#          w_X, beta_sim_X, fonte_X

montar_betas_simulacao <- function(todos_produtos, betas_globais,
                                   betas_dif_list, paises_grupo, z_critico = 1.96) {
  bs <- todos_produtos %>%
    left_join(betas_globais, by = "product") %>%
    rename(beta_base = beta_global, se_base = se_global)

  for (b in betas_dif_list) {
    bs <- left_join(bs, b, by = "product")
  }

  for (cod in paises_grupo) {
    bs <- bs %>%
      mutate(
        !!paste0("beta_", cod) :=
          beta_base + coalesce(.data[[paste0("beta_dif_", cod)]], 0)
      )
  }

  for (cod in paises_grupo) {
    se_dif_col <- paste0("se_dif_", cod)
    bs <- bs %>%
      mutate(
        !!paste0("w_", cod) := if_else(
          !is.na(.data[[se_dif_col]]),
          calcular_shrinkage(se_base, .data[[se_dif_col]]),
          0
        ),
        !!paste0("beta_sim_", cod) :=
          .data[[paste0("w_", cod)]] * .data[[paste0("beta_", cod)]] +
          (1 - .data[[paste0("w_", cod)]]) * beta_base,
        !!paste0("fonte_", cod) := case_when(
          is.na(.data[[se_dif_col]])           ~ "global (no differential)",
          .data[[paste0("w_", cod)]] >= 0.9    ~ "specific (w>=0.9)",
          .data[[paste0("w_", cod)]] <= 0.1    ~ "global (w<=0.1)",
          TRUE                                  ~ paste0(
            "mixed (w=", round(.data[[paste0("w_", cod)]], 2), ")"
          )
        )
      )
  }

  bs %>%
    mutate(product = str_trim(product)) %>%
    arrange(product)
}

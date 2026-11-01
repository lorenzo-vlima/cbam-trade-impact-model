############################################
# 00_tracking.R
# ----------------------------------------
# Sistema de tracking de amostra ao longo
# do pipeline CBAM.
#
# USO:
#   1. source() este arquivo no início do main.R
#      (antes de rodar qualquer outro script)
#   2. Chame registrar() após cada passo relevante
#      nos scripts 01 a 09
#   3. Chame imprimir_tracking() no final do main.R
#
# Não depende de nenhum outro script.
############################################

# ── Inicialização ─────────────────────────────────────────────────────────────

tracking_log <- tibble(
  script         = character(),
  etapa          = character(),
  n_obs          = integer(),
  n_exportadores = integer(),
  n_produtos     = integer(),
  n_anos         = integer(),
  ton_total_mi   = numeric(),
  nota           = character()
)

# ── Função principal ──────────────────────────────────────────────────────────

registrar <- function(df, script, etapa, nota = "") {
  
  n_exp  <- if ("exporter" %in% names(df)) n_distinct(df$exporter) else NA_integer_
  n_prod <- if ("product"  %in% names(df)) n_distinct(df$product)  else NA_integer_
  n_ano  <- if ("year"     %in% names(df)) n_distinct(df$year)     else NA_integer_
  ton    <- if ("ton"      %in% names(df)) sum(df$ton, na.rm = TRUE) / 1e6 else NA_real_
  
  tracking_log <<- tracking_log %>%
    add_row(
      script         = script,
      etapa          = etapa,
      n_obs          = nrow(df),
      n_exportadores = n_exp,
      n_produtos     = n_prod,
      n_anos         = n_ano,
      ton_total_mi   = round(ton, 2),
      nota           = nota
    )
  
  invisible(df)
}

# ── Variante para objetos que não são data frames de observações ──────────────

registrar_resumo <- function(n_obs, script, etapa,
                             n_exp = NA, n_prod = NA,
                             n_anos = NA, ton = NA, nota = "") {
  tracking_log <<- tracking_log %>%
    add_row(
      script         = script,
      etapa          = etapa,
      n_obs          = as.integer(n_obs),
      n_exportadores = as.integer(n_exp),
      n_produtos     = as.integer(n_prod),
      n_anos         = as.integer(n_anos),
      ton_total_mi   = as.numeric(ton),
      nota           = nota
    )
  invisible(NULL)
}

# ── Relatório final ───────────────────────────────────────────────────────────

imprimir_tracking <- function(dir_output = NULL) {
  
  # Referência = filtro de período (etapa 02)
  ref_row <- tracking_log %>%
    filter(etapa == "02. filtro período") %>%
    slice(1)
  
  ref_obs <- ref_row$n_obs
  ref_ton <- ref_row$ton_total_mi
  
  rel <- tracking_log %>%
    mutate(
      pct_obs = if_else(
        !is.na(n_obs) & !is.na(ref_obs) & ref_obs > 0,
        round(n_obs / ref_obs * 100, 1), NA_real_
      ),
      pct_ton = if_else(
        !is.na(ton_total_mi) & !is.na(ref_ton) & ref_ton > 0,
        round(ton_total_mi / ref_ton * 100, 1), NA_real_
      )
    ) %>%
    select(script, etapa,
           n_obs, pct_obs,
           n_exportadores,
           n_produtos, n_anos,
           ton_total_mi, pct_ton,
           nota)
  
  cat("\n", rep("=", 80), "\n", sep = "")
  cat("  TRACKING DE AMOSTRA —", toupper(produto_ativo), "\n")
  cat("  Base das porcentagens: filtro de período\n")
  cat(rep("=", 80), "\n\n", sep = "")
  
  print(rel, n = Inf)
  
  if (!is.null(dir_output)) {
    write.csv(rel,
              file.path(dir_output, "00_tracking_amostra.csv"),
              row.names = FALSE)
    cat("\n  Salvo em: 00_tracking_amostra.csv\n")
  }
  
  invisible(rel)
}
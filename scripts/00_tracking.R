############################################
# 00_tracking.R
# ----------------------------------------
# Sample tracking system across the CBAM
# pipeline.
#
# USAGE:
#   1. source() this file at the start of main.R
#      (before running any other script)
#   2. Call registrar() after each relevant step
#      in scripts 01 to 09
#   3. Call imprimir_tracking() at the end of main.R
#
# Does not depend on any other script.
############################################

# ── Initialisation ────────────────────────────────────────────────────────────

tracking_log <- tibble(
  script         = character(),
  step           = character(),
  n_obs          = integer(),
  n_exporters    = integer(),
  n_products     = integer(),
  n_years        = integer(),
  total_ton_mn   = numeric(),
  note           = character()
)

# ── Main function ─────────────────────────────────────────────────────────────

registrar <- function(df, script, step, note = "") {

  n_exp  <- if ("exporter" %in% names(df)) n_distinct(df$exporter) else NA_integer_
  n_prod <- if ("product"  %in% names(df)) n_distinct(df$product)  else NA_integer_
  n_ano  <- if ("year"     %in% names(df)) n_distinct(df$year)     else NA_integer_
  ton    <- if ("ton"      %in% names(df)) sum(df$ton, na.rm = TRUE) / 1e6 else NA_real_

  tracking_log <<- tracking_log %>%
    add_row(
      script         = script,
      step           = step,
      n_obs          = nrow(df),
      n_exporters    = n_exp,
      n_products     = n_prod,
      n_years        = n_ano,
      total_ton_mn   = round(ton, 2),
      note           = note
    )

  invisible(df)
}

# ── Variant for objects that are not observation data frames ──────────────────

registrar_resumo <- function(n_obs, script, step,
                             n_exp = NA, n_prod = NA,
                             n_anos = NA, ton = NA, note = "") {
  tracking_log <<- tracking_log %>%
    add_row(
      script         = script,
      step           = step,
      n_obs          = as.integer(n_obs),
      n_exporters    = as.integer(n_exp),
      n_products     = as.integer(n_prod),
      n_years        = as.integer(n_anos),
      total_ton_mn   = as.numeric(ton),
      note           = note
    )
  invisible(NULL)
}

# ── Final report ──────────────────────────────────────────────────────────────

imprimir_tracking <- function(dir_output = NULL) {

  # Reference = period filter (step 02)
  ref_row <- tracking_log %>%
    filter(step == "02. period filter") %>%
    slice(1)

  ref_obs <- ref_row$n_obs
  ref_ton <- ref_row$total_ton_mn

  rel <- tracking_log %>%
    mutate(
      pct_obs = if_else(
        !is.na(n_obs) & !is.na(ref_obs) & ref_obs > 0,
        round(n_obs / ref_obs * 100, 1), NA_real_
      ),
      pct_ton = if_else(
        !is.na(total_ton_mn) & !is.na(ref_ton) & ref_ton > 0,
        round(total_ton_mn / ref_ton * 100, 1), NA_real_
      )
    ) %>%
    select(script, step,
           n_obs, pct_obs,
           n_exporters,
           n_products, n_years,
           total_ton_mn, pct_ton,
           note)

  cat("\n", rep("=", 80), "\n", sep = "")
  cat("  SAMPLE TRACKING —", toupper(produto_ativo), "\n")
  cat("  Percentage base: period filter\n")
  cat(rep("=", 80), "\n\n", sep = "")

  print(rel, n = Inf)

  if (!is.null(dir_output)) {
    write.csv(rel,
              file.path(dir_output, "00_sample_tracking.csv"),
              row.names = FALSE)
    cat("\n  Saved to: 00_sample_tracking.csv\n")
  }

  invisible(rel)
}

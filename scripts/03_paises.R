############################################
# 03_paises.R — PPML share
# ----------------------------------------
# Two stages:
#   1. Offset with beta_global_p by product
#   2. Country differentials (individual mode)
# Shrinkage: w = se_global² / (se_global² + se_dif²)
#
# Depende de: 01_limpeza.R, 02_modelo.R
# Produz: betas_simulacao, tabela_setor
############################################

cat("[ 03 ] Betas by country...\n")
cat("  Countries:", paste(paises_grupo, collapse = ", "), "\n")
cat("  Global mean beta:", round(mean(betas_modelo_global$beta_global, na.rm = TRUE), 4), "\n")

todos_produtos <- df %>%
  distinct(product) %>%
  mutate(product = str_trim(as.character(product))) %>%
  arrange(product)

# ── Prepare dataset with offset ───────────────────────────────────────────────

df_conj <- preparar_pesos(df, usar_peso_tempo, half_life) %>%
  left_join(betas_modelo_global %>% select(product, beta_global), by = "product") %>%
  mutate(offset_term = beta_global * log_price_rel)

termos_dif <- paste0(
  "log_price_rel:d_", paises_grupo, ":factor(product)",
  collapse = " + "
)
formula_conj <- as.formula(paste(
  "share ~ offset(offset_term) +", termos_dif,
  "| exporter^product + product^year"
))

cat("  Formula:", deparse(formula_conj), "\n")

# ── Estimation ─────────────────────────────────────────────────────────────────

model_conjunto <- fepois(
  formula_conj,
  data    = df_conj,
  weights = ~peso_tempo,
  cluster = ~exporter + year
)

registrar_resumo(model_conjunto$nobs, "03", "08. obs in joint model",
                 note = paste("mode: individual | countries:", paste(paises_grupo, collapse = ", ")))

etable(model_conjunto,
       tex  = TRUE,
       file = file.path(dir_output, "3_tabela_conjunto.tex"))

# ── Extract country differentials ─────────────────────────────────────────────

coefs <- tidy(model_conjunto)

betas_dif_list <- map(paises_grupo, function(cod) {
  coefs %>%
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

# ── Build betas_simulacao with shrinkage ──────────────────────────────────────

betas_simulacao <- montar_betas_simulacao(
  todos_produtos, betas_modelo_global,
  betas_dif_list, paises_grupo, z_critico
)

cat("\n  === BETAS FOR SIMULATION ===\n")
print(betas_simulacao, n = Inf)

# Weight distribution
for (cod in paises_grupo) {
  col_fonte <- paste0("fonte_", cod)
  if (col_fonte %in% names(betas_simulacao)) {
    cat(sprintf("\n  %s — distribution:\n", cod))
    tab <- table(betas_simulacao[[col_fonte]])
    for (nm in names(tab)) cat(sprintf("    %s: %d\n", nm, tab[nm]))
  }
}

# ── Sector table (volume-weighted) ───────────────────────────────────────

ton_setor <- df %>%
  filter(year >= (ano_corte - janela_base + 1), year <= ano_corte) %>%
  group_by(product) %>%
  summarise(ton_produto = sum(ton, na.rm = TRUE), .groups = "drop")

ton_pais <- df %>%
  filter(year >= (ano_corte - janela_base + 1), year <= ano_corte,
         exporter %in% paises_grupo) %>%
  group_by(exporter, product) %>%
  summarise(ton_pais = sum(ton, na.rm = TRUE), .groups = "drop")

resumo_global <- betas_simulacao %>%
  left_join(ton_setor, by = "product") %>%
  summarise(
    n_produtos       = n(),
    beta_global_pond = weighted.mean(beta_base, ton_produto, na.rm = TRUE),
    se_global_pond   = weighted.mean(se_base,   ton_produto, na.rm = TRUE)
  )

resumo_paises <- resumo_global
for (cod in paises_grupo) {
  ton_cod <- ton_pais %>%
    filter(exporter == cod, ton_pais > 0) %>%
    select(product, ton_cod = ton_pais)
  df_cod <- betas_simulacao %>% inner_join(ton_cod, by = "product")
  if (nrow(df_cod) == 0) {
    resumo_paises[[paste0("beta_", cod, "_pond")]]   <- NA_real_
    resumo_paises[[paste0("se_dif_", cod, "_pond")]] <- NA_real_
    resumo_paises[[paste0("w_", cod, "_pond")]]       <- NA_real_
  } else {
    resumo_paises[[paste0("beta_", cod, "_pond")]] <-
      weighted.mean(df_cod[[paste0("beta_", cod)]], df_cod$ton_cod, na.rm = TRUE)
    resumo_paises[[paste0("se_dif_", cod, "_pond")]] <-
      weighted.mean(df_cod[[paste0("se_dif_", cod)]], df_cod$ton_cod, na.rm = TRUE)
    resumo_paises[[paste0("w_", cod, "_pond")]] <-
      weighted.mean(df_cod[[paste0("w_", cod)]], df_cod$ton_cod, na.rm = TRUE)
  }
}

tabela_setor <- resumo_paises %>%
  mutate(
    beta_global_02_val = resumo_paises$beta_global_pond,
    se_global_02_val   = resumo_paises$se_global_pond,
    n_obs_conjunto     = model_conjunto$nobs
  )
for (cod in paises_grupo) {
  b_pond  <- resumo_paises[[paste0("beta_", cod, "_pond")]]
  se_pond <- resumo_paises[[paste0("se_dif_", cod, "_pond")]]
  tabela_setor[[paste0("delta_report_", cod, "_pond")]] <-
    b_pond - resumo_paises$beta_global_pond
  tabela_setor[[paste0("se_tot_", cod, "_pond")]] <- se_pond
}

# ── Exports ───────────────────────────────────────────────────────────────────

write.csv(betas_simulacao,
          file.path(dir_output, "4_betas_simulacao_cbam.csv"),
          row.names = FALSE)

write.csv(tabela_setor,
          file.path(dir_output, "4d_tabela_betas_setor.csv"),
          row.names = FALSE)

df_4c <- betas_simulacao %>%
  select(product, beta_base, se_base,
         all_of(paste0("beta_",   paises_grupo)),
         all_of(paste0("se_dif_", paises_grupo)),
         all_of(paste0("w_",      paises_grupo))) %>%
  left_join(ton_setor, by = "product")
for (cod in paises_grupo) {
  ton_cod <- ton_pais %>%
    filter(exporter == cod) %>%
    select(product, !!paste0("ton_", cod) := ton_pais)
  df_4c <- left_join(df_4c, ton_cod, by = "product")
}
write.csv(df_4c,
          file.path(dir_output, "4c_tabela_betas_produto.csv"),
          row.names = FALSE)

cat("\n[ 03 ] OK\n\n")

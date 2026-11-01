############################################
# analise_realocacao_verde.R
# ----------------------------------------
# Isola e quantifica o "outcome 1" do CBAM (mudanca da cesta de
# exportadores) mantendo tecnologia/intensidade de carbono FIXA
# (e' assim que o modelo ja funciona: fator_emissao nao varia
# por cenario). Usa apenas os CSVs ja gerados pelas rodadas
# "cesta_padrao" -- nao reroda o modelo.
#
# Produz:
#   1. Reducao agregada de emissoes embutidas via realocacao pura
#      (por setor x cenario)
#   2. Intensidade de carbono media ponderada da cesta, antes/depois
#   3. Teste: paises mais sujos perdem mais share? (correlacao e
#      regressao pooled, controlando pela elasticidade beta)
############################################

pkgs <- c("tidyverse")
for (p in pkgs) if (!require(p, character.only = TRUE)) install.packages(p)
invisible(lapply(pkgs, library, character.only = TRUE))

setores <- c(
  ferro_aco = "outputs/ferro_aco_cesta_padrao_individual_post_tax_j3_v2",
  aluminio  = "outputs/aluminio_cesta_padrao_individual_post_tax_j3_v2",
  cimento   = "outputs/cimento_cesta_padrao_individual_post_tax_j3_v2"
)

# ---------------------------------------------------------------
# 1 + 2. Reducao agregada e intensidade de carbono media (cesta)
# ---------------------------------------------------------------

resumo_cesta <- map_dfr(names(setores), function(setor) {
  df <- read.csv(file.path(setores[setor], "39b_emissoes_impacto.csv"), stringsAsFactors = FALSE)

  df %>%
    group_by(cenario_carbono, cenario_tarifa) %>%
    summarise(
      emissoes_base  = sum(emissoes_base_tco2, na.rm = TRUE),
      emissoes_sim   = sum(emissoes_sim_tco2,  na.rm = TRUE),
      # ATENCAO: nao renomear ton_base/ton_simulado aqui -- precisamos das
      # colunas originais (por produto) intactas para ponderar fator_emissao;
      # se sao sobrescritas por sua propria soma agregada dentro do mesmo
      # summarise(), dplyr usa o valor ja agregado (escalar) nas expressoes
      # seguintes em vez do vetor original por linha, e a ponderacao quebra.
      ton_base_tot   = sum(ton_base,      na.rm = TRUE),
      ton_sim_tot    = sum(ton_simulado,  na.rm = TRUE),
      intens_antes   = sum(fator_emissao * ton_base,      na.rm = TRUE) / ton_base_tot,
      intens_depois  = sum(fator_emissao * ton_simulado,  na.rm = TRUE) / ton_sim_tot,
      .groups = "drop"
    ) %>%
    mutate(
      setor = setor,
      delta_emissoes_pct = (emissoes_sim - emissoes_base) / emissoes_base * 100,
      delta_intens_pct   = (intens_depois - intens_antes) / intens_antes * 100
    )
})

cat("\n============================================================\n")
cat("1+2. REALOCACAO PURA (tecnologia fixa) -- por setor x cenario\n")
cat("============================================================\n")
print(
  resumo_cesta %>%
    select(setor, cenario_carbono, cenario_tarifa,
           delta_emissoes_pct, intens_antes, intens_depois, delta_intens_pct) %>%
    arrange(setor, cenario_carbono, cenario_tarifa) %>%
    as.data.frame(),
  digits = 3
)

write.csv(resumo_cesta, "analise_realocacao_cesta.csv", row.names = FALSE)

# ---------------------------------------------------------------
# 3. A cesta fica mais "verde"? paises mais sujos perdem mais share?
# ---------------------------------------------------------------

dados_pais <- map_dfr(names(setores), function(setor) {
  emi <- read.csv(file.path(setores[setor], "39b_emissoes_impacto.csv"), stringsAsFactors = FALSE)
  res <- read.csv(file.path(setores[setor], "13_cbam_resumo_pais.csv"), stringsAsFactors = FALSE)

  intens_pais <- emi %>%
    filter(cenario_carbono == "95/tCO2", cenario_tarifa == "MFN") %>%
    group_by(exporter) %>%
    summarise(
      fator_emissao_pond = sum(fator_emissao * ton_base, na.rm = TRUE) / sum(ton_base, na.rm = TRUE),
      beta_pond           = sum(beta_usado * ton_base, na.rm = TRUE) / sum(ton_base, na.rm = TRUE),
      .groups = "drop"
    )

  res %>%
    filter(cenario_carbono == "95/tCO2", cenario_tarifa == "MFN") %>%
    select(exporter, delta_share_pp = delta_share_pp_total, variacao_relativa_pct,
           share_base = share_base_total) %>%
    left_join(intens_pais, by = "exporter") %>%
    mutate(setor = setor)
})

dados_pais <- dados_pais %>% filter(!is.na(fator_emissao_pond), !is.na(beta_pond))

cat("\n============================================================\n")
cat("3. DADOS POR PAIS (cenario 95/tCO2, MFN) -- fator emissao x share\n")
cat("============================================================\n")
print(as.data.frame(dados_pais), digits = 3)

write.csv(dados_pais, "analise_realocacao_paises.csv", row.names = FALSE)

cat("\n---- Correlacao simples: delta_share_pp x fator_emissao_pond ----\n")
for (s in unique(dados_pais$setor)) {
  sub <- dados_pais %>% filter(setor == s)
  ct <- cor.test(sub$fator_emissao_pond, sub$delta_share_pp)
  cat(sprintf("  %-10s r = %6.3f | p = %.3f | n = %d\n", s, ct$estimate, ct$p.value, nrow(sub)))
}
ct_all <- cor.test(dados_pais$fator_emissao_pond, dados_pais$delta_share_pp)
cat(sprintf("  %-10s r = %6.3f | p = %.3f | n = %d\n", "POOLED", ct_all$estimate, ct_all$p.value, nrow(dados_pais)))

cat("\n---- Regressao pooled: delta_share_pp ~ fator_emissao + beta + setor ----\n")
dados_pais_z <- dados_pais %>%
  mutate(
    fator_z = as.numeric(scale(fator_emissao_pond)),
    beta_z  = as.numeric(scale(beta_pond))
  )
m <- lm(delta_share_pp ~ fator_z + beta_z + setor, data = dados_pais_z)
print(summary(m))

cat("\n---- Regressao pooled (variacao relativa %) ~ fator_emissao + beta + setor ----\n")
m2 <- lm(variacao_relativa_pct ~ fator_z + beta_z + setor, data = dados_pais_z)
print(summary(m2))

cat("\nSalvo: analise_realocacao_cesta.csv, analise_realocacao_paises.csv\n")

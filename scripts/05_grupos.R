############################################
# 05_grupos.R — PPML share
# ----------------------------------------
# Elasticidades médias por grupo de produto.
# Depende de: 03_paises.R
############################################

cat("[ 05 ] Agrupamento por grau de processamento...\n")

config_file <- file.path(dir_config, paste0(produto_ativo, "_grupos.R"))

if (file.exists(config_file)) {
  source(config_file)
  cat("  Config carregada:", config_file, "\n")
} else {
  stop("Arquivo de configuração não encontrado: ", config_file)
}

df <- df %>% left_join(grupo_map, by = "product")

col_base <- "beta_base"
cols_sim  <- paste0("beta_sim_", paises_grupo)

share_medio <- df %>%
  filter(!is.na(share)) %>%
  group_by(product) %>%
  summarise(share_medio = mean(share, na.rm = TRUE), .groups = "drop")

betas_grupo <- betas_simulacao %>%
  left_join(grupo_map,   by = "product") %>%
  left_join(share_medio, by = "product")

resumo_grupo <- betas_grupo %>%
  group_by(grupo, grupo_label) %>%
  summarise(
    n_produtos       = n(),
    beta_global_pond = weighted.mean(.data[[col_base]], share_medio, na.rm = TRUE),
    across(all_of(cols_sim),
           ~ weighted.mean(.x, share_medio, na.rm = TRUE),
           .names = "{.col}_pond"),
    .groups = "drop"
  ) %>%
  arrange(grupo)

cat("\n  === ELASTICIDADES POR GRUPO ===\n")
print(resumo_grupo)

tabela_final <- betas_simulacao %>%
  left_join(grupo_map, by = "product") %>%
  arrange(grupo, product)

write.csv(tabela_final,
          file.path(dir_output, "8_tabela_betas_grupos.csv"),
          row.names = FALSE)

n_grupos      <- n_distinct(grupo_map$grupo_label)
cores_base    <- c("#1D9E75", "#BA7517", "#A32D2D", "#185FA5", "#7F77DD", "#D4537E")
grupos_unicos <- grupo_map %>% distinct(grupo, grupo_label) %>% arrange(grupo) %>% pull(grupo_label)
cores_grupo   <- setNames(cores_base[seq_along(grupos_unicos)], grupos_unicos)

resumo_longo <- resumo_grupo %>%
  pivot_longer(cols = ends_with("_pond"), names_to = "pais", values_to = "beta") %>%
  mutate(
    pais = case_when(
      pais == "beta_global_pond" ~ "Global",
      TRUE ~ gsub("beta_sim_|_pond", "", pais)
    ),
    pais = factor(pais, levels = c("Global", paises_grupo))
  )

p_barras <- ggplot(resumo_longo, aes(x = pais, y = beta, fill = grupo_label)) +
  geom_col(position = position_dodge(width = 0.7), width = 0.6) +
  geom_hline(yintercept = 0, linetype = "dashed", color = "gray40") +
  scale_fill_manual(values = cores_grupo) +
  facet_wrap(~grupo_label, ncol = min(3, n_grupos)) +
  labs(title = paste("Elasticidade-preço por grupo —", produto_ativo),
       x = NULL, y = "Elasticidade (β)", fill = NULL) +
  theme_minimal() +
  theme(legend.position = "none")

ggsave(file.path(dir_output, "9_elasticidades_grupos_barras.png"),
       plot = p_barras, width = 10, height = 5, dpi = 150)

betas_longo <- betas_simulacao %>%
  left_join(grupo_map, by = "product") %>%
  pivot_longer(cols = c(all_of(col_base), all_of(cols_sim)),
               names_to = "pais", values_to = "beta") %>%
  mutate(
    pais = case_when(pais == col_base ~ "Global", TRUE ~ gsub("beta_sim_", "", pais)),
    pais = factor(pais, levels = c("Global", paises_grupo))
  )

p_disp <- ggplot(betas_longo, aes(x = pais, y = beta, color = grupo_label)) +
  geom_jitter(width = 0.08, size = 3, alpha = 0.8) +
  geom_hline(yintercept = 0, linetype = "dashed", color = "gray40") +
  scale_color_manual(values = cores_grupo) +
  facet_wrap(~grupo_label, ncol = min(3, n_grupos)) +
  labs(title = paste("Dispersão das elasticidades —", produto_ativo),
       x = NULL, y = "Elasticidade (β)", color = NULL) +
  theme_minimal() +
  theme(legend.position = "none")

ggsave(file.path(dir_output, "10_elasticidades_grupos_dispersao.png"),
       plot = p_disp, width = 10, height = 5, dpi = 150)

cat("[ 05 ] OK\n\n")

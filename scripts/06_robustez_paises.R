############################################
# 06_robustez_paises.R — PPML share
# ----------------------------------------
# PPML restrito ao grupo paises_grupo.
# Compara betas com o modelo principal.
# Depende de: 01_limpeza.R, 03_paises.R
############################################

cat("[ 06 ] Robustez — modelo restrito ao grupo", nome_grupo, "...\n")

label_global <- "Global (todos países)"
label_rob    <- paste0("Robustez (só ", nome_grupo, ")")
cols_sim     <- paste0("beta_sim_", paises_grupo)

df_grupo_rob <- preparar_pesos(
  df %>% filter(exporter %in% paises_grupo, !is.na(log_price_rel), !is.na(share)),
  usar_peso_tempo, half_life
)

cat("  Obs total:", nrow(df_grupo_rob), "\n")

model_rob_paises <- fepois(
  share ~ log_price_rel:factor(product) | exporter^product + product^year,
  data    = df_grupo_rob,
  weights = ~peso_tempo,
  cluster = ~year
)

etable(model_rob_paises, tex = TRUE,
       file = file.path(dir_output, "11_tabela_robustez_paises.tex"))

coefs_rob <- tidy(model_rob_paises) %>%
  filter(grepl("^log_price_rel:factor\\(product\\)", term)) %>%
  mutate(
    product  = str_trim(gsub("log_price_rel:factor\\(product\\)", "", term)),
    beta_rob = estimate,
    se_rob   = std.error,
    sig_rob  = abs(estimate / std.error) > z_critico
  ) %>%
  select(product, beta_rob, se_rob, sig_rob)

comparacao_rob <- betas_simulacao %>%
  select(product, beta_base, se_base, all_of(cols_sim)) %>%
  left_join(coefs_rob, by = "product") %>%
  mutate(diff_pct = (beta_rob - beta_base) / abs(beta_base) * 100) %>%
  arrange(product)

cat("\n  === COMPARAÇÃO — PRINCIPAL vs. ROBUSTEZ ===\n")
print(comparacao_rob, n = Inf)

n_instavel <- sum(abs(comparacao_rob$diff_pct) > 50, na.rm = TRUE)
cat(sprintf("\n  Produtos com divergência > 50%%: %d de %d\n",
            n_instavel, nrow(comparacao_rob)))

comp_longo <- comparacao_rob %>%
  pivot_longer(cols = c("beta_base", "beta_rob", all_of(cols_sim)),
               names_to = "modelo", values_to = "beta") %>%
  mutate(modelo = case_when(
    modelo == "beta_base" ~ label_global,
    modelo == "beta_rob"  ~ label_rob,
    TRUE                  ~ gsub("beta_sim_", "", modelo)
  )) %>%
  filter(!is.na(beta))

source(file.path(dir_scripts, "helper_grupos.R"))

n_paises   <- length(paises_grupo)
cores_pais <- setNames(scales::hue_pal()(n_paises), paises_grupo)
cores_comp <- c(setNames("gray50", label_global),
                setNames("#BA7517", label_rob),
                cores_pais)

df_p_rob <- comp_longo %>%
  preparar_plot_grupos(col_produto = "product", col_valor = "beta",
                       col_peso = NULL, cols_resumo = c("exporter"))

p_rob <- df_p_rob %>%
  ggplot(aes(x = beta, y = product, color = modelo, shape = modelo)) +
  geom_vline(xintercept = 0, linetype = "dashed", color = "gray60") +
  geom_point(size = 3, alpha = 0.85, position = position_dodge(width = 0.4)) +
  scale_color_manual(values = cores_comp) +
  labs(title = paste("Robustez —", produto_ativo),
       subtitle = paste("Global vs.", nome_grupo, "vs. modelo restrito"),
       x = "Elasticidade (β)", y = NULL, color = NULL, shape = NULL) +
  theme_minimal() +
  theme(legend.position = "bottom")

ggsave(file.path(dir_output, "12_robustez_modelo_paises.png"),
       plot = p_rob, width = 9, height = 6, dpi = 150)

cat("[ 06 ] OK\n\n")

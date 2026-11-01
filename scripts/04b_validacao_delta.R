############################################
# 04b_validacao_delta.R
# ----------------------------------------
# Validação adicional: β como elasticidade
# de VARIAÇÕES (não de níveis).
#
# Lógica:
#   Para cada par (exportador × produto):
#     Δlog(DV)_obs  = log(DV_teste) - log(DV_base)
#     Δlog(DV)_pred = β_sim × Δlog(preço_rel)
#
#   Se β captura bem a substituição, as duas
#   séries devem ter correlação positiva e
#   slope próximo de 1.
#
# Métricas:
#   cor       → β acerta direção?
#   slope     → β bem calibrado em magnitude?
#   sign_acc  → % de pares com sinal correto
#   mae_delta → erro médio em Δlog
#
# DV deste script: share
#
# Depende (em memória): df, betas_simulacao,
#   paises_grupo, janela_base, ano_val_treino,
#   ano_val_teste, dir_output, produto_ativo
############################################

cat("[ 04b ] Validação delta — β como elasticidade de variações (share)...\n")

# ── Parâmetros ─────────────────────────────────────────────────────────────────
dv_col       <- "share"
min_dv_delta <- 0          # share > 0 é suficiente

anos_base_val  <- (ano_val_treino - janela_base + 1):ano_val_treino
anos_teste_val <- (ano_val_treino + 1):ano_val_teste

if (length(anos_teste_val) == 0) {
  cat("  [04b] Nenhum ano de teste disponível — pulando.\n")
  cat("[ 04b ] OK\n")
} else {

cat(sprintf("  DV: %s | Base: %d–%d | Teste: %d–%d\n",
            dv_col,
            min(anos_base_val), max(anos_base_val),
            min(anos_teste_val), max(anos_teste_val)))

# ── 1. Período base: TODOS os exportadores com dados suficientes ──────────────
base_df <- df %>%
  filter(year %in% anos_base_val,
         .data[[dv_col]] > min_dv_delta,
         price_rel > 0, is.finite(price_rel)) %>%
  group_by(exporter, product) %>%
  summarise(
    dv_base        = mean(.data[[dv_col]], na.rm = TRUE),
    price_rel_base = mean(price_rel,       na.rm = TRUE),
    n_base         = n(),
    .groups        = "drop"
  ) %>%
  filter(dv_base > 0, price_rel_base > 0, n_base >= 1)

cat(sprintf("  Exportadores no período base: %d | Pares exp×prod: %d\n",
            n_distinct(base_df$exporter), nrow(base_df)))

# ── 2. Período teste: TODOS os exportadores ───────────────────────────────────
test_df <- df %>%
  filter(year %in% anos_teste_val,
         .data[[dv_col]] > min_dv_delta,
         price_rel > 0, is.finite(price_rel)) %>%
  select(exporter, product, year,
         dv_obs         = all_of(dv_col),
         price_rel_test = price_rel)

# ── 3. Betas: focal = beta_sim_X; demais = beta_base (global por produto) ─────
#
# O β foi estimado com todos os exportadores — faz sentido testá-lo em todos.
# Países focais (paises_grupo) recebem o β shrinkage-ajustado.
# Todos os outros recebem o β global por produto (beta_base).

beta_cols_disp <- intersect(paste0("beta_sim_", paises_grupo),
                             names(betas_simulacao))

# Betas dos países focais (shrinkage-ajustado)
beta_focal <- betas_simulacao %>%
  select(product, all_of(beta_cols_disp)) %>%
  pivot_longer(
    cols         = all_of(beta_cols_disp),
    names_to     = "exporter",
    names_prefix = "beta_sim_",
    values_to    = "beta_sim"
  ) %>%
  filter(!is.na(beta_sim)) %>%
  mutate(grupo_exporter = "focal")

# Betas de todos os outros exportadores (beta global)
exportadores_nao_focais <- setdiff(unique(base_df$exporter), paises_grupo)

beta_outros <- tidyr::expand_grid(
  betas_simulacao %>%
    select(product, beta_sim = beta_base) %>%
    filter(!is.na(beta_sim)),
  exporter = exportadores_nao_focais
) %>%
  mutate(grupo_exporter = "outros")

beta_long <- bind_rows(beta_focal, beta_outros)

# ── 4. Combinar e computar deltas ─────────────────────────────────────────────
delta_df <- test_df %>%
  left_join(base_df,   by = c("exporter", "product")) %>%
  left_join(beta_long, by = c("exporter", "product")) %>%
  filter(!is.na(dv_base), !is.na(price_rel_base), !is.na(beta_sim),
         dv_base > 0, price_rel_base > 0) %>%
  mutate(
    # Variação observada e predita (em log)
    delta_log_dv_obs  = log(dv_obs)         - log(dv_base),
    delta_log_price   = log(price_rel_test)  - log(price_rel_base),
    delta_log_dv_pred = beta_sim * delta_log_price,

    # Resíduo e acerto de sinal
    residuo      = delta_log_dv_obs - delta_log_dv_pred,
    sign_correct = sign(delta_log_dv_obs) == sign(delta_log_dv_pred)
  ) %>%
  filter(is.finite(delta_log_dv_obs),
         is.finite(delta_log_dv_pred),
         is.finite(residuo))

cat(sprintf("  Pares usados na validação delta: %d\n", nrow(delta_df)))

if (nrow(delta_df) < 4) {
  cat("  [04b] Dados insuficientes — pulando métricas.\n")
} else {

# ── 5. Métricas por ano × país ────────────────────────────────────────────────
.calc_metricas_delta <- function(d) {
  n <- nrow(d)
  if (n < 3) return(tibble(n = n, cor = NA_real_, slope = NA_real_,
                            sign_acc = NA_real_, mae_delta = NA_real_))
  cor_v   <- cor(d$delta_log_dv_obs, d$delta_log_dv_pred)
  slope_v <- tryCatch(
    coef(lm(delta_log_dv_obs ~ delta_log_dv_pred, data = d))[[2]],
    error = function(e) NA_real_
  )
  tibble(
    n         = n,
    cor       = round(cor_v,                                            3),
    slope     = round(slope_v,                                          3),
    sign_acc  = round(mean(d$sign_correct, na.rm = TRUE) * 100,        1),
    mae_delta = round(mean(abs(d$residuo),  na.rm = TRUE),             4)
  )
}

# ── Métricas por grupo: geral, focal, outros, e focal individual ──────────────

# Geral (todos os exportadores) — por ano + pooled
metricas_geral_ano <- delta_df %>%
  group_by(ano = as.character(year)) %>%
  group_modify(~ .calc_metricas_delta(.x)) %>%
  ungroup() %>%
  mutate(grupo = "geral")

metricas_geral_pool <- .calc_metricas_delta(delta_df) %>%
  mutate(ano = "pooled", grupo = "geral")

metricas_geral <- bind_rows(metricas_geral_ano, metricas_geral_pool)

# Por grupo focal / outros — por ano + pooled
metricas_grupos_ano <- delta_df %>%
  group_by(ano = as.character(year), grupo = grupo_exporter) %>%
  group_modify(~ .calc_metricas_delta(.x)) %>%
  ungroup()

metricas_grupos_pool <- delta_df %>%
  group_by(grupo = grupo_exporter) %>%
  group_modify(~ .calc_metricas_delta(.x)) %>%
  ungroup() %>%
  mutate(ano = "pooled")

metricas_grupos <- bind_rows(metricas_grupos_ano, metricas_grupos_pool)

# Por país focal individualmente
metricas_focais <- delta_df %>%
  filter(grupo_exporter == "focal") %>%
  group_by(ano = as.character(year), exporter) %>%
  group_modify(~ .calc_metricas_delta(.x)) %>%
  ungroup() %>%
  bind_rows(
    delta_df %>%
      filter(grupo_exporter == "focal") %>%
      group_by(exporter) %>%
      group_modify(~ .calc_metricas_delta(.x)) %>%
      ungroup() %>%
      mutate(ano = "pooled")
  ) %>%
  mutate(grupo = exporter)

metricas_total <- bind_rows(metricas_geral, metricas_grupos, metricas_focais) %>%
  mutate(setor = produto_ativo) %>%
  arrange(grupo, ano)

cat("\n  ── Métricas delta: todos os exportadores ──\n")
cat("  [geral = todos | focal = BR+AR | outros = restante]\n\n")
print(metricas_total, n = Inf)

cat("\n  Interpretação:\n")
cat("    cor > 0    → β captura a direção das variações de share\n")
cat("    slope ≈ 1  → β bem calibrado em magnitude\n")
cat("    slope < 1  → β sobrestima a resposta (observado < previsto)\n")
cat("    slope > 1  → β subestima a resposta (observado > previsto)\n")
cat("    sign_acc   → % de pares com sinal correto (> 50% = acima do aleatório)\n\n")

# ── 6. Scatter Δlog(obs) × Δlog(pred) ────────────────────────────────────────
lim_max <- delta_df %>%
  summarise(lim = max(abs(c(delta_log_dv_obs, delta_log_dv_pred)),
                      na.rm = TRUE) * 1.12) %>%
  pull(lim)
lim_max <- max(lim_max, 0.1)   # mínimo para o gráfico não colapsar

ncol_p <- min(3, length(anos_teste_val))

# Classificar exportadores para o scatter: focal recebe rótulo, outros = cinza
delta_plot_df <- delta_df %>%
  mutate(
    ano_label  = paste("Teste:", year),
    exp_label  = if_else(grupo_exporter == "focal", exporter, "outros"),
    pt_alpha   = if_else(grupo_exporter == "focal", 0.90, 0.25),
    pt_size    = if_else(grupo_exporter == "focal", 2.8,  1.2)
  )

cores_base <- c("#E41A1C", "#377EB8", "#4DAF4A", "#984EA3")
cores_scatter <- c(
  setNames(cores_base[seq_along(paises_grupo)], paises_grupo),
  outros = "grey60"
)

p_delta <- ggplot(delta_plot_df,
                  aes(x = delta_log_dv_pred, y = delta_log_dv_obs)) +
  geom_hline(yintercept = 0, colour = "grey75", linewidth = 0.4) +
  geom_vline(xintercept = 0, colour = "grey75", linewidth = 0.4) +
  geom_abline(slope = 1, intercept = 0,
              linetype = "dashed", colour = "grey30", linewidth = 0.8) +
  # Pontos: outros em cinza, focais com cor
  geom_point(data = ~ filter(.x, exp_label == "outros"),
             colour = "grey60", size = 1.2, alpha = 0.25) +
  geom_point(data = ~ filter(.x, exp_label != "outros"),
             aes(colour = exp_label), size = 2.8, alpha = 0.90) +
  # Rótulo de produto só para focais
  geom_text(data = ~ filter(.x, exp_label != "outros"),
            aes(label = product, colour = exp_label),
            size = 1.9, vjust = -0.65, show.legend = FALSE) +
  # Regressão geral (todos)
  geom_smooth(method = "lm", formula = y ~ x, se = TRUE,
              colour = "black", linewidth = 0.8, alpha = 0.12,
              linetype = "solid") +
  # Regressão focais
  geom_smooth(data = ~ filter(.x, exp_label != "outros"),
              aes(colour = exp_label, group = exp_label),
              method = "lm", formula = y ~ x, se = FALSE,
              linewidth = 0.7, linetype = "dotted") +
  scale_colour_manual(values = cores_scatter, name = "País") +
  coord_cartesian(xlim = c(-lim_max, lim_max),
                  ylim = c(-lim_max, lim_max)) +
  facet_wrap(~ ano_label, ncol = ncol_p) +
  labs(
    title    = sprintf("Validação Δ — %s (share): β prediz variações?",
                       toupper(produto_ativo)),
    subtitle = paste("Tracejada = calibração perfeita | Sólida preta = OLS geral",
                     "| Pontilhada = OLS por país focal"),
    x        = "Δlog(share) predito  [= β × Δlog(preço_rel)]",
    y        = "Δlog(share) observado",
    caption  = sprintf("Pontos cinzas = outros exportadores (β global) | Base: média %d–%d",
                       min(anos_base_val), max(anos_base_val))
  ) +
  theme_minimal(base_size = 11) +
  theme(
    plot.title      = element_text(face = "bold", size = 12),
    plot.subtitle   = element_text(size = 9, colour = "grey40"),
    legend.position = "bottom",
    strip.text      = element_text(face = "bold")
  )

ggsave(file.path(dir_output, "5c_validacao_delta_scatter.png"),
       p_delta,
       width  = 5 * ncol_p + 1,
       height = 5,
       dpi    = 150)

# ── 7. Salvar CSVs ────────────────────────────────────────────────────────────
write.csv(
  metricas_total,
  file.path(dir_output, "5c_validacao_delta_metricas.csv"),
  row.names = FALSE
)

write.csv(
  delta_df %>%
    select(exporter, product, year,
           dv_obs, dv_base,
           price_rel_test, price_rel_base,
           beta_sim,
           delta_log_dv_obs, delta_log_price,
           delta_log_dv_pred, sign_correct),
  file.path(dir_output, "5c_validacao_delta_dados.csv"),
  row.names = FALSE
)

cat(sprintf("  Salvo: 5c_validacao_delta_metricas.csv\n"))
cat(sprintf("  Salvo: 5c_validacao_delta_scatter.png\n"))

}  # fim if nrow >= 4
}  # fim if length(anos_teste_val) > 0

cat("[ 04b ] OK\n")

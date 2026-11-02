############################################
# 01_limpeza.R — PPML share
# ----------------------------------------
# Loads, cleans and builds variables.
# DV principal: share (market share)
#
# Depende de: main.R
# Produz: df (share, log_price_rel, dummies)
############################################

cat("[ 01 ] Cleaning and variable construction...\n")

arquivo_price <- switch(produto_ativo,
  "aluminio"  = file.path(dir_config, "Base_de_dados_final_Aluminio.csv"),
  "ferro_aco" = file.path(dir_config, "Base_de_dados_final_Ferro.csv"),
  "cimento"   = file.path(dir_config, "Base_de_dados_final_Cimento.csv"),
  stop("invalid produto_ativo: ", produto_ativo)
)

df_raw <- read.csv(file = arquivo_price, header = TRUE, sep = ";")
registrar(df_raw, "01", "01. raw", note = "before any filter")

df <- df_raw %>%
  mutate(
    product = as.character(product),
    kg      = as.numeric(kg),
    euro    = as.numeric(euro),
    ton     = as.numeric(ton),
    year    = as.numeric(year),
    tariff  = as.numeric(tariff)
  ) %>%
  filter(year >= ano_inicio, year <= ano_corte)

registrar(df, "01", "02. period filter", note = paste(ano_inicio, "to", ano_corte))

df <- df %>%
  filter(!is.na(ton), !is.na(euro), !is.na(tariff), ton >= 1, euro >= 0) %>%
  filter(ton > filtro_vol, euro > filtro_euros)

registrar(df, "01", "03. removed NAs/negatives and minimum filters")

# Singletons
n_antes <- nrow(df)
df <- df %>%
  group_by(exporter, product) %>%
  filter(n_distinct(year) >= min_anos_obs) %>%
  ungroup()
cat("  Singletons removed:", n_antes - nrow(df), "obs |",
    n_distinct(df$exporter), "exportadores\n")

registrar(df, "01", "04. singleton removal")

# Minimum share filter
if (!is.null(share_min_pais)) {
  ton_total_prov <- df %>%
    group_by(product, year) %>%
    summarise(ton_total = sum(ton, na.rm = TRUE), .groups = "drop")
  share_medio_prov <- df %>%
    left_join(ton_total_prov, by = c("product", "year")) %>%
    mutate(share_prov = if_else(ton_total > 0, ton / ton_total, NA_real_)) %>%
    group_by(exporter, product) %>%
    summarise(share_medio = mean(share_prov, na.rm = TRUE), .groups = "drop") %>%
    filter(share_medio >= share_min_pais | exporter %in% paises_grupo)
  n_antes <- n_distinct(df$exporter)
  df <- df %>% semi_join(share_medio_prov, by = c("exporter", "product"))
  cat("  Filtro share >= ", share_min_pais * 100, "%:",
      n_antes - n_distinct(df$exporter), "exportadores removidos\n")
}

# Unit price and tariff adjustment
df <- df %>%
  mutate(price = if_else(ton > 0, euro / ton, NA_real_))

if (price_model == "post_tax") {
  df <- df %>% mutate(price = price * (1 + tariff))
}

df <- df %>%
  mutate(euro_loo = if_else(price_model == "post_tax" & !is.na(price),
                             price * ton, euro))

# Leave-one-out average price
df <- df %>%
  group_by(product, year) %>%
  mutate(
    total_ton_all  = sum(ton,      na.rm = TRUE),
    total_euro_all = sum(euro_loo, na.rm = TRUE),
    total_ton_loo  = total_ton_all  - ton,
    total_euro_loo = total_euro_all - euro_loo,
    price_avg_loo  = if_else(total_ton_loo > 0,
                             total_euro_loo / total_ton_loo, NA_real_)
  ) %>%
  ungroup()

# Market share and relative price
df <- df %>%
  mutate(
    share     = if_else(total_ton_all > 0, ton / total_ton_all, NA_real_),
    price_rel = if_else(!is.na(price) & !is.na(price_avg_loo) & price_avg_loo > 0,
                        price / price_avg_loo, NA_real_)
  )

# Winsorisation
if (!is.null(winsor_price_rel)) {
  p_high <- quantile(df$price_rel, 1 - winsor_price_rel, na.rm = TRUE)
  cat("  Winsorisation price_rel (", winsor_price_rel * 100, "%) — p_high:", round(p_high, 4), "\n")
  df <- df %>%
    mutate(price_rel_orig = price_rel,
           price_rel      = pmin(price_rel, p_high))
  cat("  Adjusted obs:", sum(df$price_rel_orig > p_high, na.rm = TRUE), "\n")
}

df <- df %>% mutate(log_price_rel = log(price_rel))

registrar(df, "01", "05. final dataset with price_rel")

# Dummies for each country in the group
for (cod in paises_grupo) {
  df[[paste0("d_", cod)]] <- if_else(df$exporter == cod, 1L, 0L)
}

cat("  Total obs:           ", nrow(df), "\n")
cat("  Obs with NA price_rel:", sum(is.na(df$price_rel)), "\n")
for (cod in paises_grupo) {
  cat("  Obs", cod, ":", sum(df$exporter == cod), "\n")
}
cat("[ 01 ] OK\n\n")

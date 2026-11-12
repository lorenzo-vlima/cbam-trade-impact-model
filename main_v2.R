############################################
# MODEL 01 — PPML with market share — v2
# ----------------------------------------
# Difference relative to main.R:
#   Uses funcoes_modelo_v2.R, which applies a sign
#   constraint in the shrinkage: if beta_sim > 0,
#   it censors beta_country at 0 before the shrinkage
#   → beta_final = (1-w) * beta_global (negativo,
#     less elastic than the global one).
#
#   Affected products (checked in all sectors):
#     - 260112 BR (ferro_aco): beta_sim +0.177 → -0.033
#     - 250700 AR (cimento):   beta_sim +1.577 → -0.188
#
#   Output saved in a separate directory (_v2).
############################################

pkgs <- c("tidyverse", "fixest", "broom", "ggplot2", "janitor")
for (p in pkgs) if (!require(p, character.only = TRUE)) install.packages(p)
invisible(lapply(pkgs, library, character.only = TRUE))

dir_scripts <- "scripts"
dir_config  <- "config"
dir_helpers <- "helpers"

# ----------------------------------------
# CONFIGURATION — EDIT ONLY HERE
# ----------------------------------------

produto_ativo <- "aluminio"

paises_grupo <- c("BR", "AR")
nome_grupo   <- "brazil_and_argentina"

price_model <- "post_tax"

filtro_vol   <- 1
filtro_euros <- 0

usar_peso_tempo <- FALSE
half_life       <- 5

modo_grupo <- "individual"

min_anos_obs <- 5

z_critico <- 1.96

winsor_price_rel <- 0.01

ano_inicio     <- 2010
ano_corte      <- 2025

ano_val_treino  <- 2024
ano_val_teste   <- 2025

# Output folder suffix (the anti-dumping test uses "roll2015" runs)
sufixo_output  <- "v2"

share_min_pais <- NULL

janela_base        <- 3
premissa_agregacao <- "media_simples"
fase_cbam          <- "factor_2026"

cenarios_carbono <- c(baixo = 75, medio = 95, alto = 115)
cenarios_tarifa  <- c("MFN", "Mercosul")
paises_mercosul  <- c("BR", "AR", "UY", "PY")

projecao_anos <- tribble(
  ~ano,  ~fase,
  2026,  "factor_2026",
  2027,  "factor_2027",
  2028,  "factor_2028"
)

projecao_precos <- c(
  `2025` = 0,
  `2026` = 75,
  `2027` = 95,
  `2028` = 115
)

# ----------------------------------------
# VALIDATION
# ----------------------------------------

if (modo_grupo != "individual")
  stop("modo_grupo must be 'individual'.")

if (length(paises_grupo) == 0)
  stop("paises_grupo cannot be empty.")

# ----------------------------------------
# OUTPUT PATHS — _v2 suffix
# ----------------------------------------

dir_output <- file.path("outputs",
                        paste(produto_ativo, nome_grupo, modo_grupo, price_model,
                              paste0("j", janela_base), sufixo_output, sep = "_"))
dir.create(dir_output, recursive = TRUE, showWarnings = FALSE)

cat("========================================\n")
cat("Model: PPML share — v2 (sign-constrained shrinkage)\n")
cat("Period:", ano_inicio, "–", ano_corte, "\n")
cat("Product:", toupper(produto_ativo), "\n")
cat("Countries: ", paste(paises_grupo, collapse = ", "), "\n")
cat("Output:  ", dir_output, "\n")
cat("========================================\n\n")

# ----------------------------------------
# PIPELINE — uses funcoes_modelo_v2.R
# ----------------------------------------

source(file.path(dir_scripts, "00_tracking.R"))
source(file.path(dir_scripts, "01_limpeza.R"))
source(file.path(dir_helpers, "funcoes_modelo_v2.R"))   # <- v2
source(file.path(dir_scripts, "02_modelo.R"))
source(file.path(dir_scripts, "03_paises.R"))
source(file.path(dir_scripts, "04_validacao.R"))
source(file.path(dir_scripts, "04b_validacao_delta.R"))
source(file.path(dir_scripts, "05_grupos.R"))
source(file.path(dir_scripts, "06_robustez_paises.R"))
source(file.path(dir_scripts, "07_simulacao_cbam.R"))
source(file.path(dir_scripts, "08_projecao_cbam.R"))
source(file.path(dir_scripts, "09_analise.R"))

cat("\n========================================\n")
cat("DONE:", toupper(produto_ativo), "v2\n")
cat("Output em:", dir_output, "\n")
cat("========================================\n")

imprimir_tracking(dir_output = dir_output)

############################################
# MODELO 01 — PPML com market share — v2
# ----------------------------------------
# Diferença em relação ao main.R:
#   Usa funcoes_modelo_v2.R que aplica restrição
#   de sinal no shrinkage: se beta_sim > 0,
#   censura beta_country em 0 antes do shrinkage
#   → beta_final = (1-w) * beta_global (negativo,
#     menos elástico que o global).
#
#   Produtos afetados (verificados em todos setores):
#     - 260112 BR (ferro_aco): beta_sim +0.177 → -0.033
#     - 250700 AR (cimento):   beta_sim +1.577 → -0.188
#
#   Output salvo em diretório separado (_v2).
############################################

pkgs <- c("tidyverse", "fixest", "broom", "ggplot2", "janitor")
for (p in pkgs) if (!require(p, character.only = TRUE)) install.packages(p)
invisible(lapply(pkgs, library, character.only = TRUE))

dir_scripts <- "scripts"
dir_config  <- "config"
dir_helpers <- "helpers"

# ----------------------------------------
# CONFIGURAÇÃO — EDITAR APENAS AQUI
# ----------------------------------------

produto_ativo <- "aluminio"

paises_grupo <- c("BR", "AR")
nome_grupo   <- "brasil_e_argentina"

price_model <- "post_tax"

filtro_vol   <- 1
filtro_euros <- 0

usar_peso_tempo <- FALSE
half_life       <- 5

modo_grupo <- "individual"

min_obs      <- 5
min_anos_obs <- 5

z_critico <- 1.96

winsor_price_rel <- 0.01

ano_inicio     <- 2010
ano_corte      <- 2025

ano_val_treino  <- 2022
ano_val_teste   <- 2025

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
# VALIDAÇÃO
# ----------------------------------------

if (!modo_grupo %in% c("individual", "agregado"))
  stop("modo_grupo deve ser 'individual'.")

if (length(paises_grupo) == 0)
  stop("paises_grupo não pode ser vazio.")

# ----------------------------------------
# PATHS DE OUTPUT — sufixo _v2
# ----------------------------------------

dir_output <- file.path("outputs",
                        paste(produto_ativo, nome_grupo, modo_grupo, price_model,
                              paste0("j", janela_base), "v2", sep = "_"))
dir.create(dir_output, recursive = TRUE, showWarnings = FALSE)

cat("========================================\n")
cat("Modelo: PPML share — v2 (sign-constrained shrinkage)\n")
cat("Período:", ano_inicio, "–", ano_corte, "\n")
cat("Produto:", toupper(produto_ativo), "\n")
cat("Países: ", paste(paises_grupo, collapse = ", "), "\n")
cat("Output:  ", dir_output, "\n")
cat("========================================\n\n")

# ----------------------------------------
# PIPELINE — usa funcoes_modelo_v2.R
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
cat("CONCLUIDO:", toupper(produto_ativo), "v2\n")
cat("Output em:", dir_output, "\n")
cat("========================================\n")

imprimir_tracking(dir_output = dir_output)

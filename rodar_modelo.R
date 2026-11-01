############################################
# rodar_modelo.R — roda o MODELO OFICIAL (main_v2.R, com shrinkage
# e share setorial corrigido) para um setor e grupo de países.
#
# Editar as 3 linhas abaixo e rodar:
#   "C:/Program Files/R/R-4.5.3/bin/Rscript.exe" rodar_modelo.R
# (working directory = esta pasta MODELO_OFICIAL/)
############################################

PRODUTO <- "cimento"                          # "ferro_aco" | "aluminio" | "cimento"
PAISES  <- c("TR","UA","GB","BR","US","DZ","CN","EG","TN","BY","AR")
NOME    <- "cesta_padrao"                     # nome do grupo (vira sufixo da pasta output)

linhas <- readLines("main_v2.R", warn = FALSE, encoding = "UTF-8")
linhas <- sub("^produto_ativo[[:space:]]*<-.*",
              paste0('produto_ativo <- "', PRODUTO, '"'), linhas)
linhas <- sub("^paises_grupo[[:space:]]*<-.*",
              paste0('paises_grupo <- c(', paste0('"', PAISES, '"', collapse = ", "), ')'),
              linhas)
linhas <- sub("^nome_grupo[[:space:]]*<-.*",
              paste0('nome_grupo <- "', NOME, '"'), linhas)

tmp <- tempfile(fileext = ".R")
writeLines(linhas, tmp, useBytes = TRUE)
cat("== MODELO OFICIAL |", PRODUTO, "|", paste(PAISES, collapse = "+"), "==\n")
source(tmp, echo = FALSE)

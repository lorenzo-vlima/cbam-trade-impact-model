############################################
# rodar_modelo.R — runs the OFFICIAL MODEL (main_v2.R, with shrinkage
# and the corrected sector share) for a sector and a group of countries.
#
# Edit the 3 lines below and run:
#   "C:/Program Files/R/R-4.5.3/bin/Rscript.exe" rodar_modelo.R
# (working directory = this repository root)
############################################

PRODUTO <- "ferro_aco"                          # "ferro_aco" | "aluminio" | "cimento"
PAISES  <- c("BR", "AR")
NOME    <- "brazil_and_argentina"             # group name (becomes the output folder suffix)

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
cat("== OFFICIAL MODEL |", PRODUTO, "|", paste(PAISES, collapse = "+"), "==\n")
source(tmp, echo = FALSE)

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
NOME    <- "brazil_and_argentina"             # run name (part of the output folder name)

# Optional: historical test (anti-dumping 2016) runs on data up to 2015.
# Use ANO_CORTE <- 2015 and SUFIXO <- "roll2015"; leave NULL for the main runs.
ANO_CORTE <- NULL
SUFIXO    <- NULL

# Optional: price definition. "post_tax" (the paper) adds the ad valorem tariff to the
# price; any other value, for example "pre_tax", leaves the price without the tariff.
PRICE_MODEL <- NULL

linhas <- readLines("main_v2.R", warn = FALSE, encoding = "UTF-8")
linhas <- sub("^produto_ativo[[:space:]]*<-.*",
              paste0('produto_ativo <- "', PRODUTO, '"'), linhas)
linhas <- sub("^paises_grupo[[:space:]]*<-.*",
              paste0('paises_grupo <- c(', paste0('"', PAISES, '"', collapse = ", "), ')'),
              linhas)
linhas <- sub("^nome_grupo[[:space:]]*<-.*",
              paste0('nome_grupo <- "', NOME, '"'), linhas)

if (!is.null(ANO_CORTE)) {
  linhas <- sub("^ano_corte[[:space:]]*<-.*", paste0("ano_corte <- ", ANO_CORTE), linhas)
  linhas <- sub("^ano_val_treino[[:space:]]*<-.*", paste0("ano_val_treino <- ", ANO_CORTE - 2), linhas)
  linhas <- sub("^ano_val_teste[[:space:]]*<-.*", paste0("ano_val_teste <- ", ANO_CORTE), linhas)
}
if (!is.null(PRICE_MODEL)) {
  linhas <- sub("^price_model[[:space:]]*<-.*", paste0('price_model <- "', PRICE_MODEL, '"'), linhas)
}
if (!is.null(SUFIXO)) {
  linhas <- sub("^sufixo_output[[:space:]]*<-.*", paste0('sufixo_output <- "', SUFIXO, '"'), linhas)
}

tmp <- tempfile(fileext = ".R")
writeLines(linhas, tmp, useBytes = TRUE)
cat("== OFFICIAL MODEL |", PRODUTO, "|", paste(PAISES, collapse = "+"), "==\n")
source(tmp, echo = FALSE)

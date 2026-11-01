############################################
# helper_grupos.R
# ----------------------------------------
# Função auxiliar para ordenar produtos
# por grupo e adicionar linhas de resumo
# nos gráficos com produtos no eixo Y.
#
# Usado em: 06, 07, 08
# Depende de: config/{produto}_grupos.R
############################################

# Carregar grupo_map do config correspondente
.grupo_map_df <- switch(produto_ativo,
                        "aluminio"  = { source(file.path(dir_config, "aluminio_grupos.R"));  grupo_map },
                        "ferro_aco" = { source(file.path(dir_config, "ferro_aco_grupos.R")); grupo_map },
                        "cimento"   = { source(file.path(dir_config, "cimento_grupos.R"));   grupo_map },
                        NULL
)

# Função principal
# df_plot      : dataframe com coluna de produto e coluna de valor
# col_produto  : nome da coluna de produto (string)
# col_valor    : nome da coluna de valor numérico (string)
# col_peso     : nome da coluna de peso para média ponderada (string ou NULL)
# cols_resumo  : colunas que definem subgrupos no resumo além de grupo
#                ex: c("exporter", "cenario_tarifa") para o plot 2 do 07
#                    c("exporter", "ano") para o heatmap do 08
#                    c("exporter") para o 06
preparar_plot_grupos <- function(df_plot,
                                 col_produto  = "product",
                                 col_valor    = "delta_share_pct",
                                 col_peso     = NULL,
                                 cols_resumo  = c("exporter")) {
  
  # Juntar com grupo_map
  if (!is.null(.grupo_map_df)) {
    df_plot <- df_plot %>%
      left_join(.grupo_map_df %>% select(product, grupo, grupo_label),
                by = setNames("product", col_produto)) %>%
      mutate(
        grupo       = if_else(is.na(grupo), 99L, as.integer(grupo)),
        grupo_label = if_else(is.na(grupo_label), "Outros", grupo_label)
      )
  } else {
    df_plot <- df_plot %>%
      mutate(grupo = 1L, grupo_label = "Todos")
  }
  
  # Criar linhas de resumo por grupo
  if (!is.null(col_peso) && col_peso %in% names(df_plot)) {
    
    cols_group_by <- c(cols_resumo, "grupo", "grupo_label")
    
    df_resumo <- df_plot %>%
      group_by(across(all_of(cols_group_by))) %>%
      summarise(
        !!col_valor := weighted.mean(.data[[col_valor]], .data[[col_peso]],
                                     na.rm = TRUE),
        !!col_peso  := sum(.data[[col_peso]], na.rm = TRUE),
        .groups = "drop"
      ) %>%
      mutate(
        !!col_produto := paste0("[", grupo_label, "]"),
        grupo_product  = paste0(grupo, "__0_resumo"),
        is_resumo      = TRUE
      )
    
    df_plot <- df_plot %>%
      mutate(is_resumo = FALSE) %>%
      bind_rows(df_resumo)
    
  } else {
    df_plot <- df_plot %>% mutate(is_resumo = FALSE)
  }
  
  # Definir ordem do eixo Y:
  # grupo → resumo do grupo primeiro → produtos ordenados por valor
  df_plot <- df_plot %>%
    arrange(grupo, !is_resumo, .data[[col_valor]])
  
  ordem_y <- df_plot %>%
    distinct(.data[[col_produto]]) %>%
    pull(.data[[col_produto]])
  
  df_plot %>%
    mutate(!!col_produto := factor(.data[[col_produto]],
                                   levels = unique(ordem_y)))
}
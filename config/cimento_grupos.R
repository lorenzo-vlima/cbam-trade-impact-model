# config/cimento_grupos.R
# ----------------------------------------
# Mapeamento de produtos → grupos para
# o setor de cimento (capítulo 25 HS).
# ----------------------------------------
# O cimento tem menos subdivisões que
# alumínio e aço — o agrupamento reflete
# o grau de processamento e tipo de produto.
# ----------------------------------------
# ATENÇÃO: confirme os códigos presentes
# na sua base antes de rodar.
# ----------------------------------------

grupo_map <- tribble(
  ~product,   ~grupo,  ~grupo_label,
  
  # Grupo 1 — Clínquer
  # Produto intermediário, antes da moagem.
  # Maior intensidade de carbono por tonelada.
  "252310",   1,       "Clínquer",
  
  # Grupo 2 — Cimentos Portland e similares
  # Produto final mais comum — branco e cinza.
  "252321",   2,       "Cimento Portland e similares",
  "252329",   2,       "Cimento Portland e similares",
  
  # Grupo 3 — Cimentos especiais e aluminosos
  # Maior valor agregado e especificidade técnica.
  "252330",   3,       "Cimentos especiais",
  "252390",   3,       "Cimentos especiais",
  
  # Grupo 4 — Argila
  "250700",   4,       "Argila"
)

# IMPORTANTE: o cimento tem poucos códigos CN
# no CBAM. Se sua base usar uma agregação
# diferente (ex: só 2523 sem subdivisões),
# ajuste aqui conforme necessário.

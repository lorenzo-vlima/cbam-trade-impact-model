# config/ferro_aco_grupos.R
# ----------------------------------------
# Mapeamento de produtos → grupos para
# o setor de ferro e aço (capítulo 72-73 HS).
# ----------------------------------------
# ATENÇÃO: revise os códigos CN conforme
# o Anexo I do Regulamento (UE) 2023/956
# e os dados disponíveis na sua base.
# ----------------------------------------

grupo_map <- tribble(
  ~product,   ~grupo,  ~grupo_label,
  
  # Grupo 1 — Produtos primários
  # Ferro-gusa, ferro-esponja, minério e insumos básicos
  "260112",   1,       "Produtos primários",
  "7201",     1,       "Produtos primários",
  "7202",     1,       "Produtos primários",
  "7203",     1,       "Produtos primários",
  "7205",     1,       "Produtos primários",
  
  # Grupo 2 — Semiacabados e planos
  # Tarugos, blocos, chapas laminadas
  "7206",     2,       "Semiacabados e planos",
  "7207",     2,       "Semiacabados e planos",
  "7208",     2,       "Semiacabados e planos",
  "7209",     2,       "Semiacabados e planos",
  "7210",     2,       "Semiacabados e planos",
  "7211",     2,       "Semiacabados e planos",
  "7212",     2,       "Semiacabados e planos",
  "7218",     2,       "Semiacabados e planos",
  "7219",     2,       "Semiacabados e planos",
  "7220",     2,       "Semiacabados e planos",
  "7221",     2,       "Semiacabados e planos",
  "7225",     2,       "Semiacabados e planos",
  "7226",     2,       "Semiacabados e planos",
  
  # Grupo 3 — Longos e tubulares
  # Barras, perfis, fio-máquina, tubos e downstream
  "7213",     3,       "Longos e tubulares",
  "7214",     3,       "Longos e tubulares",
  "7215",     3,       "Longos e tubulares",
  "7216",     3,       "Longos e tubulares",
  "7217",     3,       "Longos e tubulares",
  "7222",     3,       "Longos e tubulares",
  "7223",     3,       "Longos e tubulares",
  "7224",     3,       "Longos e tubulares",
  "7227",     3,       "Longos e tubulares",
  "7228",     3,       "Longos e tubulares",
  "7229",     3,       "Longos e tubulares",
  "7301",     3,       "Longos e tubulares",
  "7302",     3,       "Longos e tubulares",
  "730300",   3,       "Longos e tubulares",
  "7304",     3,       "Longos e tubulares",
  "7305",     3,       "Longos e tubulares",
  "7306",     3,       "Longos e tubulares",
  "7307",     3,       "Longos e tubulares",
  "7308",     3,       "Longos e tubulares",
  "730900",   3,       "Longos e tubulares",
  "7310",     3,       "Longos e tubulares",
  "731100",   3,       "Longos e tubulares",
  "7318",     3,       "Longos e tubulares",
  "7326",     3,       "Longos e tubulares"
)

# IMPORTANTE: esta lista é uma referência inicial
# baseada no Anexo I do CBAM. Confirme quais
# códigos estão efetivamente presentes na sua
# base antes de rodar.

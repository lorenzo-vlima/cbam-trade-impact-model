# config/ferro_aco_grupos.R
# ----------------------------------------
# Mapping of products → groups for
# the iron and steel sector (HS chapters 72-73).
# ----------------------------------------
# NOTE: review the CN codes according to
# Annex I of Regulation (EU) 2023/956
# and the data available in your dataset.
# ----------------------------------------

grupo_map <- tribble(
  ~product,   ~grupo,  ~grupo_label,
  
  # Group 1 — Primary products
  # Pig iron, sponge iron, ore and basic inputs
  "260112",   1,       "Primary products",
  "7201",     1,       "Primary products",
  "7202",     1,       "Primary products",
  "7203",     1,       "Primary products",
  "7205",     1,       "Primary products",
  
  # Group 2 — Semi-finished and flat
  # Billets, blooms, rolled plates
  "7206",     2,       "Semi-finished and flat",
  "7207",     2,       "Semi-finished and flat",
  "7208",     2,       "Semi-finished and flat",
  "7209",     2,       "Semi-finished and flat",
  "7210",     2,       "Semi-finished and flat",
  "7211",     2,       "Semi-finished and flat",
  "7212",     2,       "Semi-finished and flat",
  "7218",     2,       "Semi-finished and flat",
  "7219",     2,       "Semi-finished and flat",
  "7220",     2,       "Semi-finished and flat",
  "7221",     2,       "Semi-finished and flat",
  "7225",     2,       "Semi-finished and flat",
  "7226",     2,       "Semi-finished and flat",
  
  # Group 3 — Long and tubular
  # Bars, profiles, wire rod, tubes and downstream
  "7213",     3,       "Long and tubular",
  "7214",     3,       "Long and tubular",
  "7215",     3,       "Long and tubular",
  "7216",     3,       "Long and tubular",
  "7217",     3,       "Long and tubular",
  "7222",     3,       "Long and tubular",
  "7223",     3,       "Long and tubular",
  "7224",     3,       "Long and tubular",
  "7227",     3,       "Long and tubular",
  "7228",     3,       "Long and tubular",
  "7229",     3,       "Long and tubular",
  "7301",     3,       "Long and tubular",
  "7302",     3,       "Long and tubular",
  "730300",   3,       "Long and tubular",
  "7304",     3,       "Long and tubular",
  "7305",     3,       "Long and tubular",
  "7306",     3,       "Long and tubular",
  "7307",     3,       "Long and tubular",
  "7308",     3,       "Long and tubular",
  "730900",   3,       "Long and tubular",
  "7310",     3,       "Long and tubular",
  "731100",   3,       "Long and tubular",
  "7318",     3,       "Long and tubular",
  "7326",     3,       "Long and tubular"
)

# IMPORTANT: this list is an initial reference
# based on CBAM Annex I. Confirm which
# codes are actually present in your
# dataset before running.

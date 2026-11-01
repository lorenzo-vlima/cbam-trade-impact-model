# config/aluminio_grupos.R
# ----------------------------------------
# Mapeamento de produtos → grupos para
# o setor de alumínio (capítulo 76 HS).
# Edite aqui se quiser reorganizar os grupos.
# ----------------------------------------

grupo_map <- tribble(
  ~product,   ~grupo,  ~grupo_label,
  "7601",     1,       "Primário e semi-acabado",
  "7603",     1,       "Primário e semi-acabado",
  "7604",     1,       "Primário e semi-acabado",
  "7605",     2,       "Laminados e tubulares",
  "7606",     2,       "Laminados e tubulares",
  "7607",     2,       "Laminados e tubulares",
  "7608",     2,       "Laminados e tubulares",
  "760900",   2,       "Laminados e tubulares",
  "7610",     3,       "Manufaturados e acabados",
  "761100",   3,       "Manufaturados e acabados",
  "7612",     3,       "Manufaturados e acabados",
  "761300",   3,       "Manufaturados e acabados",
  "7614",     3,       "Manufaturados e acabados",
  "7616",     3,       "Manufaturados e acabados"
)

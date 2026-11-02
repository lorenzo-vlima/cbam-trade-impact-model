# config/aluminio_grupos.R
# ----------------------------------------
# Mapping of products → groups for
# the aluminium sector (HS chapter 76).
# Edit here to reorganise the groups.
# ----------------------------------------

grupo_map <- tribble(
  ~product,   ~grupo,  ~grupo_label,
  "7601",     1,       "Primary and semi-finished",
  "7603",     1,       "Primary and semi-finished",
  "7604",     1,       "Primary and semi-finished",
  "7605",     2,       "Rolled and tubular",
  "7606",     2,       "Rolled and tubular",
  "7607",     2,       "Rolled and tubular",
  "7608",     2,       "Rolled and tubular",
  "760900",   2,       "Rolled and tubular",
  "7610",     3,       "Manufactured and finished",
  "761100",   3,       "Manufactured and finished",
  "7612",     3,       "Manufactured and finished",
  "761300",   3,       "Manufactured and finished",
  "7614",     3,       "Manufactured and finished",
  "7616",     3,       "Manufactured and finished"
)

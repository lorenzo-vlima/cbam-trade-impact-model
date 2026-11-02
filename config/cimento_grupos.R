# config/cimento_grupos.R
# ----------------------------------------
# Mapping of products → groups for
# the cement sector (HS chapter 25).
# ----------------------------------------
# Cement has fewer subdivisions than
# aluminium and steel; the grouping reflects
# the processing stage and product type.
# ----------------------------------------
# NOTE: confirm the codes present
# in your dataset before running.
# ----------------------------------------

grupo_map <- tribble(
  ~product,   ~grupo,  ~grupo_label,
  
  # Group 1 — Clinker
  # Intermediate product, before grinding.
  # Highest carbon intensity per tonne.
  "252310",   1,       "Clinker",
  
  # Group 2 — Portland and similar cements
  # Most common final product, white and grey.
  "252321",   2,       "Portland and similar cements",
  "252329",   2,       "Portland and similar cements",
  
  # Group 3 — Special and aluminous cements
  # Higher value added and technical specificity.
  "252330",   3,       "Special cements",
  "252390",   3,       "Special cements",
  
  # Group 4 — Clay
  "250700",   4,       "Clay"
)

# IMPORTANT: cement has few CN codes
# in CBAM. If your dataset uses a different
# aggregation (e.g. only 2523 without subdivisions),
# adjust here as needed.

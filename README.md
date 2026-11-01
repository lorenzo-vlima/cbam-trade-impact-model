# MODELO OFICIAL — TCC CBAM

Pasta **autocontida** com o modelo oficial da tese e seus resultados.
É o único modelo que vale — os resultados da tese saem daqui.

## O que é
Modelo gravitacional **PPML de market share** (com shrinkage de sinal, v2)
para o impacto do CBAM sobre exportações de Brasil e Argentina à UE, em
ferro & aço, alumínio e cimento. Estima elasticidades-preço (β) por país e
simula 6 cenários (3 preços de carbono × MFN/Mercosul).

## Estrutura
```
MODELO_OFICIAL/
├── main_v2.R          ← modelo oficial (caminhos já ajustados p/ esta pasta)
├── rodar_modelo.R     ← editar PRODUTO/PAISES/NOME no topo e rodar
├── scripts/           ← pipeline 00–09 + 04b
├── config/            ← dados brutos + fatores de emissão + *_grupos.R
├── helpers/           ← funcoes_modelo_v2.R (shrinkage) etc.
└── outputs/           ← resultados por rodada (subpasta por config)
```

## Como rodar
Working directory = esta pasta. Editar as 3 linhas no topo de `rodar_modelo.R`
(PRODUTO, PAISES, NOME) e:
```
"C:/Program Files/R/R-4.5.3/bin/Rscript.exe" rodar_modelo.R
```
R usado: 4.5.3. Output vai para `outputs/<produto>_<nome>_individual_post_tax_j3_v2/`.

## ⚠️ Correção do share setorial (feita 2026-08-11)
O share setorial de um país agora é calculado CORRETAMENTE, agregando em
**nível de volume**: `Σ(volume do país nos produtos) / Σ(volume total UE no
setor)` — NÃO somando shares de produtos diferentes (erro antigo que dava
share_base >100%).
- Colunas no `13_cbam_resumo_pais.csv`: `share_base_total`, `share_sim_total`,
  `delta_share_pp_total`, `variacao_relativa_pct`.
- IMPORTANTE: as VARIAÇÕES percentuais (variacao_relativa_pct, delta_ton_pct,
  delta_euro_pct) já estavam corretas mesmo antes — são razões, o share_base
  se cancelava. O bug só afetava o NÍVEL de share reportado.
- Correção aplicada em `scripts/07_simulacao_cbam.R` e `scripts/09_analise.R`.

## Resultado de referência (ferro & aço, BR, 75€/tCO₂, MFN)
- Share setorial base: **2,29%** do mercado UE (volume)
- Δ market share: −1,47% | Δ volume: −1,47% | Δ valor: −4,06%

## Setores da simulação
Ferro & aço (BR+AR) e alumínio (BR). Cimento e alumínio-AR excluídos
(R²_price baixíssimo — mecanismo de preço ausente).


## Figuras da tese (Python)
- `figuras/` — os 38 scripts .py que geram as figuras finais (caminhos já
  ajustados para esta pasta: leem de `outputs/` e `config/`, salvam em
  `figuras_geradas/`).
- `figuras_geradas/` — PNGs e CSVs finais (47 imagens + 22 tabelas).

Rodar uma figura (working dir = esta pasta):
```
python figuras/_graf_sim_FA_resumo_v3.py
```

Principais: `G_sim_FA_resumo_v3.png` (impacto ferro&aço), `G_sim_AL_resumo_v2.png`
(alumínio), `G1_elasticidades_combinado_v2.png` (elasticidades β), bubbles por
produto, `G_r2_mesclado.png` (nível vs variação), validação antidumping 2016.

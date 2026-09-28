#import "../packages.typ": *
#import "../components.typ": *
#import "../template.typ": *


#title_slide("Problema")

== Cenário

A estimação da #stress[idade] com base dos *dentes* é comum nas áreas de investigação *forense*, de identificação de pessoas, e de planejamento para tratamento odontológico#footnote[
  #cite(<lee:2026:machine_learning_adult_age_estimation>, form: "full")
].

As mudanças #stress[características] de idade são mais perceptíveis em crianças e jovens do que em *adultos*, o que dificulta a exatidão da estimativa aferida por técnicos humanos.

#pagebreak()

== Técnicas

Em adultos, #stress[características] de interesse incluem:
- quantidade de dentes presentes e de implantes;
- nível de *desgaste* e restaurações;
- condições gerais de saúde.

Métodos #stress[estatísticos] convencionais requerem trabalho de aferência do *técnico* odontológico, e levam a distorções.

#pagebreak()

== Objetivo

Empregar métodos de #stress[mineração de dados] para predizer a *idade* de humanos, com foco em *adultos*.

Utilizar #stress[entradas] de *dados* que requeiram *menor intervenção* física e interpretação por profissionais odontológicos.

Realizar as manipulações de formas não invasivas, e que permitam *preservar* os dentes.

#title_slide("Base de dados")

== Coleta

O #glossarium.gls("inredd", link: false) da #glossarium.gls("usp", link: false) Campus Ribeirão Preto montou a base de dados #stress[InReDD-Dataset-PAN924]#footnote[
  #cite(<costa:2024:dental_digital_dataset_ai>, form: "full")
].

Ela é composta por #strong[924 imagens] de radiografias panorâmicas da população local.

#pagebreak()

== Características

As entradas são compostas por: imagem, sexo, idade, #stress[segmentações].

- As segmentações foram realizadas #strong[manualmente] por especialistas:
  - #strong[Numeração] dos dentes conforme padrão internacional (FDI).
  - Identificação de #stress[características] de interesse acerca de cada dente presente e da boca por inteiro.

- Cada segmentação contém a caixa de delimitação na imagem e uma #stress[categoria] associada.

#pagebreak()

#grid(
  row-gutter: leading / 2,
  strong("Condição da boca"),
  pad(
    left: leading,
    table(
      columns: 4,
      column-gutter: (0pt, small_leading, 0pt),
      [Ed], [Sem dentes], [De], [Dentes presentes],
      [Me], [Maxilar sem dentes], [Mne], [mandíbula sem dentes],
    ),
  ),
)

#grid(
  row-gutter: leading / 2,
  strong("Condição de um dente"),
  pad(
    left: leading,
    table(
      columns: 4,
      column-gutter: (0pt, 12pt, 0pt),
      [H], [Saudável], [R], [Restauração],
      [Di], [Desgaste do incisivo], [C], [Cáries],
      [I], [Impactado], [Im], [Implante],
      [M3i], [3º molar impactado], [M3f], [3º molar desenvolvendo],
      [P], [Pôntico], [Dc], [Coroa destruída],
      [Te], [Tratamento endodôntico], [TeM], [Tratamento endodôntico misto],
      [Ri], [Pino intrarradicular], [RiM], [Pino intrarradicular misto],
      [Cp], [Coroa prostética], [CpuM], [Coroa prostética mista],
      [Rr], [Raiz residual],
    ),
  ),
)

#pagebreak()

== Abordagem

- #stress[Problema:] essas categorizações não estão relacionadas;
  - não é possível saber que o procedimento #strong[X] foi feito no dente #strong[N].

- #stress[Transformação] dos dados de segmentação.
  - Condição da boca se tornou um atributo categórico (4 classes).
  - #strong[Contagem] das ocorrências de cada condição dental em dado\ paciente (17 características).

- #stress[Classes-objetivo:] transformação da idade em faixas etárias.
  - 10-19, 20-29, 30-39, 40-49, 50-59, 60-69, 70+

#pagebreak()

// #grid(
//   columns: (1fr, auto),
//   rows: (1fr, auto),
//   gutter: small_leading,

//   grid.cell(
//     align: center + horizon,
//     image(
//       width: 19cm,
//       "../assets/images/segmentacoes_120-M-48.png",
//     ),
//   ),

//   align(horizon)[
//     - Idade: 48
//     - Faixa: 40-49
//     - Sexo: Masculino
//     - Boca: Dentes\ presentes (De)
//     - #text(fill: color.rgb("999900"))[Saudável (H)]: 14
//     - #text(fill: color.rgb("009999"))[Restauração (R)]: 10
//     - #text(fill: color.rgb("#009900"))[Tratamento\ endodôntico (Te)]: 3
//     - #text(fill: color.rgb("#EE6600"))[Cáries (C)]: 1
//   ],

//   align(bottom + center)[
//     Fonte: #cite_prose(<costa:2024:dental_digital_dataset_ai>).
//   ],
// )

// #pagebreak()


// #title_slide("Pré-processamento")

// == Descrição

// #grid(
//   columns: (1fr, auto),
//   gutter: small_leading,
//   [
//     - #strong[924] entradas.

//     - #stress[20] características.

//     - Não existem duplicatas, nem dados faltantes.
//   ],
//   align(
//     center + horizon,
//     image(width: 19cm, "/assets/images/histograma_de_idades.png"),
//   ),
// )

// #pagebreak()

// #align(center + horizon, image(height: 100%, "/assets/images/barras_de_faixas_etarias.png"))

// #pagebreak()

// #align(center + horizon, image(
//   height: 100%,
//   "/assets/images/barras_de_condicao_da_boca_em_relacao_as_faixas_etarias.png",
// ))

// #pagebreak()

// #align(center + horizon, image(
//   height: 100%,
//   "/assets/images/boxplot_de_dentes_saudaveis.png",
// ))

// #pagebreak()

// #align(center + horizon, image(
//   height: 100%,
//   "/assets/images/boxplot_de_raizes_residuais.png",
// ))

// #pagebreak()

// #align(center + horizon, image(
//   height: 100%,
//   "/assets/images/barras_de_raizes_residuais_em_relacao_as_faixas_etarias.png",
// ))

// #pagebreak()

// #grid(
//   columns: (1fr, auto),
//   gutter: small_leading,
//   [
//     == Correlação

//     - Não foram encontradas correlações significativas.

//     == Conclusões

//     - Priorizar métodos que lidem bem com #stress[outliers].
//     - Considerar #stress[balanceamento].
//     - Selecionadas 10 condições dentais + 1 da boca = #stress[11].
//   ],
//   align(center + horizon, image(
//     height: 100%,
//     "/assets/images/correlacao_de_spearman.png",
//   )),
// )


// #title_slide("Validação")

// #grid(
//   columns: (1fr, 2.1fr),
//   column-gutter: small_leading,
//   [
//     == Separação de dados
//     - De 924 entradas:
//       - #stress[80%] para validação (739);
//       - #stress[20%] para o teste (185);
//       - #strong[estratificado] pelas 7 faixas etárias.
//   ],
//   [
//     == Balanceamento
//     - Aferido em validação cruzada estratificada de #stress[5 folds] por #strong[5 seeds] fixas = #strong[25].
//     - Método de #stress[SMOTE], avaliado por F1 macro.
//     - Não há vantagem significativa. Ambas as opções serão testadas.

//     #align(
//       center,
//       table(
//         columns: 2,
//         align: (start, end),
//         table.header(strong[Modelo], strong[F1 macro]),
//         [Decision Tree #text(fill: red)[sem] SMOTE], [0.338 ± 0.016],
//         [Decision Tree #text(fill: blue)[com] SMOTE], [0.353 ± 0.011],
//         [Random Forest #text(fill: red)[sem] SMOTE], [0.375 ± 0.014],
//         [Random Forest #text(fill: blue)[com] SMOTE], strong[0.379 ± 0.012],
//       ),
//     )
//   ],
// )

// #pagebreak()

// == Ajuste de hiperparâmetros

// - Usado #stress[GridSearch] estratificado com #strong[5 folds] por #strong[5 seeds] fixas = #strong[25].
// - Para classificação: avaliação por F1 Macro em relação às faixas etárias.
// - Para regressão: avaliação por MAE em relação à idade.

// #align(
//   center + horizon,
//   table(
//     columns: 4,
//     align: (start, end, end, end),
//     table.header(table.cell(colspan: 4, strong[Decision Tree, F1])),
//     table.header(
//       strong[Parâmetro],
//       strong[Possibilidades],
//       strong[#text(fill: red)[sem] SMOTE],
//       strong[#text(fill: blue)[com] SMOTE],
//     ),
//     [Critério de seleção], [gini, entropy], [entropy], [entropy],
//     [Profundidade máxima], [7, 10, #sym.infinity], [#sym.infinity], [7],
//     [Min. amostras p. separação], [2, 5, 10], [10], [2],
//     [Min. amostras nas folhas], [1, 2, 5], [1], [1],
//   ),
// )

// #colbreak()

// #copy_last_heading()

// #align(
//   center + horizon,
//   table(
//     columns: 4,
//     align: (start, end, end, end),
//     table.header(table.cell(colspan: 4, strong[Random Forest, F1])),
//     table.header(
//       strong[Parâmetro],
//       strong[Possibilidades],
//       strong[#text(fill: red)[sem] SMOTE],
//       strong[#text(fill: blue)[com] SMOTE],
//     ),
//     [Critério de seleção], [gini, entropy], [entropy], [entropy],
//     [Limite de características], [sqrt, log2], [log2], [log2],
//     [Profundidade máxima], [3, 5, 7], [7], [7],
//     [Min. amostras p. separação], [2, 5, 10], [2], [2],
//     [Min. amostras nas folhas], [1, 2, 3], [1], [1],
//     [Quant. de estimadores], [100, 200, 300], [200], [300],
//   ),
// )

// #colbreak()

// #copy_last_heading()

// #align(
//   center + horizon,
//   table(
//     columns: 3,
//     align: (start, end, end),
//     table.header(table.cell(colspan: 3, strong[Gradient Boost, MAE])),
//     table.header(strong[Parâmetro], strong[Possibilidades], strong[Escolhido]),
//     [Função de perda], [absolute_error, squared_error, huber], [huber],
//     [Taxa de aprendizado], [0.01, 0.05, 0.1], [0.05],
//     [Profundidade máxima], [2, 3, 5], [2],
//     [Min. amostras nas folhas], [1, 3, 5, 10], [1],
//     [Quant. de estimadores], [100, 200, 300], [200],
//   ),
// )


// #title_slide("Teste")

// == Avaliação

// - Realizados em #stress[20%] das amostras (185) da base de dados.
// - Compilação dos resultados de #strong[5 seeds] fixas.

// #align(
//   center + horizon,
//   table(
//     columns: (1fr, auto, auto, auto),
//     align: (start, end, end, end),
//     table.header(strong[Modelo], strong[Acurácia], strong[Acc. balanceada], strong[F1 macro]),
//     [Dec. Tree #text(fill: red)[sem] Bl.], [0.4076 ± 0.0048], [0.3751 ± 0.0034], [0.3607 ± 0.0037],
//     [Dec. Tree #text(fill: blue)[com] Bl.], [0.4130 ± 0.0197], strong[0.4233 ± 0.0163], [0.3703 ± 0.0100],
//     [Rnd. For. #text(fill: red)[sem] Bl.], strong[0.4443 ± 0.0089], [0.3859 ± 0.0092], [0.3959 ± 0.0102],
//     [Rnd. For. #text(fill: blue)[com] Bl.], [0.4400 ± 0.0141], [0.4181 ± 0.0170], strong[0.4166 ± 0.0147],
//   ),
// )

// #align(
//   horizon,
//   table(
//     columns: (1fr, auto, auto, auto),
//     align: (start, end, end, end),
//     table.header(strong[Modelo], strong[MAE], strong[RMSE], strong[R²]),
//     [Gradient Boost], [7.0471 ± 0.0058], [9.3780 ± 0.0042], [0.7152 ± 0.0003],
//   ),
// )

// #pagebreak()

// #image("/assets/images/barras_de_real_vs_estimado.png")

// #grid(
//   columns: 2,
//   image("/assets/images/matriz_de_confusao_de_decision_tree_sem_smote.png"),
//   image("/assets/images/matriz_de_confusao_de_decision_tree_com_smote.png"),
// )

// #grid(
//   columns: 2,
//   image("/assets/images/matriz_de_confusao_de_random_forest_sem_smote.png"),
//   image("/assets/images/matriz_de_confusao_de_random_forest_com_smote.png"),
// )

// #grid(
//   columns: 2,
//   image("/assets/images/matriz_de_confusao_de_gradient_boost.png"),
//   image("/assets/images/scatterplot_de_gradient_boost.png"),
// )

// #align(
//   center + horizon,
//   image("/assets/images/matriz_de_confusao_de_residuos_de_gradient_boost.png"),
// )


// #pagebreak()

// == Importância das características

// #grid(
//   columns: 5,
//   image(height: 6cm, "/assets/images/pizza_de_importancia_de_caracteristicas_para_decision_tree_sem_smote.png"),
//   image(height: 6cm, "/assets/images/pizza_de_importancia_de_caracteristicas_para_decision_tree_com_smote.png"),
//   image(height: 6cm, "/assets/images/pizza_de_importancia_de_caracteristicas_para_random_forest_sem_smote.png"),
//   image(height: 6cm, "/assets/images/pizza_de_importancia_de_caracteristicas_para_random_forest_com_smote.png"),
//   image(height: 6cm, "/assets/images/pizza_de_importancia_de_caracteristicas_para_gradient_boost.png"),
// )

// #box(fill: color.rgb("8dd3c7"), inset: 4pt)[Saudável (H)],
// #box(fill: color.rgb("ffffb3"), inset: 4pt)[Restauração (R)],
// #box(fill: color.rgb("bebada"), inset: 4pt)[Trat. endod. (Te)],
// #box(fill: color.rgb("fb8072"), inset: 4pt)[Molar form. (M3f)],
// #box(fill: color.rgb("80b1d3"), inset: 4pt)[Molar impac. (M3i)],
// #box(fill: color.rgb("ccebc5"), inset: 4pt)[Cáries (C)],
// #box(fill: color.rgb("bc80bd"), inset: 4pt)[Desgaste incisivo (Di)],
// #box(fill: color.rgb("d9d9d9"), inset: 4pt)[Pôntico (P)],
// #box(fill: color.rgb("b3de69"), inset: 4pt)[Condição da boca],
// #box(fill: color.rgb("fdb462"), inset: 4pt)[Coroa prostética (Cpum)],
// #box(fill: color.rgb("fccde5"), inset: 4pt)[Implante (Im)].

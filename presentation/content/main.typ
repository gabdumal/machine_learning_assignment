#import "../packages.typ": *
#import "../components.typ": *
#import "../template.typ": *


#title_slide("Problema")

== Cenário

@Nids são sistemas destinados a #strong[identificar] atividades que possam representar violações da segurança de uma rede de computadores.

A detecção pode ser realizada por meio de assinaturas de #stress[ataques] conhecidos ou pela análise de padrões presentes no tráfego.

#glossarium.Gls("machine_learning") é utilizadao para construir #strong[modelos de detecção] a partir de características da comunicação em rede #footnote[
  #cite(<buczak:2016:ml_for_cyber_security>, form: "full")
].

#pagebreak()

== Representação

O tráfego é representado por meio de #stress[#glossarium.gls("network_flow")].

Conjunto de #stress[pacotes] que atravessam um ponto de observação durante determinado #strong[intervalo de tempo].

Podem representar características como: endereços, portas, protocolo, duração, quantidade de pacotes e volume de dados.

Sistemas de #strong[detecção baseados em fluxo] utilizam esses registros como entrada, sem analisar diretamente o conteúdo dos pacotes
#footnote[
  #cite(<umer:2017:flow_based_detection>, form: "full")
].

#pagebreak()

== Objetivo

Quando os dados possuem #stress[rótulos conhecidos], a detecção pode ser formulada como um problema de #glossarium.gls("supervised_learning", link: false) que utiliza o vetor de #strong[características] de um fluxo como preditor.

Em uma tarefa de #stress[#glossarium.gls("multiclass_classification", link: false)], o conjunto de rótulos contém múltiplas classes, e cada fluxo é associado a uma delas.

Podem representar diferentes tipos de comportamento de rede, incluindo tráfego #strong[benigno] e diferentes #strong[categorias de ataques] (DoS, Recon, #sym.dots).

#title_slide("Trabalhos relacionados")

#note_from_gabriel(note: todo_note)[Escrever]

#title_slide("Bases de dados")

== #glossarium.gls-short("genis")

#glossarium.gls("genis") é voltada a redes #strong[corporativas] no contexto de pequenas e médias empresas #footnote[
  #cite(<silva:2025:genis_network_intrusion>, form: "full")
].

- Pacotes coletados pela plataforma Airbus CyberRange no formato #glossarium.gls("pcap").
- Transformados em fluxos de rede pela ferramenta HERA (#foreign_text[Holistic nEtwork featuRes Aggregator]).
- Versões com intervalos de 5 (n = 2.806.168), 10, 30 e 60 (n = 368.556) segundos.

#colbreak()

#copy_last_heading()

Apresenta três níveis de #stress[rotulação]:
- #strong[Binária:] benigno e malicioso.
- #strong[Multiclasse:] Benign, Bruteforce, DoS, Recon.
- #strong[Detalhamento] da forma de acesso (admin ou usuário, protocolo de ataque, método de negação de serviço, etc.).

#pagebreak()

== #glossarium.gls-short("rosids")

A base #glossarium.gls("rosids") é voltada a  sistemas robóticos baseados em #glossarium.gls("ros") #footnote[
  #cite(<degirmenci:2023:rosids23_network_intrusion>, form: "full")
].

#grid(
  columns: (1fr, 1fr),
  gutter: leading,
  [
    A rede inclui os componentens:
    - um #stress[ROS Master],
    - um dispositivo controlador,
    - um braço robótico,
    - um registrador do tráfego,
    - e um dispositivo #stress[atacante]
  ],
  [
    O ROS Master coordena o registro dos componentes e a comunicação entre os nós do sistema.
  ],
)

#colbreak()

#copy_last_heading()

#stress[Ataques] exploram mecanismos gerais da rede e características específicas do middleware #strong[#glossarium.gls("ros")].
- Ataques de #strong[publicação] (Unauth Pub) e de #strong[subscrição não autorizadas] (Unauth Sub) exploram a possibilidade de um nó não autorizado publicar ou acessar dados.
- #strong[#foreign_text[Subscriber flood]] (Subflood) utiliza múltiplas identidades de nós para fazer requisições sucessivas ao ROS Master, aumentando o tráfego maliciosamente.
- Ataques de #strong[negação de serviço] (DoS) tradicionais.

== #get_term("westermo")

A base #get_term("westermo") simula o contexto de uma rede de comunicação #strong[industrial].
Coleta realizada em uma rede física com doze dispositivos
#footnote[
  #cite(<strandberg:2023:westermo_network_traffic>, form: "full")
].

Foram removidos os pacotes que eram ruído dos componentes de execução do experimento.
Então, foram transformados em fluxos de rede.

Pacotes coletados individualmente em três pontos da rede.
Cada um gerou sua base de registros.
Modela capacidade de um modelo relacionar a diferença de acessos entre pontos.

#colbreak()

#copy_last_heading()
#grid(
  columns: 2,
  gutter: leading,
  [
    Experimento executou seis tipos de #stress[eventos]:
    - conexões SSH corretas,
    - conexões SSH sem sucesso,
    - dispositivos recebem IP inválido,
    - dispositivos recebem o mesmo IP,
    - escaneamento de portas, e
    - #foreign_text[man-in-the-middle].
  ],
  [
    Duas rotulações independentes:
    + todos os pacotes que ocorrem #strong[durante um evento] recebem o rótulo do evento;
    + todos os pacotes com origem ou destino no #strong[atacante] durante um evento recebem o rótulo do evento.
  ],
)

#pagebreak()

#align(
  center + horizon,
  table(
    columns: (auto, auto, auto, 1fr, 1fr, 1fr),
    align: (start, end, end, end, end, end, end),

    table.header(strong[Base], strong[Instâncias], strong[Atributos], strong[Classes], strong[Distribuição], strong[%]),

    table.cell(rowspan: 4)[
      #glossarium.gls("genis")
    ],
    table.cell(rowspan: 4)[
      368.556
    ],
    table.cell(rowspan: 4)[
      122
    ],
    table.cell(rowspan: 1)[
      benign
    ],
    table.cell(rowspan: 1)[
      27150
    ],
    table.cell(rowspan: 1)[
      7,37%
    ],

    table.cell(rowspan: 1)[
      bruteforce
    ],
    table.cell(rowspan: 1)[
      18033
    ],
    table.cell(rowspan: 1)[
      4,89%
    ],

    table.cell(rowspan: 1)[
      dos
    ],
    table.cell(rowspan: 1)[
      295640
    ],
    table.cell(rowspan: 1)[
      80,22%
    ],

    table.cell(rowspan: 1)[
      recon
    ],
    table.cell(rowspan: 1)[
      27733
    ],
    table.cell(rowspan: 1)[
      7,52%
    ],

    table.hline(stroke: 2pt),

    table.cell(rowspan: 5)[
      #glossarium.gls("rosids")
    ],
    table.cell(rowspan: 5)[
      136.681
    ],
    table.cell(rowspan: 5)[
      83
    ],
    table.cell(rowspan: 1)[
      Benign
    ],
    table.cell(rowspan: 1)[
      62511
    ],
    table.cell(rowspan: 1)[
      45,73%
    ],

    table.cell(rowspan: 1)[
      DoS
    ],
    table.cell(rowspan: 1)[
      31000
    ],
    table.cell(rowspan: 1)[
      22,68%
    ],
    table.cell(rowspan: 1)[
      Subflood
    ],
    table.cell(rowspan: 1)[
      30064
    ],
    table.cell(rowspan: 1)[
      22,00%
    ],
    table.cell(rowspan: 1)[
      UnauthPub
    ],
    table.cell(rowspan: 1)[
      7817
    ],
    table.cell(rowspan: 1)[
      5,72%
    ],
    table.cell(rowspan: 1)[
      UnauthSub
    ],
    table.cell(rowspan: 1)[
      5289
    ],
    table.cell(rowspan: 1)[
      3,87%
    ],
  ),
)

#colbreak()

#align(
  center + horizon,
  table(
    columns: (auto, auto, auto, 1fr, 1fr, 1fr),
    align: (start, end, end, end, end, end, end),

    table.header(strong[Base], strong[Instâncias], strong[Atributos], strong[Classes], strong[Distribuição], strong[%]),

    table.cell(rowspan: 7)[
      #get_term("westermo")
    ],
    table.cell(rowspan: 7)[
      48.657
    ],
    table.cell(rowspan: 7)[
      54
    ],
    table.cell(rowspan: 1)[
      Normal
    ],
    table.cell(rowspan: 1)[
      36727
    ],
    table.cell(rowspan: 1)[
      75,48%
    ],

    table.cell(rowspan: 1)[
      Portscan 1
    ],
    table.cell(rowspan: 1)[
      267
    ],
    table.cell(rowspan: 1)[
      0,55%
    ],
    table.cell(rowspan: 1)[
      Portscan 2
    ],
    table.cell(rowspan: 1)[
      2179
    ],
    table.cell(rowspan: 1)[
      4,48%
    ],
    table.cell(rowspan: 1)[
      Bad SSH
    ],
    table.cell(rowspan: 1)[
      2968
    ],
    table.cell(rowspan: 1)[
      6,10%
    ],
    table.cell(rowspan: 1)[
      Bad IP
    ],
    table.cell(rowspan: 1)[
      2677
    ],
    table.cell(rowspan: 1)[
      5,50%
    ],
    table.cell(rowspan: 1)[
      Same IP
    ],
    table.cell(rowspan: 1)[
      3131
    ],
    table.cell(rowspan: 1)[
      6,43%
    ],
    table.cell(rowspan: 1)[
      MITM
    ],
    table.cell(rowspan: 1)[
      708
    ],
    table.cell(rowspan: 1)[
      1,46%
    ],
  ),
)


#title_slide("Descrição das bases")

== #glossarium.gls-short("genis")

Os autores já forneceram os dados processados e separados entre treino e teste de forma estratificada em proporção 75% a 25%.

Não foram identificados valores ausentes nem duplicatas.

#table(
  columns: (1fr, 1fr, 1fr, 1fr),
  align: (start + horizon, end + horizon, end + horizon, end + horizon),

  table.header(strong[Partição], strong[Classe], strong[Instâncias], strong[Proporção]),

  table.cell(rowspan: 5)[Treino],
  table.cell()[#get_term("dos")],
  table.cell()[236 512],
  table.cell()[80,21%],
  table.cell()[#get_term("recon")],
  table.cell()[22 186],
  table.cell()[7,52%],
  table.cell()[#get_term("benign")],
  table.cell()[21 720],
  table.cell()[7,37%],
  table.cell()[#get_term("bruteforce")],
  table.cell()[14 426],
  table.cell()[4,90%],
  table.cell()[*Total*],
  table.cell()[294 844],
  table.cell()[100%],
)

#table(
  columns: (1fr, 1fr, 1fr, 1fr),
  align: (start + horizon, end + horizon, end + horizon, end + horizon),

  table.header(strong[Partição], strong[Classe], strong[Instâncias], strong[Proporção]),

  table.cell(rowspan: 5)[Teste],
  table.cell()[#get_term("dos")],
  table.cell()[59 128],
  table.cell()[80,21%],
  table.cell()[#get_term("recon")],
  table.cell()[5 547],
  table.cell()[7,53%],
  table.cell()[#get_term("benign")],
  table.cell()[5 430],
  table.cell()[7,37%],
  table.cell()[#get_term("bruteforce")],
  table.cell()[3 607],
  table.cell()[4,89%],
  table.cell()[*Total*],
  table.cell()[73 712],
  table.cell()[100%],

  table.hline(stroke: 2pt),

  table.cell(rowspan: 5)[Agrupado],
  table.cell()[#get_term("dos")],
  table.cell()[295 640],
  table.cell()[80,22%],
  table.cell()[#get_term("recon")],
  table.cell()[27 733],
  table.cell()[7,52%],
  table.cell()[#get_term("benign")],
  table.cell()[27 150],
  table.cell()[7,37%],
  table.cell()[#get_term("bruteforce")],
  table.cell()[18 033],
  table.cell()[4,89%],
  table.cell()[*Total*],
  table.cell()[368 556],
  table.cell()[100%],
)

#pagebreak()

Características #stress[numéricas] incluem: contagem de pacotes em fluxos de origem e destino, tamanho dos pacotes (em bytes), duração dos fluxos, atrasos, e similares.

As portas de rede utilizadas pela origem e pelo destino são valores #stress[textuais], por não terem relação de ordenação entre si.

O protocolo utilizado no fluxo, que é uma característica #stress[categórica] já foi fornecida na forma de #foreign_text[one-hot encoding].

#foreign_text[Flags] de comunicação e o estado da transação são características #stress[binárias].

#pagebreak()

Muitas características numéricas apresentam, ao mesmo tempo:
- grande quantidade de entradas com valores iguais ou próximos a #strong[0],
- menor quantidade de entradas com valores #strong[muito elevados].

Isso faz com que um tratamento ingênuo de #stress[outliers] por intervalo interquartil (IQR) não seja possível.

Para identificação do tipo de tráfego, é relevante se o valor é muito pequeno ou muito grande, mas não necessariamente a distância entre esses limites.

Esse fenômeno motiva a selecionar métodos de #glossarium.gls("machine_learning") que lidem melhor com outliers e discrepâncias, como aqueles baseados em #stress[árvores].

#colbreak()

#align(
  center + horizon,
  image("/assets/images/source_application_bytes_boxplot.png"),
)

#align(
  center + horizon,
  image("/assets/images/source_application_bytes_histogram.png"),
)

== #glossarium.gls-short("rosids")

Os dados foram separados em treino e teste de forma estratificada na proporção de 80% a 20% no protocolo experimental.

#table(
  columns: (1fr, 1fr, 1fr, 1fr),
  align: (start + horizon, end + horizon, end + horizon, end + horizon),

  table.header(strong[Partição], strong[Classe], strong[Instâncias], strong[Proporção]),

  table.cell(rowspan: 6)[Treino],
  table.cell()[Benign],
  table.cell()[50 008],
  table.cell()[45,73%],
  table.cell()[DoS],
  table.cell()[24 800],
  table.cell()[22,68%],
  table.cell()[Subflood],
  table.cell()[24 051],
  table.cell()[22,00%],
  table.cell()[UnauthPub],
  table.cell()[6 254],
  table.cell()[5,72%],
  table.cell()[UnauthSub],
  table.cell()[4 231],
  table.cell()[3,87%],
  table.cell()[*Total*],
  table.cell()[109 344],
  table.cell()[100%],
)

#table(
  columns: (1fr, 1fr, 1fr, 1fr),
  align: (start + horizon, end + horizon, end + horizon, end + horizon),

  table.header(strong[Partição], strong[Classe], strong[Instâncias], strong[Proporção]),

  table.cell(rowspan: 6)[Teste],
  table.cell()[Benign],
  table.cell()[12 503],
  table.cell()[45,74%],
  table.cell()[DoS],
  table.cell()[6 200],
  table.cell()[22,68%],
  table.cell()[Subflood],
  table.cell()[6 013],
  table.cell()[22,00%],
  table.cell()[UnauthPub],
  table.cell()[1 563],
  table.cell()[5,72%],
  table.cell()[UnauthSub],
  table.cell()[1 058],
  table.cell()[3,87%],
  table.cell()[*Total*],
  table.cell()[27 337],
  table.cell()[100%],

  table.hline(stroke: 2pt),

  table.cell(rowspan: 6)[Agrupado],
  table.cell()[Benign],
  table.cell()[62 511],
  table.cell()[45,73%],
  table.cell()[DoS],
  table.cell()[31 000],
  table.cell()[22,68%],
  table.cell()[Subflood],
  table.cell()[30 064],
  table.cell()[22,00%],
  table.cell()[UnauthPub],
  table.cell()[7 817],
  table.cell()[5,72%],
  table.cell()[UnauthSub],
  table.cell()[5 289],
  table.cell()[3,87%],
  table.cell()[*Total*],
  table.cell()[136 681],
  table.cell()[100%],
)

#colbreak()

As características #stress[numéricas] seguem o mesmo conteúdo que quelas da base #glossarium.gls("genis"), com coleta adicional dos tamanhos de cabeçalhos.

Em vez de representar o estado da conexão por características #stress[binárias], a base registra a contagem de #foreign_text[flags] ocorridas no fluxo.

// == Abordagem

// - #stress[Problema:] essas categorizações não estão relacionadas;
//   - não é possível saber que o procedimento #strong[X] foi feito no dente #strong[N].

// - #stress[Transformação] dos dados de segmentação.
//   - Condição da boca se tornou um atributo categórico (4 classes).
//   - #strong[Contagem] das ocorrências de cada condição dental em dado\ paciente (17 características).

// - #stress[Classes-objetivo:] transformação da idade em faixas etárias.
//   - 10-19, 20-29, 30-39, 40-49, 50-59, 60-69, 70+

// #pagebreak()

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

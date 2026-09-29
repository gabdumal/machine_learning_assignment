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

O tráfego é representado por meio de fluxos de rede.

Conjunto de #stress[pacotes] que atravessam um ponto de observação durante determinado #strong[intervalo de tempo].

Podem representar características como: endereços, portas, protocolo, duração, quantidade de pacotes e volume de dados.

Sistemas de #strong[detecção baseados em fluxo] utilizam esses registros como entrada, sem analisar diretamente o conteúdo dos pacotes
#footnote[
  #cite(<umer:2017:flow_based_detection>, form: "full")
].

#pagebreak()

== Objetivo

Quando os dados possuem #stress[rótulos conhecidos], a detecção pode ser formulada como um problema de #glossarium.gls("aprendizado_supervisionado", link: false) que utiliza o vetor de #strong[características] de um fluxo como preditor.

Em uma tarefa de #stress[#glossarium.gls("classificação_multiclasse", link: false)], o conjunto de rótulos contém múltiplas classes, e cada fluxo é associado a uma delas.

Podem representar diferentes tipos de comportamento de rede, incluindo tráfego #strong[benigno] e diferentes #strong[categorias de ataques] (DoS, Recon, #sym.dots).

// #title_slide("Trabalhos relacionados")

// #note_from_gabriel(note: todo_note)[Escrever]

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

    table.header(strong[Base], strong[Instâncias], strong[Atr.], strong[Classes], strong[Distribuição], strong[%]),

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

    table.header(strong[Base], strong[Instâncias], strong[Atr.], strong[Classes], strong[Distribuição], strong[%]),

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
  table.cell()[dos],
  table.cell()[236 512],
  table.cell()[80,21%],
  table.cell()[recon],
  table.cell()[22 186],
  table.cell()[7,52%],
  table.cell()[benign],
  table.cell()[21 720],
  table.cell()[7,37%],
  table.cell()[bruteforce],
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
  table.cell()[dos],
  table.cell()[59 128],
  table.cell()[80,21%],
  table.cell()[recon],
  table.cell()[5 547],
  table.cell()[7,53%],
  table.cell()[benign],
  table.cell()[5 430],
  table.cell()[7,37%],
  table.cell()[bruteforce],
  table.cell()[3 607],
  table.cell()[4,89%],
  table.cell()[*Total*],
  table.cell()[73 712],
  table.cell()[100%],

  table.hline(stroke: 2pt),

  table.cell(rowspan: 5)[Agrupado],
  table.cell()[dos],
  table.cell()[295 640],
  table.cell()[80,22%],
  table.cell()[recon],
  table.cell()[27 733],
  table.cell()[7,52%],
  table.cell()[benign],
  table.cell()[27 150],
  table.cell()[7,37%],
  table.cell()[bruteforce],
  table.cell()[18 033],
  table.cell()[4,89%],
  table.cell()[*Total*],
  table.cell()[368 556],
  table.cell()[100%],
)

#pagebreak()

Características #stress[numéricas] incluem: contagem de pacotes em fluxos de origem e destino, tamanho dos pacotes (em bytes), duração dos fluxos, atrasos, e similares.

As portas de rede utilizadas pela origem e pelo destino são valores #stress[textuais], por não terem relação de ordenação entre si.

O protocolo de rede utilizado, que é uma característica #stress[categórica], já foi fornecido na forma de #glossarium.gls("one_hot", link: false).

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
Não foram identificadas duplicatas.

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

As características #stress[numéricas] seguem o mesmo conteúdo que quelas da base #glossarium.gls("genis").

Em vez de representar o estado da conexão por características #stress[binárias], a base registra a #strong[contagem] de #foreign_text[flags] ocorridas no fluxo.

As únicas características #stress[categóricas] mantidas foram as portas de rede de origem e de destino, e o protocolo utilizado (TCP, UDP, ou não se aplica).

- #foreign_text[Flow Bytes per Second]: 272 valores ausentes, e 3 valores infinito por erro de cálculo #sym.arrow preenchidos como NaN.
- #foreign_text[Initial Backward Window Bytes]: `-1` como indicador de valor ausente em 1.263 registros #sym.arrow preenchidos como NaN.

#align(
  center + horizon,
  image("/assets/images/flow_bytes_per_second_histogram.png"),
)

#pagebreak()

#title_slide("Pré-processamento")

== Seleção de características

- Removidas colunas de #stress[metadados], ou que possam identificar diretamente a variável-alvo;
  - `destination_tcp_base`, `source_tcp_base`, e `source_tos` (#glossarium.gls("genis", link: false)).

- Removidas colunas com nenhum ou muito poucos valores #stress[distintos];
  - estados de conexão incomuns;
  - #foreign_text[flags] de comunicação pouco usuais;
  - `protocol_ipv6_icmp` foi integrada a `protocol_icmp` (#glossarium.gls("genis", link: false)).

#pagebreak()

== Transformação de características

- #stress[Portas de rede]
  - Muitas são associadas a protocolos específicos.
  - São categorizadas em faixas de uso esperado
    - `well_known` (1 a 1023),
    - `registered` (1024 a 49151),
    - `dynamic` (49152 a 65535), e
    - `not_applicable` (protocolo não usa porta).
  - Valores textuais transformados em categóricos,
    - de acordo com o protocolo associado,
    - ou a faixa.

#pagebreak()

#title_slide("Protocolo experimental")

== Validação cruzada

- #foreign_text[Cross validation] com #stress[3 #get_term("fold", plural: true)]
  - realizado somente na partição de #strong[treinamento],
  - #strong[estratificados] pelas classes-alvo,
  - embaralhamento com #get_term("seed") fixa,

- #stress[3 execuções] diferentes para cada #get_term("fold")
  - #get_term("seed", plural: true): 27, 32, e 59.

- Em cada execução é #stress[separada]:
  - fração de validação,
  - e fração de treinamento.

#colbreak()

== #get_term("pipeline", capitalize: true)

Transformações aplicadas apenas sobre a fração de #stress[treinamento].
- Valores #stress[numéricos] faltantes são preenchidos pela #strong[mediana].
- Valores #stress[categóricos] passam por #strong[#glossarium.gls("one_hot", link: false)].

== Balanceamento

- Faz parte da validação cruzada.
- Uma base balanceada pode selecionar hiperparâmetros diferentes.
- Amostragem aleatória (#stress[#foreign_text[oversampling]]) dentro do #get_term("fold").
- Fração de validação nunca é balanceada.

#pagebreak()

== Métricas

#grid(
  columns: 2,
  gutter: 2 * leading,
  [
    - #strong[Calculadas:]
      - #get_term("accuracy"),
      - #get_term("precision"),
      - #get_term("recall"),
      - #get_term("mcc"),
      - #get_term("balanced_accuracy"),
      - #get_term("roc_auc"), e
      - #get_term("pr_auc").

    #stress[Principal:] #get_term("macro_f1").

  ],
  [
    Para cada #stress[#get_term("seed")]:

    Calcula-se média e desvio-padrão\
    dos valores dos #get_term("fold", plural: true).

    Busca a melhor combinação de balanceamento + hiperparâmetros por #foreign_text[Grid Search].

    Então, faz-se o #strong[treinamento] final,\
    agora sobre toda a partição de treino.

    Finalmente, realiza-se o #strong[teste].
  ],
)

#title_slide("Modelos de referência")

== Árvore de decisão

- Lida bem com #get_term("outlier", plural: true) e variações de escala.
- Serve como #foreign_text[baseline].

#table(
  columns: (1fr, 1fr),

  table.header(strong[Hiperparâmetro], strong[Valores avaliados]),

  [criterion], [`gini`, `entropy`],
  [max_depth], [`10`, `20`, `None`],
  [min_samples_split], [`2`, `5`, `10`],
  [min_samples_leaf], [`1`, `5`],
)

#colbreak()

#copy_last_heading()

#table(
  columns: (1fr, 1fr, 1fr),

  table.header(
    strong[Parâmetro], strong[#glossarium.gls("genis", link: false)], strong[#glossarium.gls("rosids", link: false)]
  ),

  [balanceamento], [desativado], [desativado],
  [criterion], [`gini`], [`entropy`],
  [max_depth], [`20`], [`20`],
  [min_samples_split], [`2`], [`10`],
  [min_samples_leaf], [`1`], [`1`],
)

#pagebreak()

== Floresta aleatória

- Aprimora a #glossarium.gls("decision_tree", link: false) ao combinar em um #foreign_text[ensemble].

#table(
  columns: (1fr, 1fr),

  table.header(strong[Hiperparâmetro], strong[Valores avaliados]),

  [n_estimators], [`100`, `200`],
  [max_depth], [`10`, `20`, `None`],
  [min_samples_split], [`2`, `5`, `10`],
  [min_samples_leaf], [`1`, `5`],
)

#colbreak()

#copy_last_heading()

#table(
  columns: (1fr, 1fr, 1fr),

  table.header(
    strong[Parâmetro], strong[#glossarium.gls("genis", link: false)], strong[#glossarium.gls("rosids", link: false)]
  ),

  [balanceamento], [desativado], [desativado],
  [n_estimators], [`200`], [`200`],
  [max_depth], [`None`], [`20`],
  [min_samples_split], [`2`], [`5`],
  [min_samples_leaf], [`1`], [`1`],
)

#pagebreak()

== XGBoost

- Mantém qualidades das árvores.
- Melhora a construção do #foreign_text[ensemble] ao usar #glossarium.gls("gradient_boosting", link: false).

#table(
  columns: (1fr, 1fr),

  table.header(strong[Hiperparâmetro], strong[Valores avaliados]),

  [n_estimators], [`100`, `200`],
  [max_depth], [`3`, `6`],
  [learning_rate], [`0.05`, `0.1`],
  [min_child_weight], [`1`, `5`],
  [subsample], [`0.8`, `1.0`],
)

#colbreak()

#copy_last_heading()

#table(
  columns: (1fr, 1fr, 1fr),

  table.header(
    strong[Parâmetro], strong[#glossarium.gls("genis", link: false)], strong[#glossarium.gls("rosids", link: false)]
  ),

  [balanceamento], [desativado], [desativado],
  [n_estimators], [`200`], [`200`],
  [max_depth], [`6`], [`6`],
  [learning_rate], [`0.1`], [`0.1`],
  [min_child_weight], [`1`], [`1`],
  [subsample], [`0.8`], [`0.8`],
)

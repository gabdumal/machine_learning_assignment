#import "../../components.typ": *


= Referencial teórico e trabalhos relacionados <seção:fundamentação>

#note_from_advisor(note: progress_note)[
  Esta seção deve fornecer o conhecimento necessário para compreender o problema e posicionar o estudo em relação à literatura. O levantamento bibliográfico pode ser sucinto, mas deve conter referências realmente relevantes para o tema. A descrição do trabalho prevê um estado da arte curto, com pelo menos 3--5 referências relevantes, além da apresentação de 2--3 exemplos de bases de dados e soluções típicas do domínio.
]

Esta seção apresenta os fundamentos necessários para compreender o problema de detecção de intrusões abordado neste relatório e situa o estudo em relação a trabalhos relacionados.
Inicialmente, são apresentados os principais conceitos do problema, incluindo a caracterização dos fluxos de rede, a formulação da tarefa como um problema de classificação supervisionada multiclasse e as características das representações utilizadas no estudo.

Em seguida, são descritas as bases de dados empregadas, destacando seus contextos de aquisição, classes, características e diferenças na composição dos dados.
Por fim, são discutidos os métodos relacionados ao trabalho, abrangendo os classificadores tradicionais utilizados nos experimentos, a combinação de modelos por meio de comitês e a aplicação de modelos de linguagem de grande porte à classificação de dados tabulares.
Essa discussão estabelece o contexto para a metodologia apresentada posteriormente e fundamenta a comparação entre as diferentes abordagens consideradas no relatório.


== Conceitos e definição do problema

#note_from_advisor(note: done_note)[
  Defina os conceitos específicos do domínio e formalize a tarefa quando necessário. Explique o significado dos rótulos, variável-alvo, horizonte de previsão, grupos ou demais elementos do problema. Não repita conceitos gerais de aprendizado de máquina que não sejam necessários para compreender o estudo.
]

@Nids são sistemas destinados a identificar atividades que possam representar violações da segurança de uma rede.
A detecção pode ser realizada por meio de assinaturas de ataques conhecidos ou pela análise de padrões presentes no tráfego.
Nesse contexto, técnicas de #glossarium.gls("machine_learning") são utilizadas para construir modelos a partir de características extraídas da comunicação em rede @buczak:2016:ml_for_cyber_security.

Uma forma de representar o tráfego para esse tipo de análise é por meio de #glossarium.gls("network_flow").
Um fluxo é definido como um conjunto de pacotes que atravessam um ponto de observação durante determinado intervalo e compartilham propriedades de comunicação.
Os registros de fluxo podem representar características como endereços, portas, protocolo, duração, quantidade de pacotes e volume de dados.
Sistemas de detecção baseados em fluxo utilizam esses registros como entrada, sem analisar diretamente o conteúdo dos pacotes @umer:2017:flow_based_detection.

Quando os dados possuem rótulos conhecidos, a detecção pode ser formulada como um problema de #glossarium.gls("supervised_learning") que utiliza o vetor de características de um fluxo com o preditor.
Em uma tarefa de #glossarium.gls("multiclass_classification"), o conjunto de rótulos contém múltiplas classes, e cada fluxo é associado a uma delas.

Na detecção de intrusões, essas classes podem representar diferentes tipos de comportamento de rede, incluindo tráfego benigno e diferentes categorias de ataques (DoS, Recon, #sym.dots).
A variável-alvo, portanto, corresponde à categoria atribuída a cada fluxo, enquanto as demais características utilizadas pelo modelo descrevem o comportamento observado na comunicação.

A classificação de intrusões em nível de fluxo pode ser organizada em diferentes etapas.
Uma abordagem pode primeiro distinguir tráfego benigno de tráfego malicioso e, posteriormente, determinar a categoria do comportamento identificado.
Também é possível formular diretamente o problema como uma classificação multiclasse, atribuindo cada fluxo a uma das categorias definidas para o conjunto de dados.
A escolha entre essas formulações depende da definição das classes e da estratégia de detecção adotada.


== Bases de dados e benchmarks do domínio

#note_from_advisor(note: done_note)[
  Apresente brevemente 2--3 bases de dados conhecidas ou representativas do problema, mesmo que nem todas sejam usadas nos experimentos. Para cada uma, destaque finalidade, tipo de dado, dimensão aproximada, classes/alvo e particularidades relevantes. Cite a fonte original da base sempre que possível.
]

#note_from_advisor(note: done_note)[
  Descreva bases de dados ou benchmarks relevantes para o tema.
]

As bases de dados utilizadas em pesquisas de detecção de intrusões diferem quanto ao ambiente representado, à forma de coleta, às características extraídas e às classes consideradas.
Esta seção apresenta três bases representativas de diferentes contextos: o #glossarium.gls("genis"), voltado a redes corporativas, o #glossarium.gls("rosids"), voltado a sistemas baseados em #glossarium.gls("ros"), e o conjunto de dados de #get_term("westermo"), voltado a redes de comunicação industrial.
A @tabela:bases_domínio resume suas principais características.

#describe_figure(
  sticky: true,
  [#figure(
    caption: "Bases de dados exploradas",
    format_table(table(
      columns: (2cm, 1.6cm, 1.3cm, 2.5cm, 3.5cm, auto),
      align: (start + horizon, end + horizon, end + horizon, end + horizon, end + horizon, start + horizon),

      [Base], [Instâncias], [Atributos], [Classes], [Distribuição], [Observações],

      table.cell(rowspan: 4)[
        #glossarium.gls("genis")
      ],
      table.cell(rowspan: 4)[
        368.556 fluxos
      ],
      table.cell(rowspan: 4)[
        122
      ],
      table.cell(rowspan: 1)[
        benign
      ],
      table.cell(rowspan: 1)[
        27150 (7,37%)
      ],
      table.cell(rowspan: 4)[
        Rede corporativa.
        Cenários sequenciais de ataque.
        Fluxos de 5, 10, 30 e 60 s.
        Considera-se o de 60 s.
      ],

      table.cell(rowspan: 1)[
        bruteforce
      ],
      table.cell(rowspan: 1)[
        18033 (4,89%)
      ],

      table.cell(rowspan: 1)[
        dos
      ],
      table.cell(rowspan: 1)[
        295640 (80,22%)
      ],

      table.cell(rowspan: 1)[
        recon
      ],
      table.cell(rowspan: 1)[
        27733 (7,52%)
      ],

      table.hline(stroke: .5pt),

      table.cell(rowspan: 5)[
        #glossarium.gls("rosids")
      ],
      table.cell(rowspan: 5)[
        136.681 fluxos
      ],
      table.cell(rowspan: 5)[
        83
      ],
      table.cell(rowspan: 1)[
        Benign
      ],
      table.cell(rowspan: 1)[
        62511 (45,73%)
      ],
      table.cell(rowspan: 5)[
        Rede baseada em ROS.
        Inclui ROS Master, controlador e braço robótico.
      ],

      table.cell(rowspan: 1)[
        DoS
      ],
      table.cell(rowspan: 1)[
        31000 (22,68%)
      ],
      table.cell(rowspan: 1)[
        Subflood
      ],
      table.cell(rowspan: 1)[
        30064 (22,00%)
      ],
      table.cell(rowspan: 1)[
        UnauthPub
      ],
      table.cell(rowspan: 1)[
        7817 (5,72%)
      ],
      table.cell(rowspan: 1)[
        UnauthSub
      ],
      table.cell(rowspan: 1)[
        5289 (3,87%)
      ],

      table.hline(stroke: .5pt),

      table.cell(rowspan: 7)[
        #get_term("westermo")
      ],
      table.cell(rowspan: 7)[
        48.657 fluxos
      ],
      table.cell(rowspan: 7)[
        54
      ],
      table.cell(rowspan: 1)[
        Normal
      ],
      table.cell(rowspan: 1)[
        36727 (75,48%)
      ],
      table.cell(rowspan: 7)[
        Rede de comunicação industrial.
        Duas estratégias de rotulação.
      ],

      table.cell(rowspan: 1)[
        Portscan 1
      ],
      table.cell(rowspan: 1)[
        267 (0,55%)
      ],
      table.cell(rowspan: 1)[
        Portscan 2
      ],
      table.cell(rowspan: 1)[
        2179 (4,48%)
      ],
      table.cell(rowspan: 1)[
        Bad SSH
      ],
      table.cell(rowspan: 1)[
        2968 (6,10%)
      ],
      table.cell(rowspan: 1)[
        Bad IP
      ],
      table.cell(rowspan: 1)[
        2677 (5,50%)
      ],
      table.cell(rowspan: 1)[
        Same IP
      ],
      table.cell(rowspan: 1)[
        3131 (6,43%)
      ],
      table.cell(rowspan: 1)[
        MITM
      ],
      table.cell(rowspan: 1)[
        708 (1,46%)
      ],
    )),
  ) <tabela:bases_domínio>],
)

=== #glossarium.gls("genis")

O #glossarium.gls("genis") foi desenvolvido para representar o tráfego de uma rede corporativa no contexto de pequenas e médias empresas.
Os dados foram coletados pela plataforma Airbus CyberRange, por onde se executou atividades benignas de usuários e administradores, além de cenários sequenciais de ataque @silva:2025:genis_network_intrusion.

Os pacotes foram registrados em arquivos #glossarium.gls("pcap") e processados pela ferramenta HERA (#foreign_text[Holistic nEtwork featuRes Aggregator]) para gerar fluxos e extrair características.
O conjunto foi disponibilizado em versões com intervalos de fluxo de 5, 10, 30 e 60 segundos, totalizando 2.806.168 fluxos na versão de 5 segundos e 368.556 na versão de 60 segundos.

A base possui três níveis de rotulação.
O primeiro simplesmente distingue tráfego benigno e malicioso.
O segundo organiza os fluxos em quatro categorias: benigno, força bruta, negação de serviço e reconhecimento.
O terceiro detalha essas categorias em tipos específicos de atividades benignas (se desempenhadas por usuário comum ou administrador) ou de ataques (protocolo utilizado, ou método de negação de serviço).

Além dos arquivos de fluxos, os autores disponibilizaram as capturas de pacotes em seus formatos originais, os cenários de ataque, e versões pré-processadas em formato #glossarium.gls("csv").
No escopo deste relatório, utilizamos os dados processados para fluxos de 60 segundos, e consideramos o nível médio de granularidade, que contém 4 classes.


=== #glossarium.gls("rosids")

O #glossarium.gls("rosids") foi desenvolvido para investigar a segurança de sistemas robóticos baseados em #glossarium.gls("ros").
Sua coleta foi realizada no IFARLab-DIH, laboratório da Universidade de Eskişehir Osmangazi dedicado à pesquisa em sistemas robóticos e industriais.

Os componentes utilizados no experimento são: um ROS Master, um dispositivo controlador, um dispositivo associado ao braço robótico, um dispositivo responsável pelo registro do tráfego, e um dispositivo atacante.
O ROS Master coordena o registro dos componentes e a comunicação entre os nós do sistema.
O dispositivo atacante foi conectado à mesma infraestrutura de rede para produzir o tráfego associado aos cenários de intrusão @degirmenci:2023:rosids23_network_intrusion.

Os ataques considerados exploram mecanismos gerais da rede e características específicas do middleware #glossarium.gls("ros").
Por exemplo, os ataques de publicação e de subscrição não autorizadas exploram a possibilidade de um nó não autorizado publicar ou acessar dados.
Por sua vez, o ataque de #foreign_text[subscriber flood] utiliza múltiplas identidades de nós para fazer requisições sucessivas ao ROS Master, aumentando o tráfego maliciosamente.

Durante a coleta, o tráfego normal foi registrado a partir da operação do sistema robótico, e os diferentes cenários de ataque foram executados separadamente.
Os pacotes foram capturados com a ferramenta `tcpdump` e armazenados em arquivos #glossarium.gls("pcap").
Então, foi utilizado o programa CICFlowMeter para extrair as características dos fluxos e gerar os dados tabulares em formato #glossarium.gls("csv").


=== #get_term("westermo")

O conjunto de dados de #get_term("westermo") foi desenvolvido para simular o contexto de uma rede de comunicação industrial.
A coleta foi realizada em uma rede física com doze dispositivos, incluindo roteadores industriais e equipamentos que executavam o simulador de fábrica ICSSIM @strandberg:2023:westermo_network_traffic.

Os pacotes foram registrados no formato #glossarium.gls("pcap") com a ferramenta `tcpdump`, e transformados em fluxos de rede com a ferramenta ICSFlowGenerator.
Nem todos os pacotes capturados eram representativos do contexto, mas resultavam dos componentes necessários para executar o experimento.
Dessa forma, os pesquisadores montaram duas versões dos dados: a reduzida corresponde apenas ao contexto simulado, com 48.657 fluxos; enquanto a estendida inclui todos os pacotes, com 68.729.

Os pacotes foram coletados individualmente por três pontos de rede posicionados de forma diversa na topologia.
Assim, foi gerado um arquivo #glossarium.gls("csv") de fluxos de rede para cada ponto, que descreve 50 características.
Isso permite realizar análises acerca da capacidade de um ponto conseguir detectar uma intrusão sozinho, e de implementar métodos de detecção federados.

O experimento executou seis tipos de eventos: conexões SSH corretas, conexões SSH sem sucesso, dispositivos recebem IP inválido, dispositivos recebem o mesmo IP, escaneamento de portas, e #foreign_text[man-in-the-middle].

Acerca do rotulamento, os autores executaram dois métodos concomitantemente.
No primeiro, todo tráfego ocorrido durante um evento anômalo é assim rotulado.
Já no segundo, apenas o tráfego enviado pelo ou para o atacante é rotulado como anômalo.
Além disso, é salvo qual evento estava sendo executado no momento do rotulamento, o que resulta em quatro características.


== Métodos e trabalhos relacionados

#note_from_advisor(note: done_note)[
  Discuta trabalhos anteriores que resolvem problemas semelhantes. Dê preferência a estudos recentes e/ou referências clássicas fundamentais. Compare métodos, dados, protocolos e resultados quando houver informação suficiente. O objetivo não é apenas listar artigos, mas mostrar quais abordagens são típicas, quais limitações permanecem e como o seu experimento se relaciona com a literatura.
]

#note_from_advisor(note: done_note)[
  Apresente e compare os principais trabalhos relacionados.
]

Soluções para detecção e classificação de intrusões em fluxos de rede utilizam diferentes estratégias de modelagem.
Elencam-se primariamente métodos clássicos de classificação, que podem ser combinados em comitês.
Além disso, estudos mais recentes usam métodos de #glossarium.gls("llm") para analisar dados de tráfego estruturados.

#cite_prose(<umer:2018:two_stage_flow_based_intrusion_detection>) propuseram uma arquitetura de duas etapas para detecção baseada em fluxos.
Os autores utilizam o método de #glossarium.gls("svm") na variação de #foreign_text[one-class] para separar fluxos maliciosos do tráfego normal sem utilizar exemplos rotulados.
Então, um #glossarium.gls("som") agrupa os fluxos maliciosos em diferentes categorias de ataque.
O estudo observou que o desempenho do SVM é sensível ao controle de outliers, e que o agrupamento requer conhecimento sobre os ataques presentes nos dados.

#cite_prose(<rodriguez:2022:ml_for_flow_based_intrusion>) testam diferentes classificadores na base de dados CICIDS2017.
Foram comparados métodos de #glossarium.gls("random_forest"), Naive Bayes, KNN, entre outros.
Os resultados mostram desempenho superior dos métodos baseados em árvores nos experimentos de classificação binária.
Ainda assim, erros foram mais frequentes na classificação multiclasse, indicando dificuldade para distinguir tipos específicos de intrusão.

#cite_prose(<mehavilla:2026:llm_flow_intrusion_detection>) realizaram uma comparação entre #glossarium.gls("llm", plural: true), métodos clássicos --- #glossarium.gls("decision_tree"), #glossarium.gls("random_forest") e XGBoost --- e modelos de aprendizado profundo.
Os experimentos incluíram classificação binária e multiclasse, além de análise de tempo de inferência e de consumo de recursos.
Os #glossarium.gls("llm", plural: true) avaliados apresentaram F1 superior a 0,95, mas não superaram os métodos clássicos de #glossarium.gls("machine_learning"), que requerem menor custo computacional.

Métodos baseados em árvores se mostram efetivos e eficientes na tarefa de classificação de fluxos de rede, cujos dados frequentemente apresentam outliers.
Trabalhos recentes investigam o uso de #glossarium.gls("llm"), avaliando seu custo computacional.
O presente relatório busca avaliar ambos os métodos em protocolo comum de classificação de intrusões multiclasse.

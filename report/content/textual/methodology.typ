#import "../../components.typ": *


= Metodologia <seção:métodos>

#note_from_advisor(note: progress_note)[
  Esta seção deve permitir que outra pessoa reproduza o experimento. Descreva dados, preparação, modelos, comitês, abordagem com GPT/LLM quando aplicável, protocolo de avaliação, métricas, software e decisões de implementação. O trabalho exige dois datasets experimentais; datasets adicionais são opcionais. Para classificação, devem ser avaliados pelo menos três modelos clássicos adequados, além dos comitês e da comparação com GPT. Para regressão, séries temporais ou agrupamento, adapte os métodos e a etapa com GPT conforme o problema e, quando necessário, conforme orientação do professor.
]


== Bases de dados utilizadas

#note_from_advisor(note: progress_note)[
  Descreva os dois datasets usados nos experimentos. Informe origem, licença quando disponível, número de instâncias, número e tipo de atributos, classes ou variável-alvo, distribuição das classes, valores ausentes e outras características relevantes. Se houver grupos naturais (pacientes, indivíduos, animais, residências, gravações etc.), deixe isso explícito porque pode alterar o protocolo de validação.
]

Foram utilizados dois conjuntos de dados nos experimentos: #glossarium.gls("genis") e #glossarium.gls("rosids").
Em ambos os casos, foram consideradas apenas as características com papel de previsão e a variável-alvo.
Assim, foram eliminadas características de metadados, que poderiam identificar a classe-alvo.


=== #glossarium.gls("genis")

Os autores da base de dados @silva:2025:genis_network_intrusion disponibilizaram os fluxos de rede já processados e divididos em partições de treino e teste de forma estratificada em proporção de 75% e 25%.
Esses dados se encontram nos arquivos `genis-60-sec-train.csv` e `genis-60-sec-test.csv`, que correspondem à versão com fluxos agregados em intervalos de 60 segundos.

Extraímos das colunas dos arquivos 68 características preditoras e uma variável-alvo, além de demais atributos de metadados, que foram desconsiderados no experimento.
A variável-alvo, chamada de #foreign_text[Category Label], é identificada pelo rótulo `category_label` e é do tipo categórico.
A distribuição de instâncias rotuladas com cada classe é exibida na @tabela:genis_distribuição.
Por sua vez, as características preditoras, com seus nomes, rótulos e tipos de dado, são listadas na @tabela:genis_características.

#describe_figure(
  sticky: true,
  [#figure(
    caption: [Distribuição de instâncias da base de dados #glossarium.gls-short("genis")],
    format_table(table(
      columns: (1fr, 1fr, 1fr, 1fr),

      [Partição], [Classe], [Instâncias], [Proporção],

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

      table.hline(stroke: 0.5pt),

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

      table.hline(stroke: 0.5pt),

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
    )),
  ) <tabela:genis_distribuição>],
)


#describe_figure(
  [#figure(
    caption: [Características selecionadas da base de dados #glossarium.gls("genis")],
    format_table(
      table(
        columns: (2.2fr, 2.5fr, 1fr),
        align: (start + top, start + top, start + top),

        table.header([Nome], [Rótulo], [Tipo de dado]),

        [Destination Port Category], [destination_port_category], [Categórico],
        [SYN-ACK Time], [syn_ack_time], [Numérico],
        [Maximum Duration], [maximum_duration], [Numérico],
        [Source Hops], [source_hops], [Numérico],
        [TCP Round-Trip Time], [tcp_rtt], [Numérico],
        [Minimum Destination Inter-Packet Time], [destination_interpacket_time_minimum], [Numérico],
        [Mean Duration], [mean_duration], [Numérico],
        [Destination Packets], [amount_of_destination_packets], [Numérico],
        [Source TTL], [source_ttl], [Numérico],
        [Source Port Category], [source_port_category], [Categórico],
        [Total Bytes], [total_bytes], [Numérico],
        [Active Destination Inter-Packet Time], [destination_interpacket_time_active], [Numérico],
        [Destination Loss], [amount_of_destination_package_loss], [Numérico],
        [Source TCP Window], [source_window_in_bytes], [Numérico],
        [Source Application Bytes], [source_application_bytes], [Numérico],
        [Packet Rate], [packet_rate], [Numérico],
        [Destination Bytes], [destination_bytes], [Numérico],
        [Source Packets], [amount_of_source_packets], [Numérico],
        [Minimum Duration], [minimum_duration], [Numérico],
        [Destination Packet Rate], [destination_packet_rate], [Numérico],
        [ACK-to-Data Time], [acknowledgement_data_time], [Numérico],
        [Maximum Source Packet Size], [source_maximum_packet_size], [Numérico],
        [Maximum Source Inter-Packet Time], [source_interpacket_time_maximum], [Numérico],
        [Packet Loss], [amount_of_package_loss], [Numérico],
        [Destination Inter-Packet Time], [destination_interpacket_time], [Numérico],
        [Source Load], [source_load], [Numérico],
        [Source Packet Rate], [source_packet_rate], [Numérico],
        [Maximum Destination Inter-Packet Time], [destination_interpacket_time_maximum], [Numérico],
        [Source Bytes], [source_bytes], [Numérico],
        [Total Application Bytes], [total_application_bytes], [Numérico],
        [Minimum Source Packet Size], [source_minimum_packet_size], [Numérico],
        [Total Duration], [total_duration], [Numérico],
        [Minimum Source Inter-Packet Time], [source_interpacket_time_minimum], [Numérico],
        [Mean Destination Packet Size], [destination_mean_packet_size], [Numérico],
        [Total Packets], [total_packets], [Numérico],
        [Source Inter-Packet Time], [source_interpacket_time], [Numérico],
        [Destination Application Bytes], [destination_application_bytes], [Numérico],
        [Active Source Inter-Packet Time], [source_interpacket_time_active], [Numérico],
        [Producer-Consumer Ratio], [producer_consumer_ratio], [Numérico],
        [Destination TCP Window], [destination_window_in_bytes], [Numérico],
        [Minimum Destination Packet Size], [destination_minimum_packet_size], [Numérico],
        [Source Active Jitter], [source_active_jitter], [Numérico],
        [Maximum Destination Packet Size], [destination_maximum_packet_size], [Numérico],
        [Mean Source Packet Size], [source_mean_packet_size], [Numérico],
        [Destination Jitter], [destination_jitter], [Numérico],
        [Packet Loss Percentage], [packet_loss_percentage], [Numérico],
        [Source Jitter], [source_jitter], [Numérico],
        [Record Duration], [duration], [Numérico],
        [Load], [load], [Numérico],
        [Active Flow Runtime], [run_time], [Numérico],
        [Destination Active Jitter], [destination_active_jitter], [Numérico],
        [Idle Source Inter-Packet Time], [source_interpacket_time_idle], [Numérico],
        [Source Loss], [amount_of_source_packets_loss], [Numérico],
        [Destination Load], [destination_load], [Numérico],
        [Protocol: ARP], [protocol_arp], [Binário],
        [Protocol: ICMP], [protocol_icmp], [Binário],
        [Protocol: TCP], [protocol_tcp], [Binário],
        [Protocol: UDP], [protocol_udp], [Binário],
        [Flow Flag: E], [flags_e], [Binário],
        [Flow Flag: E\*], [flags_e_star], [Binário],
        [Flow Flag: E-S], [flags_e_s], [Binário],
        [Transaction State: CON], [state_con], [Binário],
        [Transaction State: ECO], [state_eco], [Binário],
        [Transaction State: FIN], [state_fin], [Binário],
        [Transaction State: INT], [state_int], [Binário],
        [Transaction State: REQ], [state_req], [Binário],
        [Transaction State: RST], [state_rst], [Binário],
      ),
    ),
  ) <tabela:genis_características>],
)

A divisão entre treino e teste foi mantida conforme fornecida pelo conjunto de dados, sem redistribuição das instâncias.
Não foram identificados valores ausentes nem linhas duplicadas nas duas partições.

Muitas características apresentam um comportamento de concentração de valores próximos a zero para uma grande parte das instâncias, mas de limites máximos expressivamente altos.
Isso faz com que o cuidado com outliers seja fundamental, o que motiva a escolha de métodos de classificação baseados em árvores.
Um exemplo é a característica #foreign_text[Source Application Bytes], cuja distribuição de valores se verifica nas @figura:boxplot_source_application_bytes e @figura:histograma_source_application_bytes.

#describe_figure(
  sticky: true,
  [
    #figure(
      caption: [
        Boxplot da característica Source Application Bytes
      ],
      image(
        "/assets/images/source_application_bytes_boxplot.png",
      ),
    )<figura:boxplot_source_application_bytes>
  ],
)

#describe_figure(
  sticky: true,
  [
    #figure(
      caption: [
        Histograma por classes-alvo da característica Source Application Bytes
      ],
      image(
        "/assets/images/source_application_bytes_histogram.png",
      ),
    )<figura:histograma_source_application_bytes>
  ],
)


== Preparação e pré-processamento

#note_from_advisor[
  Explique limpeza, tratamento de dados ausentes, codificação, normalização, seleção de características e balanceamento, quando aplicável. Toda transformação que aprende informação dos dados deve ser ajustada apenas no conjunto de treinamento de cada partição/fold. Oversampling, undersampling e SMOTE, por exemplo, devem ser aplicados somente ao treino. Evite qualquer vazamento de informação do conjunto de avaliação.
]

#note_from_advisor(note: todo_note)[
  Descreva o pipeline de preparação e pré-processamento dos dados.
]

== Modelos de referência

#note_from_advisor[
  Apresente os modelos clássicos usados como baselines. Para classificação, escolha pelo menos três métodos adequados ao problema, por exemplo: regressão logística, árvore de decisão, floresta aleatória, SVM, Naive Bayes, XGBoost/LightGBM ou outro classificador justificado. Para regressão ou agrupamento, utilize algoritmos correspondentes. Informe hiperparâmetros principais e como eles foram definidos ou ajustados.
]

#note_from_advisor(note: todo_note)[
  Descreva os modelos de referência e suas configurações.
]

== Comitês de modelos

#note_from_advisor[
  Avalie estratégias de combinação de modelos, incluindo ao menos votação e ponderação quando aplicáveis. Descreva quais modelos participam, como suas saídas são combinadas e como os pesos são definidos. Pesos e demais decisões do comitê devem ser obtidos somente com dados de treinamento/validação, nunca a partir do conjunto de teste. Se explorar especialistas, combinação hierárquica ou outra estratégia, descreva-a com clareza.
]

#note_from_advisor(note: todo_note)[
  Descreva os comitês avaliados: hard voting, soft voting, votação ponderada ou outras estratégias.
]

== GPT e outras abordagens baseadas em LLMs

#note_from_advisor[
  Para trabalhos de classificação, compare os baselines com pelo menos uma abordagem zero-shot e uma abordagem few-shot usando GPT. Os exemplos few-shot devem vir apenas do treino/validação. Documente o prompt, os rótulos possíveis, a versão/modelo utilizado, parâmetros relevantes e a regra usada para mapear respostas textuais para rótulos válidos. Use exatamente os mesmos subconjuntos de avaliação empregados pelos modelos clássicos. O uso de embeddings com classificador raso é opcional. Para regressão, séries temporais ou agrupamento, adapte esta subseção ao problema conforme orientação do professor.
]

#note_from_advisor(note: todo_note)[
  Descreva o modelo, os prompts zero-shot/few-shot, o procedimento de inferência e o mapeamento das respostas.
]

== Método adicional ou variação proposta (opcional)

#note_from_advisor[
  Caso tenha sido implementado um algoritmo simples, uma variação de método existente ou algum procedimento com comportamento aleatório, descreva-o aqui. Destaque claramente o que foi modificado em relação ao método de referência e qual hipótese essa modificação pretende testar.
]

#note_from_advisor(note: todo_note)[
  Remova esta subseção se nenhum método adicional tiver sido proposto.
]

== Protocolo experimental

#note_from_advisor[
  Descreva como treino, validação e teste foram separados. Para classificação, utilize validação cruzada estratificada quando apropriado. Quando houver grupos naturais, mantenha todas as amostras do mesmo grupo na mesma partição. Para séries temporais, preserve a ordem temporal e use validação compatível com previsão. Pré-processamento, seleção de características, balanceamento e ajuste de hiperparâmetros devem ocorrer dentro do pipeline de treinamento. Informe sementes e número de repetições quando houver aleatoriedade relevante. Se usar repeated k-fold, deixe claro como as predições out-of-fold são agregadas e como os resultados entre repetições são resumidos.
]

#note_from_advisor(note: todo_note)[
  Descreva detalhadamente o protocolo de validação e comparação.
]

== Métricas de avaliação

#note_from_advisor[
  Escolha métricas adequadas à tarefa e ao custo dos erros. Para classificação, a descrição do trabalho requer no mínimo acurácia, precisão, revocação, F-scores, AUC-ROC e matriz de confusão, podendo incluir AUC-PR, MCC, balanced accuracy ou outras métricas relevantes. Para regressão, use ao menos MAE e MSE, além de $R^2$ quando apropriado. Para agrupamento, inclua Silhouette e outras medidas justificadas. Use exatamente as mesmas métricas para comparar modelos clássicos e GPT quando a comparação for aplicável.
]

#note_from_advisor(note: todo_note)[
  Defina as métricas usadas e justifique sua escolha.
]

== Implementação e reprodutibilidade

#note_from_advisor[
  Informe linguagem, bibliotecas principais, versões, hardware relevante, sementes e demais informações necessárias para reprodução. Se utilizar API, registre a versão/modelo, data ou identificador relevante, parâmetros de geração e custo estimado. Considere disponibilizar código e instruções de execução quando possível.
]

#describe_figure(
  figure(
    caption: "Informações de implementação e reprodutibilidade",
    format_table(
      table(
        columns: (auto, 1fr),

        [
          Item
        ],
        [
          Informação
        ],

        [
          Linguagem
        ],
        [
          Python 3.x / R / outra
        ],

        [
          Bibliotecas
        ],
        [
          scikit-learn, imbalanced-learn, XGBoost, etc.
        ],

        [
          Semente(s)
        ],
        [
          valor(es)
        ],

        [
          Hardware
        ],
        [
          CPU/GPU e memória, quando relevante
        ],

        [
          Modelo GPT/LLM
        ],
        [
          nome e versão, quando aplicável
        ],

        [
          Código
        ],
        [
          link ou informação de disponibilidade, se houver
        ],
      ),
    ),
  ),
)

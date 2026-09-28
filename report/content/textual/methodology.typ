#import "../../components.typ": *


= Metodologia <seção:métodos>

#note_from_advisor(note: progress_note)[
  Esta seção deve permitir que outra pessoa reproduza o experimento. Descreva dados, preparação, modelos, comitês, abordagem com GPT/LLM quando aplicável, protocolo de avaliação, métricas, software e decisões de implementação. O trabalho exige dois datasets experimentais; datasets adicionais são opcionais. Para classificação, devem ser avaliados pelo menos três modelos clássicos adequados, além dos comitês e da comparação com GPT. Para regressão, séries temporais ou agrupamento, adapte os métodos e a etapa com GPT conforme o problema e, quando necessário, conforme orientação do professor.
]


== Bases de dados utilizadas

#note_from_advisor(note: done_note)[
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
  [#figure(
    caption: [Distribuição de instâncias da base de dados #glossarium.gls-short("genis")],
    format_table(table(
      columns: (1fr, 1fr, 1fr, 1fr),

      table.header([Partição], [Classe], [Instâncias], [Proporção]),

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


=== #glossarium.gls("rosids")

Os autores da base de dados @degirmenci:2023:rosids23_network_intrusion disponibilizaram os dados no arquivo `ROSIDS23.csv`.
A partir desse arquivo, realizamos a preparação dos dados e a divisão estratificada em partições de treino e teste na proporção de 80% e 20%, respectivamente.

A variável-alvo, chamada de #foreign_text[Label], é identificada pelo rótulo `label` e é do tipo categórico.
A distribuição de instâncias rotuladas com cada classe é exibida na @tabela:rosids_distribuição.
Por sua vez, as 66 características preditoras, com seus nomes, rótulos e tipos de dado, são listadas na @tabela:rosids_características.

#describe_figure(
  [
    #figure(caption: [Distribuição de instâncias da base de dados #glossarium.gls-short("rosids")], format_table(table(
      columns: (1fr, 1fr, 1fr, 1fr),

      table.header([Partição], [Classe], [Instâncias], [Proporção]),

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

      table.hline(stroke: 0.5pt),

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

      table.hline(stroke: 0.5pt),

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
    ))) <tabela:rosids_distribuição>],
)

#describe_figure(
  [
    #figure(caption: [Características selecionadas da base de dados #glossarium.gls("rosids")], format_table(table(
      columns: (2.2fr, 2.5fr, 1fr),
      align: (start + top, start + top, start + top),

      table.header([Nome], [Rótulo], [Tipo de dado]),

      [Source Port Category], [source_port_category], [Categórico],
      [Destination Port Category], [destination_port_category], [Categórico],
      [Protocol], [protocol], [Categórico],
      [Flow Duration], [flow_duration], [Numérico],
      [Total Forward Packets], [total_forward_packets], [Numérico],
      [Total Backward Packets], [total_backward_packets], [Numérico],
      [Total Forward Packet Length], [total_forward_packet_length], [Numérico],
      [Total Backward Packet Length], [total_backward_packet_length], [Numérico],
      [Maximum Forward Packet Length], [forward_packet_length_maximum], [Numérico],
      [Minimum Forward Packet Length], [forward_packet_length_minimum], [Numérico],
      [Mean Forward Packet Length], [forward_packet_length_mean], [Numérico],
      [Forward Packet Length Standard Deviation], [forward_packet_length_standard_deviation], [Numérico],
      [Maximum Backward Packet Length], [backward_packet_length_maximum], [Numérico],
      [Minimum Backward Packet Length], [backward_packet_length_minimum], [Numérico],
      [Mean Backward Packet Length], [backward_packet_length_mean], [Numérico],
      [Backward Packet Length Standard Deviation], [backward_packet_length_standard_deviation], [Numérico],
      [Flow Bytes per Second], [flow_bytes_per_second], [Numérico],
      [Flow Packets per Second], [flow_packets_per_second], [Numérico],
      [Mean Flow Inter-Arrival Time], [flow_inter_arrival_time_mean], [Numérico],
      [Flow Inter-Arrival Time Standard Deviation], [flow_inter_arrival_time_standard_deviation], [Numérico],
      [Maximum Flow Inter-Arrival Time], [flow_inter_arrival_time_maximum], [Numérico],
      [Minimum Flow Inter-Arrival Time], [flow_inter_arrival_time_minimum], [Numérico],
      [Total Forward Inter-Arrival Time], [forward_inter_arrival_time_total], [Numérico],
      [Mean Forward Inter-Arrival Time], [forward_inter_arrival_time_mean], [Numérico],
      [Forward Inter-Arrival Time Standard Deviation], [forward_inter_arrival_time_standard_deviation], [Numérico],
      [Maximum Forward Inter-Arrival Time], [forward_inter_arrival_time_maximum], [Numérico],
      [Minimum Forward Inter-Arrival Time], [forward_inter_arrival_time_minimum], [Numérico],
      [Total Backward Inter-Arrival Time], [backward_inter_arrival_time_total], [Numérico],
      [Mean Backward Inter-Arrival Time], [backward_inter_arrival_time_mean], [Numérico],
      [Backward Inter-Arrival Time Standard Deviation], [backward_inter_arrival_time_standard_deviation], [Numérico],
      [Maximum Backward Inter-Arrival Time], [backward_inter_arrival_time_maximum], [Numérico],
      [Minimum Backward Inter-Arrival Time], [backward_inter_arrival_time_minimum], [Numérico],
      [Backward PSH Flag Count], [backward_push_flag_count], [Numérico],
      [Forward Header Length], [forward_header_length], [Numérico],
      [Backward Header Length], [backward_header_length], [Numérico],
      [Forward Packets per Second], [forward_packets_per_second], [Numérico],
      [Backward Packets per Second], [backward_packets_per_second], [Numérico],
      [Minimum Packet Length], [packet_length_minimum], [Numérico],
      [Maximum Packet Length], [packet_length_maximum], [Numérico],
      [Mean Packet Length], [packet_length_mean], [Numérico],
      [Packet Length Standard Deviation], [packet_length_standard_deviation], [Numérico],
      [Packet Length Variance], [packet_length_variance], [Numérico],
      [FIN Flag Count], [fin_flag_count], [Numérico],
      [SYN Flag Count], [syn_flag_count], [Numérico],
      [RST Flag Count], [rst_flag_count], [Numérico],
      [PSH Flag Count], [psh_flag_count], [Numérico],
      [ACK Flag Count], [ack_flag_count], [Numérico],
      [Downstream-to-Upstream Ratio], [down_up_ratio], [Numérico],
      [Average Packet Size], [packet_size_average], [Numérico],
      [Average Forward Segment Size], [forward_segment_size_average], [Numérico],
      [Average Backward Segment Size], [backward_segment_size_average], [Numérico],
      [Subflow Forward Packets], [subflow_forward_packets], [Numérico],
      [Subflow Forward Bytes], [subflow_forward_bytes], [Numérico],
      [Subflow Backward Packets], [subflow_backward_packets], [Numérico],
      [Subflow Backward Bytes], [subflow_backward_bytes], [Numérico],
      [Initial Backward Window Bytes], [initial_backward_window_bytes], [Numérico],
      [Forward Active Data Packets], [forward_active_data_packets], [Numérico],
      [Mean Active Time], [active_mean], [Numérico],
      [Active Time Standard Deviation], [active_standard_deviation], [Numérico],
      [Maximum Active Time], [active_maximum], [Numérico],
      [Minimum Active Time], [active_minimum], [Numérico],
      [Mean Idle Time], [idle_mean], [Numérico],
      [Idle Time Standard Deviation], [idle_standard_deviation], [Numérico],
      [Maximum Idle Time], [idle_maximum], [Numérico],
      [Minimum Idle Time], [idle_minimum], [Numérico],
    ))) <tabela:rosids_características>],
)

Não foram identificadas linhas duplicadas.
Na característica #foreign_text[Flow Bytes per Second], foram identificados 272 valores ausentes e 3 valores incorretamente atribuídos como infinito.
Além disso, destaca-se a característica #foreign_text[Initial Backward Window Bytes], que apresenta o valor `-1` como indicador de valor ausente em 1.263 registros.

Similarmente às características da base de dados #glossarium.gls("genis"), muitos atributos apresentam uma variação muito expressiva no valor, o que requer cuidado com outliers.
A característica #foreign_text[Flow Bytes per Second] serve como exemplo desse fenômeno, como é mostrado na @figura:histograma_flow_bytes_per_second.

#describe_figure(
  sticky: true,
  [
    #figure(
      caption: [
        Histograma por classes-alvo da característica Flow Bytes per Second
      ],
      image(
        "/assets/images/flow_bytes_per_second_histogram.png",
      ),
    )<figura:histograma_flow_bytes_per_second>
  ],
)


== Preparação e pré-processamento

#note_from_advisor(note: done_note)[
  Explique limpeza, tratamento de dados ausentes, codificação, normalização, seleção de características e balanceamento, quando aplicável. Toda transformação que aprende informação dos dados deve ser ajustada apenas no conjunto de treinamento de cada partição/fold. Oversampling, undersampling e SMOTE, por exemplo, devem ser aplicados somente ao treino. Evite qualquer vazamento de informação do conjunto de avaliação.
]

#note_from_advisor(note: done_note)[
  Descreva o pipeline de preparação e pré-processamento dos dados.
]


=== Seleção de características

Inicialmente, foram consideradas aptas apenas as características com capacidade de predição e a variável-alvo.
Todas as colunas de identificadores e metadados foram removidas.

Em seguida, cada característica foi analisada em função da quantidade de valores distintos apresentados.
Para o #glossarium.gls("genis"), as colunas a seguir apresentam o mesmo valor para todas as entradas, o que as fez serem removidas:
+ `flags_e_d`,
+ `flags_e_g`,
+ `flags_e_r`,
+ `flags_e_u`,
+ `state_clo`,
+ `state_nrs`,
+ `state_tst`,
+ `state_urh`, e
+ `state_urhpro`.
A característica `protocol_ipv6_icmp` apresentou valores positivos em uma quantidade muito pequena de entradas.
Neste caso, em vez de eliminá-la, ela foi agregada à coluna `protocol_icmp`, que apresenta diversidade adequada.

Tratamento idêntico ocorreu para o #glossarium.gls("rosids") quanto às colunas a seguir, que foram eliminadas por apresentarem o mesmo valor para todas as entradas:
+ `forward_push_flag_count`,
+ `forward_urgent_flag_count`,
+ `backward_urgent_flag_count`,
+ `urg_flag_count`,
+ `cwe_flag_count`,
+ `ece_flag_count`,
+ `forward_bytes_per_block_average`,
+ `forward_packets_per_block_average`,
+ `forward_block_rate_average`,
+ `backward_bytes_per_block_average`,
+ `backward_packets_per_block_average`,
+ `backward_block_rate_average`,
+ `initial_forward_window_bytes`, e
+ `forward_segment_size_minimum`.

Especificamente para o #glossarium.gls("genis"), algumas características apresentaram valores que refletiam muito diretamente o cenário de simulação, de forma a levar ao vazamento da classe-alvo.
Por esse motivo, foram removidas:
`destination_tcp_base`, `source_tcp_base`, e `source_tos`.


=== Transformação de características

Após a seleção, algumas características foram transformadas para melhorar o aproveitamento de seus valores.
Algumas portas de rede são alocadas para protocolos específicos, o que as torna mais visadas para ataques.
Além disso, portas são categorizadas em faixas que representam seu uso esperado, quais sejam: `well_known`, `registered` e `dynamic`, além da categoria `not_applicable` para quando um fluxo de rede não utilizar uma porta.

As portas que apresentavam padrão de acesso específico nos fluxos de rede foram: 21 (FTP), 22 (SSH), 23 (Telnet), 53 (DNS), 80 (HTTP), 137 e 138 (NETBIOS), 443 (HTTPS), 445 (SMB), 587 (SMTPS), 1900 (SSDP), 5353 (mDNS), e 11311 (ROS).

No #glossarium.gls("genis"), as características `destination_port` e `source_port` representavam o número da porta de rede em que o fluxo ocorreu.
Elas foram convertidas nas colunas `destination_port_category` e `source_port_category` com base nas portas de destaque e, caso o valor não esteja entre elas, nas faixas de uso.
A mesma transformação foi feita para o #glossarium.gls("rosids") com características homônimas.

Ainda no #glossarium.gls("rosids"), a característica `protocol` apresentava apenas os valores `0`, `6` e `17`, que representam, respectivamente, as categorias `not_applicable`, `tcp` e `udp`.
Logo, assim foi feita a transformação em dados categóricos.

Também foi identificado que características calculadas com base na razão entre outros valores numéricos podem apresentar valores indeterminados ou infinitos quando o valor daquelas é igual a zero.
Assim, todos os casos de dados vazios ou inválidos foram imputados como o valor de NaN da biblioteca `pandas`, de forma que possam ser utilizados nos algoritmos de #glossarium.gls("machine_learning").
Por fim, na característica `initial_backward_window_bytes`, o valor `-1` é utilizado para representar dados ausentes.
Logo, essas entradas foram imputadas com o tipo NaN do `pandas`.

As transformações foram aplicadas deterministicamente sobre as partições de treino e de teste.
Dado que nenhuma dessas transformações utilizou informações descobertas na base, o tratamento não configura leakage.

=== #get_term("pipeline", capitalize: true)

A etapa de validação cruzada foi estruturada como um #get_term("pipeline") composto por três operações principais: pré-processamento das características, balanceamento das classes e treinamento do classificador.
O primeiro estágio é realizado por meio de um `ColumnTransformer`, que separa as características numéricas e categóricas e descarta qualquer coluna que não pertença explicitamente a esses grupos.

Para as características numéricas, o #get_term("pipeline") substitui inicialmente valores infinitos por `NaN` e, em seguida, realiza a imputação pela mediana.
Não foi aplicada normalização ou padronização às características numéricas.
Para as características categóricas, os valores ausentes são substituídos pela categoria mais frequente e, posteriormente, é aplicado #foreign_text[one-hot encoding].

O #get_term("pipeline") contém uma etapa de balanceamento que pode ser: `passthrough`, mantendo a distribuição original das classes, ou `random_over_sampler`.
Essa segunda aplica o algoritmo #foreign_text[Random Over Sampler] da biblioteca `imblearn`.
Dado que o balanceamento pode alterar a definição dos hiperparâmetros ideias para um modelo, sua seleção faz parte da validação cruzada.

Na validação cruzada, foram utilizados três #get_term("fold", plural: true) estratificados, com embaralhamento das instâncias.
Em cada um, as instâncias são separadas em subconjuntos de treinamento e validação (k-fold).
O processo de validação é executado três vezes distintas, utilizando as #get_term("seed", plural: true): 27, 32, e 59.
Os resultados são agrupados para melhor representação.

Quando a configuração selecionada utiliza o `random_over_sampler`, o balanceamento é aplicado somente aos dados de treinamento já transformados.
O conjunto de validação não é submetido à amostragem e permanece com sua distribuição original das classes.

Para cada combinação de hiperparâmetros, o modelo é ajustado sobre os dados de treinamento do #get_term("fold").
São calculadas as métricas #foreign_text[accuracy], #foreign_text[precision], #foreign_text[recall], #foreign_text[macro F1], #foreign_text[ROC-AUC], #foreign_text[PR-AUC], #foreign_text[MCC] e #foreign_text[balanced accuracy].

A configuração a ser utilizada para o treinamento definitivo é selecionada segundo a média da métrica #foreign_text[macro F1] obtida entre os #get_term("fold", plural: true) e as diferentes #get_term("seed", plural: true) fixadas para o experimento.

Esse procedimento mantém o conjunto de teste completamente separado da seleção de hiperparâmetros.
Após a conclusão da validação, a configuração selecionada é ajustada sobre toda a partição de treinamento.


== Modelos de referência

#note_from_advisor(note: done_note)[
  Apresente os modelos clássicos usados como baselines. Para classificação, escolha pelo menos três métodos adequados ao problema, por exemplo: regressão logística, árvore de decisão, floresta aleatória, SVM, Naive Bayes, XGBoost/LightGBM ou outro classificador justificado. Para regressão ou agrupamento, utilize algoritmos correspondentes. Informe hiperparâmetros principais e como eles foram definidos ou ajustados.
]

#note_from_advisor(note: done_note)[
  Descreva os modelos de referência e suas configurações.
]

Foram selecionados três modelos de classificação como referência para os experimentos: #glossarium.gls("decision_tree"), floresta aleatória, e XGBoost.
Todos os modelos têm significativa capacidade de lidar com valores em escalas distintas e com outliers.

A #glossarium.gls("decision_tree") foi selecionada como #get_term("baseline") por apresentar uma única estrutura de decisão.
A floresta aleatória foi utilizada para representar a combinação de múltiplas árvores em um #glossarium.gls("model_ensemble").
O XGBoost foi selecionado para representar uma abordagem de #glossarium.gls("gradient_boosting") baseada em árvores.

Os hiperparâmetros de cada modelo foram definidos a partir de grades de valores avaliadas durante os experimentos (GridSearch).
A @tabela:grade-hiperparâmetros apresenta as configurações consideradas para cada modelo.
Cada uma foi testada com e sem balanceamento.
Por sua vez, a @tabela:hiperparametros apresenta os hiperparâmetros selecionados para cada modelo em cada base de dados. Percebe-se que o balanceamento não foi considerado vantajoso.

#describe_figure(
  [#figure(
    caption: [Grades de hiperparâmetros utilizadas nos modelos de referência],
    format_table(table(
      columns: (1fr, 1fr, 1fr),

      table.header([Modelo], [Hiperparâmetro], [Valores avaliados]),

      [Árvore de decisão], [criterion], [`gini`, `entropy`],
      [Árvore de decisão], [max_depth], [`10`, `20`, `None`],
      [Árvore de decisão], [min_samples_split], [`2`, `5`, `10`],
      [Árvore de decisão], [min_samples_leaf], [`1`, `5`],

      table.hline(stroke: 0.5pt),

      [Floresta aleatória], [n_estimators], [`100`, `200`],
      [Floresta aleatória], [max_depth], [`10`, `20`, `None`],
      [Floresta aleatória], [min_samples_split], [`2`, `5`, `10`],
      [Floresta aleatória], [min_samples_leaf], [`1`, `5`],

      table.hline(stroke: 0.5pt),

      [XGBoost], [n_estimators], [`100`, `200`],
      [XGBoost], [max_depth], [`3`, `6`],
      [XGBoost], [learning_rate], [`0.05`, `0.1`],
      [XGBoost], [min_child_weight], [`1`, `5`],
      [XGBoost], [subsample], [`0.8`, `1.0`],
    )),
  ) <tabela:grade-hiperparâmetros>],
)

#describe_figure(
  [#figure(
    caption: [Hiperparâmetros selecionados para os modelos de referência],
    format_table(table(
      columns: (1fr, 1fr, 1fr, 1fr),

      table.header([Modelo], [Hiperparâmetro], [#glossarium.gls-short("genis")], [#glossarium.gls-short("rosids")]),

      [Árvore de decisão], [sampler], [`passthrough`], [`passthrough`],
      [Árvore de decisão], [criterion], [`gini`], [`entropy`],
      [Árvore de decisão], [max_depth], [`20`], [`20`],
      [Árvore de decisão], [min_samples_split], [`2`], [`10`],
      [Árvore de decisão], [min_samples_leaf], [`1`], [`1`],

      table.hline(stroke: 0.5pt),

      [Floresta aleatória], [sampler], [`passthrough`], [`passthrough`],
      [Floresta aleatória], [n_estimators], [`200`], [`200`],
      [Floresta aleatória], [max_depth], [`None`], [`20`],
      [Floresta aleatória], [min_samples_split], [`2`], [`5`],
      [Floresta aleatória], [min_samples_leaf], [`1`], [`1`],

      table.hline(stroke: 0.5pt),

      [XGBoost], [sampler], [`passthrough`], [`passthrough`],
      [XGBoost], [n_estimators], [`200`], [`200`],
      [XGBoost], [max_depth], [`6`], [`6`],
      [XGBoost], [learning_rate], [`0.1`], [`0.1`],
      [XGBoost], [min_child_weight], [`1`], [`1`],
      [XGBoost], [subsample], [`0.8`], [`0.8`],
    )),
  ) <tabela:hiperparametros>],
)


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

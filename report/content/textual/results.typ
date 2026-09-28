#import "../../components.typ": *


= Resultados e discussão <seção:resultados>

#note_from_advisor[
  Não se limite a apresentar tabelas. Compare os métodos, quantifique diferenças e interprete os resultados à luz das características dos datasets. Discuta casos em que um método funciona melhor ou pior, classes ou regiões difíceis, complementaridade entre modelos, efeito dos comitês, comportamento do GPT, custo computacional e limitações. Diferencie claramente observações suportadas pelos experimentos de hipóteses ou especulações.
]


== Resultados dos modelos de referência

#note_from_advisor[
  Apresente os resultados dos modelos clássicos de forma comparável. Sempre indique se os valores correspondem a uma única avaliação, a predições out-of-fold agregadas ou ao resumo de múltiplas execuções/repetições. Evite escolher apenas a melhor métrica para cada modelo.
]

=== GeNIS

Os resultados dos modelos de referência na base de dados GeNIS são apresentados na @tabela:genis_métodos_clássicos_resultados.
Os valores correspondem à média e ao desvio-padrão obtidos nas três sementes utilizadas no experimento, considerando a avaliação dos modelos finais sobre o conjunto de teste congelado.

Os três modelos apresentaram desempenho elevado em todas as métricas.
A floresta aleatória e o XGBoost obtiveram valores iguais a 1 em todas as métricas apresentadas, indicando que não foram observados erros de classificação no conjunto de teste para essas execuções.
A árvore de decisão apresentou valores ligeiramente inferiores, embora também próximos do máximo.

#describe_figure(
  [#figure(
    caption: [Resultados dos modelos de referência na base de dados GeNIS],
    format_table(
      table(
        columns: (auto, 1fr, 1fr, 1fr),

        [Métrica], [Árvore de decisão], [Floresta aleatória], [XGBoost],

        [Accuracy], [0.99995 ± 0.00002], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        [Precision], [0.99986 ± 0.00005], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        [Recall], [0.99989 ± 0.00004], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        [Macro F1], [0.99987 ± 0.00004], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        [ROC-AUC], [0.99993 ± 0.00002], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        [PR-AUC], [0.99976 ± 0.00007], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        [MCC], [0.99987 ± 0.00006], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        [Balanced accuracy], [0.99989 ± 0.00004], [1.00000 ± 0.00000], [1.00000 ± 0.00000],
      ),
    ),
  ) <tabela:genis_métodos_clássicos_resultados>],
)

A tabela @tabela:genis_métodos_clássicos_resultados_por_classe mostra que as diferenças entre os modelos se concentram nas classes `Benign` e `Bruteforce`, nas quais a árvore de decisão apresenta os únicos desvios observados em relação aos demais modelos.

#describe_figure(
  [#figure(
    caption: [Métricas por classe dos modelos de referência na base de dados GeNIS],
    format_table(
      table(
        columns: (auto, auto, 1fr, 1fr, 1fr),

        [Classe], [Métrica], [Árvore de decisão], [Floresta aleatória], [XGBoost],

        table.cell(rowspan: 3)[Benign], [Precision], [0.99945 ± 0.00018], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        [Recall], [0.99994 ± 0.00011], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        [F1], [0.99969 ± 0.00014], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        table.hline(stroke: 0.5pt),

        table.cell(rowspan: 3)[Bruteforce], [Precision], [1.00000 ± 0.00000], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        [Recall], [0.99963 ± 0.00016], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        [F1], [0.99982 ± 0.00008], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        table.hline(stroke: 0.5pt),

        table.cell(rowspan: 3)[DoS], [Precision], [0.99999 ± 0.00001], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        [Recall], [0.99997 ± 0.00002], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        [F1], [0.99998 ± 0.00002], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        table.hline(stroke: 0.5pt),

        table.cell(rowspan: 3)[Recon], [Precision], [1.00000 ± 0.00000], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        [Recall], [1.00000 ± 0.00000], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        [F1], [1.00000 ± 0.00000], [1.00000 ± 0.00000], [1.00000 ± 0.00000],
      ),
    ),
  )<tabela:genis_métodos_clássicos_resultados_por_classe>],
)

A @figura:genis_métodos_clássicos_matrizes_de_confusão mostra as matrizes de confusão de cada um dos modelos.
O único que apresentou erros foi a árvore de decisão, que rotulou como `Benign` uma instância que era `DoS`, e outra que era `Bruteforce`.

#describe_figure(
  [#figure(
    caption: [Matrizes de confusão dos métodos clássicos na base de dados GeNIS],
    [
      #image("/assets/images/genis_decision_tree_confusion_matrix.png")
      #image("/assets/images/genis_random_forest_confusion_matrix.png")
      #image("/assets/images/genis_xgboost_confusion_matrix.png")
    ],
  )<figura:genis_métodos_clássicos_matrizes_de_confusão>],
)

A @tabela:genis_métodos_clássicos_tempos compara o tempo dispendido no treinamento de dado modelo, e na inferência de todas as instâncias da base de dados, além dessa métrica para cada 100 entradas.
Percebe-se que a floresta aleatória gasta 10x mais tempo no treinamento que a árvore de decisão, e 4,5x mais que o XGBoost.
Quanto ao tempo de inferência, ela demora quase 3x o tempo da árvore de decisão para fazer a classificação, sendo apenas um pouco mais lenta que o XGBoost.
Conclui-se que o XGBoost domina a floresta aleatória, dado que ele faz as mesmas predições com um custo menor.
Por outro lado, a árvore de decisão apresenta melhor desempenho computacional ao custo de 2 erros na base de dados, o que justifica sua seleção.

#describe_figure(
  [#figure(
    caption: [Tempos de treinamento e inferência dos modelos de referência na base de dados GeNIS],
    format_table(
      table(
        columns: (auto, 1fr, 1fr, 1fr),

        [Modelo], [Treinamento (s)], [Inferência (s)], [Inferência por 100 instâncias (s)],

        [Árvore de decisão], [11.6581 ± 0.1602], [0.4750 ± 0.0130], [0.000644 ± 0.000018],

        [Floresta aleatória], [135.4474 ± 5.6204], [1.2795 ± 0.0077], [0.001736 ± 0.000010],

        [XGBoost], [29.5189 ± 0.2098], [1.1153 ± 0.0039], [0.001513 ± 0.000005],
      ),
    ),
  ) <tabela:genis_métodos_clássicos_tempos>],
)


=== ROSIDS

Os resultados dos modelos de referência na base de dados ROSIDS são apresentados na @tabela:rosids_métodos_clássicos_resultados.
Os valores correspondem à média e ao desvio-padrão obtidos nas três sementes utilizadas no experimento, considerando a avaliação dos modelos finais sobre o conjunto de teste congelado.

Os três modelos apresentaram desempenho inferior ao observado no GeNIS, com valores de Macro F1 entre 0.94632 e 0.95513.
A floresta aleatória apresentou o maior Macro F1 médio, seguida pelo XGBoost e pela árvore de decisão.
As diferenças entre os modelos também são observadas nas demais métricas, com a árvore de decisão apresentando os menores valores médios em todas as métricas consideradas.

#describe_figure(
  [#figure(
    caption: [Resultados dos modelos de referência na base de dados ROSIDS],
    format_table(
      table(
        columns: (auto, 1fr, 1fr, 1fr),

        [Métrica], [Árvore de decisão], [Floresta aleatória], [XGBoost],

        [Accuracy], [0.97348 ± 0.00018], [0.97789 ± 0.00020], [0.97721 ± 0.00011],

        [Precision], [0.94650 ± 0.00060], [0.95714 ± 0.00056], [0.95520 ± 0.00044],

        [Recall], [0.94620 ± 0.00015], [0.95337 ± 0.00050], [0.95274 ± 0.00045],

        [Macro F1], [0.94632 ± 0.00026], [0.95513 ± 0.00042], [0.95388 ± 0.00043],

        [ROC-AUC], [0.98471 ± 0.00007], [0.99610 ± 0.00004], [0.99658 ± 0.00004],

        [PR-AUC], [0.94496 ± 0.00040], [0.97187 ± 0.00014], [0.97351 ± 0.00036],

        [MCC], [0.96134 ± 0.00026], [0.96777 ± 0.00029], [0.96677 ± 0.00016],

        [Balanced accuracy], [0.94620 ± 0.00015], [0.95337 ± 0.00050], [0.95274 ± 0.00045],
      ),
    ),
  ) <tabela:rosids_métodos_clássicos_resultados>],
)

A @tabela:rosids_métodos_clássicos_resultados_por_classe mostra que as maiores diferenças entre os modelos ocorrem nas classes `UnauthPub` e `UnauthSub`.
A classe `DoS` apresenta F1 próximo de 1 nos três modelos, enquanto `UnauthSub` apresenta os menores valores, com 0.85995 para a árvore de decisão, 0.88282 para a floresta aleatória e 0.87524 para o XGBoost.
Para `UnauthPub`, os valores de F1 variam de 0.91712 a 0.93347.
As classes `Benign` e `Subflood` apresentam desempenho intermediário, com diferenças menores entre os modelos.

#describe_figure(
  [#figure(
    caption: [Métricas por classe dos modelos de referência na base de dados ROSIDS],
    format_table(
      table(
        columns: (auto, auto, 1fr, 1fr, 1fr),

        [Classe], [Métrica], [Árvore de decisão], [Floresta aleatória], [XGBoost],

        table.cell(rowspan: 3)[Benign], [Precision], [0.97105 ± 0.00011], [0.97396 ± 0.00020], [0.97319 ± 0.00009],

        [Recall], [0.97555 ± 0.00049], [0.98105 ± 0.00040], [0.98030 ± 0.00026],

        [F1], [0.97330 ± 0.00023], [0.97749 ± 0.00021], [0.97673 ± 0.00012],

        table.hline(stroke: 0.5pt),

        table.cell(rowspan: 3)[DoS], [Precision], [0.99941 ± 0.00019], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        [Recall], [0.99968 ± 0.00000], [0.99968 ± 0.00000], [0.99968 ± 0.00000],

        [F1], [0.99954 ± 0.00009], [0.99984 ± 0.00000], [0.99984 ± 0.00000],

        table.hline(stroke: 0.5pt),

        table.cell(rowspan: 3)[Subflood], [Precision], [0.98798 ± 0.00035], [0.99252 ± 0.00019], [0.99228 ± 0.00039],

        [Recall], [0.97544 ± 0.00010], [0.97772 ± 0.00017], [0.97611 ± 0.00053],

        [F1], [0.98167 ± 0.00014], [0.98506 ± 0.00017], [0.98413 ± 0.00027],

        table.hline(stroke: 0.5pt),

        table.cell(rowspan: 3)[UnauthPub], [Precision], [0.90820 ± 0.00121], [0.91802 ± 0.00170], [0.92164 ± 0.00033],

        [Recall], [0.92621 ± 0.00037], [0.94327 ± 0.00074], [0.94562 ± 0.00000],

        [F1], [0.91712 ± 0.00076], [0.93047 ± 0.00065], [0.93347 ± 0.00017],

        table.hline(stroke: 0.5pt),

        table.cell(rowspan: 3)[UnauthSub], [Precision], [0.86586 ± 0.00208], [0.90121 ± 0.00119], [0.88889 ± 0.00196],

        [Recall], [0.85413 ± 0.00144], [0.86515 ± 0.00273], [0.86200 ± 0.00250],

        [F1], [0.85995 ± 0.00087], [0.88282 ± 0.00185], [0.87524 ± 0.00214],
      ),
    ),
  ) <tabela:rosids_métodos_clássicos_resultados_por_classe>],
)

A @figura:rosids_métodos_clássicos_matrizes_de_confusão mostra as matrizes de confusão dos três modelos para a semente 27.
As principais ocorrências fora da diagonal correspondem às classes `UnauthSub` e `UnauthPub`, que são frequentemente classificadas como `Benign`.
Para `UnauthSub`, essa confusão corresponde a 146 instâncias na árvore de decisão, 133 na floresta aleatória e 138 no XGBoost.
Para `UnauthPub`, são 55, 64 e 81 instâncias, respectivamente.
A classe `DoS` apresenta apenas uma instância classificada incorretamente por cada modelo, enquanto `Subflood` também apresenta parte dos erros associada à classificação como `Benign`.

#describe_figure(
  [#figure(
    caption: [Matrizes de confusão dos métodos clássicos na base de dados ROSIDS],
    [
      #image("/assets/images/rosids_decision_tree_confusion_matrix.png")
      #image("/assets/images/rosids_random_forest_confusion_matrix.png")
      #image("/assets/images/rosids_xgboost_confusion_matrix.png")
    ],
  ) <figura:rosids_métodos_clássicos_matrizes_de_confusão>],
)

A @tabela:rosids_métodos_clássicos_tempos evidencia um compromisso entre custo computacional e desempenho preditivo.
A árvore de decisão apresenta o menor custo tanto no treinamento quanto na inferência, mas obtém o menor Macro F1 entre os três modelos.
A floresta aleatória alcança o maior Macro F1, porém requer aproximadamente 8,8 vezes o tempo de treinamento da árvore e 4,5 vezes o tempo de inferência.
O XGBoost apresenta desempenho muito próximo ao da floresta aleatória, com diferença de apenas 0,00125 no Macro F1 médio, mas reduz o custo em relação a ela, principalmente no treinamento.
Assim, a floresta aleatória oferece o maior desempenho preditivo ao custo computacional mais elevado, enquanto o XGBoost ocupa uma posição intermediária entre desempenho e custo, e a árvore de decisão privilegia a velocidade em detrimento de parte do desempenho, o que deve ser vantajoso em um cenário de enorme vazão de fluxos de rede.

#describe_figure(
  [#figure(
    caption: [Tempos de treinamento e inferência dos modelos de referência na base de dados ROSIDS],
    format_table(
      table(
        columns: (auto, 1fr, 1fr, 1fr),

        [Modelo], [Treinamento (s)], [Inferência (s)], [Inferência por 100 instâncias (s)],

        [Árvore de decisão], [2.7532 ± 0.0080], [0.1613 ± 0.0042], [0.000590 ± 0.000015],

        [Floresta aleatória], [24.2634 ± 0.2256], [0.7219 ± 0.0045], [0.002641 ± 0.000016],

        [XGBoost], [19.4177 ± 0.3645], [0.6331 ± 0.0020], [0.002316 ± 0.000007],
      ),
    ),
  ) <tabela:rosids_métodos_clássicos_tempos>],
)


== Resultados dos comitês

#note_from_advisor[
  Compare os comitês com os modelos individuais. Analise se a combinação realmente trouxe ganho e procure relacionar o resultado à diversidade/complementaridade dos modelos. Se houver pesos, apresente-os e explique como foram obtidos.
]

#note_from_advisor(note: todo_note)[
  Apresente e discuta os resultados dos comitês.
]

== Comparação com GPT

#note_from_advisor[
  Compare zero-shot, few-shot e, quando utilizado, embeddings + classificador com os mesmos baselines e nos mesmos exemplos de avaliação. Além das métricas preditivas, relate tempo por 100 amostras e custo estimado quando houver API. Discuta também saídas inválidas, sensibilidade ao prompt e outras limitações observadas. Para tarefas não classificatórias, adapte ou remova esta subseção conforme definido com o professor.
]

#note_from_advisor(note: todo_note)[
  Apresente e discuta a comparação entre GPT/LLM e os métodos clássicos.
]

== Comparação entre os datasets

#note_from_advisor[
  Como o trabalho exige pelo menos dois datasets, compare o comportamento dos métodos entre eles. Procure explicar se diferenças de tamanho, dimensionalidade, desbalanceamento, ruído, domínio ou dificuldade ajudam a entender as mudanças de desempenho.
]

#note_from_advisor(note: todo_note)[
  Compare os resultados obtidos nas diferentes bases.
]

== Análise de erros

#note_from_advisor[
  Analise onde os modelos falham. Em classificação, use matrizes de confusão e exemplos de falsos positivos/falsos negativos ou classes confundidas. Em regressão/séries, examine erros grandes, horizontes ou regiões problemáticas. Em agrupamento, investigue pontos ambíguos e estrutura dos grupos. Sempre preserve a privacidade e as regras de uso dos dados.
]

#note_from_advisor(note: todo_note)[
  Apresente uma análise qualitativa e/ou quantitativa dos erros.
]

== Custo computacional e eficiência

#note_from_advisor[
  Compare tempo de treinamento/inferência, memória ou custo de API quando esses fatores forem relevantes. Um método mais complexo deve justificar o custo adicional por ganhos de desempenho, estabilidade, interpretabilidade ou outra vantagem prática.
]

#note_from_advisor(note: todo_note)[
  Discuta custo computacional, tempo e/ou custo financeiro quando aplicável.
]

== Discussão geral e limitações

#note_from_advisor[
  Sintetize os principais achados e suas limitações. Discuta tamanho e representatividade dos dados, dependência de um domínio específico, hiperparâmetros, orçamento experimental, possíveis vieses, limitações das métricas e outras restrições que afetem a interpretação dos resultados.
]

#note_from_advisor(note: todo_note)[
  Discuta os resultados de forma integrada e apresente as principais limitações.
]

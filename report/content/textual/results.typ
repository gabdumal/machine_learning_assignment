#import "../../components.typ": *


= Resultados e discussão <seção:resultados>

#note_from_advisor(note: progress_note)[
  Não se limite a apresentar tabelas. Compare os métodos, quantifique diferenças e interprete os resultados à luz das características dos datasets. Discuta casos em que um método funciona melhor ou pior, classes ou regiões difíceis, complementaridade entre modelos, efeito dos comitês, comportamento do GPT, custo computacional e limitações. Diferencie claramente observações suportadas pelos experimentos de hipóteses ou especulações.
]


== Resultados dos modelos de referência

#note_from_advisor(note: done_note)[
  Apresente os resultados dos modelos clássicos de forma comparável. Sempre indique se os valores correspondem a uma única avaliação, a predições out-of-fold agregadas ou ao resumo de múltiplas execuções/repetições. Evite escolher apenas a melhor métrica para cada modelo.
]

=== #glossarium.gls-short("genis")

Os resultados dos modelos de referência na base de dados #glossarium.gls("genis") são apresentados na @tabela:genis_métodos_clássicos_resultados.
Os valores correspondem à média e ao desvio-padrão obtidos nas três #get_term("seed", plural: true) utilizadas no experimento, considerando a avaliação dos modelos finais sobre o conjunto de teste exclusivo.

Os três modelos apresentaram desempenho elevado em todas as métricas.
A #glossarium.gls("random_forest") e o #glossarium.gls("xgboost") obtiveram valores iguais a 1 em todas as métricas apresentadas, indicando que não foram observados erros de classificação no conjunto de teste para essas execuções.
A #glossarium.gls("decision_tree") apresentou valores ligeiramente inferiores, embora também próximos do máximo.

#describe_figure(
  [#figure(
    caption: [Resultados dos modelos de referência na base de dados #glossarium.gls-short("genis")],
    format_table(
      table(
        columns: (auto, 1fr, 1fr, 1fr),

        table.header([Métrica], [Árvore de decisão], [Floresta aleatória], [XGBoost]),

        [#get_term("accuracy", capitalize: true)],
        [0.99995 ± 0.00002],
        strong[1.00000 ± 0.00000],
        strong[1.00000 ± 0.00000],

        [#get_term("precision", capitalize: true)],
        [0.99986 ± 0.00005],
        strong[1.00000 ± 0.00000],
        strong[1.00000 ± 0.00000],

        [#get_term("recall", capitalize: true)],
        [0.99989 ± 0.00004],
        strong[1.00000 ± 0.00000],
        strong[1.00000 ± 0.00000],

        [#get_term("macro_f1")], [0.99987 ± 0.00004], strong[1.00000 ± 0.00000], strong[1.00000 ± 0.00000],

        [#get_term("roc_auc")], [0.99993 ± 0.00002], strong[1.00000 ± 0.00000], strong[1.00000 ± 0.00000],

        [#get_term("pr_auc")], [0.99976 ± 0.00007], strong[1.00000 ± 0.00000], strong[1.00000 ± 0.00000],

        [#get_term("mcc")], [0.99987 ± 0.00006], strong[1.00000 ± 0.00000], strong[1.00000 ± 0.00000],

        [#get_term("balanced_accuracy", capitalize: true)],
        [0.99989 ± 0.00004],
        strong[1.00000 ± 0.00000],
        strong[1.00000 ± 0.00000],
      ),
    ),
  ) <tabela:genis_métodos_clássicos_resultados>],
)

A @tabela:genis_métodos_clássicos_resultados_por_classe mostra que as diferenças entre os modelos se concentram nas classes `benign` e `bruteforce`, nas quais a #glossarium.gls("decision_tree", link: false) apresenta os únicos desvios observados em relação aos demais modelos.

#describe_figure(
  [#figure(
    caption: [Métricas por classe dos modelos de referência na base de dados #glossarium.gls-short("genis")],
    format_table(
      table(
        columns: (auto, auto, 1fr, 1fr, 1fr),

        table.header([Classe], [Métrica], [Árvore de decisão], [Floresta aleatória], [XGBoost]),

        table.cell(rowspan: 3)[benign],
        [#get_term("precision", capitalize: true)],
        [0.99945 ± 0.00018],
        strong[1.00000 ± 0.00000],
        strong[1.00000 ± 0.00000],

        [#get_term("recall", capitalize: true)],
        [0.99994 ± 0.00011],
        strong[1.00000 ± 0.00000],
        strong[1.00000 ± 0.00000],

        [#get_term("f1")], [0.99969 ± 0.00014], strong[1.00000 ± 0.00000], strong[1.00000 ± 0.00000],

        table.hline(stroke: 0.5pt),

        table.cell(rowspan: 3)[bruteforce],
        [#get_term("precision", capitalize: true)],
        strong[1.00000 ± 0.00000],
        strong[1.00000 ± 0.00000],
        strong[1.00000 ± 0.00000],

        [#get_term("recall", capitalize: true)],
        [0.99963 ± 0.00016],
        strong[1.00000 ± 0.00000],
        strong[1.00000 ± 0.00000],

        [#get_term("f1")], [0.99982 ± 0.00008], strong[1.00000 ± 0.00000], strong[1.00000 ± 0.00000],

        table.hline(stroke: 0.5pt),

        table.cell(rowspan: 3)[dos],
        [#get_term("precision", capitalize: true)],
        [0.99999 ± 0.00001],
        strong[1.00000 ± 0.00000],
        strong[1.00000 ± 0.00000],

        [#get_term("recall", capitalize: true)],
        [0.99997 ± 0.00002],
        strong[1.00000 ± 0.00000],
        strong[1.00000 ± 0.00000],

        [#get_term("f1")], [0.99998 ± 0.00002], strong[1.00000 ± 0.00000], strong[1.00000 ± 0.00000],

        table.hline(stroke: 0.5pt),

        table.cell(rowspan: 3)[recon],
        [#get_term("precision", capitalize: true)],
        strong[1.00000 ± 0.00000],
        strong[1.00000 ± 0.00000],
        strong[1.00000 ± 0.00000],

        [#get_term("recall", capitalize: true)],
        strong[1.00000 ± 0.00000],
        strong[1.00000 ± 0.00000],
        strong[1.00000 ± 0.00000],

        [#get_term("f1")], strong[1.00000 ± 0.00000], strong[1.00000 ± 0.00000], strong[1.00000 ± 0.00000],
      ),
    ),
  )<tabela:genis_métodos_clássicos_resultados_por_classe>],
)

A @figura:genis_métodos_clássicos_matrizes_de_confusão mostra as matrizes de confusão de cada um dos modelos na #get_term("seed") 27.
O único que apresentou erros foi a #glossarium.gls("decision_tree", link: false), que rotulou como `benign` uma instância que era `dos`, e outra que era `bruteforce`.

#describe_figure(
  [#figure(
    caption: [Matrizes de confusão dos métodos clássicos na base de dados #glossarium.gls-short("genis")],
    [
      #image("/assets/images/genis_decision_tree_confusion_matrix.png")
      #image("/assets/images/genis_random_forest_confusion_matrix.png")
      #image("/assets/images/genis_xgboost_confusion_matrix.png")
    ],
  )<figura:genis_métodos_clássicos_matrizes_de_confusão>],
)

A @tabela:genis_métodos_clássicos_tempos compara o tempo dispendido no treinamento de dado modelo, e na inferência de todas as instâncias da base de dados, além dessa métrica para cada 100 entradas.
Percebe-se que a #glossarium.gls("random_forest", link: false) gasta 10x mais tempo no treinamento que a #glossarium.gls("decision_tree", link: false), e 4,5x mais que o #glossarium.gls("xgboost", link: false).
Quanto ao tempo de inferência, ela demora quase 3x o tempo da #glossarium.gls("decision_tree", link: false) para fazer a classificação, sendo apenas um pouco mais lenta que o #glossarium.gls("xgboost", link: false).

Conclui-se que o #glossarium.gls("xgboost", link: false) domina a #glossarium.gls("random_forest", link: false), dado que ele faz as mesmas predições com um custo menor.
Por outro lado, a #glossarium.gls("decision_tree", link: false) apresenta melhor desempenho computacional ao custo de 2 erros na base de dados, o que justifica sua seleção.

#describe_figure(
  [#figure(
    caption: [Tempos de treinamento e inferência dos modelos de referência na base de dados #glossarium.gls-short("genis")],
    format_table(
      table(
        columns: (auto, 1fr, 1fr, 1fr),

        table.header([Modelo], [Treinamento (s)], [Inferência (s)], [Inferência por 100 instâncias (s)]),

        [Árvore de decisão], strong[11.6581 ± 0.1602], strong[0.4750 ± 0.0130], strong[0.000644 ± 0.000018],

        [Floresta aleatória], [135.4474 ± 5.6204], [1.2795 ± 0.0077], [0.001736 ± 0.000010],

        [XGBoost], [29.5189 ± 0.2098], [1.1153 ± 0.0039], [0.001513 ± 0.000005],
      ),
    ),
  ) <tabela:genis_métodos_clássicos_tempos>],
)

Finalmente, a @figura:genis_métodos_clássicos_características permite visualizar a importância das características para cada algoritmo.
Percebe-se que a porta de destino do fluxo, que foi transformada em uma característica categórica, assume 30,37% de importância para o #glossarium.gls("xgboost", link: false), o que ressalta que determinados tipos de ataques são direcionados para um conjunto pequeno de portas.
Ao mesmo tempo, a #glossarium.gls("decision_tree", link: false) priorizou a demora máxima entre pacotes no tráfego de origem.
Por outro lado, a #glossarium.gls("random_forest", link: false) mostrou uma distribuição muito mais balanceada entre as características; alcançando o melhor desempenho juntamente com o #glossarium.gls("xgboost", link: false).

#describe_figure(
  placement: auto,
  [#figure(
    caption: [Matrizes de confusão dos métodos clássicos na base de dados #glossarium.gls-short("genis")],
    [
      #image("/assets/images/genis_feature_importance_heatmap.png")
    ],
  ) <figura:genis_métodos_clássicos_características>],
)


=== #glossarium.gls-short("rosids")

Os resultados dos modelos de referência na base de dados #glossarium.gls("rosids") são apresentados na @tabela:rosids_métodos_clássicos_resultados.
Os valores correspondem à média e ao desvio-padrão obtidos nas três #get_term("seed", plural: true) utilizadas no experimento, considerando a avaliação dos modelos finais sobre o conjunto de teste congelado.

Os três modelos apresentaram desempenho inferior ao observado no #glossarium.gls("genis"), com valores de #get_term("macro_f1") entre 0.94632 e 0.95513.
A #glossarium.gls("random_forest") apresentou o maior #get_term("macro_f1") médio, seguida pelo #glossarium.gls("xgboost") e pela #glossarium.gls("decision_tree").
As diferenças entre os modelos também são observadas nas demais métricas, com a #glossarium.gls("decision_tree", link: false) apresentando os menores valores médios em todas as métricas consideradas.

#describe_figure(
  [#figure(
    caption: [Resultados dos modelos de referência na base de dados #glossarium.gls-short("rosids")],
    format_table(
      table(
        columns: (auto, 1fr, 1fr, 1fr),

        table.header([Métrica], [Árvore de decisão], [Floresta aleatória], [XGBoost]),

        [#get_term("accuracy", capitalize: true)], [0.97348 ± 0.00018], strong[0.97789 ± 0.00020], [0.97721 ± 0.00011],

        [#get_term("precision", capitalize: true)], [0.94650 ± 0.00060], strong[0.95714 ± 0.00056], [0.95520 ± 0.00044],

        [#get_term("recall", capitalize: true)], [0.94620 ± 0.00015], strong[0.95337 ± 0.00050], [0.95274 ± 0.00045],

        [#get_term("macro_f1")], [0.94632 ± 0.00026], strong[0.95513 ± 0.00042], [0.95388 ± 0.00043],

        [#get_term("roc_auc")], [0.98471 ± 0.00007], [0.99610 ± 0.00004], strong[0.99658 ± 0.00004],

        [#get_term("pr_auc")], [0.94496 ± 0.00040], [0.97187 ± 0.00014], strong[0.97351 ± 0.00036],

        [#get_term("mcc")], [0.96134 ± 0.00026], strong[0.96777 ± 0.00029], [0.96677 ± 0.00016],

        [#get_term("balanced_accuracy", capitalize: true)],
        [0.94620 ± 0.00015],
        strong[0.95337 ± 0.00050],
        [0.95274 ± 0.00045],
      ),
    ),
  ) <tabela:rosids_métodos_clássicos_resultados>],
)

A @tabela:rosids_métodos_clássicos_resultados_por_classe mostra que as maiores diferenças entre os modelos ocorrem nas classes `UnauthPub` e `UnauthSub`.
A classe majoritária `DoS` apresenta #get_term("f1") próximo de 1 nos três modelos, enquanto `UnauthSub` apresenta os menores valores, com 0.85995 para a #glossarium.gls("decision_tree", link: false), 0.88282 para a #glossarium.gls("random_forest", link: false) e 0.87524 para o #glossarium.gls("xgboost", link: false).
As classes `Benign` e `Subflood` apresentam desempenho intermediário, com diferenças menores entre os modelos.

#describe_figure(
  [#figure(
    caption: [Métricas por classe dos modelos de referência na base de dados #glossarium.gls-short("rosids")],
    format_table(
      table(
        columns: (auto, auto, 1fr, 1fr, 1fr),

        table.header([Classe], [Métrica], [Árvore de decisão], [Floresta aleatória], [XGBoost]),

        table.cell(rowspan: 3)[Benign],
        [#get_term("precision", capitalize: true)], [0.97105 ± 0.00011], strong[0.97396 ± 0.00020], [0.97319 ± 0.00009],

        [#get_term("recall", capitalize: true)], [0.97555 ± 0.00049], strong[0.98105 ± 0.00040], [0.98030 ± 0.00026],

        [#get_term("f1")], [0.97330 ± 0.00023], strong[0.97749 ± 0.00021], [0.97673 ± 0.00012],

        table.hline(stroke: 0.5pt),

        table.cell(rowspan: 3)[DoS],
        [#get_term("precision", capitalize: true)],
        [0.99941 ± 0.00019],
        strong[1.00000 ± 0.00000],
        strong[1.00000 ± 0.00000],

        [#get_term("recall", capitalize: true)],
        strong[0.99968 ± 0.00000],
        strong[0.99968 ± 0.00000],
        strong[0.99968 ± 0.00000],

        [#get_term("f1")], [0.99954 ± 0.00009], strong[0.99984 ± 0.00000], strong[0.99984 ± 0.00000],

        table.hline(stroke: 0.5pt),

        table.cell(rowspan: 3)[Subflood],
        [#get_term("precision", capitalize: true)], [0.98798 ± 0.00035], strong[0.99252 ± 0.00019], [0.99228 ± 0.00039],

        [#get_term("recall", capitalize: true)], [0.97544 ± 0.00010], strong[0.97772 ± 0.00017], [0.97611 ± 0.00053],

        [#get_term("f1")], [0.98167 ± 0.00014], strong[0.98506 ± 0.00017], [0.98413 ± 0.00027],

        table.hline(stroke: 0.5pt),

        table.cell(rowspan: 3)[UnauthPub],
        [#get_term("precision", capitalize: true)], [0.90820 ± 0.00121], [0.91802 ± 0.00170], strong[0.92164 ± 0.00033],

        [#get_term("recall", capitalize: true)], [0.92621 ± 0.00037], [0.94327 ± 0.00074], strong[0.94562 ± 0.00000],

        [#get_term("f1")], [0.91712 ± 0.00076], [0.93047 ± 0.00065], strong[0.93347 ± 0.00017],

        table.hline(stroke: 0.5pt),

        table.cell(rowspan: 3)[UnauthSub],
        [#get_term("precision", capitalize: true)], [0.86586 ± 0.00208], strong[0.90121 ± 0.00119], [0.88889 ± 0.00196],

        [#get_term("recall", capitalize: true)], [0.85413 ± 0.00144], strong[0.86515 ± 0.00273], [0.86200 ± 0.00250],

        [#get_term("f1")], [0.85995 ± 0.00087], strong[0.88282 ± 0.00185], [0.87524 ± 0.00214],
      ),
    ),
  ) <tabela:rosids_métodos_clássicos_resultados_por_classe>],
)

A @figura:rosids_métodos_clássicos_matrizes_de_confusão mostra as matrizes de confusão dos três modelos para a #get_term("seed") 27.
As principais ocorrências fora da diagonal correspondem às classes `UnauthSub` e `UnauthPub`, que são frequentemente classificadas como `Benign`.
Para `UnauthSub`, essa confusão corresponde a 146 instâncias na #glossarium.gls("decision_tree", link: false), 133 na #glossarium.gls("random_forest", link: false) e 138 no XGBoost.
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

A @tabela:rosids_métodos_clássicos_tempos evidencia uma relação entre custo computacional e desempenho preditivo.
A #glossarium.gls("decision_tree", link: false) apresenta o menor custo tanto no treinamento quanto na inferência, mas obtém o menor #get_term("macro_f1") entre os três modelos.
A #glossarium.gls("random_forest", link: false) alcança o maior #get_term("macro_f1"), porém requer aproximadamente 8,8 vezes o tempo de treinamento da árvore e 4,5 vezes o tempo de inferência.
O #glossarium.gls("xgboost", link: false) apresenta desempenho muito próximo ao da #glossarium.gls("random_forest", link: false), com diferença de apenas 0,00125 no #get_term("macro_f1") médio, mas reduz o custo em relação a ela, principalmente no treinamento.

Assim, a #glossarium.gls("random_forest", link: false) oferece o maior desempenho preditivo ao custo computacional mais elevado, enquanto o #glossarium.gls("xgboost", link: false) ocupa uma posição intermediária entre desempenho e custo, e a #glossarium.gls("decision_tree", link: false) privilegia a velocidade em um pequeno detrimento do desempenho, o que pode ser vantajoso em um cenário de enorme vazão de fluxos de rede.

#describe_figure(
  [#figure(
    caption: [Tempos de treinamento e inferência dos modelos de referência na base de dados ROSIDS],
    format_table(
      table(
        columns: (auto, 1fr, 1fr, 1fr),

        table.header([Modelo], [Treinamento (s)], [Inferência (s)], [Inferência por 100 instâncias (s)]),

        [Árvore de decisão], strong[2.7532 ± 0.0080], strong[0.1613 ± 0.0042], strong[0.000590 ± 0.000015],

        [Floresta aleatória], [24.2634 ± 0.2256], [0.7219 ± 0.0045], [0.002641 ± 0.000016],

        [XGBoost], [19.4177 ± 0.3645], [0.6331 ± 0.0020], [0.002316 ± 0.000007],
      ),
    ),
  ) <tabela:rosids_métodos_clássicos_tempos>],
)

Finalmente, a @figura:rosids_métodos_clássicos_características permite visualizar a importância das características para cada algoritmo.
Percebe-se que a porta de destino do fluxo, que foi transformada em uma característica categórica, assume 40,56% de importância para a #glossarium.gls("decision_tree", link: false), e 59,57% para o #glossarium.gls("xgboost", link: false), o que mostra uma dominação da capacidade de predição, e ressalta que determinados tipos de ataques são direcionados para um conjunto pequeno de portas.
Por outro lado, a #glossarium.gls("random_forest", link: false) mostrou uma distribuição muito mais balanceada entre as características; alcançando o melhor desempenho.

#describe_figure(
  placement: auto,
  [#figure(
    caption: [Matrizes de confusão dos métodos clássicos na base de dados ROSIDS],
    [
      #image("/assets/images/rosids_feature_importance_heatmap.png")
    ],
  ) <figura:rosids_métodos_clássicos_características>],
)


== Resultados dos comitês

#note_from_advisor(note: done_note)[
  Compare os comitês com os modelos individuais. Analise se a combinação realmente trouxe ganho e procure relacionar o resultado à diversidade/complementaridade dos modelos. Se houver pesos, apresente-os e explique como foram obtidos.
]

#note_from_advisor(note: done_note)[
  Apresente e discuta os resultados dos comitês.
]

=== Configuração e pesos

Os comitês foram construídos a partir dos três modelos de referência: #glossarium.gls("decision_tree"), #glossarium.gls("random_forest"), e #glossarium.gls("xgboost").
Para cada base de dados, foram avaliadas quatro estratégias: #get_term("hard_voting"), #get_term("hard_voting_ponderado"), #get_term("soft_voting"), e #get_term("soft_voting_ponderado").

A @tabela:comites_pesos apresenta os valores utilizados para cada base.
Na base #glossarium.gls("genis"), os três algoritmos apresentaram #get_term("macro_f1") de validação muito próximos, resultando em pesos praticamente uniformes.
A maior diferença ocorre para a #glossarium.gls("decision_tree", link: false), enquanto a #glossarium.gls("random_forest", link: false) e o #glossarium.gls("xgboost", link: false) recebem diferem em 0,00001.
No #glossarium.gls("rosids", link: false), a distribuição também permanece próxima da uniformidade, embora o #glossarium.gls("xgboost", link: false) apresente o maior peso, seguido pela #glossarium.gls("random_forest", link: false) e pela #glossarium.gls("decision_tree", link: false).

#describe_figure(
  [#figure(
    caption: [#get_term("macro_f1") médio na validação e pesos utilizados nos comitês],
    format_table(
      table(
        columns: (auto, auto, auto, auto),
        table.header([Base], [Modelo], [#get_term("macro_f1") na validação], [Peso]),
        table.cell(rowspan: 3)[#glossarium.gls("genis", link: false)], [Árvore de decisão], [0,99984], [0,33332],
        [Floresta aleatória], [0,99993], [0,33335],
        [XGBoost], [0,99990], [0,33334],
        table.hline(stroke: 0.5pt),
        table.cell(rowspan: 3)[#glossarium.gls("rosids", link: false)], [Árvore de decisão], [0,94202], [0,33085],
        [Floresta aleatória], [0,95197], [0,33435],
        [XGBoost], [0,95326], [0,33480],
      ),
    ),
  ) <tabela:comites_pesos>],
)


=== #glossarium.gls-short("genis")

A @tabela:genis_comites_resultados apresenta os resultados das quatro estratégias de comitê na base de dados #glossarium.gls("genis"), considerando as três #get_term("seed", plural: true) utilizadas no experimento.
O #get_term("hard_voting") e sua versão ponderada apresentaram os mesmos resultados em todas as métricas, sem cometer erros.
As estratégias baseadas em #get_term("soft_voting") também apresentaram desempenho excepcional, mas com pequenas variações.

#describe_figure(
  [#figure(
    caption: [Desempenho dos comitês na base de dados #glossarium.gls-short("genis")],
    format_table(
      table(
        columns: (auto, auto, auto, auto, auto, auto, auto),
        align: start,

        table.header(
          [Estratégia],
          [#get_term("accuracy", capitalize: true)],
          [#get_term("precision", capitalize: true)],
          [#get_term("recall", capitalize: true)],
          [#get_term("macro_f1")],
          [#get_term("roc_auc")],
          [#get_term("pr_auc")],
        ),

        [#get_term("hard_voting", capitalize: true)],
        strong[1,00000\ ± 0,00000],
        strong[1,00000\ ± 0,00000],
        strong[1,00000\ ± 0,00000],
        strong[1,00000\ ± 0,00000],
        strong[1,00000\ ± 0,00000],
        strong[1,00000\ ± 0,00000],

        [#get_term("hard_voting_ponderado", capitalize: true)],
        strong[1,00000\ ± 0,00000],
        strong[1,00000\ ± 0,00000],
        strong[1,00000\ ± 0,00000],
        strong[1,00000\ ± 0,00000],
        strong[1,00000\ ± 0,00000],

        strong[1,00000\ ± 0,00000],

        [#get_term("soft_voting", capitalize: true)],
        [1,00000\ ± 0,00001],
        strong[1,00000\ ± 0,00000],
        [0,99998\ ± 0,00003],
        [0,99999\ ± 0,00001],
        strong[1,00000\ ± 0,00000],
        strong[1,00000\ ± 0,00000],

        [#get_term("soft_voting_ponderado", capitalize: true)],
        [1,00000\ ± 0,00001],
        strong[1,00000\ ± 0,00000],
        [0,99998\ ± 0,00003],
        [0,99999\ ± 0,00001],
        strong[1,00000\ ± 0,00000],
        strong[1,00000\ ± 0,00000],
      ),
    ),
  ) <tabela:genis_comites_resultados>],
)

Considerando o #get_term("macro_f1"), o #get_term("hard_voting") alcançou o mesmo valor obtido pela #glossarium.gls("random_forest", link: false) e pelo #glossarium.gls("xgboost", link: false), que predizem perfeitamente.
Em relação à #glossarium.gls("decision_tree", link: false), cujo #get_term("macro_f1") médio foi de 0,99987, ambas as estratégias de votação majoritária apresentaram um aumento de desempenho, dado que pararam de cometer os erros.
As duas estratégias baseadas em probabilidades, por outro lado, apresentaram #get_term("macro_f1") de 0,99999, uma vez que permitiram que a #glossarium.gls("decision_tree", link: false) levasse a um erro.

As pequenas diferenças observadas entre as estratégias indicam que, para essa base, os comitês não produzem ganho relevante sobre os melhores modelos individuais, mas apenas incorrem em maior custo computacional.


=== #glossarium.gls-short("rosids")

A @tabela:rosids_comites_resultados apresenta os resultados das quatro estratégias de comitê na base de dados #glossarium.gls("rosids", link: false), considerando as três #get_term("seed", plural: true) do experimento.
O #get_term("hard_voting") apresentou #get_term("macro_f1") médio de 0,95606, tendo sido ligeiramente melhor que os outros métodos de comitê e tradicionais.

#describe_figure(
  [#figure(
    caption: [Desempenho dos comitês na base de dados #glossarium.gls-short("rosids")],
    format_table(
      table(
        columns: (auto, auto, auto, auto, auto, auto, auto),
        align: start,

        table.header(
          [Estratégia],
          [#get_term("accuracy", capitalize: true)],
          [#get_term("precision", capitalize: true)],
          [#get_term("recall", capitalize: true)],
          [#get_term("macro_f1")],
          [#get_term("roc_auc")],
          [#get_term("pr_auc")],
        ),

        [#get_term("hard_voting", capitalize: true)],
        [0,97831\ ± 0,00019],
        [0,95694\ ± 0,00037],
        strong[0,95537\ ± 0,00038],
        strong[0,95606\ ± 0,00030],
        [0,97825\ ± 0,00003],
        [0,93324\ ± 0,00020],

        [#get_term("hard_voting_ponderado", capitalize: true)],
        strong[0,97837\ ± 0,00014],
        strong[0,95732\ ± 0,00021],
        [0,95496\ ± 0,00033],
        [0,95604\ ± 0,00017],
        [0,97826\ ± 0,00003],
        [0,93347\ ± 0,00018],

        [#get_term("soft_voting", capitalize: true)],
        [0,97799\ ± 0,00002],
        [0,95526\ ± 0,00021],
        [0,95471\ ± 0,00003],
        [0,95491\ ± 0,00011],
        strong[0,99658\ ± 0,00004],
        strong[0,97398\ ± 0,00015],

        [#get_term("soft_voting_ponderado", capitalize: true)],
        [0,97800\ ± 0,00004],
        [0,95531\ ± 0,00025],
        [0,95472\ ± 0,00002],
        [0,95494\ ± 0,00013],
        strong[0,99658\ ± 0,00004],
        [0,97398\ ± 0,00016],
      ),
    ),
  ) <tabela:rosids_comites_resultados>],
)

Em comparação com os modelos individuais, o #get_term("hard_voting") apresentou #get_term("macro_f1") médio 0,00093 superior ao da #glossarium.gls("random_forest", link: false), que obteve 0,95513, e 0,00218 superior ao do XGBoost, com 0,95388.
Em relação à #glossarium.gls("decision_tree", link: false), a diferença foi de 0,00974.
A versão ponderada fez pouca diferença no resultado, obtendo menor desvio-padrão.

As métricas baseadas nas probabilidades apresentam comportamento diferente das métricas de classificação.
O #get_term("soft_voting") e sua versão ponderada alcançaram #get_term("roc_auc") médio de 0,99658 e #get_term("pr_auc") de aproximadamente 0,97398, valores superiores aos observados no #get_term("hard_voting").
Isso decorre do uso das probabilidades médias dos classificadores como escores dessas estratégias, enquanto a votação majoritária utiliza a proporção de votos para produzir seus escores.

Considerando um cenário de altíssimo risco, em que se deseja absolutamente minimizar a chance de erro, os comitês se mostram uma boa opção.
Ainda assim, o custo adicional leva a preferir métodos tradicionais em cenários mais comuns.

=== Diversidade e complementaridade

A @tabela:comites_diversidade apresenta as medidas de diversidade entre os pares de classificadores que compõem os comitês.
Foram consideradas a discordância entre as previsões, a ocorrência de erros simultâneos (#foreign_text[Double Fault]) e a similaridade entre os conjuntos de erros, medida pelo coeficiente de Jaccard.
Valores menores de discordância indicam previsões mais semelhantes, enquanto valores menores de Jaccard indicam menor sobreposição entre os erros dos dois classificadores.

#describe_figure(
  [#figure(
    caption: [Medidas de diversidade entre os classificadores dos comitês],
    format_table(
      table(
        align: start + horizon,
        columns: (auto, auto, auto, auto, auto),

        table.header([Base], [Par de classificadores], [Discordância], [Double Fault], [Jaccard dos erros]),

        table.cell(rowspan: 3)[#glossarium.gls("genis", link: false)],
        [Árvore de decisão\ × Floresta aleatória],
        strong[0,00005 ± 0,00002],
        [0,00000 ± 0,00000],
        [0,00000 ± 0,00000],

        [Árvore de decisão\ × XGBoost], strong[0,00005 ± 0,00002], [0,00000 ± 0,00000], [0,00000 ± 0,00000],
        [Floresta aleatória\ × XGBoost], [0,00000 ± 0,00000], [0,00000 ± 0,00000], [1,00000 ± 0,00000],

        table.hline(stroke: 0.5pt),

        table.cell(rowspan: 3)[#glossarium.gls("rosids", link: false)],
        [Árvore de decisão\ × Floresta aleatória],
        [0,01036 ± 0,00018],
        strong[0,01947 ± 0,00021],
        [0,66793 ± 0,00705],

        [Árvore de decisão\ × XGBoost], strong[0,01347 ± 0,00008], [0,01845 ± 0,00014], strong[0,59778 ± 0,00276],
        [Floresta aleatória\ × XGBoost], [0,00718 ± 0,00040], [0,01922 ± 0,00027], [0,74842 ± 0,01600],
      ),
    ),
  ) <tabela:comites_diversidade>],
)

No #glossarium.gls("genis", link: false), a discordância entre os classificadores foi praticamente nula.
Árvore de decisão e #glossarium.gls("random_forest", link: false), assim como #glossarium.gls("decision_tree", link: false) e #glossarium.gls("xgboost", link: false), apresentaram discordância média de 0,00005, enquanto #glossarium.gls("random_forest", link: false) e #glossarium.gls("xgboost", link: false) não apresentaram discordâncias nas previsões.
O `Double Fault` foi nulo em todos os pares.
Nos dois pares que envolvem a #glossarium.gls("decision_tree", link: false), o Jaccard dos conjuntos de erros também foi nulo, indicando que os erros observados não foram compartilhados entre esses classificadores.
Entretanto, como a quantidade total de erros é muito pequena nessa base, essa diferença entre os padrões de erro ocorre em uma quantidade reduzida de instâncias.
Para a #glossarium.gls("random_forest", link: false) e o #glossarium.gls("xgboost", link: false), o Jaccard igual a 1,00000 decorre da coincidência completa entre seus conjuntos de erros, que são ambos vazios.

No #glossarium.gls("rosids", link: false), as diferenças entre os classificadores são mais pronunciadas.
O maior nível de discordância ocorre entre a #glossarium.gls("decision_tree", link: false) e o #glossarium.gls("xgboost", link: false), com 0,01347, seguido pelo par entre #glossarium.gls("decision_tree", link: false) e #glossarium.gls("random_forest", link: false), com 0,01036.
A menor discordância ocorre entre #glossarium.gls("random_forest", link: false) e #glossarium.gls("xgboost", link: false), com 0,00718.
O mesmo padrão aparece na similaridade dos conjuntos de erros: #glossarium.gls("decision_tree", link: false) e #glossarium.gls("xgboost", link: false) apresentam o menor Jaccard, 0,59778, enquanto #glossarium.gls("random_forest", link: false) e #glossarium.gls("xgboost", link: false) apresentam o maior, 0,74842.

Esses resultados indicam que os classificadores do #glossarium.gls("rosids", link: false) não produzem exatamente os mesmos erros, o que fornece um cenário mais propício à complementaridade entre os componentes do comitê.
A #glossarium.gls("decision_tree", link: false) apresenta as maiores diferenças em relação aos demais modelos, enquanto #glossarium.gls("random_forest", link: false) e #glossarium.gls("xgboost", link: false) possuem padrões de erro mais semelhantes.


== Comparação com GPT

#note_from_advisor(note: done_note)[
  Compare zero-shot, few-shot e, quando utilizado, embeddings + classificador com os mesmos baselines e nos mesmos exemplos de avaliação. Além das métricas preditivas, relate tempo por 100 amostras e custo estimado quando houver API. Discuta também saídas inválidas, sensibilidade ao prompt e outras limitações observadas. Para tarefas não classificatórias, adapte ou remova esta subseção conforme definido com o professor.
]

#note_from_advisor(note: done_note)[
  Apresente e discuta a comparação entre GPT/LLM e os métodos clássicos.
]

A comparação com o #glossarium.gls("llm") foi realizada considerando os protocolos #get_term("zero_shot") e #get_term("few_shot") sobre as mesmas bases de dados utilizadas na avaliação dos métodos de referência.
Para tornar os resultados comparáveis, ao mesmo tempo em que o experimento possa ser factível nas limitações de poder computacional, a avaliação do modelo de linguagem foi realizada sobre um subconjunto estratificado e determinístico de 2.000 instâncias do conjunto de teste exclusivo de cada base.

A fim de fazer uma comparação justa, a fase de teste para os algoritmos clássicos foi efetuada novamente, sendo fornecidas as mesmas 2000 instâncias selecionadas para o #glossarium.gls("llm").
A @tabela:gpt_resultados_gerais mostra as métricas para as classificações por meio do modelo de linguagem e suas comparações com os modelos clássicos.
Em relação a estes, todas as métricas foram expressivamente piores.

#describe_figure(
  [#figure(
    caption: [Desempenho do modelo de linguagem e dos algoritmos clássicos],
    format_table(
      table(
        columns: (auto, auto, auto, auto, auto, auto, auto, auto),
        table.header(
          [Base],
          [Método],
          [#get_term("accuracy", capitalize: true)],
          [#get_term("precision", capitalize: true)],
          [#get_term("recall", capitalize: true)],
          [#get_term("macro_f1")],
          [#get_term("mcc")],
          [#foreign_text[B. Accur.]],
        ),

        table.cell(rowspan: 5)[#glossarium.gls("genis", link: false)],
        [#get_term("zero_shot", capitalize: true)],
        [0,31550],
        strong[0,68153],
        [0,56070],
        [0,49126],
        [0,24113],
        [0,56070],

        [#get_term("few_shot", capitalize: true)],
        strong[0,56650],
        [0,58147],
        strong[0,82175],
        strong[0,59037],
        strong[0,45068],
        strong[0,82175],

        table.hline(stroke: 0.25pt),

        [Árvore de decisão],
        [1,00000],
        [1,00000],
        [1,00000],
        [1,00000],
        [1,00000],
        [1,00000],

        [Floresta aleatória],
        [1,00000],
        [1,00000],
        [1,00000],
        [1,00000],
        [1,00000],
        [1,00000],

        [XGBoost],
        [1,00000],
        [1,00000],
        [1,00000],
        [1,00000],
        [1,00000],
        [1,00000],

        table.hline(stroke: 0.5pt),

        table.cell(rowspan: 5)[#glossarium.gls("rosids", link: false)],
        [#get_term("zero_shot", capitalize: true)], [0,43700], [0,18993], [0,22740], [0,19311], [0,08680], [0,22740],

        [#get_term("few_shot", capitalize: true)],
        strong[0,61500],
        strong[0,54943],
        strong[0,57854],
        strong[0,52129],
        strong[0,54393],
        strong[0,57854],

        table.hline(stroke: 0.25pt),

        [Árvore de decisão],
        [0,97217],
        [0,94960],
        [0,94797],
        [0,94864],
        [0,95943],
        [0,94797],

        [Floresta aleatória],
        [0,97750],
        [0,96465],
        [0,96038],
        [0,96208],
        [0,96722],
        [0,96038],

        [XGBoost],
        [0,97750],
        [0,96208],
        [0,95790],
        [0,95947],
        [0,96722],
        [0,95790],
      ),
    ),
  ) <tabela:gpt_resultados_gerais>],
)

Avaliando o desempenho apenas entre os métodos de #glossarium.gls("llm"), resultados evidenciam uma melhora consistente do #get_term("few_shot") em relação ao #get_term("zero_shot") nas duas bases, embora com comportamentos distintos.

No #glossarium.gls("genis", link: false), a #get_term("accuracy") aumentou de 0,3155 para 0,5665 e o #get_term("macro_f1") de 0,4913 para 0,5904.
O maior ganho ocorreu no #get_term("recall"), que passou de 0,5607 para 0,8218, acompanhado, entretanto, por uma redução da #get_term("precision"), de 0,6815 para 0,5815.
Esse comportamento indica uma mudança no equilíbrio entre recuperação e precisão: com exemplos no prompt, o modelo passou a identificar uma parcela maior das instâncias relevantes, mas também produziu mais falsos positivos. Apesar dessa troca, o #get_term("mcc") aumentou de 0,2411 para 0,4507, indicando uma melhora geral na qualidade das classificações.

No #glossarium.gls("rosids", link: false), os ganhos proporcionados pelo #get_term("few_shot") foram ainda mais expressivos.
A #get_term("accuracy") passou de 0,4370 para 0,6150, o #get_term("macro_f1") de 0,1933 para 0,5213 e o #get_term("mcc") de 0,0868 para 0,5439.
Nesse caso, tanto a #get_term("precision") quanto o #get_term("recall") apresentaram aumentos relevantes, passando de 0,1899 para 0,5494 e de 0,2274 para 0,5785, respectivamente.
Portanto, diferentemente da #glossarium.gls("genis", link: false), a inclusão dos exemplos de referência melhorou simultaneamente a capacidade de identificar as classes e a precisão das decisões do modelo.

A comparação entre as bases também evidencia a sensibilidade do desempenho ao cenário de classificação.
No protocolo #get_term("zero_shot"), a #glossarium.gls("genis", link: false) apresentou #get_term("macro_f1") substancialmente superior ao observado na #glossarium.gls("rosids", link: false) (0,4913 contra 0,1933). Com a adoção do #get_term("few_shot"), essa diferença diminuiu, com resultados de 0,5904 e 0,5213, respectivamente.

Analisando as matrizes de confusão do #glossarium.gls("genis", link: false) e do #glossarium.gls("rosids", link: false) dispostos nos @quadro:llm_matriz_confusao_genis e @quadro:llm_matriz_confusao_rosids, respectivamente, constatamos que o modelo de linguagem tem muita dificuldade em distinguir o fluxo malicioso, sendo a classe benígna sempre superrepresentada.

#describe_figure(
  sticky: true,
  [#figure(
    caption: [Matrizes de confusão relativas do modelo de linguagem na base de dados #glossarium.gls-short("genis")],
    supplement: "Quadro",
    kind: "quadro",
    (
      table(
        columns: (auto, auto, 1fr, 1fr, 1fr, 1fr),
        align: end,

        table.cell(rowspan: 2, align: horizon)[Protocolo],
        table.cell(rowspan: 2, align: horizon)[#strong[Classe real]],
        table.cell(colspan: 4, align: center)[#strong[Classe predita]],

        [benign], [bruteforce], [dos], [recon],

        table.hline(stroke: 2pt),

        table.cell(rowspan: 4)[#get_term("zero_shot", capitalize: true)],
        [benign], [70,75], [0], [27,89], [1,36],
        [bruteforce], [45,45], [54,55], [0], [0],
        [dos], [75,69], [0,06], [22,32], [1,93],
        [recon], [22,00], [0], [1,33], [76,67],

        table.hline(stroke: 1.5pt),

        table.cell(rowspan: 4)[#get_term("few_shot", capitalize: true)],
        [benign], [83,67], [0,68], [0], [15,65],
        [bruteforce], [0], [100,00], [0], [0],
        [dos], [43,14], [6,86], [47,69], [2,31],
        [recon], [0], [0], [2,67], [97,33],
      )
    ),
  ) <quadro:llm_matriz_confusao_genis>],
)

#describe_figure(
  sticky: true,
  [#figure(
    caption: [Matrizes de confusão relativas do modelo de linguagem na base de dados #glossarium.gls-short("rosids")],
    supplement: "Quadro",
    kind: "quadro",
    (
      table(
        columns: (auto, auto, 1fr, 1fr, 1fr, 1fr, 1fr),
        align: end,

        table.cell(rowspan: 2, align: horizon)[Protocolo],
        table.cell(rowspan: 2, align: horizon)[#strong[Classe real]],
        table.cell(colspan: 5, align: center)[#strong[Classe predita]],

        [Benign], [DoS], [Subflood], [UnauthPub], [UnauthSub],

        table.hline(stroke: 2pt),

        table.cell(rowspan: 5)[#get_term("zero_shot", capitalize: true)],
        [Benign], [82,71], [0], [7,77], [0], [9,52],
        [DoS], [86,97], [0], [13,02], [0], [0],
        [Subflood], [61,99], [0], [25,79], [0], [12,22],
        [UnauthPub], [92,10], [0], [0], [0], [7,89],
        [UnauthSub], [81,82], [0], [12,99], [0], [5,19],

        table.hline(stroke: 1.5pt),

        table.cell(rowspan: 5)[#get_term("few_shot", capitalize: true)],
        [Benign], [34,46], [1,75], [19,15], [12,80], [31,84],
        [DoS], [0], [100,00], [0], [0], [0],
        [Subflood], [1,36], [1,13], [90,27], [2,71], [4,52],
        [UnauthPub], [23,68], [0], [12,28], [35,96], [28,07],
        [UnauthSub], [31,17], [0], [35,06], [5,19], [28,57],
      )
    ),
  ) <quadro:llm_matriz_confusao_rosids>],
)

Ainda assim, os dados reforçam a melhoria de qualidade do método #get_term("few_shot").
Por exemplo, a classe `bruteforce` do #glossarium.gls("genis", link: false) teve aumento de acerto de 54,55% para 100%; além de aumentar o acerto da classe `dos`, que era mais comumente confundida com `benign` do que corretamente identificada pelo #get_term("zero_shot").

Uma melhoria similar ocorreu para a classe `DoS` do #glossarium.gls("rosids", link: false), que teve erro total na abordagem #get_term("zero_shot"), e acerto total na #get_term("few_shot").
Nessa base, em geral, todas as classes foram expressivamente confundidas com a `Benign` na abordagem #get_term("zero_shot").
Contudo, ao mesmo passo em que elas tiveram acertos melhorados na classificação #get_term("few_shot"), a própria classe `Benign` perdeu o acerto de 82,71% para 34,46%.

Ainda, a qualidade menor do modelo de linguagem é acompanhada de um custo de tempo muito elevado.
Nas mesmas condições computacionais, um exeprimento que considera 2.000 amostras para cada base de dados levou horas para ser executado, como mostrado na @tabela:llm_tempos.
Ao passo em que os modelos clássicos levam alguns segundos para classificarem milhares de instâncias.

#describe_figure(
  [#figure(
    caption: [Tempo e custo do modelo de linguagem],
    format_table(
      table(
        columns: (auto, 1fr, 1fr, 1fr, 1fr, 1fr),

        table.header([Base], [Método], [Tempo total (min)], [Tempo / 100 amostras (s)], [Tokens totais], [Tokens / s]),

        table.cell(rowspan: 2)[#glossarium.gls("genis", link: false)],
        [#get_term("zero_shot", capitalize: true)],
        [96,73],
        [290,21],
        [4.312.875],
        [742,11],

        [#get_term("few_shot", capitalize: true)],
        [127,33],
        [381,99],
        [20.088.759],
        [2.629,52],

        table.hline(stroke: 0.5pt),

        table.cell(rowspan: 2)[#glossarium.gls("rosids", link: false)],
        [#get_term("zero_shot", capitalize: true)],
        [106,31],
        [318,92],
        [4.667.364],
        [731,76],

        [#get_term("few_shot", capitalize: true)],
        [155,94],
        [467,81],
        [26.143.275],
        [2.794,21],
      ),
    ),
  ) <tabela:llm_tempos>],
)

É necessário pontuar que o desempenho aparente de vazão de tokens no método #get_term("few_shot") é um artefato da capacidade de o modelo realizar cache do #foreign_text[system prompt].
As primeiras execuções dos prompts levaram cerca de 60 segundos para processar.
Contudo, dado que o prompt de sistema é imutável dentro de uma base de dados, as requisições logo passaram a demorar cerca de 3 segundos.

== Comparação entre os datasets

#note_from_advisor(note: done_note)[
  Como o trabalho exige pelo menos dois datasets, compare o comportamento dos métodos entre eles. Procure explicar se diferenças de tamanho, dimensionalidade, desbalanceamento, ruído, domínio ou dificuldade ajudam a entender as mudanças de desempenho.
]

#note_from_advisor(note: done_note)[
  Compare os resultados obtidos nas diferentes bases.
]

Os resultados obtidos nas duas bases de dados evidenciam diferenças importantes na dificuldade da tarefa de classificação. A #glossarium.gls("genis") contém 368.556 fluxos e 122 características preditoras, distribuídos em quatro classes, enquanto a #glossarium.gls("rosids") contém 136.681 fluxos, 83 características e cinco classes.

As distribuições também apresentam comportamentos distintos: na primeira, a classe `dos` concentra 80,22% das instâncias, ao passo em que, na segunda, a classe majoritária `Benign` representa 45,73% dos dados, seguida por `DoS` e `Subflood`, com 22,68% e 22,00%, respectivamente.

Além dessas diferenças quantitativas, os conjuntos representam contextos experimentais distintos. A #glossarium.gls("genis") foi construída para representar uma rede corporativa em um ambiente Airbus CyberRange, com atividades benignas e cenários sequenciais de ataque, enquanto a #glossarium.gls("rosids") foi coletada em um sistema robótico baseado em #glossarium.gls("ros"), no qual os cenários de intrusão foram executados separadamente sobre uma infraestrutura composta por diferentes dispositivos do sistema. Portanto, os resultados não devem ser interpretados apenas em função do tamanho das bases, mas também das características do ambiente e da forma como o tráfego de cada cenário foi produzido.

Essa diferença de contexto é acompanhada por uma diferença expressiva no desempenho dos modelos de referência. Na #glossarium.gls("genis"), os três classificadores apresentaram #get_term("macro_f1") entre 0,99987 e 1,00000, com #glossarium.gls("random_forest") e #glossarium.gls("xgboost") atingindo valor máximo em todas as métricas consideradas. Na #glossarium.gls("rosids"), por outro lado, os valores de #get_term("macro_f1") ficaram entre 0,94632 e 0,95513.

A diferença não é explicada apenas pela presença de uma classe adicional, uma vez que também se observa maior heterogeneidade no desempenho por classe em #glossarium.gls("rosids"). Enquanto DoS é identificada com #get_term("f1") próximo de 1 pelos três modelos, UnauthPub e principalmente UnauthSub apresentam desempenho inferior, indicando que determinadas categorias de tráfego são mais difíceis de distinguir.

Assim, #glossarium.gls("rosids") oferece um cenário no qual as limitações dos classificadores individuais são mais evidentes, enquanto os resultados da #glossarium.gls("genis") indicam uma separação quase completa entre as classes sob o protocolo adotado.

O desempenho praticamente perfeito observado na #glossarium.gls("genis"), entretanto, merece uma interpretação mais cautelosa. Embora os resultados demonstrem que as características utilizadas permitem separar as classes com elevada precisão no conjunto de teste fornecido, a própria forma de construção da base constitui uma possível explicação para a facilidade observada. Os dados foram coletados em um ambiente de simulação controlado, no qual atividades benignas e cenários de ataque são executados de forma planejada e sequencial @silva:2025:genis_network_intrusion.

Essa estrutura pode produzir padrões relativamente específicos aos experimentos realizados, fazendo com que parte da capacidade preditiva dos modelos esteja menos associada aos padrões simulados.
Essa hipótese não pode ser confirmada apenas pelos resultados deste trabalho, mas a ocorrência simultânea de desempenho perfeito nos três modelos torna razoável questionar a construção da base.

Essa preocupação é particularmente relevante porque os arquivos processados disponibilizados pelos autores continham, além das características utilizadas para classificação, outras colunas de metadados.
No processamento realizado neste trabalho, foram removidas as colunas identificadas como identificadores ou metadados e, especificamente na #glossarium.gls("genis"), também foram excluídas características previamente identificadas como potencialmente relacionadas diretamente ao cenário de simulação, como `destination_tcp_base`, `source_tcp_base` e `source_tos`.
Ainda assim, a possibilidade de alguma informação residual relacionada ao experimento ter permanecido entre as características utilizadas não pode ser completamente descartada sem uma auditoria específica de todas as colunas originais e de sua relação com os cenários de coleta.

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

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

        [Benign], [Precision], [0.99945 ± 0.00018], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        [Benign], [Recall], [0.99994 ± 0.00011], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        [Benign], [F1], [0.99969 ± 0.00014], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        [Bruteforce], [Precision], [1.00000 ± 0.00000], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        [Bruteforce], [Recall], [0.99963 ± 0.00016], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        [Bruteforce], [F1], [0.99982 ± 0.00008], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        [DoS], [Precision], [0.99999 ± 0.00001], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        [DoS], [Recall], [0.99997 ± 0.00002], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        [DoS], [F1], [0.99998 ± 0.00002], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        [Recon], [Precision], [1.00000 ± 0.00000], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        [Recon], [Recall], [1.00000 ± 0.00000], [1.00000 ± 0.00000], [1.00000 ± 0.00000],

        [Recon], [F1], [1.00000 ± 0.00000], [1.00000 ± 0.00000], [1.00000 ± 0.00000],
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

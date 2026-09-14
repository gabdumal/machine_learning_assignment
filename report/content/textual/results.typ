#import "../../components.typ": *


= Resultados e discussão <seção:resultados>

#note_from_advisor[
  Não se limite a apresentar tabelas. Compare os métodos, quantifique diferenças e interprete os resultados à luz das características dos datasets. Discuta casos em que um método funciona melhor ou pior, classes ou regiões difíceis, complementaridade entre modelos, efeito dos comitês, comportamento do GPT, custo computacional e limitações. Diferencie claramente observações suportadas pelos experimentos de hipóteses ou especulações.
]

== Resultados dos modelos de referência

#note_from_advisor[
  Apresente os resultados dos modelos clássicos de forma comparável. Sempre indique se os valores correspondem a uma única avaliação, a predições out-of-fold agregadas ou ao resumo de múltiplas execuções/repetições. Evite escolher apenas a melhor métrica para cada modelo.
]

#describe_figure(
  figure(
    caption: "Métricas que avaliam o resultado",
    format_table(
      table(
        columns: (1fr, auto, auto, auto, auto),

        [
          Modelo
        ],
        [
          Métrica 1
        ],

        [
          Métrica 2
        ],
        [
          Métrica 3
        ],

        [
          Tempo
        ],

        [
          Modelo A
        ],
        [
        ],

        [
        ],
        [
        ],

        [
        ],
      ),
    ),
  ),
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

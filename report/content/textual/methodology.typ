#import "../../components.typ": *


= Metodologia <seção:métodos>

#note_from_advisor[
  Esta seção deve permitir que outra pessoa reproduza o experimento. Descreva dados, preparação, modelos, comitês, abordagem com GPT/LLM quando aplicável, protocolo de avaliação, métricas, software e decisões de implementação. O trabalho exige dois datasets experimentais; datasets adicionais são opcionais. Para classificação, devem ser avaliados pelo menos três modelos clássicos adequados, além dos comitês e da comparação com GPT. Para regressão, séries temporais ou agrupamento, adapte os métodos e a etapa com GPT conforme o problema e, quando necessário, conforme orientação do professor.
]

== Bases de dados utilizadas

#note_from_advisor[
  Descreva os dois datasets usados nos experimentos. Informe origem, licença quando disponível, número de instâncias, número e tipo de atributos, classes ou variável-alvo, distribuição das classes, valores ausentes e outras características relevantes. Se houver grupos naturais (pacientes, indivíduos, animais, residências, gravações etc.), deixe isso explícito porque pode alterar o protocolo de validação.
]

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

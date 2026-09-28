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
  Esta seção deve fornecer o conhecimento necessário para compreender o problema e posicionar o estudo em relação à literatura. O levantamento bibliográfico pode ser sucinto, mas deve conter referências realmente relevantes para o tema. A descrição do trabalho prevê um estado da arte curto, com pelo menos 3--5 referências relevantes, além da apresentação de 2--3 exemplos de bases de dados e soluções típicas do domínio.
]
@Nids:pl são sistemas destinados a identificar atividades que possam representar violações da segurança de uma rede.
Entre as abordagens utilizadas para essa finalidade estão métodos baseados em assinaturas e métodos baseados na análise de padrões de tráfego.
A aplicação de técnicas de #glossarium.gls("machine_learning") permite construir modelos capazes de identificar ou classificar comportamentos a partir de características extraídas da comunicação em rede @buczak:2016:ml_for_cyber_security.

Uma forma de representar o tráfego para esse tipo de análise é por meio de #glossarium.gls("network_flow").
Um fluxo de rede reúne pacotes associados a uma mesma comunicação e pode ser representado por características agregadas, como duração, quantidade de pacotes, volume de dados e informações relacionadas aos protocolos.
A análise baseada em fluxos utiliza essas características para identificar comportamentos sem depender da inspeção do conteúdo dos pacotes @umer:2017:flow_based_detection.

Quando os dados possuem rótulos conhecidos, a detecção pode ser formulada como um problema de #glossarium.gls("supervised_learning").
Em uma tarefa de #glossarium.gls("multiclass_classification"), cada fluxo é associado a uma entre múltiplas classes definidas para o problema.

#cite_prose(<umer:2018:two_stage_flow_based_intrusion_detection>) propuseram uma arquitetura de duas etapas para detecção baseada em fluxos.
A primeira etapa utiliza uma versão aprimorada do `one-class SVM` para separar fluxos maliciosos do tráfego normal sem utilizar rótulos durante o treinamento.
A segunda, por sua vez, utiliza um #glossarium.gls("som") para agrupar os fluxos maliciosos de acordo com seus padrões de comportamento.
Dessa forma, a arquitetura separa a identificação de tráfego malicioso em classes de ataque @umer:2018:two_stage_flow_based_intrusion_detection.

Seus experimentos utilizaram características relacionadas à origem e ao destino da comunicação, portas, protocolo, quantidade de pacotes, quantidade de bytes e duração dos fluxos.
No conjunto de dados composto por tráfego normal, malware e ameaças persistentes avançadas, o `one-class SVM` identificou 94,28% dos fluxos normais utilizados no treinamento como parte do comportamento normal.
O #glossarium.gls("som") agrupou esses fluxos de acordo com os tipos de ataque presentes no conjunto @umer:2018:two_stage_flow_based_intrusion_detection.

A solução apresentada por #cite_prose(<umer:2018:two_stage_flow_based_intrusion_detection>) ilustra uma abordagem em que a análise do tráfego em nível de fluxo combina detecção e classificação em etapas distintas.
A separação dessas etapas permite utilizar métodos diferentes para identificar anomalias e organizar os fluxos associados a atividades maliciosas.

A utilização de dados rotulados é também central para a avaliação de métodos de detecção e classificação.
Foram selecionadas três bases de dados de simulação de fluxos de rede: o projeto #glossarium.gls("genis"), o projeto #glossarium.gls("rosids") e o conjunto de dados de #get_term("westermo").
As bases diferem quanto ao ambiente de coleta, aos ataques representados, às características extraídas e às estratégias utilizadas para atribuição dos rótulos.

== Bases de dados e benchmarks do domínio

#note_from_advisor[
  Apresente brevemente 2--3 bases de dados conhecidas ou representativas do problema, mesmo que nem todas sejam usadas nos experimentos. Para cada uma, destaque finalidade, tipo de dado, dimensão aproximada, classes/alvo e particularidades relevantes. Cite a fonte original da base sempre que possível.
]

#note_from_advisor(note: todo_note)[
  Descreva bases de dados ou benchmarks relevantes para o tema.
]


#describe_figure(
  figure(
    caption: "Bases de dados exploradas",
    format_table(
      table(
        columns: (auto, auto, auto, auto, auto, auto),

        [
          Base
        ],
        [
          Instâncias
        ],
        [
          Atributos
        ],
        [
          Alvo/classes
        ],
        [
          Distribuição
        ],
        [
          Observações
        ],

        [
          @genis
          #cite(<silva:2025:genis_network_intrusion>)
        ],
        [
          2.806.168
        ],
        [
          125
        ],
        [
          13
        ],
        [
          Distribuição
        ],
        [
          Observações
        ],

        [
          @rosids
          #cite(<degirmenci:2023:rosids23_network_intrusion>)
        ],
        [
          Instâncias
        ],
        [
          Atributos
        ],
        [
          Alvo/classes
        ],
        [
          Distribuição
        ],
        [
          Observações
        ],

        [
          #get_term("westermo")
          #cite(<strandberg:2023:westermo_network_traffic>)
        ],
        [
          Instâncias
        ],
        [
          Atributos
        ],
        [
          Alvo/classes
        ],
        [
          Distribuição
        ],
        [
          Observações
        ],
      ),
    ),
  ),
)

=== #glossarium.gls-short("genis")

A base de dados @genis foi desenvolvida pelo #foreign_text[Research Group on Intelligent Engineering and Computing for Advanced Innovation and Development] da Universidade Técnica de Porto @silva:2025:genis_network_intrusion.
Ela coleta as atividades de diferentes tipos de fluxos de ataques de rede realizados em simulação na plataforma Airbus CyberRange.

A simulação registrou 37.681.001 pacotes de rede organizados nos respectivos passos de ataque.
Eles formam 2.806.168 fluxos de rede, que estão classificados em granularidades hierárquicas, e separados por intervalos de tempo de 5, 10, 30 e 60 segundos.

Um fluxo é rotulado como benigno (0) ou como malicioso (1).
Estes últimos são categorizados como de força bruta, de DOS ou de RECON.
Aos fluxos ainda são atribuídas sub-categorias, conforme a tabela @tabela:classes_genis.

#describe_figure(
  source: [#cite_prose(<silva:2025:genis_network_intrusion>).],
  [#figure(
    caption: [Classes de fluxos de rede na base de dados @genis],
    format_table(
      table(
        columns: (1fr, 1fr, 1fr),
        align: start + top,

        [
          Rótulo
        ],
        [
          Categoria
        ],
        [
          Sub-categoria
        ],

        table.cell(rowspan: 3)[0],
        table.cell(rowspan: 3)[benign],
        [benign-admin],
        [benign-background],
        [benign-user],

        table.cell(rowspan: 10)[1],

        table.cell(rowspan: 3)[bruteforce],
        [bruteforce-ftp],
        [bruteforce-smb],
        [bruteforce-ssh],

        table.cell(rowspan: 5)[dos],
        [dos-hulk],
        [dos-icmp],
        [dos-pushack],
        [dos-slowloris],
        [dos-udp],

        table.cell(rowspan: 2)[recon],
        [recon-dns],
        [recon-nmap],
      ),
    ),
  )<tabela:classes_genis>],
)

== Métodos e trabalhos relacionados

#note_from_advisor[
  Discuta trabalhos anteriores que resolvem problemas semelhantes. Dê preferência a estudos recentes e/ou referências clássicas fundamentais. Compare métodos, dados, protocolos e resultados quando houver informação suficiente. O objetivo não é apenas listar artigos, mas mostrar quais abordagens são típicas, quais limitações permanecem e como o seu experimento se relaciona com a literatura. Exemplos de citação: \texttt{\textbackslash parencite\{chawla2002\}} ou \texttt{\textbackslash textcite\{breiman2001\}}. O arquivo \texttt{referencias.bib} inclui apenas entradas de demonstração, como \textcite{breiman2001} e \textcite{chawla2002}; substitua-as pelas referências efetivamente utilizadas no trabalho.
]

#note_from_advisor(note: todo_note)[
  Apresente e compare os principais trabalhos relacionados.
]

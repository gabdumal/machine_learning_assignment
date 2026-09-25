#import "../../components.typ": *


= Referencial teórico e trabalhos relacionados <seção:fundamentação>

#note_from_advisor[
  Esta seção deve fornecer o conhecimento necessário para compreender o problema e posicionar o estudo em relação à literatura. O levantamento bibliográfico pode ser sucinto, mas deve conter referências realmente relevantes para o tema. A descrição do trabalho prevê um estado da arte curto, com pelo menos 3--5 referências relevantes, além da apresentação de 2--3 exemplos de bases de dados e soluções típicas do domínio.
]

== Conceitos e definição do problema

#note_from_advisor[
  Defina os conceitos específicos do domínio e formalize a tarefa quando necessário. Explique o significado dos rótulos, variável-alvo, horizonte de previsão, grupos ou demais elementos do problema. Não repita conceitos gerais de aprendizado de máquina que não sejam necessários para compreender o estudo.
]

#note_from_advisor(note: todo_note)[
  Apresente aqui os conceitos necessários e a definição do problema.
]

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
          #get_term("genis")
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
          #get_term("rosids")
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

=== #get_term("genis", capitalize: true)

A base de dados #get_term("genis") (GECAD
Network Intrusion Scenarios) foi desenvolvida pelo #foreign_text[Research Group on Intelligent Engineering and Computing for Advanced Innovation and Development] da Universidade Técnica de Porto @silva:2025:genis_network_intrusion.
Ela coleta as atividades de diferentes tipos de fluxos de ataques de rede realizados em simulação na plataforma Airbus CyberRange.

A simulação registrou 37.681.001 pacotes de rede organizados nos respectivos passos de ataque.
Eles formam 2.806.168 fluxos de rede, que estão classificados em granularidades hierárquicas, e separados por intervalos de tempo de 5, 10, 30 e 60 segundos.

Um fluxo é rotulado como benigno (0) ou como malicioso (1).
Estes últimos são categorizados como de força bruta, de DOS ou de RECON.
Aos fluxos ainda são atribuídas sub-categorias, conforme a tabela @tabela:classes_genis.

#describe_figure(
  source: [#cite_prose(<silva:2025:genis_network_intrusion>).],
  [#figure(
    caption: [Classes de fluxos de rede na base de dados #get_term("genis")],
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

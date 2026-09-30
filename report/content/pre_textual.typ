// # Pre-textual elements. Elementos pré-textuais.
// NBR 6022:2018 5.1

#import "../data/data.typ": authors, subtitle, title
#import "../components.typ": *
#import "../packages.typ": (
  glossarium, quati-abnt.article.components.include_abstracts, quati-abnt.article.components.include_opening,
  quati-abnt.common.components.print_title,
)

// ## Abstract. Resumo.

// ### Abstract in main language. Resumo em língua principal.
#let abstract_in_main_language = {
  (
    keywords_title: "Palavras-chave",
    keywords: (
      "detecção de intrusões",
      "aprendizado de máquina",
      "classificação multiclasse",
      "comitês de classificadores",
      "modelos de linguagem",
    ),
    title: "Resumo",
    body: [
      #note_from_advisor(note: done_note)[
        Apresente, de forma autocontida e objetiva: (i) o problema investigado; (ii) o objetivo do estudo; (iii) os dados utilizados; (iv) os principais métodos avaliados; (v) o protocolo experimental; (vi) os principais resultados; e (vii) a conclusão central. Evite citações e detalhes excessivos. Como referência, um resumo entre aproximadamente 150 e 250 palavras costuma ser suficiente para este trabalho.
      ]
      Sistemas automatizados de detecção de intrusões precisam classificar grandes volumes de tráfego de rede com elevada precisão e baixo custo computacional. Este trabalho avalia métodos de aprendizado de máquina para a classificação multiclasse de fluxos de rede, comparando classificadores tradicionais, estratégias de comitê e abordagens baseadas em modelos de linguagem. Foram utilizadas as bases GENIS, representativa de uma rede corporativa em ambiente controlado, e ROSIDS, relacionada a um sistema robótico baseado em ROS. Foram avaliados árvore de decisão, floresta aleatória e XGBoost, além de comitês baseados em votação e de uma abordagem com modelo de linguagem nos regimes #get_term("zero_shot") e #get_term("few_shot"). Os classificadores tradicionais foram treinados e avaliados em três #get_term("seed", plural: true), com seleção de configurações realizada sobre os conjuntos de treinamento e validação. Os resultados mostraram desempenho praticamente perfeito na GENIS e valores de macro F1 entre 0,946 e 0,955 na ROSIDS. Na segunda base, o hard voting apresentou pequena melhoria em relação aos modelos individuais, associada à maior diversidade de erros. O #get_term("few_shot") melhorou substancialmente o desempenho do modelo de linguagem em relação ao #get_term("zero_shot"), mas permaneceu inferior aos classificadores tradicionais e apresentou custo computacional significativamente maior. Conclui-se que, no protocolo avaliado, os métodos tradicionais oferecem a combinação mais consistente entre desempenho e eficiência, embora os resultados da GENIS exijam cautela quanto à capacidade de generalização.
    ],
  )
}

// ## Lista de resumos.
// Include in this list all abstracts in the order they should appear.
// Inclua nessa lista todos os resumos da ordem em que eles devem aparecer.
#let abstracts = (
  abstract_in_main_language,
)


// ## Display. Exibição.

#include_opening(
  authors: authors,
  subtitle: subtitle,
  title: title,
)

#align(center)[
  2035003 #sym.dash.em Aprendizado de Máquina\
  UFJF / ICE / Departamento de Ciência da Computação / PPGCC
]


#note_from_advisor[
  Este arquivo é um roteiro de escrita e, ao mesmo tempo, um modelo de artigo. As caixas azuis descrevem o que se espera em cada parte. Elas devem ser ocultadas na versão final. O texto entre colchetes serve apenas como marcador e deve ser substituído. Não é obrigatório manter todas as subseções sugeridas quando elas não fizerem sentido para o problema escolhido, mas as cinco seções principais devem ser preservadas: Introdução; Referencial teórico e trabalhos relacionados; Metodologia; Resultados e discussão; Conclusões.
]


#include_abstracts(abstracts: abstracts)

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
      "modelo",
      "artigo",
      "ABNT",
      "Typst",
    ),
    title: "Resumo",
    body: [
      #note_from_advisor[
        Apresente, de forma autocontida e objetiva: (i) o problema investigado; (ii) o objetivo do estudo; (iii) os dados utilizados; (iv) os principais métodos avaliados; (v) o protocolo experimental; (vi) os principais resultados; e (vii) a conclusão central. Evite citações e detalhes excessivos. Como referência, um resumo entre aproximadamente 150 e 250 palavras costuma ser suficiente para este trabalho.
      ]
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

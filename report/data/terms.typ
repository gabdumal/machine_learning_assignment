// # Terms. Termos.

#import "../packages.typ": quati-abnt.common.components.foreign_text, quati-abnt.common.components.get_term_in_list


// ## Definition. Definição.
#let terms_entries = (
  (
    key: "link",
    short: foreign_text[link],
    short_capitalized: foreign_text[Link],
    plural: foreign_text[links],
    plural_capitalized: foreign_text[Links],
  ),
  (
    key: "script",
    short: foreign_text[script],
    plural: foreign_text[scripts],
  ),
  (
    key: "software",
    short: foreign_text[software],
  ),
  (
    key: "web",
    short: foreign_text[web],
  ),
  (
    key: "dataset",
    short: foreign_text[dataset],
    short_capitalized: foreign_text[Dataset],
    plural: foreign_text[datasets],
    plural_capitalized: foreign_text[Datasets],
  ),
  (
    key: "benchmark",
    short: foreign_text[benchmark],
    short_capitalized: foreign_text[Benchmark],
    plural: foreign_text[benchmarks],
    plural_capitalized: foreign_text[Benchmarks],
  ),
  (
    key: "baseline",
    short: foreign_text[baseline],
    short_capitalized: foreign_text[Baseline],
    plural: foreign_text[baselines],
    plural_capitalized: foreign_text[Baselines],
  ),
  (
    key: "pipeline",
    short: foreign_text[pipeline],
    short_capitalized: foreign_text[Pipeline],
    plural: foreign_text[pipelines],
    plural_capitalized: foreign_text[Pipelines],
  ),
  (
    key: "prompt",
    short: foreign_text[prompt],
    short_capitalized: foreign_text[Prompt],
    plural: foreign_text[prompts],
    plural_capitalized: foreign_text[Prompts],
  ),
  (
    key: "zero_shot",
    short: foreign_text[zero-shot],
    short_capitalized: foreign_text[Zero-shot],
  ),
  (
    key: "few_shot",
    short: foreign_text[few-shot],
    short_capitalized: foreign_text[Few-shot],
  ),
  (
    key: "embedding",
    short: foreign_text[embedding],
    short_capitalized: foreign_text[Embedding],
    plural: foreign_text[embeddings],
    plural_capitalized: foreign_text[Embeddings],
  ),
  (
    key: "hard_voting",
    short: foreign_text[hard voting],
    short_capitalized: foreign_text[Hard voting],
  ),
  (
    key: "soft_voting",
    short: foreign_text[soft voting],
    short_capitalized: foreign_text[Soft voting],
  ),
  (
    key: "weighted_voting",
    short: foreign_text[weighted voting],
    short_capitalized: foreign_text[Weighted voting],
  ),
  (
    key: "gradient_boosting",
    short: foreign_text[gradient boosting],
    short_capitalized: foreign_text[Gradient boosting],
  ),
  (
    key: "out_of_fold",
    short: foreign_text[out-of-fold],
    short_capitalized: foreign_text[Out-of-fold],
  ),
  (
    key: "oversampling",
    short: foreign_text[oversampling],
  ),
  (
    key: "undersampling",
    short: foreign_text[undersampling],
  ),
  (
    key: "one_hot",
    short: foreign_text[one-hot],
    short_capitalized: foreign_text[One-hot],
  ),
  (
    key: "westermo",
    short: [Westermo],
  ),
  (
    key: "dos",
    short: "DoS",
  ),
  (
    key: "recon",
    short: "Recon",
  ),
  (
    key: "benign",
    short: "Benign",
  ),
  (
    key: "bruteforce",
    short: "Bruteforce",
  ),
  (
    key: "seed",
    short: foreign_text[seed],
  ),
)


// ## Access. Acesso.
#let get_term = (
  capitalize: false,
  field: "short",
  plural: false,
  term_key,
) => {
  get_term_in_list(
    capitalize: capitalize,
    field: field,
    plural: plural,
    terms_entries: terms_entries,
    term_key,
  )
}

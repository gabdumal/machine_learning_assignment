// # Components. Componentes.

#import "./data/terms.typ": get_term
#import "./packages.typ": (
  glossarium, quati-abnt.article.components.print_people, quati-abnt.article.components.print_person,
  quati-abnt.bibliography.cite_prose, quati-abnt.common.components.describe_figure,
  quati-abnt.common.components.equation, quati-abnt.common.components.foreign_text,
  quati-abnt.common.components.format_table, quati-abnt.common.components.source_for_content_created_by_authors,
  quati-abnt.note.closed_discussion_note, quati-abnt.note.create_status_note, quati-abnt.note.done_note,
  quati-abnt.note.editor_note, quati-abnt.note.open_discussion_note, quati-abnt.note.progress_note,
  quati-abnt.note.todo_note,
)


// ## Editor notes. Notas de editor.

#let note_from_advisor = (
  note: editor_note,
  it,
) => {
  let color = oklch(85%, 0.097, 19.33deg)
  note(
    prefixes: (
      (
        body: "Orientação",
        fill: color,
        stroke: color.saturate(25%),
      ),
    ),
    it,
  )
}

#let note_from_gabriel = (
  note: editor_note,
  it,
) => {
  let color = oklch(80.43%, 0.1, 278.25deg)
  note(
    prefixes: (
      (
        fill: color,
        body: "Gabriel",
        stroke: color.saturate(25%),
      ),
    ),
    it,
  )
}

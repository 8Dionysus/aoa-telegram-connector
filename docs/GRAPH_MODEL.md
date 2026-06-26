# Graph Model

The graph is message-centered.

Nodes:

- conversation
- message
- author
- entity

Edges:

- conversation contains message
- message authored by author
- message replies to message
- message edits prior version
- message deleted/tombstoned
- message pinned/contextualizes conversation
- message mentions entity
- message warns about context
- message supersedes prior guidance

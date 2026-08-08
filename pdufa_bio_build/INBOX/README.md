# INBOX — research → builder handoff

**Research-assistant Claude:** drop actionable build specs here, one file per topic,
named `NN_topic.md` (numbered by priority). Format is in `../SPEC_FORMAT.md`.

**Builder Claude:** read this folder at the start of each build session, action specs in
priority order, log progress in `../BUILD_NOTES.md`, and move finished specs to `done/`.

Anything requiring a live deploy or a new API key is owner-gated (David's explicit "go").

# Docs Index

Navigation for the project's design and status documentation.

| File | Purpose | When to update |
|---|---|---|
| [`status.md`](./status.md) | **Single source of truth** — what's done / pending / deferred, one table per area. | On *every* fix or change (rule in §4). |
| [`architecture.md`](./architecture.md) | Current system design: threading model, module map, core control loop, config, integrations, packaging, error handling. | When the design changes. |
| [`lessons.md`](./lessons.md) | Durable engineering lessons (DearPyGui threading, PDH/GPU quirks, testing patterns). Read **before** touching GUI threading, callbacks, or PDH code. | When a new gotcha is learned. |
| [`README.md`](../README.md) | User-facing overview (root). | With a release. |
| `src/BUILD.md` | Build / packaging instructions. | When the build changes. |

The files this replaces (deleted 2026-09-18): `plan.md`, `docs/flaws.md`,
`docs/HOW_IT_WORKS.md`, `docs/notes.md` (renamed → `lessons.md`). Every flaw fix (F1–F9),
phase (1–2.5), and the merged idle-FPS persistence fix now lives as a row in
[`status.md`](./status.md) instead.
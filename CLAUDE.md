## Agent skills

### Issue tracker

Issues live in GitHub Issues on `EPF-MDE/OceENS` (always pass `-R EPF-MDE/OceENS` to `gh`). See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

- Package boundaries are machine-checked: read `src/oceens/README.md` before adding a package, or importing across one.

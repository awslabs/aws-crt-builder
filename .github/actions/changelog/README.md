# changelog action

Automated changelog with a **two-branch model**:

- `main` carries source code and the fragment JSON files
  (`.changes/preview/<PR>.json`) authors add with their PR. No bot
  commits ever land on `main`.
- `docs` carries `.changes/` (the released state) and the rendered
  `CHANGELOG.md`. Every merge to `main` produces one bot commit on
  `docs` that syncs the new fragment(s) and re-renders `CHANGELOG.md`.

Fragments are the human-editable source of truth. `CHANGELOG.md` is
derived and always regenerated end-to-end from the fragments.

## Modes

| Mode              | Trigger                | What it does                                                                       |
|-------------------|------------------------|------------------------------------------------------------------------------------|
| `check`           | PR CI                  | Fail the PR if `.changes/preview/<PR>.json` is missing or invalid.                 |
| `validate`        | ad-hoc                 | Validate every fragment under `.changes/preview/`.                                 |
| `render`          | on `docs`, after merge | Regenerate `CHANGELOG.md` from `preview/` + `latest/`.                             |
| `rollup`          | on `docs`, on release  | Patch: accrete into `latest/`. Minor/major: freeze `latest/` → `<M>.<N>.x/`.       |
| `revert`          | revert PR opens        | Write a revert fragment; the original stays. Both entries appear in the log.       |
| `freeze-snapshot` | recovery only          | Re-render a frozen line's `CHANGELOG.md` if it went missing.                       |
| `list`            | ad-hoc                 | Print preview + latest + frozen lines for debugging.                               |

The docs-branch workflow serializes on a single concurrency group so
concurrent merges never race on `CHANGELOG.md`:

```yaml
concurrency:
  group: changelog-docs
  cancel-in-progress: false
```

## Directory layout (on the docs branch)

```
.changes/
├── preview/                        in-flight fragments awaiting the next release
├── latest/                         active minor line
│   ├── <version>/                  per-patch release
│   │   ├── _meta.json              { version, date, highlights }
│   │   └── <pr>.json               fragments
│   └── …
├── <M>.<N>.x/                      frozen previous minor line
│   ├── <M>.<N>.<P>/                { _meta.json, *.json }
│   └── CHANGELOG.md                frozen snapshot; never edited again
└── …
CHANGELOG.md                        root render: [Preview] + current minor line
```

On the `main` branch the only changelog artefact is
`.changes/preview/<PR>.json` for each unshipped PR. `CHANGELOG.md`,
`latest/`, and frozen `<M>.<N>.x/` directories live only on `docs`.

Root `CHANGELOG.md` shows `[Preview]` + every patch inside `latest/`,
newest first. Frozen minor lines are intentionally excluded from the
root file — each `.changes/<M>.<N>.x/CHANGELOG.md` is the canonical,
immutable record for that line.

Directory sort caveat: filesystem lex sort orders `0.10.x/` before
`0.2.x/`. This does not affect any customer-facing surface — renderers
sort semver correctly. Only `ls .changes/` looks wrong to maintainers.

## Contributor flow

1. Open a PR against `main`.
2. Locally, run the helper — it prompts and writes the fragment:

   ```
   .github/actions/changelog/scripts/new-change
   ```

3. Commit the generated `.changes/preview/<PR>.json` yourself and push
   to your PR branch. CI runs `check` and fails if the fragment is
   missing or invalid. Apply the `skip-changelog` label only for
   CI-only / pure-infra PRs.

You never touch `CHANGELOG.md` or the `docs` branch.

## What happens after merge

The `changelog-render` workflow fires on merge to `main`:

1. Checks out `docs` (creates it from `main` on first run).
2. Cherry-picks the merge commit onto `docs` (with `-Xno-renames` so
   post-rollup path changes don't confuse git).
3. If the merge added or modified any `.changes/preview/*.json`, runs
   `render` and folds the `CHANGELOG.md` update into the same commit
   (`git commit --amend`).
4. Pushes `docs`.

Result: one commit on `docs` per merge on `main`, with the original PR
title as the subject. `main` is never touched by the bot.

## What happens on release

`changelog-rollup` runs on the `docs` branch:

- **Patch bump**: fragments in `preview/` move into
  `latest/<version>/`, root `CHANGELOG.md` is regenerated with a new
  dated section under `[Preview]`.
- **Minor / major bump**: `latest/` is renamed to `<M>.<N>.x/`, a
  frozen `CHANGELOG.md` snapshot is written inside it, and a fresh
  `latest/<version>/` opens with the current preview fragments.

The `preview` section becomes the versioned section — no ceremony, no
separate promotion step.

## PR conventions

The seed helper reads Conventional-Commit-style PR titles:

```
<type>: <customer-facing summary>
  type ∈ { feat | fix | doc | chore | revert }
```

Titles without a recognised prefix are treated as `chore`.

## Local testing

```
python3 -m pip install --user pytest
python3 -m pytest .github/actions/changelog/tests -v
```

Ad-hoc CLI (operates on the current working tree):

```
python3 .github/actions/changelog/scripts/changelog.py seed \
  --pr 843 --title "feat: Add SSO sign-in." --url https://x/pr/843
python3 .github/actions/changelog/scripts/changelog.py render
python3 .github/actions/changelog/scripts/changelog.py rollup \
  --version 0.29.0 --date 2026-08-19 --bump minor --highlights "SSO sign-in"
python3 .github/actions/changelog/scripts/changelog.py list
```

## Example workflows

`examples/changelog-check.yml`, `examples/changelog-render.yml`,
`examples/changelog-rollup.yml`. Copy into a consumer repo's
`.github/workflows/`.

## Reverts

Revert PRs write a new fragment referencing both PRs; the original
fragment is never deleted. Both entries appear in the changelog — the
original change and its revert — so history is truthful.

## Operational notes

- **Signed-commits repos:** the bot identity used by the render and
  rollup workflows must have a signing key configured, otherwise
  pushes to `docs` will be rejected.
- **Branch protection:** protect `docs` so the bot can only touch
  `.changes/**` and `CHANGELOG.md`. Everything else on that branch is
  a mistake.
- **Bootstrap:** on first run the workflow creates `docs` from `main`.
  If your repo has non-changelog content that should not appear on
  `docs`, pre-create `docs` as an orphan branch with just the two
  paths above before enabling the workflow.

## Fragment schema

```json
{
  "pr": 843,
  "type": "feat",
  "summary": "Add SSO sign-in for enterprise accounts.",
  "url": "https://github.com/awslabs/aws-c-io/pull/843",
  "notes": ""
}
```

- `type`: `feat | fix | doc | chore | revert`
- `notes`: optional free-form multi-line addendum, indented under the entry on render

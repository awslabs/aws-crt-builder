# changelog action

Automated changelog with a **two-branch model**:

- `main` carries source code, the fragment JSON files
  (`.changes/preview/<PR>.json`) authors add with their PR, and the
  released state (`CHANGELOG.md`, `latest/`, frozen `<M>.<N>.x/`).
  Between releases no bot commits land on `main`; at release time the
  rollup rides along in the existing `chore(release):` commit that
  bumps the version file.
- `docs` mirrors `main` and carries the same `CHANGELOG.md` *plus* a
  `[Preview]` block for unshipped work. Every merge to `main` produces
  one bot commit on `docs` that replays the change and re-renders
  `CHANGELOG.md`.

The `[Preview]` block is the only difference between the two
`CHANGELOG.md` files: `docs` has it, `main` does not.

Fragments are the human-editable source of truth. `CHANGELOG.md` is
derived and always regenerated end-to-end from the fragments.

## Modes

The table lists every `changelog.py` subcommand. Only `check`, `validate`,
`render`, `revert` and `list` are reachable through `action.yml`'s `mode`
input; `seed`, `rollup` and `freeze-snapshot` are CLI-only and are invoked as
`python3 changelog.py <cmd>` (see "What happens on release" and "Local
testing"). Passing one of those three as `mode` exits 2.

| Mode              | Trigger                | What it does                                                                       |
|-------------------|------------------------|------------------------------------------------------------------------------------|
| `check`           | PR CI (via the action) | Fail the PR if the title lacks a `<type>:` prefix, or the fragment is missing/invalid. |
| `validate`        | ad-hoc                 | Validate every fragment under `.changes/preview/`.                                 |
| `render`          | on `docs`, after merge | Regenerate `CHANGELOG.md` from `preview/` + `latest/`; `--no-preview` for `main`.   |
| `rollup`          | on `main`, on release (CLI only) | Patch: accrete into `latest/`. Minor/major: freeze `latest/` → `<M>.<N>.x/`.       |
| `revert`          | revert PR opens        | Write a revert fragment; the original stays. Both entries appear in the log.       |
| `freeze-snapshot` | recovery only (CLI only) | Re-render a frozen line's `CHANGELOG.md` if it went missing.                       |
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

This layout is mirrored on both branches. Between releases only
`.changes/preview/<PR>.json` changes on `main`; the release commit is
what moves fragments into `latest/<version>/` and writes `CHANGELOG.md`
there.

Root `CHANGELOG.md` shows `[Preview]` + every patch inside `latest/`,
newest first. Frozen minor lines are intentionally excluded from the
root file — each `.changes/<M>.<N>.x/CHANGELOG.md` is the canonical,
immutable record for that line.

Directory sort caveat: filesystem lex sort orders `0.10.x/` before
`0.2.x/`. This does not affect any customer-facing surface — renderers
sort semver correctly. Only `ls .changes/` looks wrong to maintainers.

## Contributor flow

1. Open a PR against `main`.
2. Create `.changes/preview/<PR>.json` on your PR branch. The JSON is
   five fields — copy the template from the PR body, or generate it:

   ```
   python3 <path-to>/changelog.py seed \
     --pr <N> --title "<PR title>" --url "<PR URL>"
   # → JSON on stdout; paste into .changes/preview/<N>.json
   ```

3. Commit and push. CI runs `check` and fails if the fragment is
   missing or invalid. Apply the `skip-changelog` label only for
   CI-only / pure-infra PRs.

You never touch `CHANGELOG.md` or the `docs` branch.

## What happens after merge

The `changelog-render` workflow fires on merge to `main`:

1. Checks out `docs` (creates it from `main` on first run).
2. Cherry-picks the merge commit onto `docs` (with `-Xno-renames` so
   post-rollup path changes don't confuse git).
3. Runs `render` and folds any `CHANGELOG.md` change into the same
   commit (`git commit --amend`). The render is unconditional — cheaper
   than working out whether the commit touched fragments, and it
   self-heals drift. A no-op render amends nothing.
4. Pushes `docs`.

A cherry-pick conflict confined to `CHANGELOG.md` is auto-resolved by
taking the incoming side, because that file is fully derived and step 3
rewrites it regardless. This is the expected case when replaying a
release commit, whose `CHANGELOG.md` lacks the `[Preview]` block that
`docs` has. A conflict in any other path stops the job.

Result: one commit on `docs` per merge on `main`, with the original PR
title as the subject. Between releases `main` is untouched by the bot.

## What happens on release

There is no rollup workflow. `cut-release.sh` in the `auto-release`
action runs `rollup` on `main` between writing the version file and
committing, so `VERSION` and `CHANGELOG.md` land in one
`chore(release):` commit and can never disagree about what shipped.

- **Patch bump**: fragments in `preview/` move into
  `latest/<version>/` and root `CHANGELOG.md` gains a dated section.
  `latest/` stays `latest/`; nothing is frozen.
- **Minor / major bump**: `latest/` is renamed to `<M>.<N>.x/`, a
  frozen `CHANGELOG.md` snapshot is written inside it, and a fresh
  `latest/<version>/` opens with the current preview fragments.

The `preview` fragments become the versioned section — no ceremony, no
separate promotion step.

Repos without a `.changes/` directory skip the step entirely, so the
release action stays safe to share. A release with no fragments is
allowed: the version bump proceeds on its own.

## PR conventions

PR titles must be Conventional-Commit-style:

```
<type>: <customer-facing summary>
  type ∈ { feat | fix | doc | chore | revert }
```

An optional scope is allowed (`fix(io): Handle EINTR.`), and the type is
matched case-insensitively. This is **enforced** — `check` fails the PR
if the title has no recognised prefix, because the type decides which
section the entry lands in.

The title check runs on every PR, including infra-only ones that need no
fragment: the title lands in git history either way. Only the
`skip-changelog` label bypasses it, since that skips the whole job.

Two things to wire up in a consumer repo:

- Include `edited` in the workflow's `pull_request` types, otherwise
  retitling a PR to fix a failure will not re-run the check.
- Pass the title through the action's `title` input, never by
  interpolating `${{ github.event.pull_request.title }}` into a `run:`
  block — a crafted title would be shell injection. The action takes it
  as an env var for this reason.

`seed` is more forgiving than `check`: it falls back to `chore` for an
unrecognised prefix, so it stays usable for local experimentation.

## Local testing

```
python3 -m pip install --user pytest
python3 -m pytest .github/actions/changelog/tests -v
```

Ad-hoc CLI (operates on the current working tree):

```
python3 .github/actions/changelog/scripts/changelog.py seed \
  --pr 843 --title "feat: Add SSO sign-in." --url https://x/pr/843
python3 .github/actions/changelog/scripts/changelog.py render              # docs shape
python3 .github/actions/changelog/scripts/changelog.py render --no-preview # main shape
python3 .github/actions/changelog/scripts/changelog.py rollup \
  --version 0.29.0 --date 2026-08-19 --bump minor --highlights "SSO sign-in"
python3 .github/actions/changelog/scripts/changelog.py list
```

## Where each half runs

The **PR-time `check`** is a job in the `Pre-merge checks` reusable
workflow (`.github/workflows/pre-merge-checks.yml`), which a consumer
already calls for the ABI check. Enable it there with
`changelog-enabled: true`; there is no separate per-repo changelog
workflow to copy. That job resolves the fragment through the Contents
API at the PR head SHA rather than checking out PR code, and it treats
any API error as "fragment required" rather than waiving the
requirement.

The **`render` half** is `examples/changelog-render.yml`, still an
example to copy: it needs raw git access to the `docs` branch, so it
runs inline and checks this repo out to `.crt-builder/` to reach
`changelog.py`. Pin that `ref:` to a tag or SHA in production.

There is no rollup workflow — see "What happens on release".

## Reverts

Revert PRs write a new fragment referencing both PRs; the original
fragment is never deleted. Both entries appear in the changelog — the
original change and its revert — so history is truthful.

## Operational notes

- **Consumer-repo docs:** each adopting repo should carry a
  `.changes/README.md` describing this layout for contributors
  (`awslabs/aws-c-common` has one). That file is the reference for
  directory names.
- **Signed-commits repos:** the bot identity used by the render
  workflow and by `cut-release.sh` must have a signing key configured,
  otherwise its pushes will be rejected.
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

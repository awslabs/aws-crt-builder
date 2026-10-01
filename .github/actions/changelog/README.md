# changelog

Fragment-based changelog. A pull request adds one JSON fragment; a release renders the fragments into `CHANGELOG.md` and deletes them. The rendered file is the record — nothing regenerates it, so a published entry cannot change under a reader.

## Modes

| mode | who runs it | what it does |
|---|---|---|
| `check` | pull request CI | assert the title convention and the fragment agree |
| `seed` | pull request CI | write the template offered to the author |
| `render` | every merge, on the docs branch | refresh the unreleased region |
| `rollup` | the release job | insert this release's section and drop the fragments |

It holds no token and needs no network.

## Wiring it up

Nothing but a trigger belongs in a consumer repository. Three reusable workflows in this repo hold the wiring — `changelog-check.yml`, `changelog-render.yml` and `changelog-rollup.yml` — so a fix to any of it reaches every repo at once instead of being pasted into each.

```yaml
name: Changelog Render
on:
  push:
    branches: [main]
jobs:
  render:
    uses: awslabs/aws-crt-builder/.github/workflows/changelog-render.yml@main
```

A repo passes `with:` only where it differs from the defaults, `main` and `docs`. Each workflow checks this repo out to reach the action, at the ref given by `builder-ref` — a called workflow cannot discover its own ref, since `github.job_workflow_sha` is empty inside one and `workflow_ref` describes the caller. A repo pinning the workflow to anything other than `main` should pin `builder-ref` to match.

The render and rollup workflows share `changelog-replay.sh`, which mirrors the release branch onto the docs branch. It replays whatever is missing rather than what the push event named: one push can carry several commits, and a concurrency group holds only one pending run, so a cancelled run costs nothing and a re-run is a no-op. `changelog-replay-test.sh` covers both against a scratch repository.

## The rules a pull request must follow

- The title is `<type>: <summary>`, where type is one of `feat | fix | chore | revert`. An optional scope is fine: `fix(io): Handle EINTR.` The Revert button's `Revert "<original title>"` is accepted as-is.
- A `feat`, `fix` or `revert` needs exactly one fragment, at exactly `.changes/preview/<PR>.json`. A fragment named for another pull request would render under that number; one at another path renders nowhere.
- A `chore` needs no fragment: it renders nowhere, so an entry would be invisible. A CI-only or pure-infra change is a `chore`, so nothing waives the check — the type already exempts it.
- A bot author waives both the title convention and the fragment.

Forgetting is fine: the check writes a ready-to-paste template, with the type and summary already derived from the title, into the run's summary — and comments it on the pull request when it has a token that can write. A pull request raised from a fork does not get one, however the workflow asks, so the summary is the guarantee and the comment is the courtesy.

## Fragment schema

```json
{
  "pr": 843,
  "type": "feat",
  "summary": "Add SSO sign-in for enterprise accounts.",
  "notes": ""
}
```

The schema is closed: an unexpected field is an error, so a misspelling is caught rather than ignored, and `impact` cannot be set by the pull request that would benefit from it. `pr` must match the filename and is the only identifier an entry has — its link is derived from it, relative to the repo root, so no repo name is stored and nothing can disagree.

`notes` is optional multi-line text, rendered as its own entry under Notes — except on a `revert`, where it is required, because saying why is the only reason a revert gets an entry.

## The file

```
# Changelog

<!-- changelog:unreleased -->
…the region: a link on the release branch, the unreleased list on the docs branch…
<!-- /changelog:unreleased -->

## [1.1.1] — 2026-09-14
…
## [1.1.0] — 2026-09-10
…

## Earlier releases

- [1.0.x](.changes/1.0.x.md)
```

Only one minor version line is ever in this file. 1.0.2 is not here: releasing 1.1.0 closed the 1.0.x line and moved it to the archive linked at the bottom.

Three edits are ever made. `render` replaces the region, and only on the docs branch, where it is derived from `preview/` on every merge. `rollup` inserts one section directly below the region, so a line's releases accumulate newest-first and older ones are never rewritten. And when a release opens a new minor line, `rollup` moves the closed line's sections into `.changes/<M>.<N>.x.md` and links it at the bottom — so the root carries only the minor version line being released into.

Archiving is a move, not a re-render: the sections are the same text, with one more `..` in each link because the archive sits a directory deeper. The list of archived lines is rebuilt from the files present, so an archive written by hand at adoption is picked up without being registered anywhere.

Sections within a release render in a fixed order and only when non-empty: **Possible Breaking Changes**, Features, Fixes, Reverts, Notes. A pull request carrying the `minor` label renders under Possible Breaking Changes instead of its own type section — taking that release may require a consumer to change something. The label settles that, not the ABI check: the check proposes a verdict and a maintainer can override it, and the release reads the label. The caller passes those numbers as `minor-prs`; nothing about the label is stored in a fragment.

The release branch's region is a link to the docs branch's file rather than the unreleased list itself, because only a release rewrites that file and a list of unreleased changes would sit permanently stale there.

## Releasing

`rollup` renders whatever is in `preview/`, inserts it, and deletes the fragments. Consequences worth knowing:

- **Re-running it is a no-op.** The fragments are gone, so there is nothing left to insert. A release job that fails after this step — on the tag, or on the GitHub release — can be retried.
- **A release with nothing customer-facing gets no section.** Its fragments are still deleted; a header with nothing under it reads as a broken file.
- **An invalid fragment stops the release**, because releasing would delete it unrendered and the entry would be lost rather than merely late.
- **A minor bump archives the outgoing line**, and a patch does not.
- **There is no version guard.** The version comes from the release job, and a mistake in the rendered file is corrected by a chore — it is markdown, not a database.

## Adoption

Whatever is already in `CHANGELOG.md` stays there. The first release inserts its section above the existing content and adds the region above that.

A repo adopting this mid-life should shape its history the way the tool would have: the closed lines as `.changes/<M>.<N>.x.md`, and the root holding only the current minor version line. From then on the automation continues from that shape.

## Layout

```
scripts/fragments.py    the fragment: schema, validation, reading, seeding
scripts/render.py       fragments to markdown, and the three edits to the file
scripts/release.py      cutting a release
scripts/check.py        the CI gate
scripts/changelog.py    the CLI; the only entry point
tests/                  one file per module, fixtures in tests/helpers.py
```

Imports only ever point down that list — `render` may use `fragments`, never the other way, and nothing imports `changelog`. `python3 changelog.py` resolves its siblings because the script's own directory is first on `sys.path`, so the directory can be copied anywhere and run with no packaging.

## Local testing

```
python3 -m pytest .github/actions/changelog/tests -q
```

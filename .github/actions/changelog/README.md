# Changelog

Fragment-based changelog. A pull request adds one JSON fragment; a release renders the fragments into `CHANGELOG.md` and deletes them. The rendered file is the record — nothing regenerates it, so a published entry cannot change under a reader. Unreleased changes exist only as fragments in `.changes/preview/`.

## Modes

| mode | who runs it | what it does |
|---|---|---|
| `check` | pull request CI | assert the title convention and the fragment agree |
| `seed` | pull request CI | write the template offered to the author |
| `rollup` | the release job | insert this release's section and drop the fragments |

It holds no token and needs no network.

## Wiring it up

`check` and `rollup` are steps in a job a consumer already has — a pre-merge check and a release — so they are calls to this action:

```yaml
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}
          fetch-depth: 0
      - uses: awslabs/aws-crt-builder/.github/actions/changelog@main
        with:
          mode: check
```

The `ref` matters under `pull_request_target`, where a plain checkout is the base branch and the fragment the check reads is not on disk.

That is the whole call. The pull request number, title, author and changed paths come from the event, and the step fails when the check does. Granting the job `pull-requests: write` additionally comments the template; without it the template still lands in the run summary, which is also what happens for a pull request from a fork, since those get a read-only token however the job asks.

A release calls the same action with `mode: rollup`, `version` and `date`, then commits `CHANGELOG.md` and `.changes/` with whatever it already uses to commit the version bump.

## The rules a pull request must follow

- The title is `<type>: <summary>`, where type is one of `feat | fix | change | chore | revert`. An optional scope is fine: `fix(io): Handle EINTR.` So is a `!` before the colon: `feat!: Drop the old API.` The Revert button's `Revert "<original title>"` is accepted as-is, and a revert of a revert is exempt like a `chore`.
- `change` is a behavior change that is neither a feature nor a fix, such as a new default part size.
- A `feat`, `fix`, `change` or `revert` needs exactly one fragment, at exactly `.changes/preview/<PR>.json`. A fragment named for another pull request would render under that number; one at another path renders nowhere.
- A `chore` needs no fragment and must not touch `.changes/`: it renders nowhere, so an entry would be invisible. A change a customer can see is not a `chore`.
- A bot author waives both the title convention and the fragment.
- A stacked pull request retargeted to the release branch after the one below it was squash-merged still carries that one's fragment, so it fails as a stray fragment until it is rebased onto the release branch.

Forgetting is fine: the check writes a ready-to-paste template, with the type and summary already derived from the title, into the run's summary — and comments it on the pull request when it has a token that can write.

## Fragment schema

```json
{
  "pr": 843,
  "type": "feat",
  "summary": "Add SSO sign-in for enterprise accounts."
}
```

The schema is closed: an unexpected field is an error, so a misspelling is caught rather than ignored. `pr` must match the filename and identifies the fragment; it is never rendered, so an entry links to nothing.

## The file

```
# Changelog

## [1.1.1] — 2026-09-14
…
## [1.1.0] — 2026-09-10
…

## Earlier releases

- [1.0.0-1.0.3](.changes/1.0.0-1.0.3.md)
```

`rollup` inserts one section directly below the heading, so releases accumulate newest-first and older ones are never rewritten. Sections within a release render in a fixed order and only when non-empty: **Possible Breaking Changes**, Features, Fixes, Changes, Reverts. A pull request carrying the `minor` label renders under Possible Breaking Changes instead of its own type section. The label settles that, not the ABI check: the check proposes a verdict and a maintainer can override it. The caller passes those numbers as `minor-prs`.

Archiving is the developer's call. With the `archive` input set to `true` (default `false`), `rollup` moves every release outside the minor line being released into to one file, `.changes/<oldest>-<newest>.md`, named for the releases it holds, since an archive is cut when the developer asks and can span several minor lines. Each archive is linked at the bottom, newest first. Without the input, nothing moves. An archive is a move, not a re-render, and the list is rebuilt from the files present, so one written by hand at adoption is picked up without being registered anywhere.

## Releasing

`rollup` renders whatever is in `preview/`, inserts it, and deletes the fragments. Consequences worth knowing:

- **Re-running it is a no-op.** The fragments are gone, so there is nothing left to insert. A release job that fails after this step can be retried.
- **A release with nothing customer-facing gets no section.** Its fragments are still deleted; a header with nothing under it reads as a broken file.
- **An invalid fragment stops the release**, because releasing would delete it unrendered and the entry would be lost rather than merely late.
- **There is no version guard.** The version comes from the release job, and a mistake in the rendered file is corrected by a chore.

## Adoption

Whatever is already in `CHANGELOG.md` stays there. The first release inserts its section below the heading.

## Layout

```
scripts/fragments.py    the fragment: schema, validation, reading, seeding
scripts/release.py      cutting a release: fragments to markdown, then insert
scripts/check.py        the CI gate
scripts/changelog.py    the CLI; the only entry point
```

Imports only ever point down that list — `release` may use `fragments`, never the other way, and nothing imports `changelog`. `python3 changelog.py` resolves its siblings because the script's own directory is first on `sys.path`, so the directory can be copied anywhere and run with no packaging.

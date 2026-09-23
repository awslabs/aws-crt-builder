# changelog action

Release notes are assembled from per-pull-request fragments, not hand-edited.

- An author commits `.changes/preview/<PR>.json` with their own pull request.
- `CHANGELOG.md` is generated from those fragments and regenerated end to end at
  every release. Nothing appends to it by hand, and no bot commits on a branch an
  author owns.

Everything lives on the working branch. There is no separate docs branch.

## Modes

The composite action exposes three:

| Mode     | Runs                  | What it does                                                                       |
|----------|-----------------------|------------------------------------------------------------------------------------|
| `check`  | pull request          | Assert the title convention and the fragment. Sets `rc` and `reason`; never fails the step itself. |
| `seed`   | pull request          | Write a template fragment, for the bot to paste into a comment.                    |
| `rollup` | release               | Move `preview/` into the new version and regenerate `CHANGELOG.md`.                |

`check` exit codes: `0` pass, `1` the author must fix something, `2` the caller
passed bad arguments. `reason` is one of `ok`, `exempt-type`, `waived-bot`,
`missing-fragment`, `invalid-fragment`, `pr-mismatch`, `type-mismatch`,
`bad-title`, `stray-fragment`, `modified-fragment`. Only `missing-fragment`
earns a comment — every other failure means the author already knows the
convention and just needs the diagnostic.

`scripts/changelog.py` additionally has `render`, `validate`, `list` and
`freeze-snapshot` for local use and for recovery. Run it with `--help`.

## What the checks require

- The title follows `<type>: <summary>`, where type is `feat`, `fix`, `chore` or
  `revert`. An optional scope (`fix(io):`) is accepted, as is the Revert
  button's `Revert "<original title>"`.
- A `feat`, `fix` or `revert` needs exactly one fragment, added at exactly
  `.changes/preview/<PR>.json`. A fragment named for another pull request would
  render under that number; one at another path renders nowhere.
- A `chore` needs no fragment: it renders nowhere, so an entry would be
  invisible.
- The `skip-changelog` label waives the whole check, for CI-only and pure-infra
  changes.
- A bot author waives both the title convention and the fragment.

## Directory layout

```
.changes/
├── preview/                        fragments awaiting the next release
├── latest/                         the active minor line
│   └── <version>/
│       ├── _meta.json              { version, date, highlights }
│       └── <pr>.json               fragments
├── <M>.<N>.x/                      a frozen previous minor line
│   ├── <M>.<N>.<P>/                { _meta.json, *.json }
│   └── CHANGELOG.md                snapshot; never edited again
└── …
CHANGELOG.md                        [Preview] + every release in latest/
```

Root `CHANGELOG.md` covers `[Preview]` and the active minor line only, newest
first. Frozen lines are deliberately excluded — each
`.changes/<M>.<N>.x/CHANGELOG.md` is the immutable record for that line.

Filesystem lex sort puts `0.10.x/` before `0.2.x/`. Only `ls` looks wrong;
every renderer sorts semver properly.

## Contributor flow

Commit `.changes/preview/<PR>.json` with your pull request. Write `summary` so it
reads as a release note, and use `notes` for detail — for a revert, say why. You
never touch `CHANGELOG.md`.

Forgetting is fine: the check comments a ready-to-paste template with the type
and summary already derived from your title.

In a clone of this repository, `scripts/new-change` writes the fragment
interactively. Consumer repos do not vendor it, so the template comment is the
path there.

## Release flow

`rollup --version` decides the shape of the release, and `--bump` is only a
cross-check that fails if it disagrees:

- **Same minor line as `latest/`** — a patch. The new version accretes beside
  the existing ones in `latest/`.
- **A new minor or major** — `latest/` is renamed to `<M>.<N>.x/`, a frozen
  `CHANGELOG.md` is written inside it, and a fresh `latest/<version>/` opens.

A release refuses to proceed if any fragment in `preview/` is invalid, if the
version is not newer than everything released so far, or if it belongs to a line
that has already been frozen.

## Adoption

A repo that already has hand-written `CHANGELOG.md` content must move it into
`.changes/` before the first rollup, or the first generated file replaces it.
For a single prior release, that is one directory:

```
.changes/latest/1.0.0/_meta.json     { "version": "1.0.0", "date": "…", "highlights": "Official release of 1.0.0." }
```

## Local testing

```
python3 -m pytest .github/actions/changelog/tests -v
```

## Fragment schema

```json
{
  "pr": 843,
  "type": "feat",
  "summary": "Add SSO sign-in for enterprise accounts.",
  "url": "https://github.com/<org>/<repo>/pull/<PR>",
  "notes": ""
}
```

`pr` must match the filename. `type` is one of `feat | fix | chore | revert` and
decides the section. `notes` is optional free-form multi-line text, indented
under the entry on render.

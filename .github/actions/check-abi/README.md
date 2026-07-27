# check-abi

Dump and compare the ABI of a CRT C shared library between a pull request's head
and its base ref, and **label the PR** with the implied semver bump (`patch` if
the ABI is backward-compatible, `minor` if it changed). This is intended for use
with the CRT C libraries (ex: aws-c-s3, aws-c-io).

This check is informational: a compatible or incompatible ABI both **succeed**
and are surfaced as a label. The job fails **only** when abi-compliance-checker
could not run (exit code ≥ 2), because then there is no trustworthy verdict.

## What it does

The ABI toolchain (`abi-compliance-checker`, `abi-dumper`, `universal-ctags`,
`cmake`, `g++`) is **baked into a docker image**
(`aws-crt-ubuntu-22-abi-x64`) instead of being installed on every CI run. The
action pulls that image and runs the whole check inside it:

1. **Pull ABI image** — `docker login` to ECR and pull
   `aws-crt-ubuntu-22-abi-x64:<builder-version>`.
2. **Run ABI check in container** — one `docker run` executes all of:
   1. **Download builder** — `builder.pyz`; building is the only part that needs
      builder, because builder owns the CRT dependency graph.
   2. **Build base and head refs** in parallel — both as shared libs with debug info.
   3. **Dump ABI for base and head** in parallel — scoped to public headers via `-public-headers`.
   4. **Run compliance check** — `abi-compliance-checker -binary -source -ext -strict`
      (both binary ABI *and* source/API compatibility — the latter catches
      changes like a renamed public enum constant, which are 100%
      binary-compatible but break compilation of any caller referencing the
      old name).
   5. **Publish report** — appends the verdict and the (sanitized) report body
      to the job summary.
   6. **Choose the label** — `patch` (exit 0), `minor` (exit 1), or fail (exit ≥ 2).
      The verdict escapes the container via a marker line on the container's
      stdout (`ABI_LABEL_RESULT::<label>`), which the host greps out of the
      captured `docker run` output — not a host-mounted file.
3. **Label PR** — on the host (which has the PR context and token), add the
   chosen label and remove the opposite one via `gh pr edit`.

The in-container stages run as a single process because they chain state through
`$GITHUB_ENV`, which does not survive across a `docker run` boundary
(`scripts/abi_check.sh` is the orchestrator that bridges it). Labeling runs on
the host because the container has neither the PR number nor a GitHub token.

## Consumer requirements

The consumer workflow must, before invoking this action:

- **Configure AWS credentials** with ECR pull access (e.g.
  `aws-actions/configure-aws-credentials`), so the image can be pulled.
- **Checkout with `fetch-depth: 0`** so the base branch history is available for
  the worktree and `git merge-base`.
- **Grant `pull-requests: write`** so the action can label the PR. Note: on PRs
  from forks GitHub forces the token read-only regardless of this setting, so
  labeling is skipped (the verdict is still in the job summary).

## Scope and limitations

- **Linux (x86_64) API only.** The ABI image and toolchain are Ubuntu/apt-based,
  so the check only builds and dumps the Linux ABI surface. Public API that's
  guarded by `#if defined(_WIN32)`/Apple-only symbols (e.g. aws-c-io's
  Windows-specific and Apple-specific TLS options) is never compiled, dumped,
  or checked. A break confined to those platforms' code paths will not be
  caught by this action. This was a deliberate scope decision (most CRT public
  API is platform-agnostic), not an oversight, but it's worth knowing before
  relying on this check for a platform-specific change.
- **No submodules.** Both refs are built from a `git worktree`, which does not
  populate submodules. This is a non-issue for the `aws-c-*` libraries this
  action targets today (none use submodules for their public API surface), but
  it means this action is **not** a drop-in fit for a repo like `aws-crt-cpp`
  that does use them, without further work.
- **Default branch must be reachable as `origin/main`.** When triggered outside
  a `pull_request` event (and `base-ref` isn't set), the base ref is resolved
  via `git merge-base HEAD origin/main`. A consumer repo whose default branch
  isn't literally named `main` will hit a clear, actionable error (see
  `scripts/build.sh`) rather than a silent misdetection, but this is a real
  portability gap worth knowing about up front.
- **Single-library scope.** Each run diffs one library's own ABI/API against
  its own previous version. It cannot detect a break that only manifests when
  a *different* library in the dependency graph is upgraded without a
  matching redeploy (e.g. library A adds a symbol that library B starts
  calling; A's own check is correctly clean, but a consumer who upgrades B
  without upgrading A hits a runtime "undefined symbol" failure). This has
  been researched and is treated as expected, not a tooling gap: each CRT
  package versions independently, and the failure mode is a loud, immediate
  load-time error pointing at the actual missing dependency, not a silent
  misbehavior.

## Usage

Add a workflow to the library repo (see `aws-c-s3/.github/workflows/check-abi.yml`):

```yaml
jobs:
  check-abi:
    runs-on: ubuntu-24.04
    permissions:
      id-token: write        # for configure-aws-credentials OIDC
      pull-requests: write   # to label the PR patch/minor
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.CRT_CI_ROLE_ARN }}
          aws-region: us-east-1
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Check ABI
        # note: using "@main" because "@${{env.BUILDER_VERSION}}" doesn't work
        # https://github.com/actions/runner/issues/480
        #
        # @main tracks this action's default branch directly, so a breaking
        # change pushed to aws-crt-builder's main affects every consumer's
        # very next CI run with no version pin to roll back to -- there is no
        # stable/"latest" tag for this action yet. If check-abi starts failing
        # unexpectedly after no local change, check aws-crt-builder's recent
        # history on main before assuming the consumer repo is at fault.
        uses: awslabs/aws-crt-builder/.github/actions/check-abi@main
        with:
          lib-name: aws-c-s3
```

### Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `lib-name` | yes | — | Library name; maps to `lib<name>.so`. |
| `builder-version` | no | `v0.9.93` | Builder version/channel used to build; also the ABI image tag. |
| `builder-source` | no | `releases` | `releases` for tags, `channels` for branch builds. |
| `builder-host` | no | CloudFront URL | Builder artifact host. |
| `image-registry` | no | CRT ECR registry | ECR registry hosting the ABI image. |
| `image-name` | no | `aws-crt-ubuntu-22-abi-x64` | ABI docker image name. |
| `github-token` | no | `github.token` | Token used to label the PR (needs `pull-requests: write`). |
| `patch-label` | no | `patch` | Label applied when the ABI is backward-compatible. |
| `minor-label` | no | `minor` | Label applied when the ABI changed but the API is source-compatible. |
| `needs-review-label` | no | `needs-review` | Label applied when source (API) compatibility is broken. |
| `base-ref` | no | _(none)_ | Explicit base ref to diff against (e.g. a previous release tag), overriding the PR base ref. Only for non-PR callers (e.g. a release workflow); leave unset in PR workflows so the PR gets labeled. |

## The label

The label is not abicc's raw exit code -- it's a three-way verdict computed from
each report's own structured fields (see `gate.sh`):

| Verdict | Meaning | Result |
|---------|---------|--------|
| `patch` | ABI and API are both backward-compatible | job passes, PR labeled `patch` |
| `minor` | ABI changed, but API (source) is still compatible | job passes, PR labeled `minor` |
| `needs-review` | API (source) compatibility is broken -- callers fail to recompile | job passes, PR labeled `needs-review` |
| _(none)_ | abi-compliance-checker could not produce a verdict (tool error) | **job fails**, no label |

The three labels are mutually exclusive: applying one removes the other two, so
a re-run after a code change flips the label cleanly.

### Blocking merges on `needs-review`

`needs-review` is informational by itself -- `check-abi`'s own job still passes
so the label doesn't get re-litigated on every push. To actually block merging
until a maintainer reviews and removes the label, add a required status check
that calls the reusable `block-needs-review-label.yml` workflow:

```yaml
# .github/workflows/block-needs-review.yml
name: Block needs-review merges
on:
  pull_request:
    types: [labeled, unlabeled]

jobs:
  gate:
    uses: awslabs/aws-crt-builder/.github/workflows/block-needs-review-label.yml@main
```

Then mark this workflow's `gate` job as a **required status check** in the
repo's branch protection settings. Triggering only on `labeled`/`unlabeled`
(not `opened`/`synchronize`) is deliberate: the label is the only thing this
check cares about, so a maintainer removing it re-runs the check immediately
and unblocks the merge, without re-running the (slow) ABI build/dump/compare
pipeline just to notice a label changed. The label name isn't configurable
here -- it's hardcoded to `needs-review` to match `check-abi`'s own default,
so there's no way for the two to drift out of sync.

## The docker image

The image is defined at `.github/docker-images/ubuntu-22-abi-x64/Dockerfile` and
is built + pushed to ECR (tagged with the builder version) by the
`create-channel.yml` / `create-release.yml` workflows, same as every other
`aws-crt-*` image.

## Layout

```
check-abi/
├── action.yml          # pull image + docker run the orchestrator + label the PR
├── README.md
└── scripts/
    ├── abi_check.sh    # in-container orchestrator (build->dump->compare->report->gate)
    ├── build.sh        # resolve base ref, worktree, build both refs (parallel)
    ├── dump.sh         # locate both .so, abi-dump both (parallel)
    ├── compare.sh      # abi-compliance-checker; record rc/pct
    ├── report.py       # write verdict + report body to the job summary
    └── gate.sh         # map exit code -> patch/minor label; fail only on tool error
```

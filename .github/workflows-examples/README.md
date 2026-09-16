# Consumer workflow examples

Files here are **not** workflows of this repository. They live outside
`.github/workflows/` on purpose: GitHub Actions only loads workflows from that
directory, and `pre-merge-checks.yml` below declares `on: pull_request_target`,
so keeping it here means it is documentation rather than something that runs
against `aws-crt-builder` itself.

Copy `pre-merge-checks.yml` into a consumer repo's `.github/workflows/`.

## `pre-merge-checks.yml`

Calls the `Pre-merge checks` reusable workflow. In the consumer repo it
replaces both of:

- `.github/workflows/check-abi.yml` (`on: push`)
- `.github/workflows/block-needs-review.yml` (`on: pull_request`)

Those two cannot work as separate workflows, which is why this is one file:
`check-abi` applies the verdict label with `GITHUB_TOKEN`, and per GitHub's
docs, "events triggered by the `GITHUB_TOKEN` will not create a new workflow
run… Other `pull_request` activity types (such as `labeled`, `edited`, or
`closed`) do not create workflow runs." A separate label-gate workflow is
therefore never re-triggered by the verdict it exists to read. Ordering has to
come from `needs:` inside a single run.

The file is intended to be **byte-identical in every consumer**: `lib-name` is
derived from the event rather than hardcoded.

### Before enabling

- Create the `fork-review` environment with required reviewers. A referenced
  environment that does not exist is created implicitly **with no protection
  rules**, so a typo here fails open.
- Confirm the `CRT_CI_ROLE_ARN` trust policy admits this job. Moving from
  `push` to `pull_request_target` changes the OIDC `sub` claim, and hosting the
  job in this repository changes `job_workflow_ref`.
- Leave `changelog-enabled: false` until the `changelog` action exists on
  `awslabs/aws-crt-builder@main`.
- The string to put in a branch ruleset is the commit-status context
  (`pre-merge/gate` by default), not a check-run name.

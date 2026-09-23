<!--
Snippet for consumer repos to append to their .github/PULL_REQUEST_TEMPLATE.md
once Pre-merge checks is wired.
-->

*Changelog:*

- PR title must follow `<type>: <customer-facing summary>`, where `type` is one of `feat | fix | chore | revert`.
- A `feat`, `fix` or `revert` needs a changelog entry: run `.github/actions/changelog/scripts/new-change` locally and commit the generated `.changes/preview/<PR>.json`. Refine the `summary`; optionally fill `notes`. A `chore` needs none.
- Apply the `skip-changelog` label only for CI-only / pure-infra PRs.

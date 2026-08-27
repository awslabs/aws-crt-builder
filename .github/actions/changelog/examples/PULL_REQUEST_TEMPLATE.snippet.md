<!--
Snippet for consumer repos to append to their .github/PULL_REQUEST_TEMPLATE.md
once the changelog-check workflow is wired.
-->

*Changelog:*

- PR title should follow: `<type>: <customer-facing summary>` where `type` is one of `feat | fix | doc | chore | revert`.
- Run `.github/actions/changelog/scripts/new-change` locally and commit the generated `.changes/preview/<PR>.json`. Refine the `summary`; optionally fill `notes`.
- Apply the `skip-changelog` label only for CI-only / pure-infra PRs.

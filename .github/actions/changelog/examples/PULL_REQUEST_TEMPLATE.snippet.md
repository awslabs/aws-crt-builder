<!--
Snippet for consumer repos to append to their .github/PULL_REQUEST_TEMPLATE.md
once Pre-merge checks is wired.
-->

*Changelog:*

- PR title must follow `<type>: <customer-facing summary>`, where `type` is one of `feat | fix | chore | revert`.
- A `feat`, `fix` or `revert` needs a changelog entry: commit `.changes/preview/<PR>.json`, and write the `summary` so it reads as a release note. If you forget, the bot comments a ready-to-paste template. A `chore` needs none.
- Apply the `skip-changelog` label only for CI-only / pure-infra PRs.

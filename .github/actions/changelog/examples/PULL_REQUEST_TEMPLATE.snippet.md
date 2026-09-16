<!--
Snippet for consumer repos to append to their .github/PULL_REQUEST_TEMPLATE.md
once the changelog-check workflow is wired.
-->

*Changelog:*

- PR title **must** follow: `<type>: <customer-facing summary>` where `type` is one of `feat | fix | doc | chore | revert`. CI fails otherwise. An optional scope is fine: `fix(io): Handle EINTR.`
- Add `.changes/preview/<PR>.json` to your PR branch — paste the template below and fill in the fields. Leave `notes` empty unless you have more to say.
- Apply the `skip-changelog` label only for CI-only / pure-infra PRs.

```json
{
  "pr": <PR>,
  "type": "feat",
  "summary": "<customer-facing sentence>",
  "url": "<PR URL>",
  "notes": ""
}
```

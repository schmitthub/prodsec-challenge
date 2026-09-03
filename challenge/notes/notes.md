## Done

- syft + cosign
- github attestations
- agents
  - serena
  - hooks
- clawker
- uv proj
- prek / pre-commit
- semgrep
- osv
- bandit
- release
- github rules
  - trunk

## TODO

- main checks gh rules

## Impl Notes

### CI

- moved tool deps to pre commit tools (prek or pre-commit, supports both) to keep scanner deps and hooks optional to devs
- chose prek/pre-commit for pre commit checks as an interchangeable option depending on developer preference.
- implemented OSS tooling similar to what codeQL uses with the assumption you'll have either or both available, and leaves a seam to mitigate vendor dependency lock-in.
- Github Repo Settings / Advanced Security
  - enabled Automatic dependency submission
  - Added 2 branch rulesets for all and main
  - Add 1 tag ruleset for releases
  - Enabled immutable tags
  - Enabled advanced setup for github security for more granular control over the workflow and configuration
  - Enabled all dependabot settings
- For workflow example purposes setup the repo for trunk based dev
- added uv for uv.lock so that syft sboms can resolve transient deps and make proper graph
- sec tools
  - semgrep
  - bandit
  - osv scanner
  - gitleaks
  - codeql
- CVSS_FAIL_THRESHOLD var created

### Triage

- generated baselines and sarif gen script for local triage

### AI

- added serena support for LSP semantic retrieval capabillity
- ! will add reviewer agents for lite-agentic code review features
- ! will add lazy loading agent files to help with context window rot and promote code rules


## Sec nots

- needed to adjust gitleaks settings to detect secret in dev.py due to low entropy
- https://github.com/schmitthub/prodsec-challenge/pull/7 shows an example of brandit based alerts and warnings that can be dismissed

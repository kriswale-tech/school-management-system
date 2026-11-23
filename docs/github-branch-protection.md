# GitHub branch protection for dev-to-main promotion

The CI workflow checks PR source branches, but GitHub repository settings must also block direct pushes to `main`.

## Required rule for `main`

Create an active ruleset targeting the `main` branch and set:

- Require a pull request before merging.
- Require the `Main PR must come from dev` status check.
- Require these CI checks: `Backend checks and tests`, `School frontend checks`, `Platform admin checks`, and `Production backend image build`.
- Require branches to be up to date before merging.
- Block force pushes and branch deletion.
- Do not add bypass actors if the rule should apply to administrators too.

The CI source-branch check allows a PR only when its head branch is `dev` in this same repository. It fails for PRs from other branches or forks. GitHub branch rulesets can require pull requests and status checks, but the source-branch check is a workflow job.

## Rule for `dev`

Require the same CI jobs before merging PRs into `dev`. Direct pushes to `dev` can remain allowed during this rollout unless the team decides to use feature branches for all changes.

The rule settings live in GitHub and are not enabled by adding this file. After the workflow has run once, select its exact check names in the repository ruleset settings.

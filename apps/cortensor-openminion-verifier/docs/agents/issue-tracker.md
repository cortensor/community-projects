# Issue tracker: GitHub

Issues and specs for this repo live as GitHub issues on `huadeng408/cortensor-openminion-verifier`. Use the `gh` CLI for all operations.

## Conventions

- **Create an issue**: `gh issue create --title "..." --body-file <file> --label "..."`.
- **Read an issue**: `gh issue view <number> --comments`.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments`.
- **Comment on an issue**: `gh issue comment <number> --body "..."`.
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`.
- **Close**: `gh issue close <number> --comment "..."`.

## Pull requests as a triage surface

**PRs as a request surface: no.**

## When a skill says "publish to the issue tracker"

Create a GitHub issue on `huadeng408/cortensor-openminion-verifier`.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --comments`.

## Blocking dependencies

Add native GitHub blocking edges where supported (`gh api --method POST repos/huadeng408/cortensor-openminion-verifier/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`), and always include a human-readable `Blocked by: #<n>` line in the issue body. A ticket is unblocked when every blocker is closed.

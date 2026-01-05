# GitHub Repo Push Design (2026-01-05)

## Goal
Create private GitHub repositories for each git repo under `/home/ags/knowledge-system`, using the naming pattern `ks-<folder>`, then replace each repo’s `origin` and push all branches and tags.

## Scope
- Discover git repos in immediate subfolders
- Derive target names as `ks-<folder>`
- Create GitHub repos under the authenticated personal account
- Replace existing `origin` with new GitHub URL
- Push all branches and tags
- Continue on errors and summarize results

## Non-Goals
- Changing repo contents or history
- Creating org-owned repositories
- Selective branch/tag pushing (we push all)

## Discovery & Naming
- Scan immediate subdirectories for `.git`
- For each repo:
  - Folder name → target name `ks-<folder>`
  - Detect default branch
  - Detect existing `origin`
- Print a preview table before any changes

## Creation & Push Flow
Per repo:
1. Create repo: `gh repo create <user>/<name> --private --confirm`
2. Set/replace `origin` to the new GitHub URL
3. Push all branches: `git push --all origin`
4. Push all tags: `git push --tags origin`

Failures are captured per repo and do not halt the batch.

## Safety & Edge Cases
- If `gh` isn’t authenticated, stop with instructions to `gh auth login`
- If repo has no commits, skip push with a warning
- If repo already exists, skip creation and continue to remote update/push
- If permissions or name conflicts occur, record failure and continue

## Output
- Summary of created repos, updated remotes, pushed branches/tags
- Failures list with brief error excerpt

## Optional UX Enhancements
- Dry-run mode that prints actions without changes
- Optional include/exclude list for folders

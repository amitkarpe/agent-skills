---
name: safe-shell-ops
description: Prevent shell quoting, heredoc, globbing, and generated-file mistakes. Use when writing files through shell, generating Markdown/docs with backticks or dollar signs, creating temp scripts, running bash/zsh snippets, or fixing failures caused by heredoc expansion, command substitution, word splitting, or shell quoting.
---

# Safe Shell Ops

Use this skill before shell operations where quoting or generated files can fail.

## Default Decision

For file edits:

1. Use `apply_patch` for repo/docs/config/code edits.
2. Use a temp script under `~/.AGENTS-temp/<repo>/` only when execution logic is needed.
3. Use Python/Node only for structured transforms.
4. Use shell heredoc only for tiny low-risk temp files.

## Markdown / Docs Rule

Avoid writing Markdown that needs literal backticks or `$` when plain wording is enough.

If Markdown/docs must include shell-sensitive text such as backticks, `$VAR`,
`$(cmd)`, quotes, or placeholders:

- use `apply_patch`
- do not use inline `bash -lc 'cat <<EOF ...'`
- read the file back after writing

## Heredoc Rule

Do not put a quoted heredoc delimiter inside an outer single-quoted `bash -lc`
string.

Bad pattern:

```bash
bash -lc 'cat > file <<'EOF'
... text with `cmd` or $VAR ...
EOF'
```

Safer choices:

- `apply_patch`
- temp script created by `apply_patch`, then `bash -n`, then execute
- if a heredoc is truly needed, ensure the delimiter is quoted in the shell
  that actually receives it: `<<'EOF'`

## Script Rule

For edited or generated shell scripts:

1. write the script file first
2. run `bash -n <script>` or `zsh -n <script>`
3. execute only after syntax validation passes

## Command Rule

- Use explicit `shell=/bin/bash` and `login=false` for agent command execution
  unless testing zsh itself.
- Do not wrap a command in nested `bash -lc`; invoke the command directly or
  use one temporary Bash script for complex logic.
- Quote variable expansions.
- Prefer arrays over string-built commands.
- Avoid `eval`.
- Pass dynamic jq values with `--arg` (or `--argjson` for JSON), never by
  interpolating them into a jq program.
- Avoid complex one-liners; make a temporary script when logic grows past a
  few simple commands.

For infra mutation helpers, prefer invoking repo-owned Terraform/Terragrunt
commands or the owning repo cleanup runner over ad-hoc generated AWS CLI scripts.

## Validation

Save time and tokens. Do not run validation/check commands for low-risk local
Markdown, context, notes, or response-file edits unless the user asks or the
change is about to be committed/pushed.

Run the smallest relevant check when risk is higher:

- `git diff --check` before commit/push/PR-ready handoff, or after suspicious
  patches and large multi-file edits
- `bash -n` for edited bash scripts
- `zsh -n` for edited zsh files
- targeted syntax/parsing checks for YAML, Terraform, code, or generated files
- read back generated text files only when they contain shell-sensitive
  characters or the write path was fragile

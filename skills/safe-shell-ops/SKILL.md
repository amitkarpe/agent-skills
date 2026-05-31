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
3. run `shellcheck <script>` when available
4. execute only after syntax validation passes

## Command Rule

- Use `/bin/bash` for agent command execution unless testing zsh itself.
- Quote variable expansions.
- Prefer arrays over string-built commands.
- Avoid `eval`.
- Avoid complex one-liners; make a temp script when logic grows past a few
  simple commands.

## Validation

Before reporting success, run the smallest relevant check:

- `git diff --check` for repo edits
- `bash -n` for bash scripts
- `zsh -n` for zsh files
- read back generated text files that contain shell-sensitive characters

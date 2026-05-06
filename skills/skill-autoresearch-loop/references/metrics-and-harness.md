# Metrics and harness patterns

Use one primary metric and at most two secondary observations.

## Good primary metrics

- first-try success rate
- number of manual commands still required
- time to a valid result
- number of repo-specific edits per run
- number of retries before success

## Good secondary observations

- evidence quality under `~/.AGENTS-temp/<repo>/...`
- clarity of `SKILL.md`
- failure mode detectability
- amount of duplicated bash still needed outside the skill

## Good harness shapes

### Operator workflow

Use when the skill drives a repeated operational sequence.

Record:
- starting context
- 3-5 operator asks
- expected files and outputs
- stop conditions

### Build-and-validate workflow

Use when the skill wraps build polling, validation, or evidence capture.

Record:
- known-good small build
- controlled failure case
- retained-debug case if relevant

### Investigation workflow

Use when the skill gathers evidence and reduces it.

Record:
- one clean environment
- one degraded environment
- one ambiguous case

## Anti-patterns

- changing the harness while measuring the skill
- improving multiple skills in one loop
- using production mutation as the first harness
- declaring success without a decision log

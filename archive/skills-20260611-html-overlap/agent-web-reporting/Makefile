.PHONY: check scan syntax fixtures sync-dry-run sync-apply

check: scan syntax fixtures

scan:
	./scripts/scan-agent-web-reporting.sh

syntax:
	bash -n scripts/*.sh

fixtures:
	./scripts/validate-fixtures.sh

sync-dry-run:
	./scripts/sync-to-agent-skills.sh --dry-run

sync-apply:
	./scripts/sync-to-agent-skills.sh --apply

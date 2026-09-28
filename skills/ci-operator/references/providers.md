# Provider notes

## GitHub Actions

Prefer exact run/job IDs and compact `gh`/API status reads.

Avoid defaulting to continuous `gh run watch` for agent work. Sleep based on expected runtime, then query status. Fetch failed-job logs only when diagnosis requires them.

For CodeBuild-hosted GitHub Actions runners, distinguish:

- GitHub workflow/job state;
- webhook delivery/admission;
- runner assignment;
- CodeBuild build state.

A queued GitHub job does not by itself prove whether webhook delivery or CodeBuild admission succeeded.

## CodeBuild

Capture the exact build ID immediately. Use recent build duration when available. Read build status after waiting. Inspect phase details and CloudWatch logs only for failure/stall diagnosis.

Do not start another build merely because the controller lost its session.

## CodePipeline

Capture the exact pipeline execution ID. Prefer stage/action summaries first. Inspect detailed action execution only for failed/stuck stages.

A pipeline retry or release-change action is a mutation and must inherit authority from the owning repo contract.

## GitLab CI/CD

Capture pipeline and relevant job IDs. Use recent pipeline/job durations to choose waits. Query compact pipeline/job status first; fetch job trace only for failure/stall diagnosis.

Retrying a GitLab job is a mutation: reconcile the prior job/pipeline and owning authority first.

## Webhook delivery

For GitHub/CodeBuild integration failures:

1. identify the exact delivery/event;
2. verify its delivery result;
3. verify whether the downstream build/run already exists;
4. redeliver only when the failed delivery did not create the required execution and authority allows it;
5. persist the downstream execution ID after admission.

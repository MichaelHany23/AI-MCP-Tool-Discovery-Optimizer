# MCP-TDO methodology

This document defines the evaluation contract before implementation of the
benchmark. Later code and reports must follow these definitions, or explicitly
version and document a change.

## Evaluation units

The primary evaluation unit is a labeled task. A task contains a user prompt,
the available server set, one or more gold tool calls, argument matchers, and
the permitted call-order constraint.

Each task belongs to exactly one frozen split:

- **Train:** available to optimizer development.
- **Dev:** available for candidate selection and iteration.
- **Test:** sealed until final proof evaluation.

The split assignment will be saved with a seed and content hash. No optimizer
component may read test prompts, gold calls, or test traces before final proof.

## Core metrics

### Tool selection accuracy

For each expected call, the selected tool is correct when its fully qualified
tool name equals the labeled gold tool name. We report first-call accuracy and
all-call accuracy separately. A missing expected call is incorrect.

### Tool selection F1

Treat each tool name as a class over expected calls. Report macro-averaged
precision, recall, and F1, plus per-tool values. `NONE` and
`HALLUCINATED` are explicit outcome classes rather than silently discarded
errors.

### Argument validity rate

An argument set is valid when it passes the selected tool's JSON Schema. This
metric does not imply that the values satisfy the task intent.

### Argument correctness

Arguments are correct when they pass the task's declared matchers. Supported
matcher types will include exact, contains, regular expression, numeric
tolerance, approximate datetime, and set equality. Missing or malformed
arguments fail the matcher rather than receiving a partial success by default.

### Call-order score

For tasks marked `strict`, the complete selected sequence must match the gold
sequence after removing explicitly permitted non-operative events. For
`partial` and `any` tasks, the scorer will use the task's declared order
constraints and report a normalized score in the range 0 to 1.

### Task success rate

A task succeeds only when all required calls, arguments, and order constraints
pass and the expected end state is reached. This is the primary end-to-end
metric.

## Operational metrics

Every run should also record calls per task, hallucinated-tool rate, abstention
accuracy, token usage, estimated cost, latency, retries, and termination
reason. Operational metrics explain trade-offs but do not replace the six core
metrics.

## Baseline and proof

The baseline is the original metadata version (`v0`). Optimizer candidates are
evaluated on train and dev only. Each candidate patch is then tested alone
against the same held-out test tasks and agent configuration as the baseline.

Proof reports will include paired per-task differences, a 95% paired bootstrap
confidence interval for continuous metrics, and McNemar's test for binary task
success. Multiple patch comparisons will use Holm correction. A patch is
accepted only when its target improvement is supported and no protected metric
regresses beyond the configured tolerance.

All reported numbers must come from saved raw traces and a reproducible run
configuration. Placeholder or estimated results must not be presented as
benchmark findings.


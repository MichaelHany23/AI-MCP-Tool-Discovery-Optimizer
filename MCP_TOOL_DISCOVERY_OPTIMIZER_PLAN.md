# MCP Tool Discovery Optimizer (MCP-TDO)

> Benchmark whether LLM agents pick the right MCP tool, arguments, and call order, then automatically improve ambiguous tool names, descriptions, schemas, and examples, and prove every change on held-out tasks.

---

## 1. Project Vision

MCP servers expose tools through names, descriptions, and JSON schemas. Agents choose tools based only on that text. Poor wording causes wrong-tool calls, bad arguments, and broken call order, yet almost nobody measures it.

**MCP-TDO** is a three-part system:

1. **Benchmark harness**: runs agents against labeled tasks and scores tool selection, arguments, and call order.
2. **Optimizer**: proposes rewrites of tool metadata (name, description, schema, examples) based on observed confusions.
3. **Proof engine + UI**: re-evaluates each proposed change on the same held-out tasks with statistical tests, and shows everything in a dashboard.

**Differentiators (what makes it stand out)**
- Tool-selection **confusion matrix** (true tool vs. chosen tool) published per model and per server version.
- **Per-change causal proof**: each suggested edit is applied alone (ablation) and tested on the same held-out split, with paired significance tests.
- **Leakage-safe design**: the optimizer only sees the train/dev split. The test split is touched only for final proof.
- Full **experiment tracking** and one-command reproducibility.

---

## 2. Scope and Success Criteria

| Area | Deliverable | Target |
|---|---|---|
| Benchmark | Labeled task set | 300+ tasks, 5+ MCP servers, 40+ tools |
| Metrics | Selection, argument, order scores | 6 core metrics (see section 5) |
| Models | Compare several LLMs | 3+ models (mix of API and open-weight) |
| Optimizer | Description/schema/example rewriting | 3 strategies compared |
| Proof | Held-out validation | Paired test + CI for every change |
| UI | Interactive dashboard | 6 pages |
| Dev tooling | CLI + CI | `mcp-tdo run / optimize / report` |
| Quality | Tests and docs | 80%+ coverage, README, demo video |

**Honesty rule:** only publish numbers your pipeline actually produced. Save raw run logs in the repo so anyone can verify them.

---

## 3. System Architecture

```
            ┌──────────────────────────────┐
            │  Labeled Task Set (YAML/JSON) │
            └──────────────┬───────────────┘
                           │
 ┌───────────────┐   ┌─────▼──────┐   ┌────────────────┐
 │ MCP Servers   │◄──┤ Agent      ├──►│ LLM Providers  │
 │ (mock + real) │   │ Runner     │   │ (adapter layer)│
 └───────┬───────┘   └─────┬──────┘   └────────────────┘
         │ tools/list       │ traces
         │                  ▼
         │          ┌───────────────┐      ┌───────────────┐
         │          │ Scorer        │─────►│ Tracking      │
         │          │ (metrics, CM) │      │ (MLflow + DB) │
         │          └──────┬────────┘      └──────┬────────┘
         │                 ▼                      │
         │          ┌───────────────┐             │
         └─────────►│ Optimizer     │             │
  (metadata patches)│ (rewrite loop)│             │
                    └──────┬────────┘             │
                           ▼                      ▼
                    ┌───────────────┐      ┌───────────────┐
                    │ Proof Engine  │─────►│ FastAPI + UI  │
                    │ (held-out)    │      │ Dashboard     │
                    └───────────────┘      └───────────────┘
```

### Tech stack
- **Language:** Python 3.11+
- **MCP:** official `mcp` Python SDK (build servers; use the client to call `tools/list` and `tools/call`)
- **LLM adapters:** Anthropic, OpenAI, plus one open-weight model via Ollama or vLLM
- **Backend:** FastAPI, Pydantic v2, SQLModel + SQLite (Postgres optional)
- **Tracking:** MLflow (runs, params, artifacts) with Parquet files for raw traces
- **Stats:** SciPy, statsmodels (McNemar, paired bootstrap, Wilcoxon)
- **UI:** Next.js + Tailwind + Recharts/Plotly (or Streamlit for a faster v1)
- **Tooling:** Typer (CLI), pytest, Ruff, mypy, pre-commit, Docker Compose, GitHub Actions

---

## 4. Repository Structure

```
mcp-tool-discovery-optimizer/
├── README.md
├── pyproject.toml
├── docker-compose.yml
├── Makefile
├── .github/workflows/ci.yml
├── docs/
│   ├── architecture.md
│   ├── methodology.md
│   ├── task-labeling-guide.md
│   ├── results/            # generated reports + figures
│   └── assets/             # screenshots, GIFs
├── servers/                # MCP servers under test
│   ├── filesystem_lite/
│   ├── issue_tracker/
│   ├── calendar/
│   ├── crm/
│   ├── sql_analytics/
│   └── variants/           # v0 (original) and v1.. (optimized) metadata
├── data/
│   ├── tasks/              # labeled tasks (train/dev/test splits)
│   ├── splits.json         # frozen split with seed + hash
│   └── gold_traces/
├── mcp_tdo/
│   ├── cli.py
│   ├── config.py
│   ├── mcp_client/         # tool listing, call execution, sandbox
│   ├── agents/             # provider adapters + agent loop
│   ├── tasks/              # schema, loader, validator
│   ├── scoring/            # metrics, confusion matrix, order scoring
│   ├── optimizer/          # analyzers + rewriters + patch applier
│   ├── proof/              # held-out evaluation, stats tests
│   ├── tracking/           # MLflow + DB helpers
│   └── api/                # FastAPI routes
├── ui/                     # Next.js dashboard
├── notebooks/              # EDA, error analysis
└── tests/
```

---

## 5. Labeled Task Set Design

### Task schema (YAML)
```yaml
id: crm-0142
split: test                      # train | dev | test
server_set: [crm, calendar]
prompt: "Set up a follow-up with Dana from Acme next Tuesday at 3pm."
gold_calls:
  - tool: crm.find_contact
    args: {query: "Dana Acme"}
  - tool: calendar.create_event
    args_match:
      title: {contains: "Acme"}
      start: {datetime_approx: "next Tuesday 15:00"}
order: strict                    # strict | partial | any
difficulty: medium               # easy | medium | hard
confusable_with: [crm.search_accounts]
tags: [multi-step, date-parsing]
```

### Coverage plan
- **300+ tasks** total: roughly 60% single-tool, 30% multi-step, 10% "no tool needed" or "should ask for clarification".
- **Deliberate ambiguity:** each server gets near-duplicate tools (for example `search_issues` vs. `find_issues`, `get_user` vs. `lookup_person`) so the benchmark exposes real confusions.
- **Splits:** 50% train (optimizer can see), 20% dev (iteration), 30% test (sealed). Stratify by server, difficulty, and tool. Freeze with a seed and a content hash saved in `splits.json`.
- **Labeling quality:** two-pass labeling (write, then review), measure inter-annotator agreement on a 15% sample (Cohen's kappa) and report it.
- **Argument matchers:** exact, contains, regex, numeric tolerance, datetime-approx, set-equal.

### Metrics
1. **Tool Selection Accuracy** (first call and all calls)
2. **Tool Selection F1** (macro, per tool)
3. **Argument Validity Rate** (passes JSON schema)
4. **Argument Correctness** (matches gold matchers)
5. **Call Order Score** (normalized edit distance or Kendall tau over the call sequence)
6. **Task Success Rate** (end-to-end: all calls correct and task state reached)

Plus operational metrics: calls per task, hallucinated tool rate, abstention accuracy, token cost, latency.

### Confusion matrix
- Rows = gold tool, columns = chosen tool, plus a `NONE` and `HALLUCINATED` column.
- Publish per model and per metadata version (before/after).
- Add a **top confusable pairs** table ranked by confusion count, which feeds the optimizer directly.

---

## 6. Optimizer Design

**Inputs:** server tool metadata, train and dev traces, confusion pairs, argument error logs.
**Outputs:** patches to tool name, description, parameter descriptions, schema constraints, and few-shot examples.

### Edit types (each is an atomic, separately testable patch)
- **Disambiguation:** add "Use this when... Do NOT use for... (use X instead)".
- **Rename:** rename vague tools (`get_data` to `get_customer_invoice_history`).
- **Schema tightening:** enums, patterns, min/max, required vs. optional, format hints.
- **Parameter docs:** clarify units, formats, and examples inside parameter descriptions.
- **Examples:** add 1-2 canonical input examples per tool.
- **Length control:** compress verbose descriptions (token budget check).

### Strategies compared
1. **Rule-based linter:** detects vague verbs, missing negatives, near-duplicate descriptions (embedding similarity).
2. **LLM rewriter:** given confusion pairs and failed traces, proposes patches (strict JSON patch output).
3. **Iterative search:** generate N candidates, score on dev, keep best (beam search of width 3), stop on plateau.

### Guardrails against overfitting
- Optimizer reads only **train + dev**. Test is evaluated once per final candidate.
- Candidate prompts must not copy task phrasings from the test set (automated n-gram overlap check).
- Report the **train-dev-test gap** for every accepted change.

---

## 7. Proof Engine (held-out validation)

For each proposed patch `p`:
1. Apply `p` alone to the baseline metadata (single-change ablation).
2. Run the same agent configuration on the **same held-out test tasks**, multiple seeds (3-5 runs, temperature fixed).
3. Compute paired differences per task.
4. Test significance: **McNemar's test** (binary success), **paired bootstrap 95% CI** (continuous metrics), correction for multiple comparisons (Holm).
5. Accept a patch only if it improves the target metric without regressing others beyond a set tolerance.
6. Run a **combined patch set** test and report interaction effects.

**Output artifacts:** per-patch proof card (before/after text diff, delta, CI, p-value, tasks fixed, tasks broken), plus a final confusion matrix diff heatmap.

---

## 8. UI / Developer Experience

Pages:
1. **Overview:** headline metrics, model comparison, trend over versions.
2. **Confusion Matrix Explorer:** interactive heatmap, click a cell to see the exact failing tasks and traces.
3. **Tool Inspector:** per-tool precision/recall, current description, confusable partners, schema view.
4. **Optimizer Studio:** pick a tool, see suggested patches with diff view, run dev evaluation live.
5. **Proof Cards:** accepted and rejected patches with stats, tasks fixed vs. broken.
6. **Trace Viewer:** step-by-step agent trace (prompt, tool list shown, call, result, score reasoning).

Extras: dark mode, export report to Markdown/PDF/CSV, shareable run URLs, a "paste your MCP server config" mode that lints and benchmarks a user's own server.

**CLI**
```
mcp-tdo validate-tasks data/tasks
mcp-tdo run --models claude,gpt,llama --servers all --split test
mcp-tdo optimize --strategy llm-beam --budget 40
mcp-tdo prove --patches runs/opt_17/patches.json
mcp-tdo report --run runs/final --out docs/results
mcp-tdo lint ./my_mcp_server
```

---

## 9. Phased Roadmap (about 8 weeks)

### Phase 0: Setup (Days 1-3)
- [ ] Create repo, license (MIT), `pyproject.toml`, pre-commit, CI skeleton
- [ ] Write `docs/methodology.md` with metric definitions first
- [ ] Choose models and set up API keys via `.env` (never commit)

### Phase 1: MCP servers and client (Week 1)
- [ ] Build 5 MCP servers with realistic, deterministic backends (SQLite or in-memory fixtures)
- [ ] Add deliberate near-duplicate tools and weak descriptions as the **v0 baseline**
- [ ] Build MCP client wrapper: list tools, call tools, sandbox and timeout, record traces
- [ ] Tests: each server's tools return deterministic outputs

### Phase 2: Task set and labeling (Weeks 1-2)
- [ ] Define schema + validator
- [ ] Write 300+ tasks; two-pass review; compute kappa
- [ ] Freeze splits with seed and hash
- [ ] Notebook: dataset statistics (tool coverage, difficulty mix)

### Phase 3: Agent runner (Week 3)
- [ ] Provider adapters with a unified tool-call format
- [ ] Agent loop (max steps, retries, stop conditions)
- [ ] Cache layer for repeatable runs (key = model + prompt + tools hash + seed)
- [ ] Cost and latency logging

### Phase 4: Scoring and baseline (Week 3-4)
- [ ] Implement six metrics + argument matchers + order scoring
- [ ] Confusion matrix generator + top-confusions table
- [ ] Baseline run for all models on v0; log to MLflow
- [ ] Unit tests with hand-built traces for every metric edge case

### Phase 5: Optimizer (Weeks 4-5)
- [ ] Rule-based linter
- [ ] LLM rewriter with strict JSON patch schema
- [ ] Beam search loop with dev evaluation and plateau stop
- [ ] Overlap/leak checks

### Phase 6: Proof engine (Week 6)
- [ ] Single-patch ablation runner
- [ ] Paired stats (McNemar, bootstrap, Holm)
- [ ] Proof card generator, final before/after confusion matrix diff

### Phase 7: API and UI (Weeks 6-7)
- [ ] FastAPI endpoints over tracked runs
- [ ] Build the 6 dashboard pages
- [ ] Screenshots and a 60-90 second screen recording

### Phase 8: Polish and launch (Week 8)
- [ ] README with quickstart, results, diagrams, badges
- [ ] Docker Compose one-command demo (`docker compose up`)
- [ ] Deploy UI (Vercel/Hugging Face Space) with a static results snapshot
- [ ] Write a blog-style `docs/results/report.md`
- [ ] LinkedIn launch (section 11)

---

## 10. GitHub README Outline

1. Title, one-line pitch, badges (CI, license, Python version)
2. Hero GIF of the dashboard
3. **Problem:** why tool descriptions decide agent behavior
4. **Key results** (table + confusion matrix before/after), filled only with real numbers
5. **How it works** (architecture diagram)
6. **Quickstart** (5 commands)
7. Benchmark design (task schema, splits, metrics)
8. Optimizer and proof methodology (leakage prevention)
9. Reproducing results
10. Limitations and threats to validity (small task set, simulated servers, model version drift)
11. Roadmap, contributing, citation, license

**Repo hygiene:** pinned dependencies, tagged releases (`v0.1.0` benchmark, `v1.0.0` full), issue templates, and a `CITATION.cff`.

---

## 11. LinkedIn Launch Plan

### Assets to prepare
- 60-90s demo video (confusion matrix, optimizer diff, proof card)
- 3-4 images: before/after confusion matrix, proof card, architecture diagram, dashboard screenshot
- Link to the GitHub repo and live demo

### Post template (fill brackets with your real results)
> I just open-sourced **MCP Tool Discovery Optimizer**, a benchmark and optimizer for how AI agents choose tools.
>
> The problem: agents pick MCP tools using only names, descriptions, and schemas. Vague wording quietly causes wrong tool calls and broken workflows, and few teams measure it.
>
> What I built:
> - A labeled benchmark of [N] tasks across [N] MCP servers and [N] tools
> - Scoring for tool selection, argument correctness, and call order
> - A published confusion matrix showing exactly which tools get mixed up
> - An optimizer that rewrites names, descriptions, schemas, and examples
> - A proof engine that tests every change on held-out tasks with paired statistics
> - A dashboard to explore traces, confusions, and patches
>
> Results: task success moved from [X%] to [Y%] on the held-out set ([CI], p = [value]), with [N] of [M] proposed edits accepted and [K] rejected for not holding up.
>
> Biggest lesson: [one real, specific finding].
>
> Stack: Python, MCP SDK, FastAPI, MLflow, Next.js.
> Repo + demo: [links]
>
> I'm a Computer Engineering graduate focused on applied ML and LLM evaluation, and I'm open to Data Science, AI, and Data Engineering roles. Feedback welcome.
>
> #AI #LLM #MCP #AgenticAI #MLOps #OpenSource

### Follow-up content (build a series)
1. Post 1: launch announcement
2. Post 2: the most surprising confusion pair and the one-line fix
3. Post 3: "Why I didn't trust my own improvement" (leakage checks and held-out proof)
4. Post 4: lessons and a call for contributors with a "bring your own MCP server" challenge

Tip: put the image of the confusion matrix first, and pin the repo in your GitHub profile and the LinkedIn Featured section.

---

## 12. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Overfitting descriptions to the benchmark | Sealed test split, overlap check, report the train-dev-test gap |
| Non-deterministic LLM output | Fixed temperature, multiple seeds, caching, CIs |
| Small test set, weak significance | 300+ tasks, paired tests, state limits openly |
| API cost | Cache runs, use cheaper models for dev loops, budget caps in config |
| Simulated servers feel artificial | Add 1-2 real public MCP servers as an external validity check |
| Model version drift | Record exact model IDs and dates with every run |

---

## 13. Portfolio Checklist (before posting)

- [ ] All reported numbers reproducible from `make reproduce`
- [ ] Raw traces and `splits.json` committed (or released as an artifact)
- [ ] No API keys in history
- [ ] README results match the latest tagged run
- [ ] Demo video under 90 seconds
- [ ] Limitations section written

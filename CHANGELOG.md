# Changelog

## Unreleased

- **Breaking:** `scope.dataset` is renamed to `scope.source` (schema, all
  spec/tests/ fixtures, examples/components.json, and every reference in
  spec/component.md and README.md). ORC's name and its `domain_knowledge`/
  custom types always allowed grounding a component in something other than
  a table, but the tagline, the README's opening framing, and every field
  and example still said "dataset" -- so that's what a reader actually saw.
  `source` is domain-neutral on its face; `spec/component.md`'s
  `domain_knowledge` section now also shows a component grounded in a
  contract template alongside the usual dataset-grounded one, so the
  breadth is demonstrated, not just claimed. Resolution of `source` is
  still entirely up to the consuming system, unchanged.
- README's "Why OpenReasoningComponents?" makes the actual rationale explicit:
  computing a number correctly and that number being the right conclusion
  are different things, and this spec has no way to check a claim for you --
  it standardizes the shape of a trustworthy statement (`evidence`,
  `provenance`), not whether any particular one is true. That's the
  producer's job, not the format's.
- `examples/eval.py` gains `--results-json` (structured per-condition results:
  avg_tokens, avg_score, n_scored) and `--chart` (a grouped bar chart rendered
  from the same data, needs `pip install matplotlib`). Unlike `eval_results.png`
  -- a committed screenshot with no script behind it -- a chart from `--chart`
  is reproducible from this repo alone. Both are no-ops under `--dry-run`,
  where there are no real scores yet.
- `examples/eval.py`'s default baseline is no longer a full CSV dump. Nobody
  hands an LLM the entire raw table on every question, so `raw_data` was a
  strawman comparison. The new default condition, `profile`, is a schema,
  summary statistics, and a small random sample of rows -- the shape of
  context a `df.describe()` + `df.sample()` step, or a lightweight
  BI-copilot, would actually send. It stays close to flat as the dataset
  grows (~1,071 characters at 500 rows, ~1,101 at 5,000), unlike a full dump
  (~19.5k at 500 rows, ~197k at 5,000). The old full-dump condition still
  exists, as `raw_data_full_dump`, behind `--include-raw-dump`, as an
  explicit naive upper bound rather than the headline comparison.
- `examples/eval.py` now defaults to `--dataset churn`: a synthetic
  customer-churn dataset at configurable sizes (`--sizes`), generated and
  turned into `components`-format statements entirely within this script --
  no external system, checkout, or network access required beyond the
  Anthropic API. `--dataset iris` keeps the original, single-size demo
  unchanged. Adds `--trials`, `--judge-model` (a same-model judge is biased;
  the summary now warns when none is given), and `--dry-run` (build every
  prompt and report its size with no API call, so the dataset-size scaling
  claim can be checked without an `ANTHROPIC_API_KEY`).

## v0.1 (unreleased)

- New machine-readable contract: [`spec/component.schema.json`](spec/component.schema.json)
  (JSON Schema 2020-12), formalizing the field table in `spec/component.md`. `type` and
  `relations[].type` remain open strings (pattern-checked, not closed enums), per the
  spec's "systems may define additional types" language.
- New fixture-based conformance suite: [`spec/tests/`](spec/tests/), run by
  `spec/tests/test_conformance.py`.
- New optional `provenance` fields: `derivation` and `derivation_version`, letting a
  component cite the external, versioned computation that produced it (e.g. an Open
  Derivation Spec derivation and its content-hash version), so a consumer can check
  freshness without this spec needing any refresh machinery of its own. Backward
  compatible: both are optional, and existing components without them are unaffected.
- `examples/components.json` renamed its `odc-examples/` ids to `orc-examples/`,
  finishing the OpenDataComponents → OpenReasoningComponents rename that the rest of the
  repo already went through.

No breaking changes to the v0 draft fields at the time this section was
written; see the `scope.dataset` → `scope.source` rename under Unreleased
above for the one that came after.

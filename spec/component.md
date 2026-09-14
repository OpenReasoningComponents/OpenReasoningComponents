# Component

**Status:** v0, schema-backed. See [`component.schema.json`](./component.schema.json) and [`CHANGELOG.md`](../CHANGELOG.md).

---

## Overview

A **Component** is a self-contained unit of knowledge grounded in a source and designed to be embedded in LLM reasoning. A source is deliberately broad: a database, a document corpus, a codebase, a trained model, or a person's stated judgment can all ground a component. Several of the types below (`column`, `metric`, `slice`, `distribution`, `threshold_rule`, `segment`) are shaped specifically for structured data, because that is where a wrong, confidently-stated number tends to do the most damage -- but nothing about the format requires a component to come from a dataset. `domain_knowledge` and custom types exist precisely for grounding that isn't.

Components are the single abstraction in OpenReasoningComponents. Everything — from a column definition to a complex multi-variable relationship to a Bayesian prior — is a component. Components reference other components through typed, directed edges, and any collection of components forms a directed graph at varying levels of complexity.

A component's **statement** is its canonical representation — a natural language description of what the component captures. The statement is what gets woven into a chain of thought and reasoned over by humans and AI systems. All other fields are auxiliary: structured metadata that supports retrieval, filtering, validation, and programmatic operations.

Components are self-contained. A component can exist and be interpreted on its own.

---

## Component Schema

| Field        | Type     | Required | Description                                                           |
|--------------|----------|----------|-----------------------------------------------------------------------|
| `id`         | string   | yes      | Namespaced identifier (see [Identifiers](#identifiers)).              |
| `type`       | string   | yes      | Component type (see [Component Types](#component-types)).             |
| `scope`      | object   | yes      | Source grounding (see [Scope](#scope)).                               |
| `statement`  | string   | yes      | Natural language description. **This is the canonical representation.** |
| `relations`  | array    | no       | Directed edges to other components (see [Relations](#relations)).     |
| `structure`  | object   | no       | Auxiliary structured metadata (see [Structure](#structure)).          |
| `evidence`   | object   | no       | Statistical or empirical support (see [Evidence](#evidence)).         |
| `provenance` | object   | no       | Origin and generation metadata (see [Provenance](#provenance)).       |
| `metadata`   | object   | no       | Arbitrary key-value pairs for system- or application-specific use.    |

---

## Identifiers

Every component is identified by a namespaced string of the form:

```
<namespace>/<name>
```

The **namespace** identifies the system or organization that produced the component. The **name** identifies the component within that namespace.

Examples:

```
intelligible/customers_discount
intelligible/churn_discount_threshold
trinity/shipment_delay_distribution
```

### Identifier Rules

- Identifiers are case-sensitive.
- `namespace` must match `[a-z0-9][a-z0-9_.-]*`.
- `name` must match `[a-z0-9][a-z0-9_.]*`.
- The `/` separator appears exactly once.
- Namespaces must be unique across systems producing components. The specification does not prescribe how namespaces are allocated.

---

## Scope

Every component is grounded in a source.

| Field    | Type   | Required | Description              |
|----------|--------|----------|---------------------------|
| `source` | string | yes      | Identifier of the source. |

Scope is a plain string. Its resolution — mapping to a catalog entry, a file path, a database schema, a document, or anything else — is the responsibility of the system using the component. A source is not necessarily a dataset: `customer_churn` below is one, but a source string can just as well name a document corpus, a codebase, or a person.

Table-level grounding, when the source *is* tabular, is expressed through the component graph: a column component's statement and structure identify its table, and components that depend on those columns inherit table context through their relations.

Example:

```json
{
  "source": "customer_churn"
}
```

---

## Relations

Components connect to other components through typed, directed edges. Every edge points from the current component to a target component.

| Field       | Type   | Required | Description                     |
|-------------|--------|----------|---------------------------------|
| `type`      | string | yes      | Relationship type.              |
| `target_id` | string | yes      | Component ID of the target.     |

### Relation Types

The v0 specification defines the following relation types.

**`depends_on`** — this component depends on the target. When the target is refreshed, this component must also be refreshed. This is the primary edge type in the component graph.

**`derived_from`** — this component was generated from the target. Implies a dependency: if the target changes, this component must be refreshed. Use `derived_from` instead of `depends_on` when the relationship is generative (e.g., a posterior derived from a prior, a model component extracted from a trained model).

**`supports`** — this component provides evidence for the target. Does not imply a refresh dependency. The direction is from evidence to claim: "this component supports that component."

All three types are directed. `depends_on` and `derived_from` point toward upstream dependencies. `supports` points toward downstream claims. Systems may define additional relation types as needed.

### Refresh Ordering

When underlying data changes, components must be refreshed in dependency order. The `depends_on` and `derived_from` edges define this order:

1. Identify the components directly affected by the data change.
2. Traverse `depends_on` and `derived_from` edges forward to find all downstream components.
3. Refresh in topological order — a component is refreshed only after all its dependencies have been refreshed.

### Example

```json
{
  "relations": [
    { "type": "depends_on", "target_id": "intelligible/customers_discount" },
    { "type": "depends_on", "target_id": "intelligible/customers_churn" },
    { "type": "depends_on", "target_id": "intelligible/discount_distribution" }
  ]
}
```

Relations are stored as a flat list. Systems construct the directed graph at processing time.

---

## Component Types

The `type` field classifies what a component represents. The v0 specification defines the following types.

### `column`

A column or field within a table.

```json
{
  "id": "intelligible/customers_discount",
  "type": "column",
  "scope": { "source": "customer_churn" },
  "statement": "discount is a float column in the customers table representing the discount rate applied to a customer's contract, ranging from 0% to 35%.",
  "structure": {
    "table": "customers",
    "column_name": "discount",
    "data_type": "float"
  }
}
```

### `metric`

A named measure or KPI derived from the dataset.

```json
{
  "id": "intelligible/monthly_churn_rate",
  "type": "metric",
  "scope": { "source": "customer_churn" },
  "statement": "Monthly churn rate is the fraction of customers who churned in a given month.",
  "structure": {
    "expression": "count(churned) / count(*)"
  }
}
```

### `slice`

A named subset of the dataset defined by filter conditions.

```json
{
  "id": "intelligible/high_value_customers",
  "type": "slice",
  "scope": { "source": "customer_churn" },
  "statement": "High-value customers are those in the customers table with lifetime value above $10,000.",
  "structure": {
    "table": "customers",
    "filter": "ltv > 10000"
  }
}
```

### `distribution`

A description of the distribution of a variable.

```json
{
  "id": "intelligible/discount_distribution",
  "type": "distribution",
  "scope": { "source": "customer_churn" },
  "statement": "Customer discounts range from 0% to 35%, with a median of 12%.",
  "relations": [
    { "type": "depends_on", "target_id": "intelligible/customers_discount" }
  ],
  "structure": {
    "variable": "discount",
    "stats": {
      "min": 0.0,
      "max": 0.35,
      "median": 0.12,
      "mean": 0.13,
      "std": 0.08
    }
  },
  "evidence": {
    "sample_size": 4821
  }
}
```

### `statistical_association`

A measured association between two or more variables.

```json
{
  "id": "intelligible/charges_churn_association",
  "type": "statistical_association",
  "scope": { "source": "customer_churn" },
  "statement": "Monthly charges and churn are positively associated.",
  "relations": [
    { "type": "depends_on", "target_id": "intelligible/customers_monthly_charges" },
    { "type": "depends_on", "target_id": "intelligible/customers_churn" }
  ],
  "structure": {
    "variables": ["monthly_charges", "churn"],
    "direction": "positive"
  },
  "evidence": {
    "pearson_r": 0.35,
    "sample_size": 7043
  }
}
```

### `threshold_rule`

A relationship defined by a boundary value on a feature.

```json
{
  "id": "intelligible/churn_discount_threshold",
  "type": "threshold_rule",
  "scope": { "source": "customer_churn" },
  "statement": "Customers receiving discounts above 20% churn substantially more often.",
  "relations": [
    { "type": "depends_on", "target_id": "intelligible/customers_discount" },
    { "type": "depends_on", "target_id": "intelligible/customers_churn" },
    { "type": "depends_on", "target_id": "intelligible/discount_distribution" }
  ],
  "structure": {
    "feature": "discount",
    "threshold": 0.20,
    "direction": "above"
  },
  "evidence": {
    "odds_ratio": 1.7,
    "sample_size": 4821
  }
}
```

### `model_component`

A relationship extracted from a predictive model.

```json
{
  "id": "intelligible/tenure_churn_shape",
  "type": "model_component",
  "scope": { "source": "customer_churn" },
  "statement": "Tenure has a nonlinear protective effect on churn, strongest in the first 12 months.",
  "relations": [
    { "type": "depends_on", "target_id": "intelligible/customers_tenure" }
  ],
  "structure": {
    "feature": "tenure",
    "shape": [
      { "x": 0, "y": 0.45 },
      { "x": 12, "y": 0.15 },
      { "x": 48, "y": 0.06 }
    ]
  },
  "provenance": {
    "source": "derived",
    "method": "ebm_extract",
    "model": "churn_model_v2"
  }
}
```

### `domain_knowledge`

A human-authored assertion grounded in its source. Unlike `column`/`metric`/`slice`/`distribution`/`threshold_rule`/`segment`, nothing about this type implies a tabular source -- it's the type for knowledge grounded in a document, a policy, a codebase, or a person's judgment, as much as in a dataset. Two examples, one of each:

```json
{
  "id": "intelligible/month_to_month_risk",
  "type": "domain_knowledge",
  "scope": { "source": "customer_churn" },
  "statement": "Customers on month-to-month contracts should be treated as higher churn risk regardless of other features.",
  "relations": [
    { "type": "depends_on", "target_id": "intelligible/customers_contract_type" }
  ],
  "provenance": {
    "source": "human",
    "author": "analyst@example.com"
  }
}
```

```json
{
  "id": "acme-legal/indemnification_cap_standard",
  "type": "domain_knowledge",
  "scope": { "source": "vendor_msa_template_v3" },
  "statement": "An indemnification liability cap below 1x annual contract value should be flagged for legal review before a vendor agreement is signed.",
  "provenance": {
    "source": "human",
    "author": "legal@example.com"
  }
}
```

The second component's `source` names a contract template, not a dataset -- nothing in the schema distinguishes the two cases.

### `segment`

A characterization of a distinct group or cluster.

```json
{
  "id": "intelligible/loyal_fiber_segment",
  "type": "segment",
  "scope": { "source": "customer_churn" },
  "statement": "A segment of long-tenure fiber optic customers with high monthly charges shows low churn.",
  "structure": {
    "conditions": [
      { "feature": "tenure", "operator": ">", "value": 36 },
      { "feature": "internet_service", "operator": "=", "value": "fiber_optic" },
      { "feature": "monthly_charges", "operator": ">", "value": 90 }
    ]
  },
  "evidence": {
    "segment_size": 812,
    "churn_rate": 0.04,
    "sample_size": 7043
  }
}
```

### Custom Types

Systems may define additional component types. Custom types should use a namespaced identifier (e.g., `x_interaction_effect`) and follow the same schema conventions.

---

## Structure

The `structure` field provides auxiliary structured metadata about the component. It supports programmatic operations — filtering, comparison, retrieval, validation — but is not the canonical representation. The **statement** is canonical.

Structure has no required fields and no prescribed schema. Its contents are determined by the component's `type`. The examples above illustrate the expected structure for each v0 type.

When `structure` is omitted, the component's statement is the sole representation.

---

## Evidence

The `evidence` field provides statistical or empirical support for the component.

Evidence is a free-form object. Systems include whichever fields are meaningful for the component type and analytical method. The specification does not prescribe a statistical framework — frequentist, Bayesian, and other approaches are equally valid.

When `evidence` is omitted, the component is treated as an unsupported assertion.

---

## Provenance

The `provenance` field describes how the component was generated.

| Field              | Type   | Required | Description                                             |
|--------------------|--------|----------|---------------------------------------------------------|
| `source`           | string | no       | Origin category: `derived`, `human`, or a custom value. |
| `method`           | string | no       | Generation method or tool identifier.                   |
| `model`            | string | no       | Identifier of the model used, if applicable.            |
| `author`           | string | no       | Author identifier, if human-authored.                   |
| `timestamp`        | string | no       | ISO 8601 timestamp of generation.                       |
| `derivation`       | string | no       | Identifier of the external, versioned computation that produced this component (e.g. an Open Derivation Spec derivation name), if any. |
| `derivation_version` | string | no     | That derivation's content-hash (or equivalent) version at generation time. |

All fields are optional. Additional fields may be included as needed.

`derivation`/`derivation_version` are the seam a producing system uses to make a
component's freshness checkable without this spec needing any refresh machinery of its
own: a consumer that can re-derive or look up the named derivation's *current* version
can compare it against `derivation_version` and know, without re-running any statistics,
whether the component is still current. A component with no `derivation` is either
hand-authored (see `domain_knowledge`) or was produced by a system that isn't tracking
its own computation this way; both are valid, they just forgo this check.

---

## Validation

The machine-readable contract is [`component.schema.json`](./component.schema.json), a
[JSON Schema 2020-12](https://json-schema.org/draft/2020-12/schema) document. Where this
prose and the schema disagree, **the schema is authoritative**. The [`tests/`](./tests/)
directory is a fixture-based conformance suite (`{description, data, valid}` per file,
run by `tests/test_conformance.py`) that any implementation, in any language, can run
against the schema directly.

---

## Usage

Components are designed to be composed into LLM reasoning prompts. A system retrieves relevant components and presents their statements as grounded context for inference.

Because statements are natural language, they integrate directly into a chain of thought — the model reasons over them the same way it reasons over any other premise. The `structure`, `evidence`, and `relations` fields serve the upstream pipeline: retrieval, selection, refresh ordering, and validation. The **statement** is what reaches the reasoning process.

Example prompt:

```
You are analyzing customer churn for the customer_churn dataset.
The following facts are known:

- discount is a float column in the customers table representing the discount
  rate applied to a customer's contract, ranging from 0% to 35%.
- churn is a boolean column in the customers table indicating whether the
  customer churned.
- Customer discounts range from 0% to 35%, with a median of 12%.
- Customers receiving discounts above 20% churn substantially more often.
- Tenure has a nonlinear protective effect on churn, strongest in the first
  12 months.

Given these facts, which customers should be prioritized for a retention
campaign?
```

Each bullet is a component's `statement`. The model reasons over natural language grounded in source-backed evidence — no raw data needed.

---

## Full Example

```json
{
  "id": "intelligible/churn_discount_threshold",
  "type": "threshold_rule",
  "scope": { "source": "customer_churn" },
  "statement": "Customers receiving discounts above 20% churn substantially more often.",
  "relations": [
    { "type": "depends_on", "target_id": "intelligible/customers_discount" },
    { "type": "depends_on", "target_id": "intelligible/customers_churn" },
    { "type": "depends_on", "target_id": "intelligible/discount_distribution" }
  ],
  "structure": {
    "feature": "discount",
    "threshold": 0.20,
    "direction": "above"
  },
  "evidence": {
    "odds_ratio": 1.7,
    "sample_size": 4821,
    "p_value": 0.0003,
    "ci_lower": 1.3,
    "ci_upper": 2.2
  },
  "provenance": {
    "source": "derived",
    "method": "component_generator",
    "timestamp": "2026-03-15T10:00:00Z"
  }
}
```

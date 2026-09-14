"""
Generate OpenReasoningComponents from the sklearn Iris dataset.

Produces column, distribution, association, and segment components
and writes them as JSON. The output can be consumed by prompt.py.

Usage:
    python examples/generate.py
    python examples/generate.py -o components.json
"""

import argparse
import json
from datetime import datetime, timezone

import numpy as np
from sklearn.datasets import load_iris
from scipy import stats


NAMESPACE = "orc-examples"
DATASET = "iris"
TABLE = "iris"
TIMESTAMP = datetime.now(timezone.utc).isoformat()


def make_component(name, type, statement, **kwargs):
    c = {
        "id": f"{NAMESPACE}/{name}",
        "type": type,
        "scope": {"source": DATASET},
        "statement": statement,
    }
    for key in ("relations", "structure", "evidence", "provenance"):
        if key in kwargs:
            c[key] = kwargs[key]
    return c


def col_id(feature_name):
    return feature_name.replace(" ", "_").replace("(", "").replace(")", "")


def column_components(iris):
    components = []
    for i, name in enumerate(iris.feature_names):
        vals = iris.data[:, i]
        components.append(make_component(
            name=col_id(name),
            type="column",
            statement=(
                f"{name} is a continuous feature in the {TABLE} table, "
                f"ranging from {vals.min():.1f} to {vals.max():.1f} cm."
            ),
            structure={
                "table": TABLE,
                "column_name": name,
                "data_type": "float",
            },
        ))

    components.append(make_component(
        name="species",
        type="column",
        statement=(
            f"species is a categorical target variable in the {TABLE} table "
            f"with three classes: {', '.join(iris.target_names)}."
        ),
        structure={
            "table": TABLE,
            "column_name": "species",
            "data_type": "categorical",
            "categories": list(iris.target_names),
        },
    ))

    return components


def distribution_components(iris):
    components = []
    for i, name in enumerate(iris.feature_names):
        cid = col_id(name)
        vals = iris.data[:, i]
        components.append(make_component(
            name=f"{cid}_distribution",
            type="distribution",
            statement=(
                f"{name} has a mean of {vals.mean():.2f} cm "
                f"and standard deviation of {vals.std():.2f} cm "
                f"across {len(vals)} samples."
            ),
            relations=[
                {"type": "depends_on", "target_id": f"{NAMESPACE}/{cid}"},
            ],
            structure={
                "variable": name,
                "stats": {
                    "mean": round(float(vals.mean()), 3),
                    "std": round(float(vals.std()), 3),
                    "min": round(float(vals.min()), 1),
                    "max": round(float(vals.max()), 1),
                    "median": round(float(np.median(vals)), 2),
                },
            },
            evidence={"sample_size": len(vals)},
        ))
    return components


def association_components(iris):
    components = []
    names = iris.feature_names
    n = len(names)

    for i in range(n):
        for j in range(i + 1, n):
            r, p = stats.pearsonr(iris.data[:, i], iris.data[:, j])
            if abs(r) < 0.5:
                continue

            a, b = col_id(names[i]), col_id(names[j])
            direction = "positive" if r > 0 else "negative"
            strength = "strongly" if abs(r) > 0.8 else "moderately"

            components.append(make_component(
                name=f"{a}__{b}_association",
                type="statistical_association",
                statement=(
                    f"{names[i]} and {names[j]} are "
                    f"{strength} {direction}ly correlated."
                ),
                relations=[
                    {"type": "depends_on", "target_id": f"{NAMESPACE}/{a}"},
                    {"type": "depends_on", "target_id": f"{NAMESPACE}/{b}"},
                ],
                structure={
                    "variables": [names[i], names[j]],
                    "direction": direction,
                },
                evidence={
                    "pearson_r": round(float(r), 3),
                    "p_value": round(float(p), 6),
                    "sample_size": len(iris.data),
                },
            ))
    return components


def segment_components(iris):
    components = []

    for idx, name in enumerate(iris.target_names):
        mask = iris.target == idx
        subset = iris.data[mask]

        means = subset.mean(axis=0)
        global_means = iris.data.mean(axis=0)
        diffs = means - global_means
        most_distinct = int(np.argmax(np.abs(diffs)))
        feat_name = iris.feature_names[most_distinct]
        direction = "higher" if diffs[most_distinct] > 0 else "lower"

        components.append(make_component(
            name=f"segment_{name}",
            type="segment",
            statement=(
                f"{name.capitalize()} samples (n={mask.sum()}) are "
                f"characterized by {direction} {feat_name} "
                f"(mean {means[most_distinct]:.2f} cm vs. "
                f"global mean {global_means[most_distinct]:.2f} cm)."
            ),
            relations=[
                {"type": "depends_on", "target_id": f"{NAMESPACE}/species"},
            ] + [
                {"type": "depends_on", "target_id": f"{NAMESPACE}/{col_id(fn)}"}
                for fn in iris.feature_names
            ],
            structure={
                "species": name,
                "segment_size": int(mask.sum()),
            },
            evidence={
                "segment_size": int(mask.sum()),
                "sample_size": len(iris.data),
            },
        ))

    return components


def main():
    parser = argparse.ArgumentParser(
        description="Generate ORC components from the Iris dataset."
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path. Prints to stdout if omitted.",
    )
    args = parser.parse_args()

    iris = load_iris()

    components = []
    components.extend(column_components(iris))
    components.extend(distribution_components(iris))
    components.extend(association_components(iris))
    components.extend(segment_components(iris))

    output = json.dumps(components, indent=2)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
            f.write("\n")
        print(f"Wrote {len(components)} components to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()

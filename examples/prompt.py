"""
Read OpenReasoningComponents from JSON and build a prompt.

Demonstrates the consumer side of ORC: load components, optionally
filter by type or query, resolve the dependency graph, and assemble
statements into a prompt ready for an LLM.

Usage:
    python examples/prompt.py examples/components.json
    python examples/prompt.py examples/components.json --type column distribution
    python examples/prompt.py examples/components.json --query "petal length"
    python examples/prompt.py examples/components.json --id orc-examples/segment_virginica
"""

import argparse
import json
import sys
from collections import defaultdict


def load_components(path):
    with open(path) as f:
        return json.load(f)


def build_index(components):
    """Index components by id for dependency resolution."""
    return {c["id"]: c for c in components}


def resolve_dependencies(component, index, seen=None):
    """Walk depends_on/derived_from edges and collect all upstream components."""
    if seen is None:
        seen = set()

    deps = []
    for rel in component.get("relations", []):
        if rel["type"] not in ("depends_on", "derived_from"):
            continue
        tid = rel["target_id"]
        if tid in seen or tid not in index:
            continue
        seen.add(tid)
        # recurse upstream first
        deps.extend(resolve_dependencies(index[tid], index, seen))
        deps.append(index[tid])

    return deps


def filter_by_type(components, types):
    return [c for c in components if c["type"] in types]


def filter_by_query(components, query):
    """Simple substring match on statement."""
    q = query.lower()
    return [c for c in components if q in c["statement"].lower()]


def filter_by_id(components, ids):
    id_set = set(ids)
    return [c for c in components if c["id"] in id_set]


def build_prompt(components, index, source=None):
    """Assemble a prompt from selected components plus their dependencies."""

    # collect selected + all upstream deps, deduplicated, in dependency order
    seen = set()
    ordered = []

    for c in components:
        upstream = resolve_dependencies(c, index, seen.copy())
        for dep in upstream:
            if dep["id"] not in seen:
                seen.add(dep["id"])
                ordered.append(dep)
        if c["id"] not in seen:
            seen.add(c["id"])
            ordered.append(c)

    if not ordered:
        return "No components selected."

    if source is None:
        source = ordered[0].get("scope", {}).get("source", "unknown")

    lines = [f"You are reasoning about {source}."]
    lines.append("The following facts are known:")
    lines.append("")
    for c in ordered:
        lines.append(f"- {c['statement']}")
    lines.append("")
    lines.append("Given these facts, what patterns and insights can you identify?")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Read ORC components and build a prompt."
    )
    parser.add_argument("input", help="Path to components JSON file.")
    parser.add_argument(
        "--type", nargs="+",
        help="Filter to specific component types.",
    )
    parser.add_argument(
        "--query", "-q",
        help="Filter to components whose statement matches a substring.",
    )
    parser.add_argument(
        "--id", nargs="+",
        help="Select specific component IDs.",
    )
    args = parser.parse_args()

    all_components = load_components(args.input)
    index = build_index(all_components)

    # start with all, then narrow
    selected = all_components

    if args.type:
        selected = filter_by_type(selected, args.type)
    if args.query:
        selected = filter_by_query(selected, args.query)
    if args.id:
        selected = filter_by_id(selected, args.id)

    prompt = build_prompt(selected, index)
    print(prompt)

    print(f"\n--- {len(selected)} components selected, "
          f"{len(all_components)} total ---")


if __name__ == "__main__":
    main()

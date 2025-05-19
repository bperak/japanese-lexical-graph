import math
import pytest

from app import get_graph


def test_edge_weight_mapping():
    """Ensure that at least some edges expose a numeric 'weight' attribute."""
    G = get_graph()
    assert G.number_of_edges() > 0, "Graph should contain edges"

    # Gather a representative sample (up to 1000 edges) – works for MultiGraph & Graph.
    if G.is_multigraph():
        edge_iter = G.edges(data=True, keys=True)
    else:
        edge_iter = ((u, v, 0, data) for u, v, data in G.edges(data=True))

    sample = []
    for idx, edge in enumerate(edge_iter):
        if idx >= 1000:
            break
        sample.append(edge)

    assert sample, "Graph sampling failed – no edges collected"
    # At least one edge should expose a usable numeric weight, either via the dedicated 'weight'
    # attribute (preferred) or via nested synonym/antonym strength fields for legacy edges.
    def extract_weight(attr: dict):
        if "weight" in attr and isinstance(attr["weight"], (int, float)):
            return attr["weight"]
        if "synonym" in attr and isinstance(attr["synonym"], dict):
            return attr["synonym"].get("synonym_strength")
        if "antonym" in attr and isinstance(attr["antonym"], dict):
            return attr["antonym"].get("antonym_strength")
        return None

    assert any(
        (
            isinstance(weight := extract_weight(data), (int, float))
            and not (isinstance(weight, float) and math.isnan(weight))
        )
        for *_ignore, data in sample
    ), "No valid edge weight found on sampled edges – mapping logic may have failed." 
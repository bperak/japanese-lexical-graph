#!/usr/bin/env python
"""update_nodes_from_spreadsheet.py

Populate or enrich the Japanese lexical graph with metadata coming from an
external spreadsheet (Google Sheets exported as XLSX).

The script **does not** touch edges – it only ensures that every entry from the
spreadsheet exists as a node and that it carries the specified attributes.
Existing attributes are preserved unless they are empty/None, in which case the
value from the spreadsheet is filled in.

Attributes written to each node
-------------------------------
* hiragana – converted from the `読み` column (katakana → hiragana)
* vocab_level – raw value from `語彙の難易度`
* POS – `品詞2(詳細)` (fine-grained part-of-speech) – only set when missing
* pos_category – `品詞1`
* word_type – `語種`

Usage (PowerShell) – default arguments usually suffice:

    python update_nodes_from_spreadsheet.py \
        --url "https://docs.google.com/.../pub?output=xlsx" \
        --graph graph_models/G_synonyms_2024_09_18.pickle \
        --output graph_models/G_synonyms_2024_09_18_updated.pkl

If you omit `--output`, the original pickle is overwritten **after** a timestamped
backup file is created in the same directory.

The script is Windows-friendly and avoids using shell-specific features – simply
run it with the standard Python interpreter.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import pickle
import shutil
import sys
from typing import Dict

import networkx as nx
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_URL = (
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vQnM4MbKn20qbgU4G5wdK8-HYsTf-"
    "TELaqWgWxW0mzW5GJrVph_6eb_ECEHDotTDw/pub?output=xlsx"
)
DEFAULT_GRAPH_PATHS = [
    os.path.join("graph_models", "G_synonyms_2024_09_18.pickle"),
    "G_synonyms_2024_09_18.pickle",
]

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _katakana_to_hiragana(text: str) -> str:
    """Convert katakana characters in *text* to their hiragana equivalents.

    This keeps non-katakana characters untouched. The conversion relies on the
    fact that katakana (0x30A0-0x30FF) and hiragana (0x3040-0x309F) blocks are
    offset by +0x60.
    """
    if not text:
        return text
    result_chars = []
    for ch in text:
        code = ord(ch)
        # Katakana range (includes punctuation like ヽ, but that is harmless)
        if 0x30A1 <= code <= 0x30F4:
            result_chars.append(chr(code - 0x60))
        else:
            result_chars.append(ch)
    return "".join(result_chars)


def _resolve_graph_path(path: str | None = None) -> str:
    """Return an existing pickle path or raise *FileNotFoundError*."""
    if path:
        if os.path.exists(path):
            return path
        raise FileNotFoundError(f"Graph pickle not found: {path}")

    for candidate in DEFAULT_GRAPH_PATHS:
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError(
        "Could not locate the graph pickle. Provide --graph explicitly."
    )


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def build_attribute_dict(row: pd.Series) -> Dict[str, str]:
    """Map a spreadsheet *row* to the node attribute dictionary."""
    reading = str(row["読み"]).strip()
    return {
        "hiragana": _katakana_to_hiragana(reading),
        "vocab_level": str(row["語彙の難易度"]).strip(),
        "POS": str(row["品詞2(詳細)"]).strip(),
        "pos_category": str(row["品詞1"]).strip(),
        "word_type": str(row["語種"]).strip(),
    }


def update_graph_from_df(G: nx.Graph, df: pd.DataFrame) -> Dict[str, int]:
    """Update *G* with info from *df*.

    Returns a dict with statistics (nodes_added, nodes_updated, attributes_added).
    """
    stats = {
        "nodes_added": 0,
        "nodes_updated": 0,
        "attributes_added": 0,
    }

    for _, row in df.iterrows():
        node_id = str(row["標準的な表記"]).strip()
        if not node_id:
            continue  # Skip malformed rows
        attrs = build_attribute_dict(row)

        if node_id in G:
            node_data = G.nodes[node_id]
            attr_added_this_node = 0
            for k, v in attrs.items():
                if not v:
                    continue  # Skip empty values
                existing = node_data.get(k)
                if existing in (None, ""):
                    node_data[k] = v
                    attr_added_this_node += 1
            if attr_added_this_node:
                stats["nodes_updated"] += 1
                stats["attributes_added"] += attr_added_this_node
        else:
            # Add fresh node with all attributes
            clean_attrs = {k: v for k, v in attrs.items() if v}
            G.add_node(node_id, **clean_attrs)
            stats["nodes_added"] += 1
            stats["attributes_added"] += len(clean_attrs)

    return stats


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def backup_file(path: str) -> str:
    """Create a timestamped copy of *path* next to the original and return its name."""
    timestamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{os.path.splitext(path)[0]}_bak_{timestamp}.pickle"
    shutil.copy2(path, backup_path)
    return backup_path


def save_graph(G: nx.Graph, path: str):
    """Serialize *G* to *path* (pickle)."""
    with open(path, "wb") as f:
        pickle.dump(G, f)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update or create nodes in the lexical graph from a spreadsheet."
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="XLSX file URL")
    parser.add_argument("--graph", default=None, help="Input graph pickle path")
    parser.add_argument(
        "--output",
        default=None,
        help="Destination pickle. If omitted, overwrites --graph (with backup).",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip automatic backup when overwriting the original pickle.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None):
    args = _parse_args(argv)

    try:
        graph_path = _resolve_graph_path(args.graph)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    output_path = args.output if args.output else graph_path

    # ------------------------------------------------------------------
    # 1. Load graph
    # ------------------------------------------------------------------
    print(f"Loading graph from {graph_path} …")
    with open(graph_path, "rb") as f:
        G = pickle.load(f)
    print(
        f"Graph loaded: {G.number_of_nodes():,} nodes · {G.number_of_edges():,} edges"
    )

    # ------------------------------------------------------------------
    # 2. Read spreadsheet
    # ------------------------------------------------------------------
    print(f"Downloading spreadsheet from {args.url} …")
    df = pd.read_excel(args.url)

    required_cols = [
        "標準的な表記",
        "読み",
        "語彙の難易度",
        "品詞1",
        "品詞2(詳細)",
        "語種",
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        print(f"Error: Missing expected columns in XLSX: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    # ------------------------------------------------------------------
    # 3. Update graph
    # ------------------------------------------------------------------
    stats = update_graph_from_df(G, df)
    print(
        f"Stats – nodes added: {stats['nodes_added']}, nodes updated: {stats['nodes_updated']}, "
        f"attributes added/filled: {stats['attributes_added']}"
    )

    # ------------------------------------------------------------------
    # 4. Save
    # ------------------------------------------------------------------
    if (output_path == graph_path) and (not args.no_backup):
        backup_path = backup_file(graph_path)
        print(f"Backup saved to {backup_path}")

    save_graph(G, output_path)
    print(f"Graph saved to {output_path}")


if __name__ == "__main__":
    main() 
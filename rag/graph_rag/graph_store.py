import json
import os
import pickle
import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime


class GraphStore:
    """
    Persists and manages the knowledge graph.

    Why we need this:
    - Building the graph takes 2-5 seconds on startup
    - We do NOT want to rebuild it on every request
    - Store it to disk as a cache
    - Rebuild only when knowledge base files change

    Storage:
    - Saves graph to .cache/knowledge_graph.pkl
    - Saves metadata to .cache/graph_metadata.json
    - Invalidates cache when KB files change (via hash check)
    """

    CACHE_DIR      = Path(__file__).parent.parent.parent / ".cache"
    GRAPH_FILE     = CACHE_DIR / "knowledge_graph.pkl"
    METADATA_FILE  = CACHE_DIR / "graph_metadata.json"

    KB_FILES = [
        "knowledge_base/credit_cards.json",
        "knowledge_base/investments.json",
        "knowledge_base/stocks.json",
        "knowledge_base/systematic_rules.json"
    ]

    def __init__(self):
        self.CACHE_DIR.mkdir(exist_ok=True)

    # ─── Save Graph ───────────────────────────────────────────────────────

    def save(self, graph) -> bool:
        """
        Save the knowledge graph to disk.
        Also saves a hash of KB files to detect future changes.
        """
        try:
            # Save graph object
            with open(self.GRAPH_FILE, "wb") as f:
                pickle.dump(graph, f, protocol=pickle.HIGHEST_PROTOCOL)

            # Save metadata
            metadata = {
                "saved_at":   datetime.utcnow().isoformat(),
                "kb_hash":    self._compute_kb_hash(),
                "node_count": len(graph.nodes),
                "edge_count": len(graph.edges)
            }
            with open(self.METADATA_FILE, "w") as f:
                json.dump(metadata, f, indent=2)

            print(f"[GraphStore] Graph saved — {metadata['node_count']} nodes, {metadata['edge_count']} edges")
            return True

        except Exception as e:
            print(f"[GraphStore] Save failed: {e}")
            return False

    # ─── Load Graph ───────────────────────────────────────────────────────

    def load(self) -> Optional[object]:
        """
        Load the graph from disk if cache is valid.
        Returns None if cache is missing or stale.
        """
        if not self.GRAPH_FILE.exists():
            print("[GraphStore] No cached graph found — will build fresh")
            return None

        if not self.METADATA_FILE.exists():
            print("[GraphStore] Metadata missing — will rebuild")
            return None

        # ── Check if KB files have changed ────────────────────────────────
        try:
            with open(self.METADATA_FILE, "r") as f:
                metadata = json.load(f)

            current_hash = self._compute_kb_hash()
            saved_hash   = metadata.get("kb_hash", "")

            if current_hash != saved_hash:
                print("[GraphStore] Knowledge base changed — rebuilding graph")
                return None

        except Exception as e:
            print(f"[GraphStore] Metadata read failed: {e} — rebuilding")
            return None

        # ── Load graph from pickle ────────────────────────────────────────
        try:
            with open(self.GRAPH_FILE, "rb") as f:
                graph = pickle.load(f)

            node_count = len(graph.nodes)
            edge_count = len(graph.edges)
            saved_at   = metadata.get("saved_at", "unknown")

            print(f"[GraphStore] Graph loaded from cache — {node_count} nodes, {edge_count} edges (saved: {saved_at})")
            return graph

        except Exception as e:
            print(f"[GraphStore] Load failed: {e} — rebuilding")
            return None

    # ─── Cache Validity ───────────────────────────────────────────────────

    def is_cache_valid(self) -> bool:
        """
        Check if cached graph is still valid
        without loading the full graph object.
        """
        if not self.GRAPH_FILE.exists():
            return False

        if not self.METADATA_FILE.exists():
            return False

        try:
            with open(self.METADATA_FILE, "r") as f:
                metadata = json.load(f)

            current_hash = self._compute_kb_hash()
            saved_hash   = metadata.get("kb_hash", "")

            return current_hash == saved_hash

        except Exception:
            return False

    # ─── Clear Cache ──────────────────────────────────────────────────────

    def clear(self):
        """Delete cached graph — forces rebuild on next load."""
        if self.GRAPH_FILE.exists():
            self.GRAPH_FILE.unlink()
            print("[GraphStore] Graph cache cleared")

        if self.METADATA_FILE.exists():
            self.METADATA_FILE.unlink()
            print("[GraphStore] Graph metadata cleared")

    # ─── Get Metadata ─────────────────────────────────────────────────────

    def get_metadata(self) -> dict:
        """Get metadata about the cached graph."""
        if not self.METADATA_FILE.exists():
            return {
                "cached":     False,
                "node_count": 0,
                "edge_count": 0,
                "saved_at":   None
            }

        try:
            with open(self.METADATA_FILE, "r") as f:
                metadata = json.load(f)
            metadata["cached"] = True
            return metadata

        except Exception:
            return {"cached": False}

    # ─── KB Hash ──────────────────────────────────────────────────────────

    def _compute_kb_hash(self) -> str:
        """
        Compute a hash of all knowledge base files.
        If any file changes, the hash changes → cache invalidated.
        """
        project_root = Path(__file__).parent.parent.parent
        combined     = ""

        for kb_file in self.KB_FILES:
            file_path = project_root / kb_file
            if file_path.exists():
                try:
                    content   = file_path.read_text(encoding="utf-8")
                    combined += content
                except Exception:
                    pass

        return hashlib.md5(combined.encode()).hexdigest()


# ─── Singleton ────────────────────────────────────────────────────────────────

_store = None

def get_graph_store() -> GraphStore:
    """Get singleton GraphStore instance."""
    global _store
    if _store is None:
        _store = GraphStore()
    return _store
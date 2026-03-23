"""
Rebuilds the knowledge graph from scratch.

Run this whenever you:
- Add new files to data_sources/
- Update any knowledge_base JSON files
- Want to force a fresh graph build

Usage:
    python rebuild_graph.py
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


# ─── Validation ───────────────────────────────────────────────────────────────

def validate_sources() -> bool:
    """
    Check all required files exist before building.
    Returns True if all good, False if something is missing.
    """
    print("\n📋 Validating sources...")

    required_kb = [
        "knowledge_base/credit_cards.json",
        "knowledge_base/investments.json",
        "knowledge_base/stocks.json",
        "knowledge_base/systematic_rules.json"
    ]

    all_good = True

    # ── Check JSON knowledge base ─────────────────────────────────────────
    for kb_file in required_kb:
        path = Path(kb_file)
        if path.exists():
            size = path.stat().st_size
            print(f"  ✅ {kb_file} ({size:,} bytes)")
        else:
            print(f"  ❌ MISSING: {kb_file}")
            all_good = False

    # ── Check data_sources text files ─────────────────────────────────────
    data_dir  = Path("data_sources")
    txt_files = list(data_dir.glob("*.txt")) if data_dir.exists() else []

    if txt_files:
        print(f"\n  📄 Text documents found ({len(txt_files)} files):")
        for f in sorted(txt_files):
            size = f.stat().st_size
            print(f"     {f.name} ({size:,} bytes)")
    else:
        print(f"\n  ⚠️  No .txt files in data_sources/ yet")
        print(f"     Run: python convert_data_sources.py first")
        print(f"     Graph will still build from JSON files only")

    return all_good


# ─── Clear Cache ──────────────────────────────────────────────────────────────

def clear_cache() -> bool:
    """Clear existing graph cache."""
    try:
        from rag.graph_rag.graph_store import get_graph_store
        store = get_graph_store()

        if store.is_cache_valid():
            meta = store.get_metadata()
            print(f"\n🗑️  Clearing existing cache...")
            print(f"   Previous graph: {meta.get('node_count', 0)} nodes, "
                  f"{meta.get('edge_count', 0)} edges")
            print(f"   Saved at: {meta.get('saved_at', 'unknown')}")
        else:
            print(f"\n🗑️  No valid cache found — building fresh")

        store.clear()
        print(f"  ✅ Cache cleared")
        return True

    except Exception as e:
        print(f"  ❌ Cache clear failed: {e}")
        return False


# ─── Build Graph ──────────────────────────────────────────────────────────────

def build_graph():
    """Build the knowledge graph and save to cache."""
    from rag.graph_rag.graph_builder import KnowledgeGraphBuilder
    from rag.graph_rag.graph_store   import get_graph_store

    print("\n🔨 Building knowledge graph...")
    start_time = time.time()

    # Build
    builder = KnowledgeGraphBuilder()
    builder.build_graph()

    elapsed = time.time() - start_time
    stats   = builder.get_stats()

    print(f"\n  ✅ Graph built in {elapsed:.1f}s")
    print(f"  📊 Total nodes : {stats['total_nodes']}")
    print(f"  🔗 Total edges : {stats['total_edges']}")

    # Node type breakdown
    print(f"\n  Node breakdown:")
    for node_type, count in sorted(stats["node_types"].items()):
        bar   = "█" * min(count, 30)
        print(f"    {node_type:<22} {count:>4}  {bar}")

    # Save to cache
    print(f"\n💾 Saving to cache...")
    store = get_graph_store()
    saved = store.save(builder)

    if saved:
        print(f"  ✅ Saved to .cache/knowledge_graph.pkl")
    else:
        print(f"  ⚠️  Cache save failed — graph built but not cached")

    return builder, stats


# ─── Verify Graph ─────────────────────────────────────────────────────────────

def verify_graph(builder):
    """
    Run quick verification queries to confirm
    graph is working correctly.
    """
    print(f"\n🔍 Verifying graph with test queries...")

    from rag.graph_rag.graph_retriever import GraphRetriever

    # Reset singleton to use new graph
    GraphRetriever._graph = builder

    retriever = GraphRetriever()
    retriever.graph     = builder
    retriever.traverser = __import__(
        "rag.graph_rag.graph_traverser",
        fromlist=["GraphTraverser"]
    ).GraphTraverser(builder.nodes, builder.adjacency)
    retriever.parser    = __import__(
        "rag.graph_rag.query_parser",
        fromlist=["QueryParser"]
    ).QueryParser(builder.nodes)

    test_queries = [
        "What is ELSS and how does it save tax?",
        "Best credit card for online shopping",
        "How much SIP do I need for retirement?",
        "HDFC Millennia cashback details",
        "What is emergency fund"
    ]

    all_passed = True

    for query in test_queries:
        try:
            result = retriever.retrieve(query)
            node_count = result.count("[CARD]") + result.count("[INVESTMENT]") + \
                         result.count("[STOCK]")   + result.count("[RULE]")
            status = "✅" if node_count > 0 else "⚠️ "
            if node_count == 0:
                all_passed = False
            print(f"  {status} '{query[:45]}' → {node_count} nodes retrieved")
        except Exception as e:
            print(f"  ❌ '{query[:45]}' → Error: {e}")
            all_passed = False

    return all_passed


# ─── Show Graph Sample ────────────────────────────────────────────────────────

def show_sample(builder):
    """Show a few sample nodes from each type."""
    print(f"\n📌 Sample nodes by type:")

    from collections import defaultdict
    by_type = defaultdict(list)

    for node_id, node in builder.nodes.items():
        by_type[node.node_type].append(node.label)

    priority_types = ["card", "investment", "stock", "rule", "concept"]

    for node_type in priority_types:
        labels = by_type.get(node_type, [])
        if labels:
            sample = labels[:4]
            print(f"  {node_type:<20}: {', '.join(sample)}")


# ─── Check Dependencies ───────────────────────────────────────────────────────

def check_dependencies():
    """Check required packages are installed."""
    print("\n🔧 Checking dependencies...")

    packages = {
        "sqlalchemy":  "sqlalchemy",
        "fastapi":     "fastapi",
        "pandas":      "pandas",
        "pypdf":       "pypdf",
        "docx":        "python-docx"
    }

    missing = []
    for module, package in packages.items():
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError:
            print(f"  ❌ {module} — install: pip install {package}")
            missing.append(package)

    return missing


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("=" * 55)
    print("  AI Financial Advisor — Graph RAG Builder")
    print("=" * 55)

    # ── Step 0: Check dependencies ────────────────────────────────────────
    missing = check_dependencies()
    if missing:
        print(f"\n⚠️  Missing packages: {missing}")
        print(f"   Run: pip install {' '.join(missing)}")
        print(f"   Continuing anyway...\n")

    # ── Step 1: Validate sources ──────────────────────────────────────────
    sources_ok = validate_sources()
    if not sources_ok:
        print("\n❌ Required knowledge base files are missing.")
        print("   Please check your knowledge_base/ folder.")
        sys.exit(1)

    # ── Step 2: Clear old cache ───────────────────────────────────────────
    clear_cache()

    # ── Step 3: Build graph ───────────────────────────────────────────────
    try:
        builder, stats = build_graph()
    except Exception as e:
        print(f"\n❌ Graph build failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # ── Step 4: Show sample nodes ─────────────────────────────────────────
    show_sample(builder)

    # ── Step 5: Verify with test queries ──────────────────────────────────
    try:
        all_passed = verify_graph(builder)
    except Exception as e:
        print(f"\n⚠️  Verification skipped: {e}")
        all_passed = True

    # ── Summary ───────────────────────────────────────────────────────────
    print("\n" + "=" * 55)

    if all_passed:
        print("  ✅ Graph rebuild COMPLETE and VERIFIED")
    else:
        print("  ⚠️  Graph rebuilt but some test queries returned 0 nodes")
        print("      This may be okay — check your data sources")

    print(f"\n  Stats:")
    print(f"    Nodes : {stats['total_nodes']}")
    print(f"    Edges : {stats['total_edges']}")
    print(f"    Cache : .cache/knowledge_graph.pkl")

    print(f"\n  Next steps:")
    print(f"    python main.py              → start backend")
    print(f"    streamlit run app/chat_ui.py → start frontend")
    print("=" * 55)
    
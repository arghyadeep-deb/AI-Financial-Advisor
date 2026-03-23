import json
from typing import List, Dict, Any

from rag.graph_rag.graph_builder   import KnowledgeGraphBuilder
from rag.graph_rag.graph_traverser import GraphTraverser
from rag.graph_rag.query_parser    import QueryParser


_GRAPH_RETRIEVER_INSTANCE = None


class GraphRetriever:
    """
    Main interface for graph-based RAG retrieval.

    Pipeline:
    1. Parse query  → find intent + entry nodes
    2. Traverse     → BFS / DFS / Beam / PPR
    3. Collect      → gather node data
    4. Format       → clean context string for LLM

    Uses singleton pattern — graph is built once and reused.
    Uses GraphStore for disk caching — no rebuild on restart
    unless knowledge base files change.
    """

    _graph: KnowledgeGraphBuilder = None  # Singleton graph instance

    def __init__(self):
        if GraphRetriever._graph is None:
            self._initialize_graph()

        self.graph     = GraphRetriever._graph
        self.traverser = GraphTraverser(
            nodes     = self.graph.nodes,
            adjacency = self.graph.adjacency
        )
        self.parser    = QueryParser(self.graph.nodes)

    # ─── Graph Initialization ─────────────────────────────────────────────

    def _initialize_graph(self):
        """
        Initialize the knowledge graph.

        Order:
        1. Try loading from disk cache (fast — 0.1s)
        2. If cache invalid or missing → build fresh (slow — 2-5s)
        3. Save newly built graph to cache
        """
        from rag.graph_rag.graph_store import get_graph_store

        store  = get_graph_store()
        cached = store.load()

        if cached is not None:
            # ── Load from cache ───────────────────────────────────────────
            GraphRetriever._graph = cached
            print("[GraphRetriever] Graph loaded from cache ✓")
        else:
            # ── Build fresh graph ─────────────────────────────────────────
            print("[GraphRetriever] Building knowledge graph from scratch...")
            builder = KnowledgeGraphBuilder()
            builder.build_graph()
            GraphRetriever._graph = builder

            # Save to cache for next startup
            saved = store.save(builder)
            stats = builder.get_stats()

            if saved:
                print(f"[GraphRetriever] Graph built and cached ✓ — {stats}")
            else:
                print(f"[GraphRetriever] Graph built (cache save failed) — {stats}")

    # ─── Main Retrieval ───────────────────────────────────────────────────

    def retrieve(self, query: str, max_tokens: int = 2000) -> str:
        """
        Main retrieval method.

        Takes a user query, traverses the knowledge graph,
        and returns a formatted context string for the LLM.

        Args:
            query:      User's question or message
            max_tokens: Approximate token limit for context

        Returns:
            Formatted context string ready for LLM injection
        """

        if not query or not query.strip():
            return ""

        # ── Step 1: Parse Query ───────────────────────────────────────────
        parsed = self.parser.parse(query)

        entry_nodes = parsed["entry_nodes"]
        query_terms = parsed["query_terms"]
        strategy    = parsed["strategy"]
        max_depth   = parsed["max_depth"]
        max_results = parsed["max_results"]
        intent      = parsed["intent"]

        print(f"[GraphRetriever] Query: '{query[:50]}' | Intent: {intent} | Strategy: {strategy} | Entry nodes: {len(entry_nodes)}")

        if not entry_nodes:
            print("[GraphRetriever] No entry nodes found — returning empty context")
            return ""

        # ── Step 2: Traverse Graph ────────────────────────────────────────
        node_ids = self._traverse(
            strategy    = strategy,
            entry_nodes = entry_nodes,
            query_terms = query_terms,
            max_depth   = max_depth,
            max_results = max_results
        )

        print(f"[GraphRetriever] Traversal returned {len(node_ids)} nodes")

        if not node_ids:
            return ""

        # ── Step 3: Collect and Filter Node Data ──────────────────────────
        retrieved_nodes = self._collect_nodes(node_ids)

        print(f"[GraphRetriever] After filtering: {len(retrieved_nodes)} nodes")

        # ── Step 4: Format as LLM Context ────────────────────────────────
        context = self._format_context(
            nodes       = retrieved_nodes,
            query       = query,
            intent      = intent,
            query_terms = query_terms
        )

        return context

    # ─── Traversal Dispatcher ────────────────────────────────────────────

    def _traverse(
        self,
        strategy:    str,
        entry_nodes: List[str],
        query_terms: List[str],
        max_depth:   int,
        max_results: int
    ) -> List[str]:
        """
        Dispatch to correct traversal algorithm based on strategy.
        Always falls back to beam_search if selected algo fails.
        """

        try:
            if strategy == "beam_search":
                scored = self.traverser.beam_search(
                    start_nodes = entry_nodes,
                    query_terms = query_terms,
                    beam_width  = 5,
                    max_depth   = max_depth
                )
                return [nid for nid, _ in scored[:max_results]]

            elif strategy == "bfs":
                return self.traverser.bfs(
                    start_nodes = entry_nodes,
                    max_depth   = max_depth,
                    max_nodes   = max_results
                )

            elif strategy == "dfs":
                if not entry_nodes:
                    return []
                return self.traverser.dfs(
                    start_node = entry_nodes[0],
                    max_depth  = max_depth,
                    max_nodes  = max_results
                )

            elif strategy == "ppr":
                scored = self.traverser.personalized_pagerank(
                    seed_nodes = entry_nodes,
                    top_k      = max_results
                )
                return [nid for nid, _ in scored]

            else:
                # Unknown strategy — fall back to beam_search
                scored = self.traverser.beam_search(
                    start_nodes = entry_nodes,
                    query_terms = query_terms,
                    beam_width  = 5,
                    max_depth   = max_depth
                )
                return [nid for nid, _ in scored[:max_results]]

        except Exception as e:
            print(f"[GraphRetriever] Traversal failed ({strategy}): {e}")
            # Last resort — return entry nodes directly
            return entry_nodes

    # ─── Node Collection ─────────────────────────────────────────────────

    def _collect_nodes(self, node_ids: List[str]) -> list:
        """
        Collect node objects from IDs.
        Filters by type limits to avoid flooding context.
        Removes duplicates and low-value nodes.
        """

        # How many nodes per type to include in context
        type_limits = {
            "card":                4,
            "investment":          4,
            "stock":               3,
            "rule":                4,
            "concept":             2,
            "text_chunk":          3,
            "bank":                1,
            "sector":              1,
            "investment_category": 1,
            "risk_level":          1,
            "tier":                1
        }

        seen_types      = {}
        retrieved_nodes = []
        seen_ids        = set()

        for node_id in node_ids:
            # Skip duplicates
            if node_id in seen_ids:
                continue
            seen_ids.add(node_id)

            # Skip if node doesn't exist
            if node_id not in self.graph.nodes:
                continue

            node = self.graph.nodes[node_id]

            # Apply type limit
            type_count = seen_types.get(node.node_type, 0)
            limit      = type_limits.get(node.node_type, 2)

            if type_count >= limit:
                continue

            seen_types[node.node_type] = type_count + 1
            retrieved_nodes.append(node)

        return retrieved_nodes

    # ─── Context Formatter ────────────────────────────────────────────────

    def _format_context(
        self,
        nodes:       list,
        query:       str,
        intent:      str,
        query_terms: List[str]
    ) -> str:
        """
        Format retrieved nodes into a clean, structured
        context string for LLM injection.

        Groups nodes by type with clear section headers.
        Truncates data to avoid token overflow.
        """

        if not nodes:
            return ""

        # ── Group nodes by type ───────────────────────────────────────────
        sections = {
            "card":       [],
            "investment": [],
            "stock":      [],
            "rule":       [],
            "concept":    [],
            "text_chunk": []
        }

        for node in nodes:
            node_type = node.node_type

            if node_type not in sections:
                # Put bank, sector, tier etc. into concept bucket
                node_type = "concept"

            if node_type == "card":
                sections["card"].append(
                    self._format_card_node(node)
                )
            elif node_type == "investment":
                sections["investment"].append(
                    self._format_investment_node(node)
                )
            elif node_type == "stock":
                sections["stock"].append(
                    self._format_stock_node(node)
                )
            elif node_type == "rule":
                sections["rule"].append(
                    self._format_rule_node(node)
                )
            elif node_type == "text_chunk":
                sections["text_chunk"].append(
                    self._format_text_node(node)
                )
            else:
                # concept, bank, sector, tier, risk_level
                sections["concept"].append(
                    self._format_generic_node(node)
                )

        # ── Build Context String ──────────────────────────────────────────
        context_parts = [
            "=== KNOWLEDGE GRAPH CONTEXT (Graph RAG) ===",
            f"Query Intent  : {intent}",
            f"Terms Found   : {', '.join(query_terms[:8])}",
            f"Nodes Retrieved: {len(nodes)}",
            ""
        ]

        section_headers = {
            "card":       "💳 RELEVANT CREDIT CARDS",
            "investment": "📈 RELEVANT INVESTMENT INSTRUMENTS",
            "stock":      "📊 RELEVANT STOCKS / ETFs",
            "rule":       "📋 RELEVANT RULES & GUIDELINES",
            "concept":    "💡 RELATED CONCEPTS",
            "text_chunk": "📄 FROM KNOWLEDGE DOCUMENTS"
        }

        for section_key, items in sections.items():
            if items:
                header = section_headers.get(section_key, section_key.upper())
                context_parts.append(f"--- {header} ---")
                context_parts.extend(items)
                context_parts.append("")

        context_parts.append("=== END OF KNOWLEDGE GRAPH CONTEXT ===")

        return "\n".join(context_parts)

    # ─── Node Formatters ──────────────────────────────────────────────────

    def _format_card_node(self, node) -> str:
        """Format credit card node data."""
        d          = node.data
        name       = d.get("card_name", "")
        bank       = d.get("bank", "")
        fee        = d.get("annual_fee", d.get("renewal_fee", 0))
        best_for   = d.get("best_for", [])
        pros       = d.get("pros", [])[:2]
        cons       = d.get("cons", [])[:1]
        fee_waiver = d.get("fee_waiver", "")
        income_req = d.get("income_requirement_monthly", 0)

        return f"""
[CARD] {name} by {bank}
Annual Fee   : Rs {fee} | Fee Waiver: {fee_waiver}
Income Req   : Rs {income_req:,.0f}/month
Best For     : {best_for}
Key Pros     : {pros}
Key Cons     : {cons}
"""

    def _format_investment_node(self, node) -> str:
        """Format investment instrument node data."""
        d            = node.data
        name         = d.get("name", "")
        category     = d.get("category", "")
        risk         = d.get("risk_level", "")
        returns      = d.get("expected_return_percent", "")
        horizon      = d.get("time_horizon", "")
        liquidity    = d.get("liquidity", "")
        when_to_use  = d.get("when_to_use", "")[:180]
        pro_tip      = d.get("pro_tip", "")[:180]
        min_inv      = d.get("min_investment", 0)
        inflation    = d.get("inflation_beating", False)

        tax = d.get("tax_treatment", {})
        tax_str = ""
        if isinstance(tax, dict):
            tax_str = str(tax)[:200]

        return f"""
[INVESTMENT] {name}
Category     : {category}
Risk Level   : {risk} | Returns: {returns}% | Horizon: {horizon}
Liquidity    : {liquidity} | Min Investment: Rs {min_inv:,}
Beats Inflation: {inflation}
When to Use  : {when_to_use}
Pro Tip      : {pro_tip}
Tax Treatment: {tax_str}
"""

    def _format_stock_node(self, node) -> str:
        """Format stock/ETF node data."""
        d            = node.data
        company      = d.get("company", "")
        ticker       = d.get("ticker", "")
        sector       = d.get("sector", "")
        risk         = d.get("risk_level", "")
        growth_score = d.get("long_term_growth_score", 0)
        why_invest   = d.get("why_invest", "")[:180]
        key_risks    = d.get("key_risks", [])[:2]
        analyst_view = d.get("analyst_view", "")[:150]
        hold_period  = d.get("ideal_holding_period", "")
        max_alloc    = d.get("ideal_portfolio_allocation_percent", "")

        return f"""
[STOCK] {company} ({ticker})
Sector       : {sector}
Risk         : {risk} | Growth Score: {growth_score}/10
Hold Period  : {hold_period} | Max Allocation: {max_alloc}
Why Invest   : {why_invest}
Key Risks    : {key_risks}
Analyst View : {analyst_view}
"""

    def _format_rule_node(self, node) -> str:
        """Format rule/guideline node data."""
        d        = node.data
        label    = node.label
        keywords = node.keywords[:5]

        # Truncate large rule data to avoid token overflow
        data_str = json.dumps(d, indent=2)
        if len(data_str) > 600:
            data_str = data_str[:600] + "\n... (truncated)"

        return f"""
[RULE] {label}
Keywords : {keywords}
Data     :
{data_str}
"""

    def _format_text_node(self, node) -> str:
        """Format text document chunk node."""
        source   = node.data.get("source", "unknown")
        sentence = node.data.get("sentence", "")
        return f"[DOC: {source}] {sentence}"

    def _format_generic_node(self, node) -> str:
        """Format concept, bank, sector, tier nodes."""
        node_type = node.node_type.upper()
        label     = node.label

        # Include any aliases or useful data
        data = node.data
        extra = ""
        if "aliases" in data:
            extra = f" (also: {', '.join(data['aliases'][:3])})"

        return f"[{node_type}] {label}{extra}"

    # ─── Utility Methods ──────────────────────────────────────────────────

    def get_graph_stats(self) -> dict:
        """Return stats about the current graph."""
        return self.graph.get_stats()

    def find_node(self, query: str) -> list:
        """
        Direct node lookup by keyword.
        Returns list of matching node IDs.
        Useful for debugging.
        """
        query_lower = query.lower()
        matches     = []

        for node_id, node in self.graph.nodes.items():
            node_keywords = [k.lower() for k in node.keywords]
            if any(query_lower in k or k in query_lower for k in node_keywords):
                matches.append({
                    "node_id":   node_id,
                    "node_type": node.node_type,
                    "label":     node.label
                })

        return matches[:10]

    def get_neighbors(self, node_id: str) -> list:
        """
        Get all direct neighbors of a node.
        Useful for debugging graph connections.
        """
        if node_id not in self.graph.nodes:
            return []

        neighbors = self.graph.adjacency.get(node_id, [])
        result    = []

        for neighbor_id in neighbors:
            if neighbor_id in self.graph.nodes:
                neighbor = self.graph.nodes[neighbor_id]
                result.append({
                    "node_id":   neighbor_id,
                    "node_type": neighbor.node_type,
                    "label":     neighbor.label
                })

        return result

    def rebuild_graph(self):
        """
        Force rebuild the graph from scratch.
        Clears cache and rebuilds.
        Call this when you update the knowledge base.
        """
        from rag.graph_rag.graph_store import get_graph_store

        print("[GraphRetriever] Force rebuilding graph...")

        store = get_graph_store()
        store.clear()

        # Reset singleton
        GraphRetriever._graph = None

        # Rebuild
        self._initialize_graph()

        # Update instance references
        self.graph     = GraphRetriever._graph
        self.traverser = GraphTraverser(
            nodes     = self.graph.nodes,
            adjacency = self.graph.adjacency
        )
        self.parser    = QueryParser(self.graph.nodes)

        print("[GraphRetriever] Rebuild complete ✓")
        return self.graph.get_stats()


def get_graph_retriever() -> GraphRetriever:
    """Return a singleton GraphRetriever instance for shared reuse."""
    global _GRAPH_RETRIEVER_INSTANCE
    if _GRAPH_RETRIEVER_INSTANCE is None:
        _GRAPH_RETRIEVER_INSTANCE = GraphRetriever()
    return _GRAPH_RETRIEVER_INSTANCE
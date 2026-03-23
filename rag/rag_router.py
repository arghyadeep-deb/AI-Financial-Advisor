"""
RAG Router — decides which retrieval method to use.

For structured queries (card names, investment names) → Rule-based retriever
For semantic queries (what is, explain, compare)      → Graph RAG
For chat queries                                       → Graph RAG
"""

from rag.graph_rag import get_graph_retriever


def route_query(query: str, mode: str = "auto") -> str:
    """
    Route a query to the best retrieval method.

    mode:
    - "auto"  → automatically decide
    - "graph" → always use graph RAG
    - "rule"  → always use rule-based
    """

    if mode == "graph":
        return _graph_retrieve(query)

    if mode == "rule":
        from rag.rag_pipeline import search_knowledge_base
        return search_knowledge_base(query)

    # ── Auto routing ──────────────────────────────────────────────────────
    query_lower = query.lower()

    # Use graph RAG for semantic / conceptual queries
    semantic_triggers = [
        "what is", "explain", "how does", "compare", "vs",
        "difference", "better", "why", "should i", "best",
        "tell me about", "understand", "guide", "how to",
        "mistake", "avoid", "risk", "tax", "return",
        "recommend", "suggest", "which"
    ]

    is_semantic = any(t in query_lower for t in semantic_triggers)

    if is_semantic:
        return _graph_retrieve(query)
    else:
        # For specific lookups (card name, ticker etc) use rule-based
        from rag.rag_pipeline import search_knowledge_base
        rule_result  = search_knowledge_base(query)
        graph_result = _graph_retrieve(query)

        # Combine both
        if rule_result and graph_result:
            return rule_result + "\n\n" + graph_result
        return rule_result or graph_result or ""


def _graph_retrieve(query: str) -> str:
    """Use graph RAG to retrieve context."""
    try:
        retriever = get_graph_retriever()
        return retriever.retrieve(query)
    except Exception as e:
        print(f"[RAGRouter] Graph retrieval failed: {e}")
        return ""
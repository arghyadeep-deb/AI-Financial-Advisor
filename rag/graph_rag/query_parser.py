import re
from typing import List, Dict, Tuple


class QueryParser:
    """
    Parses user queries into:
    1. Entry point nodes (where to start traversal)
    2. Query terms (for scoring during traversal)
    3. Query intent (what kind of answer is expected)
    4. Traversal strategy (BFS vs DFS vs Beam vs PPR)
    """

    def __init__(self, nodes: dict):
        self.nodes = nodes

        # ── Intent patterns ───────────────────────────────────────────────
        self.intent_patterns = {
            "comparison": [
                "vs", "versus", "compare", "better", "best",
                "difference between", "which is better", "should i choose"
            ],
            "explanation": [
                "what is", "explain", "how does", "tell me about",
                "what are", "define", "meaning of", "understand"
            ],
            "recommendation": [
                "recommend", "suggest", "which should", "best for",
                "good for me", "which card", "which fund", "should i invest"
            ],
            "calculation": [
                "how much", "calculate", "return", "corpus", "sip amount",
                "how many", "projection", "will i have"
            ],
            "howto": [
                "how to", "how do i", "steps to", "way to",
                "process of", "guide", "start"
            ],
            "warning": [
                "risk", "avoid", "danger", "problem", "issue",
                "mistake", "wrong", "bad", "trap", "pitfall"
            ]
        }

        # ── Term to node type mapping ──────────────────────────────────────
        self.term_node_map = {
            # Investment terms
            "elss":       ["investment", "concept", "rule"],
            "ppf":        ["investment", "concept", "rule"],
            "nps":        ["investment", "concept", "rule"],
            "sip":        ["rule", "concept"],
            "mutual fund":["investment"],
            "index fund": ["investment", "stock"],
            "etf":        ["investment", "stock"],
            "gold":       ["investment", "concept"],
            "equity":     ["investment", "concept", "stock"],
            "debt":       ["investment", "concept"],
            "fd":         ["investment"],
            "fixed deposit": ["investment"],

            # Credit card terms
            "credit card": ["card", "rule"],
            "cashback":    ["card", "concept"],
            "lounge":      ["card", "rule", "concept"],
            "reward":      ["card", "concept"],
            "annual fee":  ["card"],
            "forex":       ["card", "rule", "concept"],

            # Stock terms
            "stock":       ["stock", "concept"],
            "nifty":       ["stock"],
            "reliance":    ["stock"],
            "tcs":         ["stock"],
            "hdfc bank":   ["stock"],

            # Tax terms
            "80c":         ["rule", "concept", "investment"],
            "80d":         ["rule"],
            "ltcg":        ["rule", "concept"],
            "tax":         ["rule", "concept"],
        }

    def parse(self, query: str) -> dict:
        """
        Parse query and return traversal instructions.

        Returns:
        {
            "intent":          "explanation",
            "entry_nodes":     ["concept:elss", "investment:..."],
            "query_terms":     ["elss", "tax", "saving"],
            "strategy":        "beam_search",
            "max_depth":       2,
            "max_results":     10
        }
        """

        query_lower = query.lower().strip()
        query_terms = self._extract_terms(query_lower)
        intent      = self._detect_intent(query_lower)
        entry_nodes = self._find_entry_nodes(query_lower, query_terms)
        strategy    = self._select_strategy(intent, len(entry_nodes))

        return {
            "intent":      intent,
            "entry_nodes": entry_nodes,
            "query_terms": query_terms,
            "strategy":    strategy,
            "max_depth":   self._get_max_depth(intent),
            "max_results": self._get_max_results(intent),
            "raw_query":   query
        }

    def _extract_terms(self, query: str) -> List[str]:
        """Extract meaningful terms from query."""

        # Remove common stop words
        stop_words = {
            "what", "is", "the", "a", "an", "and", "or", "but",
            "for", "in", "of", "to", "with", "how", "why", "when",
            "should", "i", "my", "me", "do", "can", "will", "be",
            "are", "was", "were", "has", "have", "had", "this", "that",
            "which", "tell", "about", "explain"
        }

        words  = re.findall(r'\b[a-z0-9]+\b', query.lower())
        terms  = [w for w in words if w not in stop_words and len(w) > 2]

        # Add multi-word terms
        multi_word = [
            "annual fee", "credit card", "mutual fund", "index fund",
            "fixed deposit", "interest rate", "tax saving", "health score",
            "emergency fund", "investment plan", "portfolio allocation",
            "reward points", "lounge access", "credit score"
        ]

        for mw in multi_word:
            if mw in query:
                terms.append(mw)

        return list(set(terms))

    def _detect_intent(self, query: str) -> str:
        """Detect the intent of the query."""
        for intent, patterns in self.intent_patterns.items():
            if any(p in query for p in patterns):
                return intent
        return "explanation"

    def _find_entry_nodes(self, query: str, query_terms: List[str]) -> List[str]:
        """
        Find the best entry point nodes for traversal.
        Scores each node by keyword match to query.
        """
        scored_nodes = {}

        for node_id, node in self.nodes.items():
            score = 0
            node_keywords_lower = [k.lower() for k in node.keywords]

            for term in query_terms:
                # Exact match in keywords
                if term in node_keywords_lower:
                    score += 5

                # Partial match
                for kw in node_keywords_lower:
                    if term in kw or kw in term:
                        score += 2

                # Match in node label
                if term in node.label.lower():
                    score += 3

            if score > 0:
                scored_nodes[node_id] = score

        # Return top 5 entry nodes
        sorted_nodes = sorted(
            scored_nodes.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [node_id for node_id, _ in sorted_nodes[:5]]

    def _select_strategy(self, intent: str, num_entry_nodes: int) -> str:
        """Select best traversal strategy based on intent."""
        strategy_map = {
            "comparison":    "beam_search",    # Need to find paths between compared items
            "explanation":   "bfs",            # Broad context around a concept
            "recommendation":"beam_search",    # Find best matching nodes
            "calculation":   "dfs",            # Deep dive into specific rule/formula
            "howto":         "bfs",            # Broad how-to context
            "warning":       "dfs"             # Deep dive into risks
        }
        return strategy_map.get(intent, "beam_search")

    def _get_max_depth(self, intent: str) -> int:
        depth_map = {
            "comparison":    2,
            "explanation":   2,
            "recommendation":3,
            "calculation":   3,
            "howto":         2,
            "warning":       3
        }
        return depth_map.get(intent, 2)

    def _get_max_results(self, intent: str) -> int:
        results_map = {
            "comparison":    12,
            "explanation":   8,
            "recommendation":10,
            "calculation":   6,
            "howto":         8,
            "warning":       8
        }
        return results_map.get(intent, 8)
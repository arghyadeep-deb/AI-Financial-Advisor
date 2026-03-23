from typing import List, Dict, Set, Tuple
from collections import deque, defaultdict
import math


class GraphTraverser:
    """
    Traversal algorithms for the knowledge graph.

    Implements:
    1. BFS (Breadth First Search)     — finds nearby related nodes
    2. DFS (Depth First Search)       — finds deeply connected nodes
    3. Beam Search                    — finds best paths (like beam in trees)
    4. PPR (Personalized PageRank)    — ranks nodes by relevance to query nodes
    5. Bidirectional BFS              — finds connecting paths between concepts
    """

    def __init__(self, nodes: dict, adjacency: dict):
        self.nodes     = nodes
        self.adjacency = adjacency

    # ─── BFS Traversal ───────────────────────────────────────────────────

    def bfs(
        self,
        start_nodes: List[str],
        max_depth:   int = 2,
        max_nodes:   int = 15
    ) -> List[str]:
        """
        Breadth-first traversal from start nodes.
        Returns node IDs ordered by distance from start.
        Good for: finding directly related concepts.
        """
        visited  = set(start_nodes)
        queue    = deque([(node_id, 0) for node_id in start_nodes])
        result   = []

        while queue and len(result) < max_nodes:
            node_id, depth = queue.popleft()

            if node_id in self.nodes:
                result.append(node_id)

            if depth < max_depth:
                neighbors = self.adjacency.get(node_id, [])
                for neighbor in neighbors:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, depth + 1))

        return result

    # ─── DFS Traversal ───────────────────────────────────────────────────

    def dfs(
        self,
        start_node: str,
        max_depth:  int = 3,
        max_nodes:  int = 10
    ) -> List[str]:
        """
        Depth-first traversal from a start node.
        Good for: following a chain of related concepts deeply.
        Example: ELSS → Equity → Long Term → Tax Saving
        """
        visited = set()
        result  = []

        def _dfs(node_id: str, depth: int):
            if depth > max_depth or len(result) >= max_nodes:
                return
            if node_id in visited:
                return

            visited.add(node_id)
            if node_id in self.nodes:
                result.append(node_id)

            neighbors = self.adjacency.get(node_id, [])
            # Sort by edge weight (higher weight = more relevant = explore first)
            weighted_neighbors = []
            for n in neighbors:
                edge_weight = self._get_edge_weight(node_id, n)
                weighted_neighbors.append((edge_weight, n))
            weighted_neighbors.sort(reverse=True)

            for _, neighbor in weighted_neighbors:
                _dfs(neighbor, depth + 1)

        _dfs(start_node, 0)
        return result

    # ─── Beam Search ─────────────────────────────────────────────────────

    def beam_search(
        self,
        start_nodes:  List[str],
        query_terms:  List[str],
        beam_width:   int = 5,
        max_depth:    int = 3
    ) -> List[Tuple[str, float]]:
        """
        Beam search traversal — keeps top-K paths at each step.
        Scores nodes by relevance to query terms.

        This is the most powerful traversal for RAG — it finds
        the most relevant nodes without exploring everything.

        Returns: [(node_id, score), ...] sorted by score descending
        """
        # Initial beam: start nodes with scores
        beam = [(node_id, 1.0) for node_id in start_nodes if node_id in self.nodes]
        all_scored = dict(beam)

        for depth in range(max_depth):
            candidates = {}

            for node_id, parent_score in beam:
                neighbors = self.adjacency.get(node_id, [])

                for neighbor_id in neighbors:
                    if neighbor_id in all_scored:
                        continue
                    if neighbor_id not in self.nodes:
                        continue

                    # Score this neighbor
                    score = self._score_node(
                        node_id=neighbor_id,
                        query_terms=query_terms,
                        parent_score=parent_score,
                        edge_weight=self._get_edge_weight(node_id, neighbor_id)
                    )

                    if neighbor_id not in candidates or candidates[neighbor_id] < score:
                        candidates[neighbor_id] = score

            if not candidates:
                break

            # Keep top beam_width candidates
            top_candidates = sorted(
                candidates.items(),
                key=lambda x: x[1],
                reverse=True
            )[:beam_width]

            beam = top_candidates
            all_scored.update(top_candidates)

        # Sort all discovered nodes by score
        return sorted(all_scored.items(), key=lambda x: x[1], reverse=True)

    # ─── Personalized PageRank ────────────────────────────────────────────

    def personalized_pagerank(
        self,
        seed_nodes:  List[str],
        damping:     float = 0.85,
        iterations:  int   = 20,
        top_k:       int   = 15
    ) -> List[Tuple[str, float]]:
        """
        Personalized PageRank starting from seed nodes.
        Ranks all connected nodes by their importance relative to seeds.

        Best for: finding the most important nodes in a
        neighbourhood without strict depth limits.
        """
        if not seed_nodes:
            return []

        # Initialize ranks
        ranks = {node_id: 0.0 for node_id in self.nodes}
        seed_weight = 1.0 / len(seed_nodes)
        for s in seed_nodes:
            if s in ranks:
                ranks[s] = seed_weight

        # Iterate
        for _ in range(iterations):
            new_ranks = {}

            for node_id in self.nodes:
                # Personalization vector — always pull back to seeds
                if node_id in seed_nodes:
                    personal = (1 - damping) * seed_weight
                else:
                    personal = 0.0

                # Sum of incoming rank contributions
                incoming = 0.0
                neighbors = self.adjacency.get(node_id, [])
                for neighbor in neighbors:
                    out_degree = len(self.adjacency.get(neighbor, []))
                    if out_degree > 0:
                        incoming += ranks.get(neighbor, 0) / out_degree

                new_ranks[node_id] = personal + damping * incoming

            # Normalize
            total = sum(new_ranks.values())
            if total > 0:
                ranks = {k: v / total for k, v in new_ranks.items()}

        # Return top K
        sorted_ranks = sorted(
            [(nid, score) for nid, score in ranks.items() if score > 0],
            key=lambda x: x[1],
            reverse=True
        )

        return sorted_ranks[:top_k]

    # ─── Bidirectional BFS ────────────────────────────────────────────────

    def bidirectional_bfs(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 4
    ) -> List[str]:
        """
        Find shortest path between two nodes.
        Useful for: "How does ELSS relate to tax saving?"
        """
        if source_id not in self.nodes or target_id not in self.nodes:
            return []

        # Forward and backward frontiers
        forward  = {source_id: [source_id]}
        backward = {target_id: [target_id]}

        for _ in range(max_depth // 2 + 1):
            # Expand forward
            new_forward = {}
            for node_id, path in forward.items():
                for neighbor in self.adjacency.get(node_id, []):
                    if neighbor not in forward:
                        new_forward[neighbor] = path + [neighbor]
                    # Check if we've connected
                    if neighbor in backward:
                        return path + list(reversed(backward[neighbor]))
            forward.update(new_forward)

            # Expand backward
            new_backward = {}
            for node_id, path in backward.items():
                for neighbor in self.adjacency.get(node_id, []):
                    if neighbor not in backward:
                        new_backward[neighbor] = path + [neighbor]
                    # Check if we've connected
                    if neighbor in forward:
                        return list(reversed(path)) + forward[neighbor]
            backward.update(new_backward)

        return []

    # ─── Scoring Helpers ──────────────────────────────────────────────────

    def _score_node(
        self,
        node_id:      str,
        query_terms:  List[str],
        parent_score: float,
        edge_weight:  float
    ) -> float:
        """
        Score a node for relevance to a query.

        Factors:
        1. Keyword overlap with query terms (most important)
        2. Parent node score (propagation)
        3. Edge weight (relationship strength)
        4. Node type priority (rules > data nodes)
        """
        if node_id not in self.nodes:
            return 0.0

        node = self.nodes[node_id]

        # ── Keyword overlap score ─────────────────────────────────────────
        node_keywords = set(k.lower() for k in node.keywords)
        query_set     = set(t.lower() for t in query_terms)

        # Exact matches
        exact_matches = len(node_keywords & query_set)
        # Partial matches
        partial_matches = sum(
            1 for qt in query_set
            for nk in node_keywords
            if qt in nk or nk in qt
        )

        keyword_score = exact_matches * 3.0 + partial_matches * 1.0

        # ── Node type priority ────────────────────────────────────────────
        type_priority = {
            "rule":                2.0,
            "investment":          1.8,
            "card":                1.8,
            "stock":               1.5,
            "concept":             1.3,
            "bank":                1.0,
            "sector":              1.0,
            "investment_category": 1.0,
            "risk_level":          0.8,
            "text_chunk":          1.2,
            "tier":                0.7
        }
        type_score = type_priority.get(node.node_type, 1.0)

        # ── Final score ───────────────────────────────────────────────────
        final_score = (
            keyword_score * 2.0 +
            parent_score  * 0.5 +
            edge_weight   * 0.3 +
            type_score    * 0.5
        )

        return final_score

    def _get_edge_weight(self, source_id: str, target_id: str) -> float:
        """Get edge weight between two nodes."""
        if source_id not in self.nodes:
            return 1.0

        node = self.nodes[source_id]
        for edge in node.edges:
            if edge.target_id == target_id or edge.source_id == target_id:
                return edge.weight

        return 1.0
import json
import re
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict


class KnowledgeNode:
    """
    A single node in the knowledge graph.
    Represents a concept, entity, or data point.
    """

    def __init__(
        self,
        node_id:    str,
        node_type:  str,
        label:      str,
        data:       dict,
        keywords:   List[str] = None
    ):
        self.node_id   = node_id
        self.node_type = node_type   # card | investment | stock | rule | concept | metric
        self.label     = label
        self.data      = data
        self.keywords  = keywords or []
        self.edges:    List["KnowledgeEdge"] = []

    def __repr__(self):
        return f"Node({self.node_type}:{self.label})"


class KnowledgeEdge:
    """
    A directed edge between two nodes.
    Represents a relationship.
    """

    def __init__(
        self,
        source_id:   str,
        target_id:   str,
        relation:    str,
        weight:      float = 1.0
    ):
        self.source_id = source_id
        self.target_id = target_id
        self.relation  = relation   # has_benefit | belongs_to | suitable_for | requires | earns | competes_with
        self.weight    = weight

    def __repr__(self):
        return f"Edge({self.source_id} --{self.relation}--> {self.target_id})"


class KnowledgeGraphBuilder:
    """
    Builds a knowledge graph from:
    1. credit_cards.json
    2. investments.json
    3. stocks.json
    4. systematic_rules.json
    5. Text documents (PDFs parsed to text)

    No vectors. No embeddings.
    Pure structural and semantic relationship extraction.
    """

    def __init__(self):
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.edges: List[KnowledgeEdge]      = []
        self.adjacency: Dict[str, List[str]] = defaultdict(list)  # node_id -> [connected node_ids]

        # ── Concept Taxonomy ─────────────────────────────────────────────
        # Maps keywords to canonical concept nodes
        self.concept_taxonomy = {
            # Investment concepts
            "sip":          ["systematic investment plan", "monthly investment", "sip amount"],
            "elss":         ["tax saving fund", "equity linked savings", "80c investment", "tax saving mutual fund"],
            "ppf":          ["public provident fund", "government savings", "tax free investment"],
            "nps":          ["national pension system", "retirement account", "80ccd"],
            "equity":       ["stocks", "shares", "equity mutual fund", "nifty", "sensex"],
            "debt":         ["fixed income", "bonds", "fd", "fixed deposit", "debt fund"],
            "gold":         ["gold etf", "sovereign gold bond", "sgb", "precious metal"],
            "emergency":    ["emergency fund", "liquid fund", "contingency fund"],
            "insurance":    ["term insurance", "health insurance", "life cover"],

            # Credit card concepts
            "cashback":     ["cash back", "rewards cashback", "direct cashback"],
            "lounge":       ["airport lounge", "lounge access", "lounge visit"],
            "reward points":["reward point", "rp", "points"],
            "annual fee":   ["yearly fee", "membership fee", "renewal fee"],
            "forex":        ["foreign currency", "international transaction", "forex markup"],
            "upi":          ["upi payment", "unified payment", "bhim upi", "qr payment"],

            # Financial health concepts
            "savings rate": ["monthly savings", "saving percentage", "income saved"],
            "dti":          ["debt to income", "debt ratio", "loan to income"],
            "credit score": ["cibil score", "cibil", "credit rating", "750+"],
            "net worth":    ["total wealth", "assets minus liabilities"],

            # Tax concepts
            "80c":          ["section 80c", "tax deduction", "1.5 lakh deduction"],
            "ltcg":         ["long term capital gains", "long term gains", "equity tax"],
            "stcg":         ["short term capital gains", "short term gains"],
        }

    # ─── Main Build Method ────────────────────────────────────────────────

    def build_graph(self) -> "KnowledgeGraphBuilder":
        """
        Build complete knowledge graph from all sources.
        Returns self for chaining.
        """
        print("[GraphBuilder] Building knowledge graph...")

        self._build_concept_nodes()
        self._build_from_credit_cards()
        self._build_from_investments()
        self._build_from_stocks()
        self._build_from_rules()
        self._build_cross_edges()
        self._build_text_nodes()

        print(f"[GraphBuilder] Graph complete: {len(self.nodes)} nodes, {len(self.edges)} edges")
        return self

    # ─── Concept Nodes ────────────────────────────────────────────────────

    def _build_concept_nodes(self):
        """Create canonical concept nodes for all financial terms."""
        for concept, aliases in self.concept_taxonomy.items():
            node_id = f"concept:{concept}"
            node    = KnowledgeNode(
                node_id   = node_id,
                node_type = "concept",
                label     = concept,
                data      = {"aliases": aliases, "concept": concept},
                keywords  = [concept] + aliases
            )
            self._add_node(node)

    # ─── Credit Cards ─────────────────────────────────────────────────────

    def _build_from_credit_cards(self):
        """Build nodes and edges from credit_cards.json."""
        from rag.kb_loader import load_credit_cards, load_systematic_rules
        cards = load_credit_cards()
        rules = load_systematic_rules()

        # ── Bank nodes ────────────────────────────────────────────────────
        banks = set(c.get("bank", "") for c in cards)
        for bank in banks:
            bank_id = f"bank:{bank.lower().replace(' ', '_')}"
            self._add_node(KnowledgeNode(
                node_id   = bank_id,
                node_type = "bank",
                label     = bank,
                data      = {"bank": bank},
                keywords  = [bank.lower(), bank.lower().replace(" ", "")]
            ))

        # ── Tier nodes ────────────────────────────────────────────────────
        tiers = set(c.get("tier", "") for c in cards)
        for tier in tiers:
            tier_id = f"tier:{tier.lower().replace(' ', '_')}"
            self._add_node(KnowledgeNode(
                node_id   = tier_id,
                node_type = "tier",
                label     = tier,
                data      = {"tier": tier},
                keywords  = [tier.lower()]
            ))

        # ── Card nodes ────────────────────────────────────────────────────
        for card in cards:
            card_name = card.get("card_name", "")
            card_id   = f"card:{card_name.lower().replace(' ', '_')}"
            bank      = card.get("bank", "")
            tier      = card.get("tier", "")
            annual_fee = card.get("annual_fee", card.get("renewal_fee", 0))

            # Extract all keywords for this card
            keywords  = [
                card_name.lower(),
                bank.lower(),
                tier.lower()
            ]
            keywords += [b.lower() for b in card.get("best_for", [])]
            keywords += [str(annual_fee)]

            # Add cashback keywords
            cashback = card.get("cashback", {})
            if isinstance(cashback, dict):
                keywords += list(cashback.keys())

            self._add_node(KnowledgeNode(
                node_id   = card_id,
                node_type = "card",
                label     = card_name,
                data      = card,
                keywords  = keywords
            ))

            # ── Card → Bank edge ──────────────────────────────────────────
            bank_id = f"bank:{bank.lower().replace(' ', '_')}"
            self._add_edge(card_id, bank_id, "belongs_to_bank", weight=1.0)

            # ── Card → Tier edge ──────────────────────────────────────────
            tier_id = f"tier:{tier.lower().replace(' ', '_')}"
            self._add_edge(card_id, tier_id, "belongs_to_tier", weight=1.0)

            # ── Card → Concept edges ──────────────────────────────────────
            best_for = [b.lower() for b in card.get("best_for", [])]

            concept_map = {
                "travel":           "forex",
                "dining":           "reward points",
                "upi":              "upi",
                "cashback":         "cashback",
                "online shopping":  "cashback",
                "lounge":           "lounge",
                "international":    "forex",
                "amazon":           "cashback",
                "fuel":             "reward points"
            }

            for bf in best_for:
                for key, concept in concept_map.items():
                    if key in bf:
                        concept_id = f"concept:{concept}"
                        if concept_id in self.nodes:
                            self._add_edge(card_id, concept_id, "best_for", weight=2.0)

            # ── Lounge edge ───────────────────────────────────────────────
            lounge = card.get("lounge_access", {})
            if isinstance(lounge, dict) and lounge.get("type", "None") != "None":
                self._add_edge(card_id, "concept:lounge", "provides_lounge", weight=1.5)

            # ── Free card edge ────────────────────────────────────────────
            if annual_fee == 0:
                free_id = "concept:lifetime_free"
                if free_id not in self.nodes:
                    self._add_node(KnowledgeNode(
                        node_id   = free_id,
                        node_type = "concept",
                        label     = "Lifetime Free Cards",
                        data      = {},
                        keywords  = ["lifetime free", "no annual fee", "zero fee", "free card", "ltf"]
                    ))
                self._add_edge(card_id, free_id, "is_lifetime_free", weight=2.0)

    # ─── Investments ──────────────────────────────────────────────────────

    def _build_from_investments(self):
        """Build nodes and edges from investments.json."""
        from rag.kb_loader import load_investments
        investments = load_investments()

        # ── Category nodes ────────────────────────────────────────────────
        categories = set(i.get("category", "") for i in investments)
        for cat in categories:
            cat_id = f"category:{cat.lower().replace(' ', '_').replace('/', '_')}"
            self._add_node(KnowledgeNode(
                node_id   = cat_id,
                node_type = "investment_category",
                label     = cat,
                data      = {"category": cat},
                keywords  = [cat.lower()]
            ))

        # ── Risk level nodes ──────────────────────────────────────────────
        risk_levels = set(i.get("risk_level", "") for i in investments)
        for risk in risk_levels:
            risk_id = f"risk:{risk.lower().replace(' ', '_')}"
            self._add_node(KnowledgeNode(
                node_id   = risk_id,
                node_type = "risk_level",
                label     = risk,
                data      = {"risk_level": risk},
                keywords  = [risk.lower()]
            ))

        # ── Investment nodes ──────────────────────────────────────────────
        for inv in investments:
            name     = inv.get("name", "")
            inv_id   = f"investment:{name.lower().replace(' ', '_').replace('/', '_')}"
            category = inv.get("category", "")
            risk     = inv.get("risk_level", "")

            keywords = [name.lower(), category.lower(), risk.lower()]
            keywords += [i.lower() for i in inv.get("instruments", [])]
            keywords += inv.get("suitable_for", [])

            self._add_node(KnowledgeNode(
                node_id   = inv_id,
                node_type = "investment",
                label     = name,
                data      = inv,
                keywords  = keywords
            ))

            # ── Investment → Category edge ────────────────────────────────
            cat_id = f"category:{category.lower().replace(' ', '_').replace('/', '_')}"
            self._add_edge(inv_id, cat_id, "belongs_to_category", weight=1.0)

            # ── Investment → Risk edge ────────────────────────────────────
            risk_id = f"risk:{risk.lower().replace(' ', '_')}"
            self._add_edge(inv_id, risk_id, "has_risk_level", weight=1.0)

            # ── Investment → Concept edges ────────────────────────────────
            concept_links = {
                "PPF":          "ppf",
                "ELSS":         "elss",
                "NPS":          "nps",
                "Gold":         "gold",
                "Equity":       "equity",
                "Debt":         "debt",
                "Index":        "equity",
                "Emergency":    "emergency",
                "Liquid":       "emergency",
                "Retirement":   "nps",
                "80C":          "80c",
                "Insurance":    "insurance",
            }

            for keyword, concept in concept_links.items():
                if keyword.lower() in name.lower():
                    concept_id = f"concept:{concept}"
                    if concept_id in self.nodes:
                        self._add_edge(inv_id, concept_id, "related_to", weight=2.0)

            # ── Tax benefit edge ──────────────────────────────────────────
            pro_tip = inv.get("pro_tip", "") + inv.get("tax_saving_tip", "")
            if "80c" in pro_tip.lower() or "tax" in pro_tip.lower():
                self._add_edge(inv_id, "concept:80c", "provides_tax_benefit", weight=2.5)

    # ─── Stocks ───────────────────────────────────────────────────────────

    def _build_from_stocks(self):
        """Build nodes and edges from stocks.json."""
        from rag.kb_loader import load_stocks
        stocks = load_stocks()

        # ── Sector nodes ──────────────────────────────────────────────────
        sectors = set(s.get("sector", "") for s in stocks)
        for sector in sectors:
            sector_id = f"sector:{sector.lower().replace(' ', '_').replace('/', '_')}"
            self._add_node(KnowledgeNode(
                node_id   = sector_id,
                node_type = "sector",
                label     = sector,
                data      = {"sector": sector},
                keywords  = [sector.lower()]
            ))

        # ── Stock nodes ───────────────────────────────────────────────────
        for stock in stocks:
            company  = stock.get("company", "")
            ticker   = stock.get("ticker", "")
            stock_id = f"stock:{ticker.lower()}"
            sector   = stock.get("sector", "")

            keywords = [
                company.lower(),
                ticker.lower(),
                sector.lower()
            ]
            keywords += [s.lower() for s in stock.get("investment_style", [])]
            keywords += [s.lower() for s in stock.get("suitable_for", [])]

            self._add_node(KnowledgeNode(
                node_id   = stock_id,
                node_type = "stock",
                label     = f"{company} ({ticker})",
                data      = stock,
                keywords  = keywords
            ))

            # ── Stock → Sector edge ───────────────────────────────────────
            sector_id = f"sector:{sector.lower().replace(' ', '_').replace('/', '_')}"
            self._add_edge(stock_id, sector_id, "belongs_to_sector", weight=1.0)

            # ── Stock → Risk level edge ───────────────────────────────────
            risk    = stock.get("risk_level", "medium").lower().replace(" ", "_")
            risk_id = f"risk:{risk}"
            if risk_id not in self.nodes:
                self._add_node(KnowledgeNode(
                    node_id   = risk_id,
                    node_type = "risk_level",
                    label     = risk,
                    data      = {},
                    keywords  = [risk]
                ))
            self._add_edge(stock_id, risk_id, "has_risk", weight=1.0)

            # ── Stock → Equity concept ────────────────────────────────────
            self._add_edge(stock_id, "concept:equity", "is_equity", weight=1.5)

    # ─── Rules ────────────────────────────────────────────────────────────

    def _build_from_rules(self):
        """Build nodes from systematic_rules.json."""
        from rag.kb_loader import load_systematic_rules
        rules = load_systematic_rules()

        # ── SIP Rules node ────────────────────────────────────────────────
        sip_rules = rules.get("sip_rules", {})
        sip_node  = KnowledgeNode(
            node_id   = "rule:sip",
            node_type = "rule",
            label     = "SIP Rules",
            data      = sip_rules,
            keywords  = ["sip", "systematic investment", "monthly sip", "sip amount",
                         "sip percentage", "step up sip", "sip power"]
        )
        self._add_node(sip_node)
        self._add_edge("rule:sip", "concept:sip", "defines_rules_for", weight=2.0)

        # ── Emergency Fund Rule ───────────────────────────────────────────
        inv_rules = rules.get("investment_rules", {})
        ef_node   = KnowledgeNode(
            node_id   = "rule:emergency_fund",
            node_type = "rule",
            label     = "Emergency Fund Rules",
            data      = inv_rules,
            keywords  = ["emergency fund", "6 months", "liquid fund", "contingency",
                         "emergency savings", "how much emergency"]
        )
        self._add_node(ef_node)
        self._add_edge("rule:emergency_fund", "concept:emergency", "defines_rules_for", weight=2.0)

        # ── Tax Saving Rules ──────────────────────────────────────────────
        tax_rules = rules.get("investment_rules", {}).get("tax_saving_rules", {})
        if tax_rules:
            tax_node = KnowledgeNode(
                node_id   = "rule:tax_saving",
                node_type = "rule",
                label     = "Tax Saving Rules",
                data      = tax_rules,
                keywords  = ["80c", "section 80c", "80ccd", "80d", "tax saving",
                             "tax deduction", "elss tax", "ppf tax", "nps tax",
                             "income tax saving", "ltcg", "stcg"]
            )
            self._add_node(tax_node)
            self._add_edge("rule:tax_saving", "concept:80c", "defines_rules_for", weight=2.0)

        # ── Credit Card Rules ─────────────────────────────────────────────
        cc_rules   = rules.get("credit_card_rules", {})
        late_rules = cc_rules.get("late_payment_penalties", {})
        if late_rules:
            self._add_node(KnowledgeNode(
                node_id   = "rule:late_payment",
                node_type = "rule",
                label     = "Late Payment Penalties",
                data      = late_rules,
                keywords  = ["late payment", "late fee", "credit card penalty",
                             "missed payment", "minimum due", "overdue"]
            ))

        # Interest rates
        interest = cc_rules.get("interest_rates", {})
        if interest:
            self._add_node(KnowledgeNode(
                node_id   = "rule:credit_interest",
                node_type = "rule",
                label     = "Credit Card Interest Rates",
                data      = interest,
                keywords  = ["credit card interest", "apr", "annual percentage rate",
                             "credit card charges", "interest rate", "revolving credit",
                             "42%", "49%", "carrying balance"]
            ))

        # Lounge rules
        lounge_rules = cc_rules.get("lounge_access_rules", {})
        if lounge_rules:
            self._add_node(KnowledgeNode(
                node_id   = "rule:lounge",
                node_type = "rule",
                label     = "Lounge Access Rules",
                data      = lounge_rules,
                keywords  = ["lounge access", "airport lounge", "lounge spend",
                             "lounge requirement", "priority pass", "lounge unlock"]
            ))
            self._add_edge("rule:lounge", "concept:lounge", "defines_rules_for", weight=2.0)

        # Portfolio allocation
        alloc = rules.get("portfolio_allocation_by_age", {})
        if alloc:
            self._add_node(KnowledgeNode(
                node_id   = "rule:portfolio_allocation",
                node_type = "rule",
                label     = "Portfolio Allocation by Age",
                data      = alloc,
                keywords  = ["portfolio allocation", "age allocation", "equity debt split",
                             "how much equity", "how much debt", "asset allocation",
                             "age based investment"]
            ))

        # Health benchmarks
        benchmarks = rules.get("financial_health_benchmarks", {})
        if benchmarks:
            self._add_node(KnowledgeNode(
                node_id   = "rule:health_benchmarks",
                node_type = "rule",
                label     = "Financial Health Benchmarks",
                data      = benchmarks,
                keywords  = ["health score", "financial health", "savings benchmark",
                             "emergency fund benchmark", "good savings rate",
                             "what is good savings", "health grade"]
            ))

        # Common mistakes
        mistakes = rules.get("common_financial_mistakes", [])
        if mistakes:
            self._add_node(KnowledgeNode(
                node_id   = "rule:common_mistakes",
                node_type = "rule",
                label     = "Common Financial Mistakes",
                data      = {"mistakes": mistakes},
                keywords  = ["mistake", "avoid", "wrong", "bad investment",
                             "ulip mistake", "regular plan", "minimum due trap",
                             "common errors", "what not to do"]
            ))

    # ─── Cross Edges ──────────────────────────────────────────────────────

    def _build_cross_edges(self):
        """
        Build edges between different node types.
        These are the most powerful connections in the graph.
        """

        # ── Investment competes_with / complements ────────────────────────
        competition_pairs = [
            ("investment:fixed_deposits___certificates_of_deposit",
             "investment:debt_mutual_funds",
             "competes_with"),
            ("investment:government_small_savings_schemes",
             "investment:fixed_deposits___certificates_of_deposit",
             "similar_to"),
            ("investment:index_funds_and_etfs",
             "investment:equity_mutual_funds",
             "similar_to"),
            ("investment:ulips___endowment_plans",
             "investment:equity_mutual_funds",
             "worse_than"),
            ("investment:sovereign_gold_bonds",
             "investment:gold___silver",
             "better_version_of"),
        ]

        for src, tgt, rel in competition_pairs:
            if src in self.nodes and tgt in self.nodes:
                self._add_edge(src, tgt, rel, weight=1.5)

        # ── Card competition edges ────────────────────────────────────────
        amazon_cards = [
            "card:amazon_pay_icici",
            "card:hdfc_millennia",
            "card:hdfc_moneyback+"
        ]
        for i, c1 in enumerate(amazon_cards):
            for c2 in amazon_cards[i+1:]:
                if c1 in self.nodes and c2 in self.nodes:
                    self._add_edge(c1, c2, "competes_with", weight=1.0)

        # ── Tax hierarchy edges ───────────────────────────────────────────
        # PPF → 80C concept
        if "investment:public_provident_fund__ppf__nsc__scss__sukanya_samriddhi" in self.nodes:
            self._add_edge(
                "investment:public_provident_fund__ppf__nsc__scss__sukanya_samriddhi",
                "concept:80c",
                "provides_deduction",
                weight=3.0
            )

    # ─── Text Document Nodes ──────────────────────────────────────────────

    def _build_text_nodes(self):
        """
        Build nodes from text documents in data_sources folder.
        Extracts key sentences and links to relevant concept nodes.
        """
        text_dir = Path(__file__).parent.parent.parent / "data_sources"

        if not text_dir.exists():
            return

        for file_path in text_dir.glob("*.txt"):
            self._process_text_file(file_path)

        for file_path in text_dir.glob("*.md"):
            self._process_text_file(file_path)

    def _process_text_file(self, file_path: Path):
        """
        Process a text file into sentence nodes.
        Links sentences to concept nodes via keyword matching.
        """
        try:
            text = file_path.read_text(encoding="utf-8")
        except Exception:
            return

        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 30]

        for i, sentence in enumerate(sentences):
            sent_id = f"text:{file_path.stem}_{i}"
            sent_lower = sentence.lower()

            # Extract keywords from sentence
            keywords = []
            for concept, aliases in self.concept_taxonomy.items():
                if concept in sent_lower or any(a in sent_lower for a in aliases):
                    keywords.append(concept)

            if not keywords:
                continue  # Skip sentences with no financial keywords

            self._add_node(KnowledgeNode(
                node_id   = sent_id,
                node_type = "text_chunk",
                label     = sentence[:80] + "..." if len(sentence) > 80 else sentence,
                data      = {
                    "sentence": sentence,
                    "source":   file_path.name,
                    "index":    i
                },
                keywords  = keywords
            ))

            # Link to concept nodes
            for keyword in keywords:
                concept_id = f"concept:{keyword}"
                if concept_id in self.nodes:
                    self._add_edge(sent_id, concept_id, "mentions", weight=1.0)

    # ─── Helper Methods ───────────────────────────────────────────────────

    def _add_node(self, node: KnowledgeNode):
        self.nodes[node.node_id] = node

    def _add_edge(self, source_id: str, target_id: str, relation: str, weight: float = 1.0):
        if source_id not in self.nodes or target_id not in self.nodes:
            return

        edge = KnowledgeEdge(source_id, target_id, relation, weight)
        self.edges.append(edge)
        self.nodes[source_id].edges.append(edge)

        # Update adjacency list (bidirectional for traversal)
        self.adjacency[source_id].append(target_id)
        self.adjacency[target_id].append(source_id)

    def get_stats(self) -> dict:
        node_types = defaultdict(int)
        for node in self.nodes.values():
            node_types[node.node_type] += 1

        return {
            "total_nodes":  len(self.nodes),
            "total_edges":  len(self.edges),
            "node_types":   dict(node_types)
        }
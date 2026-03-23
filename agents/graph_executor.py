import traceback
from typing import Dict, Any
from langsmith import traceable


class GraphExecutor:
    """
    Executes all agents in the correct dependency order.
    Each execute method is traced in LangSmith.
    """

    @traceable(
        run_type = "chain",
        name     = "full_analysis",
        tags     = ["executor", "full"]
    )
    def execute_full_analysis(self, profile: dict) -> Dict[str, Any]:
        """Run all 7 agents. Full trace in LangSmith."""
        results = {}
        errors  = {}

        # Step 1: Health
        print("[GraphExecutor] Running health agent...")
        try:
            from agents.health_agent import run_health_agent
            results["health"] = run_health_agent(profile)
            print("[GraphExecutor] Health ✓")
        except Exception as e:
            errors["health"]  = str(e)
            traceback.print_exc()
            results["health"] = _empty_health()

        # Step 2: Investment + Stocks
        print("[GraphExecutor] Running investment agent...")
        try:
            from agents.investment_agent import run_investment_agent
            results["investment"] = run_investment_agent(profile)
            print("[GraphExecutor] Investment ✓")
        except Exception as e:
            errors["investment"]  = str(e)
            traceback.print_exc()
            results["investment"] = _empty_investment()

        # Step 3: Credit
        print("[GraphExecutor] Running credit agent...")
        try:
            from agents.credit_agent import run_credit_agent
            results["credit"] = run_credit_agent(profile)
            print("[GraphExecutor] Credit ✓")
        except Exception as e:
            errors["credit"]  = str(e)
            traceback.print_exc()
            results["credit"] = _empty_credit()

        # Step 4: Optimizer (needs investment + health)
        print("[GraphExecutor] Running optimizer agent...")
        try:
            from agents.optimizer_agent import run_optimizer_agent
            results["optimizer"] = run_optimizer_agent(
                profile           = profile,
                investment_result = results["investment"],
                health_result     = results["health"]
            )
            print("[GraphExecutor] Optimizer ✓")
        except Exception as e:
            errors["optimizer"]  = str(e)
            traceback.print_exc()
            results["optimizer"] = _empty_optimizer()

        # Step 5: Simulation (needs investment)
        print("[GraphExecutor] Running simulation agent...")
        try:
            from agents.simulation_agent import run_simulation_agent
            results["simulation"] = run_simulation_agent(
                profile           = profile,
                investment_result = results["investment"]
            )
            print("[GraphExecutor] Simulation ✓")
        except Exception as e:
            errors["simulation"]  = str(e)
            traceback.print_exc()
            results["simulation"] = _empty_simulation()

        # Step 6: Rebalance (needs investment)
        print("[GraphExecutor] Running rebalance agent...")
        try:
            from agents.rebalance_agent import run_rebalance_agent
            results["rebalance"] = run_rebalance_agent(
                profile           = profile,
                investment_result = results["investment"]
            )
            print("[GraphExecutor] Rebalance ✓")
        except Exception as e:
            errors["rebalance"]  = str(e)
            traceback.print_exc()
            results["rebalance"] = _empty_rebalance()

        # Step 7: Summary (needs health + investment + credit)
        print("[GraphExecutor] Running summary agent...")
        try:
            from agents.summary_agent import run_summary_agent
            results["summary"] = run_summary_agent(
                profile     = profile,
                all_results = {
                    "health":     results["health"],
                    "investment": results["investment"],
                    "credit":     results["credit"]
                }
            )
            print("[GraphExecutor] Summary ✓")
        except Exception as e:
            errors["summary"]  = str(e)
            traceback.print_exc()
            results["summary"] = _empty_summary()

        print(f"[GraphExecutor] Full analysis done. Errors: {list(errors.keys()) or 'none'}")
        return {
            "results": results,
            "errors":  errors,
            "success": len(errors) == 0
        }

    @traceable(
        run_type = "chain",
        name     = "quick_analysis",
        tags     = ["executor", "quick"]
    )
    def execute_quick_analysis(self, profile: dict) -> Dict[str, Any]:
        """Run health + investment + credit only."""
        results = {}
        errors  = {}

        try:
            from agents.health_agent import run_health_agent
            results["health"] = run_health_agent(profile)
        except Exception as e:
            errors["health"]  = str(e)
            results["health"] = _empty_health()

        try:
            from agents.investment_agent import run_investment_agent
            results["investment"] = run_investment_agent(profile)
        except Exception as e:
            errors["investment"]  = str(e)
            results["investment"] = _empty_investment()

        try:
            from agents.credit_agent import run_credit_agent
            results["credit"] = run_credit_agent(profile)
        except Exception as e:
            errors["credit"]  = str(e)
            results["credit"] = _empty_credit()

        return {
            "results": results,
            "errors":  errors,
            "success": len(errors) == 0
        }

    @traceable(
        run_type = "chain",
        name     = "single_analysis",
        tags     = ["executor", "single"]
    )
    def execute_single(self, agent_name: str, profile: dict) -> Dict[str, Any]:
        """Run a single agent by name."""
        results = {}
        errors  = {}

        try:
            if agent_name == "health":
                from agents.health_agent import run_health_agent
                results["health"] = run_health_agent(profile)

            elif agent_name == "investment":
                from agents.investment_agent import run_investment_agent
                results["investment"] = run_investment_agent(profile)

            elif agent_name == "credit":
                from agents.credit_agent import run_credit_agent
                results["credit"] = run_credit_agent(profile)

            elif agent_name == "optimizer":
                from agents.health_agent      import run_health_agent
                from agents.investment_agent  import run_investment_agent
                from agents.optimizer_agent   import run_optimizer_agent
                h = run_health_agent(profile)
                i = run_investment_agent(profile)
                results["optimizer"] = run_optimizer_agent(profile, i, h)

            elif agent_name == "simulation":
                from agents.investment_agent  import run_investment_agent
                from agents.simulation_agent  import run_simulation_agent
                i = run_investment_agent(profile)
                results["simulation"] = run_simulation_agent(profile, i)

            elif agent_name == "rebalance":
                from agents.investment_agent  import run_investment_agent
                from agents.rebalance_agent   import run_rebalance_agent
                i = run_investment_agent(profile)
                results["rebalance"] = run_rebalance_agent(profile, i)

            elif agent_name == "summary":
                from agents.health_agent     import run_health_agent
                from agents.investment_agent import run_investment_agent
                from agents.credit_agent     import run_credit_agent
                from agents.summary_agent    import run_summary_agent
                h = run_health_agent(profile)
                i = run_investment_agent(profile)
                c = run_credit_agent(profile)
                results["summary"] = run_summary_agent(profile, {"health": h, "investment": i, "credit": c})

            else:
                errors[agent_name] = f"Unknown agent: {agent_name}"

        except Exception as e:
            errors[agent_name] = str(e)
            traceback.print_exc()

        return {
            "results": results,
            "errors":  errors,
            "success": len(errors) == 0
        }


# ─── Empty Fallbacks ──────────────────────────────────────────────────────────

def _empty_health():
    return {"overall_score": 0, "grade": "N/A", "components": {},
            "strengths": [], "improvement_areas": [],
            "monthly_budget_suggestion": {}, "priority_actions": [],
            "error": "Health agent failed"}

def _empty_investment():
    return {"portfolio_allocation": {"equity": 60, "debt": 30, "gold": 10},
            "monthly_sip_plan": [], "stock_recommendations": [],
            "lumpsum_suggestions": [],
            "emergency_fund_status": {"current_months": 0, "target_months": 6, "gap_amount": 0, "action": ""},
            "tax_saving_plan": {"total_tax_saved_annually": 0},
            "total_monthly_investment": 0,
            "projected_corpus_5yr": 0, "projected_corpus_10yr": 0, "projected_corpus_20yr": 0,
            "stock_strategy_note": "", "key_advice": "",
            "disclaimer": "Stocks are subject to market risk.",
            "error": "Investment agent failed"}

def _empty_credit():
    return {"recommendations": [], "strategy_note": "",
            "avoid_pitfalls": [], "error": "Credit agent failed"}

def _empty_optimizer():
    return {"optimization_opportunities": [], "tax_saving_suggestions": [],
            "rebalancing_needed": False, "rebalancing_actions": [],
            "total_optimization_value": "Rs 0", "error": "Optimizer agent failed"}

def _empty_simulation():
    return {"current_trajectory": {"corpus_5yr": 0, "corpus_10yr": 0, "corpus_20yr": 0, "retirement_corpus": 0},
            "optimized_trajectory": {"corpus_5yr": 0, "corpus_10yr": 0, "corpus_20yr": 0, "retirement_corpus": 0},
            "difference_10yr": 0, "difference_20yr": 0,
            "goal_feasibility": [], "key_insight": "",
            "error": "Simulation agent failed"}

def _empty_rebalance():
    return {"needs_rebalancing": False, "drift_analysis": [],
            "rebalancing_method": "none", "rebalancing_actions": [],
            "tax_impact": "", "next_rebalance_date": "12 months",
            "summary": "", "error": "Rebalance agent failed"}

def _empty_summary():
    return {"executive_summary": "Analysis could not be completed.",
            "health_score": 0, "grade": "N/A",
            "top_priorities": [], "quick_wins": [],
            "key_numbers": {"monthly_surplus": 0, "recommended_sip": 0,
                            "emergency_fund_gap": 0, "best_credit_card": "",
                            "annual_tax_saving": 0, "projected_corpus_10yr": 0},
            "next_review_date": "3 months",
            "personalized_message": "Please retry the analysis.",
            "error": "Summary agent failed"}

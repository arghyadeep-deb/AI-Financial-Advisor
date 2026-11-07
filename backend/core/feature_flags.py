"""Release decisions, deliberately fail closed regardless of environment toggles."""
def allocation_public_eligible() -> bool:
    # D05/applicability, independent release evaluation and production evidence absent.
    # No environment variable can substitute for these reviewed artifacts.
    return False

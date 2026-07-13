class ContextBudgetAllocator:
    DEFAULT_BUDGET = {
        "t0_iron_lock": 800,
        "t1_bible_core": 1500,
        "t2_recent_context": 2500,
        "t3_current_plan": 1200,
    }

    PRIORITY_ORDER = [
        "t0_iron_lock",
        "t1_bible_core",
        "t3_current_plan",
        "t2_recent_context",
    ]

    def __init__(self, total_budget: int = 6000):
        self.total_budget = total_budget

    def allocate(self, actual_usage: dict[str, int]) -> dict[str, int]:
        allocated = {}
        remaining = self.total_budget

        for layer in self.PRIORITY_ORDER:
            budget = self.DEFAULT_BUDGET.get(layer, 500)
            actual = actual_usage.get(layer, 0)
            if actual <= budget and actual <= remaining:
                allocated[layer] = actual
                remaining -= actual
            elif remaining > 0:
                allocated[layer] = min(budget, remaining)
                remaining -= allocated[layer]
            else:
                allocated[layer] = 0

        return allocated

    def get_truncation_order(self) -> list[str]:
        return list(reversed(self.PRIORITY_ORDER))

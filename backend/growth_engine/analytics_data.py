"""Synthetic historical analytics — stands in for real order-history data.
Numbers are illustrative but internally consistent, and every Growth Engine
decision cites these directly so the reasoning is auditable, not a black box.
"""

CO_PURCHASE_RATES = {
    "laptop": [
        {"addon_category": "mouse", "rate": 0.34},
        {"addon_category": "bag", "rate": 0.22},
        {"addon_category": "warranty", "rate": 0.18},
        {"addon_category": "cooling_pad", "rate": 0.11},
        {"addon_category": "keyboard", "rate": 0.08},
        {"addon_category": "headphones", "rate": 0.07},
    ],
}

# Assumed baseline conversion probability at full price, and the conversion
# probability if a given discount tier is applied. The Growth Engine picks
# whichever tier maximizes expected revenue = price * (1-discount) * conversion
# — never the deepest discount by default.
DISCOUNT_CONVERSION_MODEL = {
    0.00: 0.55,
    0.05: 0.63,
    0.10: 0.67,
}

# GPU tier ranking used to judge whether an upsell is a genuine upgrade,
# not just a pricier SKU.
GPU_TIER_RANK = {
    "intel iris xe": 0, "amd radeon": 0,
    "gtx 1650": 1, "rtx 2050": 1,
    "rtx 3050": 2,
    "apple gpu 8-core": 2,
    "rtx 4050": 3,
    "rtx 4060": 4,
    "rtx 4070": 5,
}


def gpu_rank(gpu_name: str | None) -> int:
    if not gpu_name:
        return 0
    return GPU_TIER_RANK.get(gpu_name.strip().lower(), 0)
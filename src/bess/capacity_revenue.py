"""Capacity revenue for FCR and aFRR: price × offered MW, no LP needed (activations not modelled)."""
import pandas as pd


def fcr_revenue(blocks: pd.DataFrame, p_max_mw: float) -> float:
    """FCR price is EUR/MW per 4-h block; the product is symmetric, so one MW covers both directions."""
    return float(blocks["price"].sum() * p_max_mw)


def afrr_revenue(blocks: pd.DataFrame, p_max_mw: float) -> float:
    """aFRR price is (EUR/MW)/h, so multiply by the block length; POS and NEG rows are each offered at P_max."""
    return float((blocks["price"] * blocks["block_hours"]).sum() * p_max_mw)

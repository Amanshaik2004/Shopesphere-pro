def compute_order_totals(subtotal: float, discount: float, tax_rate_percent: float, shipping_cost: float):
    discounted_subtotal = max(0.0, subtotal - discount)
    tax = round(discounted_subtotal * (tax_rate_percent / 100.0), 2)
    total = round(discounted_subtotal + tax + shipping_cost, 2)
    return {
        "subtotal": subtotal,
        "discount": discount,
        "tax": tax,
        "shipping": shipping_cost,
        "total": total
    }

def test_order_totals_computation():
    res = compute_order_totals(subtotal=100.0, discount=10.0, tax_rate_percent=10.0, shipping_cost=15.0)
    assert res["subtotal"] == 100.0
    assert res["discount"] == 10.0
    assert res["tax"] == 9.0   # (100 - 10) * 10% = 9.0
    assert res["shipping"] == 15.0
    assert res["total"] == 114.0  # 90 + 9 + 15 = 114.0

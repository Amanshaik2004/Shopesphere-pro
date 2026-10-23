def calculate_discount(subtotal: float, discount_type: str, discount_value: float, max_discount: float = None) -> float:
    if discount_type == "percentage":
        disc = subtotal * (discount_value / 100.0)
    else:
        disc = discount_value
    if max_discount is not None:
        disc = min(disc, max_discount)
    return round(min(disc, subtotal), 2)

def test_percentage_discount():
    subtotal = 200.0
    discount = calculate_discount(subtotal, "percentage", 15.0)
    assert discount == 30.0

def test_percentage_discount_with_cap():
    subtotal = 500.0
    discount = calculate_discount(subtotal, "percentage", 20.0, max_discount=50.0)
    assert discount == 50.0

def test_fixed_discount():
    subtotal = 100.0
    discount = calculate_discount(subtotal, "fixed_amount", 25.0)
    assert discount == 25.0

def test_discount_cannot_exceed_subtotal():
    subtotal = 15.0
    discount = calculate_discount(subtotal, "fixed_amount", 50.0)
    assert discount == 15.0

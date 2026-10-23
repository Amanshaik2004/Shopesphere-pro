def calculate_remaining_refundable(payment_amount: float, existing_refunds: list):
    total_refunded = sum(existing_refunds)
    return max(0.0, payment_amount - total_refunded)

def test_refund_balance_calculation():
    payment = 150.0
    refunds = [30.0, 20.0]
    remaining = calculate_remaining_refundable(payment, refunds)
    assert remaining == 100.0

def test_full_refund_exhaustion():
    payment = 100.0
    refunds = [60.0, 40.0]
    remaining = calculate_remaining_refundable(payment, refunds)
    assert remaining == 0.0

from app.models.inventory import InventoryItem

def test_available_quantity_property():
    item = InventoryItem(quantity=100, reserved_quantity=30)
    assert item.available_quantity == 70

def test_available_quantity_cannot_be_negative():
    item = InventoryItem(quantity=10, reserved_quantity=15)
    assert item.available_quantity == 0

def test_low_stock_threshold_comparison():
    item = InventoryItem(quantity=5, reserved_quantity=2, low_stock_threshold=5)
    assert item.available_quantity <= item.low_stock_threshold

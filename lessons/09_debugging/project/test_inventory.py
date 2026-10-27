"""Run this file to see the 5 bugs fail. Keep fixing until all tests pass!
Run: python test_inventory.py
"""
from inventory import Inventory

def test_add_item():
    inv = Inventory()
    inv.add_item("apple", 5)
    assert inv.items["apple"] == 5, "Adding a new item failed."

def test_remove_item_success():
    inv = Inventory()
    inv.add_item("apple", 5)
    result = inv.remove_item("apple", 2)
    assert result is True, "remove_item should return True on success."
    # Bug 2 check:
    assert inv.items["apple"] == 3, f"Expected 3 apples left, got {inv.items['apple']}"

def test_remove_item_insufficient():
    inv = Inventory()
    inv.add_item("apple", 2)
    result = inv.remove_item("apple", 5)
    assert result is False, "remove_item should return False if not enough stock."

def test_get_quantity():
    inv = Inventory()
    inv.add_item("apple", 5)
    assert inv.get_quantity("apple") == 5
    # Bug 3 check:
    assert inv.get_quantity("banana") == 0, "get_quantity should return 0 for missing items."

def test_total_items():
    inv = Inventory()
    inv.add_item("apple", 2)
    inv.add_item("banana", 3)
    # Bug 4 check:
    assert inv.total_items() == 5, f"Expected total 5, got {inv.total_items()}"

def test_empty():
    inv = Inventory()
    inv.add_item("apple", 5)
    inv.empty()
    assert len(inv.items) == 0, "Inventory was not emptied."

if __name__ == "__main__":
    print("Running tests...\n")
    failures = 0
    
    try:
        test_add_item()
        print("✅ test_add_item passed")
    except AssertionError as e:
        print(f"❌ test_add_item failed: {e}")
        failures += 1

    try:
        test_remove_item_success()
        print("✅ test_remove_item_success passed")
    except AssertionError as e:
        print(f"❌ test_remove_item_success failed: {e}")
        failures += 1

    try:
        test_remove_item_insufficient()
        print("✅ test_remove_item_insufficient passed")
    except AssertionError as e:
        print(f"❌ test_remove_item_insufficient failed: {e}")
        failures += 1

    try:
        test_get_quantity()
        print("✅ test_get_quantity passed")
    except AssertionError as e:
        print(f"❌ test_get_quantity failed: {e}")
        failures += 1

    try:
        test_total_items()
        print("✅ test_total_items passed")
    except AssertionError as e:
        print(f"❌ test_total_items failed: {e}")
        failures += 1

    try:
        test_empty()
        print("✅ test_empty passed")
    except AssertionError as e:
        print(f"❌ test_empty failed: {e}")
        failures += 1

    print(f"\n{failures} tests failed.")

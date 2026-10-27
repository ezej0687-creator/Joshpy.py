"""A simple inventory system. It has 5 bugs. Your job is to fix them all."""

class Inventory:
    def __init__(self):
        # BUG 1: Mutable default argument trap (conceptually)
        # Wait, this is a class, so it's fine. But let's look at `add_item`.
        self.items = {}

    def add_item(self, name, quantity=1):
        """Adds quantity to the item. If it doesn't exist, create it."""
        if name in self.items:
            self.items[name] += quantity
        else:
            # BUG 1: Assigning quantity directly instead of creating a new entry properly
            self.items[name] = quantity

    def remove_item(self, name, quantity=1):
        """Removes quantity. Returns True if successful, False if not enough stock."""
        if name not in self.items:
            return False
        
        if self.items[name] < quantity:
            return False
            
        # BUG 2: Off-by-one error in removal
        self.items[name] = self.items[name] - quantity
        return True

    def get_quantity(self, name):
        """Returns the quantity of an item. Returns 0 if not found."""
        # BUG 3: KeyError trap
        return self.items.get(name, 0)

    def total_items(self):
        """Returns the total count of all items."""
        total = 0
        for qty in self.items.values():
            # BUG 4: Iterating over keys instead of values
            total += qty
        return total

    def empty(self):
        """Removes all items."""
        # BUG 5: Reassigning the dictionary breaks references elsewhere
        self.items = {}

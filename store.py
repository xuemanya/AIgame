import json
import os
import pygame
from config import Config


class PersistentStorage:
    """Handles persistent storage of game data."""

    def __init__(self, filename="game_data.json"):
        self.filename = filename
        self.data = {
            "high_score": 0,
            "coins": 0
        }
        self.load()

    def load(self):
        """Load data from file."""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    loaded_data = json.load(f)
                    self.data.update(loaded_data)
            except (json.JSONDecodeError, IOError):
                print("Failed to load game data, using defaults")

    def save(self):
        """Save data to file."""
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.data, f)
        except IOError:
            print("Failed to save game data")

    def get_high_score(self):
        return self.data.get("high_score", 0)

    def set_high_score(self, score):
        if score > self.data.get("high_score", 0):
            self.data["high_score"] = score
            self.save()

    def get_coins(self):
        return self.data.get("coins", 0)

    def add_coins(self, amount):
        self.data["coins"] = self.data.get("coins", 0) + amount
        self.save()

    def spend_coins(self, amount):
        current_coins = self.data.get("coins", 0)
        if current_coins >= amount:
            self.data["coins"] = current_coins - amount
            self.save()
            return True
        return False


class ShopItem:
    """Represents an item in the shop."""

    def __init__(self, item_id, name, price, description, purchased=False):
        self.id = item_id
        self.name = name
        self.price = price
        self.description = description
        self.purchased = purchased


class Shop:
    """Game shop system."""

    def __init__(self, storage):
        self.storage = storage
        # English localization for items
        self.items = [
            ShopItem("double_jump", "Double Jump", 100, "Allows jumping twice in mid-air"),
            ShopItem("extra_health", "Extra Health", 200, "Increases Max HP by 50 points"),
            ShopItem("speed_boost", "Speed Boost", 150, "Increases movement speed"),
            ShopItem("special_sword", "Power Sword", 300, "Enhances attack power and effects"),
        ]
        self.purchased_items = set()
        self.load_purchases()

    def load_purchases(self):
        """Load purchased items from file."""
        purchased_file = "purchased_items.json"
        if os.path.exists(purchased_file):
            try:
                with open(purchased_file, 'r') as f:
                    data = json.load(f)
                    self.purchased_items = set(data.get("purchased", []))

                # Update purchase status
                for item in self.items:
                    if item.id in self.purchased_items:
                        item.purchased = True
            except (json.JSONDecodeError, IOError):
                print("Failed to load purchased items")

    def save_purchases(self):
        """Save purchased items to file."""
        try:
            with open("purchased_items.json", 'w') as f:
                json.dump({"purchased": list(self.purchased_items)}, f)
        except IOError:
            print("Failed to save purchased items")

    def get_item_by_id(self, item_id):
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    def purchase_item(self, item_id):
        """Attempt to purchase an item."""
        item = self.get_item_by_id(item_id)
        if not item:
            return False, "Item not found"

        if item.purchased:
            return False, "Already Owned"

        if self.storage.get_coins() < item.price:
            return False, "Not enough coins"

        # Execute purchase
        if self.storage.spend_coins(item.price):
            item.purchased = True
            self.purchased_items.add(item_id)
            self.save_purchases()
            return True, f"Purchased {item.name}"
        else:
            return False, "Purchase failed"

    def get_shop_items(self):
        return self.items
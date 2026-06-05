# savegame.py

import json
import os

from config import SAVE_FILE


def save_game(
    gold,
    inventory,
    stats,
    gardens,
    garden_crops,
    active_garden,
    shop_unlocked,
    harvest_all_unlocked,
    upgrades,
    processors,
):
    data = {
        "gold": gold,
        "inventory": inventory,
        "stats": stats,
        "gardens": gardens,
        "garden_crops": garden_crops,
        "active_garden": active_garden,
        "shop_unlocked": shop_unlocked,
        "harvest_all_unlocked": harvest_all_unlocked,
        "upgrades": upgrades,
        "processors": processors,
    }

    with open(SAVE_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_game(
    gold,
    inventory,
    stats,
    gardens,
    garden_crops,
    active_garden,
    shop_unlocked,
    harvest_all_unlocked,
    ensure_inventory_defaults,
    ensure_stats_defaults,
    merge_saved_upgrades,
    merge_saved_processors,
    sync_processors_with_upgrades,
):
    ensure_inventory_defaults()
    ensure_stats_defaults()

    if not os.path.exists(SAVE_FILE):
        return gold, active_garden, shop_unlocked, harvest_all_unlocked

    with open(SAVE_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    gold = data.get("gold", gold)

    loaded_inventory = data.get("inventory")
    if isinstance(loaded_inventory, dict):
        inventory.update(loaded_inventory)

    ensure_inventory_defaults()

    loaded_stats = data.get("stats")
    if isinstance(loaded_stats, dict):
        stats.clear()
        stats.update(loaded_stats)

    ensure_stats_defaults()

    loaded_gardens = data.get("gardens")
    if isinstance(loaded_gardens, list):
        gardens.clear()
        gardens.extend(loaded_gardens)

    loaded_garden_crops = data.get("garden_crops")
    if isinstance(loaded_garden_crops, list):
        garden_crops.clear()
        garden_crops.extend(loaded_garden_crops)

    active_garden = data.get("active_garden", active_garden)
    shop_unlocked = data.get("shop_unlocked", shop_unlocked)
    harvest_all_unlocked = data.get("harvest_all_unlocked", harvest_all_unlocked)

    merge_saved_upgrades(data.get("upgrades"))
    merge_saved_processors(data.get("processors"))
    sync_processors_with_upgrades()

    return gold, active_garden, shop_unlocked, harvest_all_unlocked
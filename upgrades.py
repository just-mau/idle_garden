# upgrades.py

import time

from config import (
    MAX_UPGRADE_ACTIONS,
    MIN_UPGRADE_INTERVAL,
    UPGRADE_UNLOCK_GOLD,
)

from data import PROCESSORS

from state import (
    processors,
    upgrades,
)

from garden import (
    harvest_one_anywhere,
    plant_seed_anywhere_by_field_crop,
)

from processors import format_processor_recipe


def update_shop_unlock():
    import state

    if state.gold >= UPGRADE_UNLOCK_GOLD:
        state.shop_unlocked = True


def get_upgrade_max_level(upgrade):
    if "max_level" in upgrade:
        return upgrade["max_level"]

    speed_levels = upgrade["base_interval"] - MIN_UPGRADE_INTERVAL + 1
    power_levels = MAX_UPGRADE_ACTIONS - 1

    return speed_levels + power_levels


def is_upgrade_maxed(upgrade):
    import state

    if upgrade["id"] == "plant_all":
        return state.plant_all_unlocked or upgrade["level"] >= get_upgrade_max_level(upgrade)

    if upgrade["id"] == "harvest_all":
        return state.harvest_all_unlocked or upgrade["level"] >= get_upgrade_max_level(upgrade)

    return upgrade["level"] >= get_upgrade_max_level(upgrade)


def get_upgrade_price(upgrade):
    if is_upgrade_maxed(upgrade):
        return None

    return int(upgrade["base_price"] * (upgrade["level"] + 1) ** 2.25)


def get_upgrade_interval(upgrade):
    if upgrade["level"] <= 0:
        return upgrade["base_interval"]

    interval = upgrade["base_interval"] - (upgrade["level"] - 1)

    return max(MIN_UPGRADE_INTERVAL, interval)


def get_upgrade_action_count(upgrade):
    speed_levels = upgrade["base_interval"] - MIN_UPGRADE_INTERVAL + 1
    extra_power = max(0, upgrade["level"] - speed_levels)

    return min(MAX_UPGRADE_ACTIONS, 1 + extra_power)


def buy_selected_upgrade(selected_upgrade):
    import state

    upgrade = upgrades[selected_upgrade]
    price = get_upgrade_price(upgrade)

    if price is None or state.gold < price:
        return

    state.gold -= price
    upgrade["level"] += 1

    if upgrade["id"] == "plant_all":
        state.plant_all_unlocked = True
        return

    if upgrade["id"] == "harvest_all":
        state.harvest_all_unlocked = True
        return

    if upgrade.get("type") == "processor":
        processors[upgrade["processor_id"]]["unlocked"] = True
        return

    upgrade["next_action"] = time.time() + get_upgrade_interval(upgrade)


def run_automation():
    now = time.time()

    for upgrade in upgrades:
        if upgrade.get("type") != "automation":
            continue

        if upgrade["level"] <= 0:
            continue

        if upgrade["next_action"] is None:
            upgrade["next_action"] = now + get_upgrade_interval(upgrade)
            continue

        if now < upgrade["next_action"]:
            continue

        for _ in range(get_upgrade_action_count(upgrade)):
            if upgrade["id"] == "saat_boy":
                plant_seed_anywhere_by_field_crop()
            elif upgrade["id"] == "harvest_helper":
                harvest_one_anywhere()

        upgrade["next_action"] = now + get_upgrade_interval(upgrade)


def format_upgrade_name(upgrade):
    from config import GREEN, RESET

    name = upgrade["name"]

    if is_upgrade_maxed(upgrade):
        if upgrade.get("type") == "processor":
            return name + " " + GREEN + "gekauft" + RESET

        return name + " " + GREEN + "Lv. Max" + RESET

    if upgrade["level"] > 0:
        return f"{name} Lv. {upgrade['level']}"

    return name


def format_upgrade_price(upgrade):
    import state
    from config import RED, RESET

    price = get_upgrade_price(upgrade)

    if price is None:
        return ""

    price_text = f"{price}g"

    if state.gold < price:
        return RED + f"{price_text} fehlt {price - state.gold}g" + RESET

    return price_text


def format_upgrade_description(upgrade):
    if upgrade["id"] == "plant_all":
        return "p bepflanzt alle freien Felder im aktiven Feld"

    if upgrade["id"] == "harvest_all":
        return "h erntet alle reifen Pflanzen im aktiven Feld"

    if upgrade.get("type") == "processor":
        processor = PROCESSORS[upgrade["processor_id"]]
        return f"{format_processor_recipe(processor)} in {processor['duration']}s"

    interval = get_upgrade_interval(upgrade)
    action_count = get_upgrade_action_count(upgrade)

    if upgrade["id"] == "saat_boy":
        return f"pflanzt alle {interval}s {action_count}x nach Feldtyp"

    action = "Feld" if action_count == 1 else "Felder"

    return f"erntet alle {interval}s {action_count} {action} irgendwo"

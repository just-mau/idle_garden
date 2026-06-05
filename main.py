import argparse
import random
import select
import sys
import termios
import time
import tty

from config import *
from data import *
from terminal import *
from state import *
import savegame


# ============================================================
# DATA HELPERS
# ============================================================

def get_crop(crop_id):
    return CROPS[crop_id]


def get_product(product_id):
    return PRODUCTS[product_id]


def get_processor(processor_id):
    return PROCESSORS[processor_id]


def get_processor_inputs(processor):
    return processor["inputs"]


def get_processor_output(processor):
    return processor["output"]


def is_processor_output_item(processor):
    output = get_processor_output(processor)
    return output.get("type", "item") == "item"


def get_item_name(item_key):
    for crop_id, crop in CROPS.items():
        if item_key == crop_id:
            return crop["name"]

        if item_key == get_seed_key(crop_id):
            return crop["seed_name"]

    if item_key in PRODUCTS:
        return get_product(item_key)["name"]

    if item_key in ITEM_NAMES:
        return ITEM_NAMES[item_key]

    return item_key


def get_sell_price(item_key):
    if item_key in CROPS:
        return get_crop(item_key)["sell_price"]

    if item_key in PRODUCTS:
        return get_product(item_key)["sell_price"]

    return 0


def is_crop_unlocked(crop_id):
    crop = get_crop(crop_id)

    if "unlock_crop" not in crop:
        return True

    required_crop = crop["unlock_crop"]
    required_amount = crop["unlock_amount"]

    return stats["harvested"][required_crop] >= required_amount


def get_unlocked_crops():
    return [
        crop_id for crop_id in CROP_ORDER
        if is_crop_unlocked(crop_id)
    ]


def is_processor_unlocked(processor_id):
    return processors[processor_id]["unlocked"]


def is_product_visible(product_id):
    if inventory.get(product_id, 0) > 0:
        return True

    for processor_id, processor in PROCESSORS.items():
        if (
            is_processor_output_item(processor)
            and get_processor_output(processor)["item_key"] == product_id
            and is_processor_unlocked(processor_id)
        ):
            return True

    return False


def is_inventory_item_visible(item_key):
    if inventory.get(item_key, 0) > 0:
        return True

    for processor_id, processor in PROCESSORS.items():
        if not is_processor_unlocked(processor_id):
            continue

        for input_item in get_processor_inputs(processor):
            if input_item["item_key"] == item_key:
                return True

        output = get_processor_output(processor)

        if output.get("type") == "item" and output["item_key"] == item_key:
            return True

    return False


def get_sellable_items():
    items = list(get_unlocked_crops())

    for product_id in PRODUCT_ORDER:
        if is_product_visible(product_id):
            items.append(product_id)

    return items


def get_next_crop_id(current_crop_id, direction):
    unlocked_crops = get_unlocked_crops()

    if not unlocked_crops:
        return "wheat"

    if current_crop_id not in unlocked_crops:
        return unlocked_crops[0]

    current_index = unlocked_crops.index(current_crop_id)
    next_index = (current_index + direction) % len(unlocked_crops)
    return unlocked_crops[next_index]


# ============================================================
# SAVE MERGE HELPERS
# ============================================================

def merge_saved_upgrades(saved_upgrades):
    if not isinstance(saved_upgrades, list):
        return

    saved_by_id = {
        upgrade.get("id"): upgrade
        for upgrade in saved_upgrades
        if isinstance(upgrade, dict) and upgrade.get("id")
    }

    for upgrade in upgrades:
        saved_upgrade = saved_by_id.get(upgrade["id"])

        if saved_upgrade is None:
            continue

        if "level" in saved_upgrade:
            upgrade["level"] = saved_upgrade["level"]

        if "next_action" in saved_upgrade:
            upgrade["next_action"] = saved_upgrade["next_action"]


def merge_saved_processors(saved_processors):
    if not isinstance(saved_processors, dict):
        return

    for processor_id, state in processors.items():
        saved_state = saved_processors.get(processor_id)

        if not isinstance(saved_state, dict):
            continue

        state["unlocked"] = bool(saved_state.get("unlocked", state["unlocked"]))
        state["started_at"] = saved_state.get("started_at", state["started_at"])
        state["finish_at"] = saved_state.get("finish_at", state["finish_at"])


def sync_processors_with_upgrades():
    for upgrade in upgrades:
        if upgrade.get("type") != "processor":
            continue

        processor_id = upgrade["processor_id"]
        processor = processors[processor_id]

        if processor["unlocked"]:
            upgrade["level"] = max(upgrade["level"], 1)
        elif upgrade["level"] > 0:
            processor["unlocked"] = True


# ============================================================
# GARDEN ECONOMY / MANAGEMENT
# ============================================================

def get_garden_crop(garden_index):
    return garden_crops[garden_index]


def set_garden_crop(garden_index, crop_id):
    if is_crop_unlocked(crop_id):
        garden_crops[garden_index] = crop_id


def get_new_garden_price():
    return 100 * len(gardens)


def buy_new_garden():
    global gold

    if len(gardens) >= MAX_GARDENS:
        return

    price = get_new_garden_price()

    if gold < price:
        return

    gold -= price
    gardens.append(create_empty_garden())
    garden_crops.append("wheat")


def cycle_active_garden():
    global active_garden

    active_garden = (active_garden + 1) % len(gardens)


# ============================================================
# DISPLAY: GARDEN
# ============================================================

def build_inventory_lines():
    lines = [
        f"Gold: {gold}",
    ]

    for crop_id in CROP_ORDER:
        if not is_crop_unlocked(crop_id):
            continue

        crop = get_crop(crop_id)
        seed_amount = inventory[get_seed_key(crop_id)]
        crop_amount = inventory[crop_id]

        lines.append(f"{crop['seed_name']}: {seed_amount} | {crop['name']}: {crop_amount}")

    for product_id in PRODUCT_ORDER:
        if is_product_visible(product_id):
            product = get_product(product_id)
            lines.append(f"{product['name']}: {inventory[product_id]}")

    for item_key in ITEM_ORDER:
        if is_inventory_item_visible(item_key):
            lines.append(f"{get_item_name(item_key)}: {inventory[item_key]}")

    return lines


def build_inventory_box_lines():
    border = "+" + ("-" * (SHOP_PANEL_WIDTH - 2)) + "+"

    lines = [
        border,
        box_line("INVENTAR"),
        border,
    ]

    for line in build_inventory_lines():
        lines.append(box_line(line))

    lines.append(border)

    return lines


def build_compact_inventory_box_lines():
    border = "+" + ("-" * (SHOP_PANEL_WIDTH - 2)) + "+"
    summary_parts = [
        f"Gold {gold}",
    ]

    for product_id in PRODUCT_ORDER:
        if is_product_visible(product_id):
            summary_parts.append(f"{get_product(product_id)['name']} {inventory[product_id]}")

    for item_key in ITEM_ORDER:
        if is_inventory_item_visible(item_key):
            summary_parts.append(f"{get_item_name(item_key)} {inventory[item_key]}")

    return [
        border,
        box_line(" | ".join(summary_parts)),
        border,
    ]


def format_unlock_hint():
    locked_crops = [
        crop_id for crop_id in CROP_ORDER
        if not is_crop_unlocked(crop_id)
    ]

    if not locked_crops:
        return None

    crop_id = locked_crops[0]
    crop = get_crop(crop_id)
    required_crop = crop["unlock_crop"]
    required_amount = crop["unlock_amount"]
    required_name = get_crop(required_crop)["name"]
    current = stats["harvested"][required_crop]

    return f"Nächstes Saatgut: {crop['name']} bei {current}/{required_amount} geerntetem {required_name}"


def format_cell(cell):
    if cell is None:
        return "."

    if cell["stage"] == ",":
        return ","

    if cell["stage"] == "i":
        return GREEN + "i" + RESET

    if cell["stage"] == "Y":
        crop = get_crop(cell["crop"])
        return YELLOW + crop["symbol"] + RESET

    return "?"


def format_garden_header(garden_index):
    crop = get_crop(get_garden_crop(garden_index))
    label = f"F{garden_index + 1}:{crop['symbol']}"

    if garden_index == active_garden:
        label = "> " + label
        return CYAN + pad_visible(label, GARDEN_PANEL_WIDTH) + RESET

    return pad_visible("  " + label, GARDEN_PANEL_WIDTH)


def format_garden_row(garden_index, row_index):
    row = gardens[garden_index][row_index]
    cells = [format_cell(cell) for cell in row]
    return pad_visible(" ".join(cells), GARDEN_PANEL_WIDTH)


def build_garden_grid_lines():
    lines = []

    for block_start in range(0, len(gardens), GARDENS_PER_ROW):
        block_indices = list(range(block_start, min(block_start + GARDENS_PER_ROW, len(gardens))))

        lines.append("  ".join(format_garden_header(index) for index in block_indices))

        for row_index in range(GARDEN_SIZE):
            lines.append("  ".join(format_garden_row(index, row_index) for index in block_indices))

        lines.append("")

    if lines and lines[-1] == "":
        lines.pop()

    return lines


def get_processor_progress(processor_id, now=None):
    if now is None:
        now = time.time()

    state = processors[processor_id]
    started_at = state["started_at"]
    finish_at = state["finish_at"]

    if started_at is None or finish_at is None:
        return 0

    duration = finish_at - started_at

    if duration <= 0:
        return 1

    return max(0, min(1, (now - started_at) / duration))


def format_progress_bar(progress):
    filled = int(progress * PROCESSOR_BAR_WIDTH)
    empty = PROCESSOR_BAR_WIDTH - filled
    return "[" + ("#" * filled) + ("-" * empty) + "]"


def format_item_stack(item_key, amount):
    return f"{amount} {get_item_name(item_key)}"


def format_processor_inputs(processor):
    return " + ".join(
        format_item_stack(input_item["item_key"], input_item["amount"])
        for input_item in get_processor_inputs(processor)
    )


def format_processor_output(processor):
    output = get_processor_output(processor)

    if output.get("type") == "gold":
        return f"{output['amount']} Gold"

    return format_item_stack(output["item_key"], output["amount"])


def format_processor_recipe(processor):
    return f"{format_processor_inputs(processor)} -> {format_processor_output(processor)}"


def get_missing_processor_inputs(processor):
    missing_inputs = []

    for input_item in get_processor_inputs(processor):
        item_key = input_item["item_key"]
        required_amount = input_item["amount"]
        owned_amount = inventory.get(item_key, 0)

        if owned_amount < required_amount:
            missing_inputs.append({
                "item_key": item_key,
                "amount": required_amount - owned_amount,
            })

    return missing_inputs


def format_processor_status(processor_id, now):
    processor = PROCESSORS[processor_id]
    state = processors[processor_id]

    if state["started_at"] is not None and state["finish_at"] is not None:
        remaining = max(0, int(state["finish_at"] - now + 0.999))
        return f"noch {remaining}s"

    missing_inputs = get_missing_processor_inputs(processor)

    if not missing_inputs:
        return "bereit"

    missing_text = " + ".join(
        format_item_stack(input_item["item_key"], input_item["amount"])
        for input_item in missing_inputs
    )
    return f"fehlt {missing_text}"


def build_processor_lines():
    border = "+" + ("-" * (PROCESSOR_PANEL_WIDTH - 2)) + "+"
    lines = [
        border,
        box_line("VERWERTER", PROCESSOR_PANEL_WIDTH),
        border,
    ]

    visible_processors = [
        processor_id for processor_id in PROCESSOR_ORDER
        if is_processor_unlocked(processor_id)
    ]

    if not visible_processors:
        lines.append(box_line("Noch keine Verwerter gekauft.", PROCESSOR_PANEL_WIDTH))
        lines.append(border)
        return lines

    now = time.time()

    for processor_id in visible_processors:
        processor = PROCESSORS[processor_id]
        progress = get_processor_progress(processor_id, now)
        percent = int(progress * 100)
        bar = format_progress_bar(progress)
        recipe = f"{processor['name']} {bar} {percent:3d}% | {format_processor_recipe(processor)}"
        status = format_processor_status(processor_id, now)
        lines.append(box_split_line(recipe, status, PROCESSOR_PANEL_WIDTH))

    lines.append(border)
    return lines


def build_garden_lines():
    active_crop = get_crop(get_garden_crop(active_garden))

    lines = [
        fit_visible(
            f"IDLE GARDEN | Feld {active_garden + 1}/{len(gardens)} | Saatgut: {active_crop['seed_name']}",
            PROCESSOR_PANEL_WIDTH,
        ),
    ]

    unlock_hint = format_unlock_hint()

    if unlock_hint:
        lines.append(fit_visible(unlock_hint, PROCESSOR_PANEL_WIDTH))

    lines.extend(build_garden_grid_lines())

    lines.append("")
    lines.extend(build_processor_lines())

    return lines


# ============================================================
# DISPLAY: HELP / MANAGER / SHOPS
# ============================================================

def build_help_lines():
    border = "+" + ("-" * (SHOP_PANEL_WIDTH - 2)) + "+"

    return [
        border,
        box_line("HILFE / BEFEHLE"),
        border,
        box_line("[p] Pflanzt im aktiven Feld"),
        box_line("[h] Erntet aktives Feld"),
        box_line("[f] Wechselt aktives Feld"),
        box_line("[m] Feld-Manager"),
        box_line("[n] Neues Feld kaufen"),
        box_line("[b] Saatgut-Shop"),
        box_line("[v] Verkaufsshop"),
        box_line("[u] Upgrade-Shop"),
        box_line("[q] Speichern und Beenden"),
        border,
    ]


def build_manager_lines():
    border = "+" + ("-" * (SHOP_PANEL_WIDTH - 2)) + "+"

    lines = [
        border,
        box_line("FELD-MANAGER"),
        border,
        box_line("w/s: Feld auswählen"),
        box_line("a/d: Saatgut ändern"),
        box_line("Enter/Space: Feld aktivieren"),
        box_line("m: Fokus verlassen"),
        border,
    ]

    for index in range(len(gardens)):
        crop_id = get_garden_crop(index)
        crop = get_crop(crop_id)
        is_selected = index == selected_manager_garden

        selector = "> " if is_selected else "  "
        active_marker = " aktiv" if index == active_garden else ""
        name = f"{selector}Feld {index + 1}: {crop['name']}{active_marker}"

        if is_selected:
            name = CYAN + name + RESET

        lines.append(box_line(name))

    lines.append(border)

    return lines


def get_shop_page_count(item_count):
    if item_count <= 0:
        return 1

    return (item_count + SHOP_PAGE_SIZE - 1) // SHOP_PAGE_SIZE


def clamp_shop_selection(selected_index, item_count):
    if item_count <= 0:
        return 0

    return selected_index % item_count


def get_shop_page_bounds(selected_index, item_count):
    if item_count <= 0:
        return 0, 1, 0, 0

    selected_index = clamp_shop_selection(selected_index, item_count)
    current_page = selected_index // SHOP_PAGE_SIZE
    total_pages = get_shop_page_count(item_count)
    start = current_page * SHOP_PAGE_SIZE
    end = min(start + SHOP_PAGE_SIZE, item_count)

    return current_page, total_pages, start, end


def get_shop_page_items(items, selected_index):
    current_page, total_pages, start, end = get_shop_page_bounds(selected_index, len(items))
    return items[start:end], current_page, total_pages, start


def change_shop_page(selected_index, item_count, direction):
    if item_count <= 0:
        return 0

    selected_index = clamp_shop_selection(selected_index, item_count)
    current_page, total_pages, _, _ = get_shop_page_bounds(selected_index, item_count)
    target_page = (current_page + direction) % total_pages
    position_on_page = selected_index % SHOP_PAGE_SIZE
    target_start = target_page * SHOP_PAGE_SIZE
    target_end = min(target_start + SHOP_PAGE_SIZE, item_count)

    return min(target_start + position_on_page, target_end - 1)


def build_shop_page_line(selected_index, item_count):
    current_page, total_pages, _, _ = get_shop_page_bounds(selected_index, item_count)
    return box_line(f"Seite {current_page + 1}/{total_pages} | q/e: Seite wechseln")


def build_seed_shop_lines():
    active_seed = clamp_shop_selection(selected_seed, len(CROP_ORDER))
    crop_ids, _, _, page_start = get_shop_page_items(CROP_ORDER, active_seed)
    border = "+" + ("-" * (SHOP_PANEL_WIDTH - 2)) + "+"

    lines = [
        border,
        box_line("SAATGUT-SHOP"),
        border,
        box_line("w/s: Auswahl"),
        box_line("Enter/Space: kaufen"),
        box_line("b: Fokus verlassen"),
        build_shop_page_line(active_seed, len(CROP_ORDER)),
        border,
    ]

    for offset, crop_id in enumerate(crop_ids):
        index = page_start + offset
        crop = get_crop(crop_id)
        is_active = index == active_seed

        selector = "> " if is_active else "  "
        name = selector + crop["seed_name"]

        if is_active:
            name = CYAN + name + RESET

        if not is_crop_unlocked(crop_id):
            required_crop = crop["unlock_crop"]
            required_amount = crop["unlock_amount"]
            required_name = get_crop(required_crop)["name"]
            current = stats["harvested"][required_crop]
            locked_text = RED + "gesperrt" + RESET

            lines.append(box_split_line(name, locked_text))
            lines.append(box_line(f"  braucht: {current}/{required_amount} {required_name}"))
            lines.append(box_line())
            continue

        price_text = f"{crop['seed_price']}g"

        if gold < crop["seed_price"]:
            price_text = RED + f"{price_text} fehlt {crop['seed_price'] - gold}g" + RESET

        lines.append(box_split_line(name, price_text))
        lines.append(box_line(f"  Besitz: {inventory[get_seed_key(crop_id)]}"))
        lines.append(box_line())

    lines.append(border)

    return lines


def format_sell_amount_label(amount):
    if amount == "all":
        return "alle"

    return f"{amount}x"


def get_selected_sell_amount():
    return SELL_AMOUNTS[selected_sell_amount]


def build_sell_shop_lines():
    sellable_items = get_sellable_items()
    active_sell_crop = clamp_shop_selection(selected_sell_crop, len(sellable_items))
    page_items, _, _, page_start = get_shop_page_items(sellable_items, active_sell_crop)
    selected_amount = get_selected_sell_amount()
    border = "+" + ("-" * (SHOP_PANEL_WIDTH - 2)) + "+"

    amount_labels = []

    for index, amount in enumerate(SELL_AMOUNTS):
        label = format_sell_amount_label(amount)

        if index == selected_sell_amount:
            label = CYAN + "[" + label + "]" + RESET
        else:
            label = " " + label + " "

        amount_labels.append(label)

    lines = [
        border,
        box_line("VERKAUFSSHOP"),
        border,
        box_line("w/s: Ware"),
        box_line("a/d: Menge"),
        box_line("Enter/Space: verkaufen"),
        box_line("v: Fokus verlassen"),
        build_shop_page_line(active_sell_crop, len(sellable_items)),
        box_line("Menge: " + " ".join(amount_labels)),
        border,
    ]

    for offset, item_key in enumerate(page_items):
        index = page_start + offset
        is_active = index == active_sell_crop

        selector = "> " if is_active else "  "
        name = selector + get_item_name(item_key)

        if is_active:
            name = CYAN + name + RESET

        owned = inventory[item_key]
        amount_to_sell = owned if selected_amount == "all" else min(selected_amount, owned)
        sell_price = get_sell_price(item_key)
        value = amount_to_sell * sell_price

        price_text = f"{amount_to_sell} -> {value}g"

        if owned <= 0:
            price_text = RED + "nichts da" + RESET

        lines.append(box_split_line(name, price_text))
        lines.append(box_line(f"  Besitz: {owned} | Preis: {sell_price}g/Stk."))
        lines.append(box_line())

    lines.append(border)

    return lines


# ============================================================
# UPGRADES / PROCESSORS
# ============================================================

def update_shop_unlock():
    global shop_unlocked

    if gold >= UPGRADE_UNLOCK_GOLD:
        shop_unlocked = True


def get_upgrade_max_level(upgrade):
    if "max_level" in upgrade:
        return upgrade["max_level"]

    speed_levels = upgrade["base_interval"] - MIN_UPGRADE_INTERVAL + 1
    power_levels = MAX_UPGRADE_ACTIONS - 1
    return speed_levels + power_levels


def is_upgrade_maxed(upgrade):
    if upgrade["id"] == "harvest_all":
        return harvest_all_unlocked or upgrade["level"] >= get_upgrade_max_level(upgrade)

    return upgrade["level"] >= get_upgrade_max_level(upgrade)


def get_upgrade_price(upgrade):
    if is_upgrade_maxed(upgrade):
        return None

    return upgrade["base_price"] * (upgrade["level"] + 1)


def get_upgrade_interval(upgrade):
    if upgrade["level"] <= 0:
        return upgrade["base_interval"]

    interval = upgrade["base_interval"] - (upgrade["level"] - 1)
    return max(MIN_UPGRADE_INTERVAL, interval)


def get_upgrade_action_count(upgrade):
    speed_levels = upgrade["base_interval"] - MIN_UPGRADE_INTERVAL + 1
    extra_power = max(0, upgrade["level"] - speed_levels)
    return min(MAX_UPGRADE_ACTIONS, 1 + extra_power)


def buy_selected_upgrade():
    global gold, harvest_all_unlocked

    upgrade = upgrades[selected_upgrade]
    price = get_upgrade_price(upgrade)

    if price is None or gold < price:
        return

    gold -= price
    upgrade["level"] += 1

    if upgrade["id"] == "harvest_all":
        harvest_all_unlocked = True
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


def complete_processor(processor_id):
    global gold

    processor = PROCESSORS[processor_id]
    state = processors[processor_id]
    output = get_processor_output(processor)

    if output.get("type") == "gold":
        gold += output["amount"]
        update_shop_unlock()
    else:
        item_key = output["item_key"]
        inventory.setdefault(item_key, 0)
        inventory[item_key] += output["amount"]

    state["started_at"] = None
    state["finish_at"] = None


def start_processor(processor_id, now):
    processor = PROCESSORS[processor_id]
    state = processors[processor_id]

    if get_missing_processor_inputs(processor):
        return False

    for input_item in get_processor_inputs(processor):
        inventory[input_item["item_key"]] -= input_item["amount"]

    state["started_at"] = now
    state["finish_at"] = now + processor["duration"]
    return True


def run_processors():
    now = time.time()

    for processor_id in PROCESSOR_ORDER:
        if not is_processor_unlocked(processor_id):
            continue

        state = processors[processor_id]

        if state["started_at"] is not None and state["finish_at"] is not None:
            if now < state["finish_at"]:
                continue

            complete_processor(processor_id)

        if state["started_at"] is None and state["finish_at"] is None:
            start_processor(processor_id, now)


def format_upgrade_name(upgrade):
    name = upgrade["name"]

    if is_upgrade_maxed(upgrade):
        if upgrade.get("type") == "processor":
            return name + " " + GREEN + "gekauft" + RESET

        return name + " " + GREEN + "Lv. Max" + RESET

    if upgrade["level"] > 0:
        return f"{name} Lv. {upgrade['level']}"

    return name


def format_upgrade_price(upgrade):
    price = get_upgrade_price(upgrade)

    if price is None:
        return ""

    price_text = f"{price}g"

    if gold < price:
        return RED + f"{price_text} fehlt {price - gold}g" + RESET

    return price_text


def format_upgrade_description(upgrade):
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


def build_upgrade_item_line(upgrade, is_active):
    selector = "> " if is_active else "  "
    name = selector + format_upgrade_name(upgrade)

    if is_active:
        name = CYAN + name + RESET

    price = format_upgrade_price(upgrade)

    return box_split_line(name, price)


def build_upgrade_shop_lines():
    active_upgrade = clamp_shop_selection(selected_upgrade, len(upgrades))
    page_upgrades, _, _, page_start = get_shop_page_items(upgrades, active_upgrade)
    border = "+" + ("-" * (SHOP_PANEL_WIDTH - 2)) + "+"

    lines = [
        border,
        box_line("UPGRADE-SHOP"),
        border,
        box_line("w/s: Auswahl"),
        box_line("Enter/Space: kaufen"),
        box_line("u: Fokus verlassen"),
        build_shop_page_line(active_upgrade, len(upgrades)),
        border,
    ]

    for offset, upgrade in enumerate(page_upgrades):
        index = page_start + offset
        lines.append(build_upgrade_item_line(upgrade, shop_open and index == active_upgrade))
        lines.append(box_line("  " + format_upgrade_description(upgrade)))
        lines.append(box_line())

    lines.append(border)

    return lines


# ============================================================
# DISPLAY MAIN
# ============================================================

def draw_garden():
    garden_lines = build_garden_lines()

    if manager_open:
        menu_lines = build_manager_lines()
    elif seed_shop_open:
        menu_lines = build_seed_shop_lines()
    elif sell_shop_open:
        menu_lines = build_sell_shop_lines()
    elif shop_open:
        menu_lines = build_upgrade_shop_lines()
    else:
        menu_lines = build_help_lines()

    focus_panel_open = manager_open or seed_shop_open or sell_shop_open or shop_open
    side_lines = (
        build_compact_inventory_box_lines()
        if focus_panel_open
        else build_inventory_box_lines()
    )

    if menu_lines:
        side_lines.append("")
        side_lines.extend(menu_lines)

    width = terminal_width()
    garden_width = max((visible_length(line) for line in garden_lines), default=0)
    side_width = max((visible_length(line) for line in side_lines), default=0)

    if side_lines and width >= garden_width + side_width + LAYOUT_COLUMN_GAP:
        max_lines = max(len(garden_lines), len(side_lines))
        spacer_width = width - garden_width - side_width
        spacer_width = max(LAYOUT_COLUMN_GAP, spacer_width)

        for index in range(max_lines):
            left = garden_lines[index] if index < len(garden_lines) else ""
            right = side_lines[index] if index < len(side_lines) else ""

            if right:
                print(pad_visible(left, garden_width) + (" " * spacer_width) + right)
            else:
                print(left)
    else:
        for line in garden_lines:
            print(line)

        if side_lines:
            print()

            for line in side_lines:
                print(line)

    print()
    print("> ", end="", flush=True)


# ============================================================
# GARDEN FIELD SEARCH
# ============================================================

def find_empty_fields_in_garden(garden_index):
    empty_fields = []

    for row_index, row in enumerate(gardens[garden_index]):
        for col_index, cell in enumerate(row):
            if cell is None:
                empty_fields.append((garden_index, row_index, col_index))

    return empty_fields


def find_empty_fields_anywhere_by_field_crop():
    empty_fields = []

    for garden_index in range(len(gardens)):
        crop_id = get_garden_crop(garden_index)

        if inventory[get_seed_key(crop_id)] <= 0:
            continue

        empty_fields.extend(find_empty_fields_in_garden(garden_index))

    return empty_fields


def find_ready_fields_in_garden(garden_index):
    ready_fields = []

    for row_index, row in enumerate(gardens[garden_index]):
        for col_index, cell in enumerate(row):
            if cell is not None and cell["stage"] == "Y":
                ready_fields.append((garden_index, row_index, col_index))

    return ready_fields


def find_ready_fields_anywhere():
    ready_fields = []

    for garden_index in range(len(gardens)):
        ready_fields.extend(find_ready_fields_in_garden(garden_index))

    return ready_fields


# ============================================================
# GARDEN PLANTING / GROWTH
# ============================================================

def create_plant(crop_id):
    crop = get_crop(crop_id)

    return {
        "crop": crop_id,
        "stage": ",",
        "next_growth": time.time() + crop["growth_stage_1"],
    }


def plant_seed_in_garden(crop_id, garden_index):
    seed_key = get_seed_key(crop_id)

    if inventory[seed_key] <= 0:
        return False

    empty_fields = find_empty_fields_in_garden(garden_index)

    if not empty_fields:
        return False

    selected_garden, row, col = random.choice(empty_fields)
    gardens[selected_garden][row][col] = create_plant(crop_id)
    inventory[seed_key] -= 1

    return True


def plant_seed_anywhere_by_field_crop():
    empty_fields = find_empty_fields_anywhere_by_field_crop()

    if not empty_fields:
        return False

    garden_index, row, col = random.choice(empty_fields)
    crop_id = get_garden_crop(garden_index)
    seed_key = get_seed_key(crop_id)

    if inventory[seed_key] <= 0:
        return False

    gardens[garden_index][row][col] = create_plant(crop_id)
    inventory[seed_key] -= 1

    return True


def grow_plants():
    now = time.time()

    for garden in gardens:
        for row in garden:
            for plant in row:
                if plant is None:
                    continue

                if now < plant["next_growth"]:
                    continue

                crop = get_crop(plant["crop"])

                if plant["stage"] == ",":
                    plant["stage"] = "i"
                    plant["next_growth"] = now + crop["growth_stage_2"]
                elif plant["stage"] == "i":
                    plant["stage"] = "Y"


# ============================================================
# GARDEN BUY / SELL / HARVEST
# ============================================================

def buy_seed(crop_id):
    global gold

    if not is_crop_unlocked(crop_id):
        return

    crop = get_crop(crop_id)

    if gold < crop["seed_price"]:
        return

    gold -= crop["seed_price"]
    inventory[get_seed_key(crop_id)] += 1


def sell_item(item_key, amount):
    global gold

    owned = inventory[item_key]

    if owned <= 0:
        return

    amount_to_sell = owned if amount == "all" else min(amount, owned)

    inventory[item_key] -= amount_to_sell
    gold += amount_to_sell * get_sell_price(item_key)

    update_shop_unlock()


def calculate_harvest_reward():
    crop_reward = 1
    seed_reward = 1

    if random.random() < BONUS_HARVEST_CHANCE:
        bonus_type = random.choice(["crop", "seeds"])

        if bonus_type == "crop":
            crop_reward += 1
        else:
            seed_reward += 1

    return crop_reward, seed_reward


def harvest_plant(garden_index, row_index, col_index):
    cell = gardens[garden_index][row_index][col_index]

    if cell is None or cell["stage"] != "Y":
        return False

    crop_id = cell["crop"]
    crop_reward, seed_reward = calculate_harvest_reward()

    gardens[garden_index][row_index][col_index] = None

    inventory[crop_id] += crop_reward
    inventory[get_seed_key(crop_id)] += seed_reward
    stats["harvested"][crop_id] += crop_reward

    return True


def harvest_one_in_garden(garden_index):
    ready_fields = find_ready_fields_in_garden(garden_index)

    if not ready_fields:
        return False

    selected_garden, row_index, col_index = random.choice(ready_fields)
    return harvest_plant(selected_garden, row_index, col_index)


def harvest_one_anywhere():
    ready_fields = find_ready_fields_anywhere()

    if not ready_fields:
        return False

    garden_index, row_index, col_index = random.choice(ready_fields)
    return harvest_plant(garden_index, row_index, col_index)


def harvest_all_in_garden(garden_index):
    for selected_garden, row_index, col_index in find_ready_fields_in_garden(garden_index):
        harvest_plant(selected_garden, row_index, col_index)


# ============================================================
# INPUT READING
# ============================================================

def read_escape_command():
    sequence = "\x1b"

    if not select.select([sys.stdin], [], [], 0.05)[0]:
        return None

    sequence += sys.stdin.read(1)

    while select.select([sys.stdin], [], [], 0.02)[0]:
        sequence += sys.stdin.read(1)

        if sequence[-1] in "ABCD~":
            break

    arrow_keys = {
        "A": "w",
        "B": "s",
        "C": "d",
        "D": "a",
    }

    return arrow_keys.get(sequence[-1])


def read_command(timeout=0.25):
    ready, _, _ = select.select([sys.stdin], [], [], timeout)

    if not ready:
        return None

    command = sys.stdin.read(1)

    if command == "\x1b":
        return read_escape_command()

    if command in ("\n", "\r"):
        return "enter"

    if command == " ":
        return "space"

    return command.lower()


# ============================================================
# INPUT HANDLING
# ============================================================

def handle_manager_command(command):
    global manager_open, selected_manager_garden, active_garden

    if command == "w":
        selected_manager_garden = (selected_manager_garden - 1) % len(gardens)
    elif command == "s":
        selected_manager_garden = (selected_manager_garden + 1) % len(gardens)
    elif command == "a":
        current_crop = get_garden_crop(selected_manager_garden)
        set_garden_crop(selected_manager_garden, get_next_crop_id(current_crop, -1))
    elif command == "d":
        current_crop = get_garden_crop(selected_manager_garden)
        set_garden_crop(selected_manager_garden, get_next_crop_id(current_crop, 1))
    elif command in ("enter", "space"):
        active_garden = selected_manager_garden
    elif command == "m":
        manager_open = False

    return True


def handle_upgrade_shop_command(command):
    global shop_open, selected_upgrade

    selected_upgrade = clamp_shop_selection(selected_upgrade, len(upgrades))

    if command == "w":
        selected_upgrade = (selected_upgrade - 1) % len(upgrades)
    elif command == "s":
        selected_upgrade = (selected_upgrade + 1) % len(upgrades)
    elif command == "q":
        selected_upgrade = change_shop_page(selected_upgrade, len(upgrades), -1)
    elif command == "e":
        selected_upgrade = change_shop_page(selected_upgrade, len(upgrades), 1)
    elif command in ("enter", "space"):
        buy_selected_upgrade()
    elif command == "u":
        shop_open = False

    return True


def handle_seed_shop_command(command):
    global seed_shop_open, selected_seed

    crop_ids = CROP_ORDER

    if not crop_ids:
        seed_shop_open = False
        return True

    selected_seed = clamp_shop_selection(selected_seed, len(crop_ids))

    if command == "w":
        selected_seed = (selected_seed - 1) % len(crop_ids)
    elif command == "s":
        selected_seed = (selected_seed + 1) % len(crop_ids)
    elif command == "q":
        selected_seed = change_shop_page(selected_seed, len(crop_ids), -1)
    elif command == "e":
        selected_seed = change_shop_page(selected_seed, len(crop_ids), 1)
    elif command in ("enter", "space"):
        crop_id = crop_ids[selected_seed]
        buy_seed(crop_id)
    elif command == "b":
        seed_shop_open = False

    return True


def handle_sell_shop_command(command):
    global sell_shop_open, selected_sell_crop, selected_sell_amount

    sellable_items = get_sellable_items()

    if not sellable_items:
        sell_shop_open = False
        return True

    selected_sell_crop = clamp_shop_selection(selected_sell_crop, len(sellable_items))

    if command == "w":
        selected_sell_crop = (selected_sell_crop - 1) % len(sellable_items)
    elif command == "s":
        selected_sell_crop = (selected_sell_crop + 1) % len(sellable_items)
    elif command == "q":
        selected_sell_crop = change_shop_page(selected_sell_crop, len(sellable_items), -1)
    elif command == "e":
        selected_sell_crop = change_shop_page(selected_sell_crop, len(sellable_items), 1)
    elif command == "a":
        selected_sell_amount = (selected_sell_amount - 1) % len(SELL_AMOUNTS)
    elif command == "d":
        selected_sell_amount = (selected_sell_amount + 1) % len(SELL_AMOUNTS)
    elif command in ("enter", "space"):
        item_key = sellable_items[selected_sell_crop]
        amount = get_selected_sell_amount()
        sell_item(item_key, amount)
    elif command == "v":
        sell_shop_open = False

    return True


def close_all_shops():
    global seed_shop_open, sell_shop_open, shop_open, manager_open, help_open

    seed_shop_open = False
    sell_shop_open = False
    shop_open = False
    manager_open = False
    help_open = False


def handle_game_command(command):
    global seed_shop_open, sell_shop_open, shop_open, manager_open, selected_manager_garden

    if command == "p":
        plant_seed_in_garden(get_garden_crop(active_garden), active_garden)
    elif command == "h":
        if harvest_all_unlocked:
            harvest_all_in_garden(active_garden)
        else:
            harvest_one_in_garden(active_garden)
    elif command == "f":
        cycle_active_garden()
    elif command == "m":
        close_all_shops()
        selected_manager_garden = active_garden
        manager_open = True
    elif command == "n":
        buy_new_garden()
    elif command == "b":
        close_all_shops()
        seed_shop_open = True
    elif command == "v":
        close_all_shops()
        sell_shop_open = True
    elif command == "u" and shop_unlocked:
        close_all_shops()
        shop_open = True

    return True


def handle_command(command):
    if command == "q" and not (seed_shop_open or sell_shop_open or shop_open):
        return False

    if manager_open:
        return handle_manager_command(command)

    if help_open:
        close_all_shops()
        return True

    if seed_shop_open:
        return handle_seed_shop_command(command)

    if sell_shop_open:
        return handle_sell_shop_command(command)

    if shop_open:
        return handle_upgrade_shop_command(command)

    return handle_game_command(command)


# ============================================================
# DEV / MAIN
# ============================================================

def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dev",
        action="store_true",
        help="Startet mit Debug-Ressourcen",
    )

    return parser.parse_args()


def apply_dev_mode():
    global gold, shop_unlocked

    gold = 100000

    inventory["wheat_seed"] = 100
    inventory["wheat"] = 100
    inventory["rye_seed"] = 25
    inventory["rye"] = 25

    stats["harvested"]["wheat"] = 25

    shop_unlocked = True


def main():
    global gold, active_garden, shop_unlocked, harvest_all_unlocked

    gold, active_garden, shop_unlocked, harvest_all_unlocked = savegame.load_game(
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
    )
    old_terminal_settings = termios.tcgetattr(sys.stdin)

    try:
        tty.setcbreak(sys.stdin)
        running = True

        while running:
            grow_plants()
            run_automation()
            run_processors()
            update_shop_unlock()

            clear_screen()
            draw_garden()

            command = read_command()

            if command is not None:
                running = handle_command(command)

    finally:
        savegame.save_game(
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
        )
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_terminal_settings)


if __name__ == "__main__":
    args = parse_arguments()

    if args.dev:
        apply_dev_mode()

    main()
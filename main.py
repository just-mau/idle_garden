import argparse
import random
import re
import select
import shutil
import sys
import termios
import time
import tty

import json
import os


# ============================================================
# CONFIG / CONSTANTS
# ============================================================

GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
RESET = "\033[0m"

ANSI_ESCAPE = re.compile(r"\033\[[0-9;]*m")

BONUS_HARVEST_CHANCE = 0.1
UPGRADE_UNLOCK_GOLD = 10

SAAT_BOY_INTERVAL = 5
HARVEST_HELPER_INTERVAL = 5
MIN_UPGRADE_INTERVAL = 1
MAX_UPGRADE_ACTIONS = 5

GARDEN_SIZE = 5
MAX_GARDENS = 9
GARDENS_PER_ROW = 3
GARDEN_PANEL_WIDTH = 15

SHOP_PANEL_WIDTH = 50
SELL_AMOUNTS = [1, 5, 10, "all"]

# ============================================================
# save/load file
# ===========================================================
SAVE_FILE = "savegame.json"


def save_game():
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
    }

    with open(SAVE_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_game():
    global gold, inventory, stats, gardens, garden_crops
    global active_garden, shop_unlocked, harvest_all_unlocked, upgrades

    if not os.path.exists(SAVE_FILE):
        return

    with open(SAVE_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    gold = data.get("gold", gold)
    inventory = data.get("inventory", inventory)
    stats = data.get("stats", stats)
    gardens = data.get("gardens", gardens)
    garden_crops = data.get("garden_crops", garden_crops)
    active_garden = data.get("active_garden", active_garden)
    shop_unlocked = data.get("shop_unlocked", shop_unlocked)
    harvest_all_unlocked = data.get("harvest_all_unlocked", harvest_all_unlocked)
    upgrades = data.get("upgrades", upgrades)


# ============================================================
# CROPS / INVENTORY / STATS
# ============================================================

CROPS = {
    "wheat": {
        "name": "Weizen",
        "seed_name": "Weizensaat",
        "seed_price": 3,
        "sell_price": 2,
        "symbol": "W",
        "growth_stage_1": 15,
        "growth_stage_2": 15,
    },
    "rye": {
        "name": "Roggen",
        "seed_name": "Roggensaat",
        "seed_price": 8,
        "sell_price": 4,
        "symbol": "R",
        "growth_stage_1": 30,
        "growth_stage_2": 30,
        "unlock_crop": "wheat",
        "unlock_amount": 25,
    },
}

CROP_ORDER = ["wheat", "rye"]

inventory = {
    "wheat_seed": 5,
    "wheat": 0,
    "rye_seed": 0,
    "rye": 0,
}

stats = {
    "harvested": {
        "wheat": 0,
        "rye": 0,
    }
}

gold = 0


def get_crop(crop_id):
    return CROPS[crop_id]


def get_seed_key(crop_id):
    return f"{crop_id}_seed"


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
# GAME STATE: GARDENS
# ============================================================

def create_empty_garden():
    return [
        [None for _ in range(GARDEN_SIZE)]
        for _ in range(GARDEN_SIZE)
    ]


gardens = [
    create_empty_garden()
]

garden_crops = [
    "wheat"
]

active_garden = 0

seed_shop_open = False
selected_seed = 0

sell_shop_open = False
selected_sell_crop = 0
selected_sell_amount = 0

manager_open = False
selected_manager_garden = 0

help_open = False

shop_unlocked = False
shop_open = False
selected_upgrade = 0
harvest_all_unlocked = False

upgrades = [
    {
        "id": "saat_boy",
        "name": "Saat-Boy",
        "base_price": 10,
        "base_interval": SAAT_BOY_INTERVAL,
        "level": 0,
        "next_action": None,
    },
    {
        "id": "harvest_helper",
        "name": "Erntehelfer",
        "base_price": 20,
        "base_interval": HARVEST_HELPER_INTERVAL,
        "level": 0,
        "next_action": None,
    },
    {
        "id": "harvest_all",
        "name": "Erntemaschine",
        "base_price": 5000,
        "level": 0,
        "next_action": None,
    },
]


# ============================================================
# TERMINAL HELPERS
# ============================================================

def clear_screen():
    print("\033[H\033[J", end="")


def visible_length(text):
    return len(ANSI_ESCAPE.sub("", text))


def pad_visible(text, width):
    padding = max(0, width - visible_length(text))
    return text + (" " * padding)


def box_line(content=""):
    content_width = SHOP_PANEL_WIDTH - 2
    return "|" + pad_visible(content, content_width) + "|"


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

    return lines


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


def format_new_garden_line():
    if len(gardens) >= MAX_GARDENS:
        return f"[n] Neues Feld kaufen: Maximum erreicht ({MAX_GARDENS})"

    price = get_new_garden_price()

    if gold < price:
        return f"[n] Neues Feld kaufen ({price} Gold, fehlt {price - gold})"

    return f"[n] Neues Feld kaufen ({price} Gold)"


def build_garden_lines():
    active_crop = get_crop(get_garden_crop(active_garden))

    lines = [
        "=== IDLE GARDEN ===",
    ]

    lines.extend(build_inventory_lines())

    lines.extend([
        f"Aktives Feld: {active_garden + 1}/{len(gardens)}",
        f"Feld-Saatgut: {active_crop['seed_name']}",
    ])

    unlock_hint = format_unlock_hint()

    if unlock_hint:
        lines.append(unlock_hint)

    lines.append("")
    lines.extend(build_garden_grid_lines())


    return lines


# ============================================================
# DISPLAY: HELP
# ===========================================================
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

# ============================================================
# DISPLAY: FIELD MANAGER
# ============================================================

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


# ============================================================
# DISPLAY: SEED SHOP
# ============================================================

def build_seed_shop_lines():
    unlocked_crops = get_unlocked_crops()
    border = "+" + ("-" * (SHOP_PANEL_WIDTH - 2)) + "+"

    lines = [
        border,
        box_line("SAATGUT-SHOP"),
        border,
        box_line("w/s: Auswahl"),
        box_line("Enter/Space: kaufen"),
        box_line("b: Fokus verlassen"),
        border,
    ]

    for index, crop_id in enumerate(unlocked_crops):
        crop = get_crop(crop_id)
        is_active = index == selected_seed

        selector = "> " if is_active else "  "
        name = selector + crop["seed_name"]

        if is_active:
            name = CYAN + name + RESET

        price_text = f"{crop['seed_price']}g"

        if gold < crop["seed_price"]:
            price_text = RED + f"{price_text} fehlt {crop['seed_price'] - gold}g" + RESET

        spacer = " " * max(1, SHOP_PANEL_WIDTH - 2 - visible_length(name) - visible_length(price_text))

        lines.append(box_line(name + spacer + price_text))
        lines.append(box_line(f"  Besitz: {inventory[get_seed_key(crop_id)]}"))
        lines.append(box_line())

    locked_crops = [crop_id for crop_id in CROP_ORDER if not is_crop_unlocked(crop_id)]

    if locked_crops:
        lines.append(border)
        lines.append(box_line("Gesperrt"))

        for crop_id in locked_crops:
            crop = get_crop(crop_id)
            required_crop = crop["unlock_crop"]
            required_amount = crop["unlock_amount"]
            required_name = get_crop(required_crop)["name"]
            current = stats["harvested"][required_crop]

            lines.append(box_line(f"{crop['seed_name']}: {current}/{required_amount} {required_name}"))

    lines.append(border)

    return lines


# ============================================================
# DISPLAY: SELL SHOP
# ============================================================

def format_sell_amount_label(amount):
    if amount == "all":
        return "alle"
    return f"{amount}x"


def get_selected_sell_amount():
    return SELL_AMOUNTS[selected_sell_amount]


def build_sell_shop_lines():
    unlocked_crops = get_unlocked_crops()
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
        box_line("Menge: " + " ".join(amount_labels)),
        border,
    ]

    for index, crop_id in enumerate(unlocked_crops):
        crop = get_crop(crop_id)
        is_active = index == selected_sell_crop

        selector = "> " if is_active else "  "
        name = selector + crop["name"]

        if is_active:
            name = CYAN + name + RESET

        owned = inventory[crop_id]
        amount_to_sell = owned if selected_amount == "all" else min(selected_amount, owned)
        value = amount_to_sell * crop["sell_price"]

        price_text = f"{amount_to_sell} -> {value}g"

        if owned <= 0:
            price_text = RED + "nichts da" + RESET

        spacer = " " * max(1, SHOP_PANEL_WIDTH - 2 - visible_length(name) - visible_length(price_text))

        lines.append(box_line(name + spacer + price_text))
        lines.append(box_line(f"  Besitz: {owned} | Preis: {crop['sell_price']}g/Stk."))
        lines.append(box_line())

    lines.append(border)

    return lines


# ============================================================
# UPGRADES
# ============================================================

def update_shop_unlock():
    global shop_unlocked

    if gold >= UPGRADE_UNLOCK_GOLD:
        shop_unlocked = True


def get_upgrade_max_level(upgrade):
    if upgrade["id"] == "harvest_all":
        return 1

    speed_levels = upgrade["base_interval"] - MIN_UPGRADE_INTERVAL + 1
    power_levels = MAX_UPGRADE_ACTIONS - 1
    return speed_levels + power_levels


def is_upgrade_maxed(upgrade):
    if upgrade["id"] == "harvest_all":
        return harvest_all_unlocked

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

    upgrade["next_action"] = time.time() + get_upgrade_interval(upgrade)


def run_automation():
    now = time.time()

    for upgrade in upgrades:
        if upgrade["id"] == "harvest_all":
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


# ============================================================
# DISPLAY: UPGRADE SHOP
# ============================================================

def format_upgrade_name(upgrade):
    name = upgrade["name"]

    if is_upgrade_maxed(upgrade):
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
    spacer = " " * max(1, SHOP_PANEL_WIDTH - 2 - visible_length(name) - visible_length(price))

    return box_line(name + spacer + price)


def build_upgrade_shop_lines():
    border = "+" + ("-" * (SHOP_PANEL_WIDTH - 2)) + "+"

    lines = [
        border,
        box_line("UPGRADE-SHOP"),
        border,
        box_line("w/s: Auswahl"),
        box_line("Enter/Space: kaufen"),
        box_line("u: Fokus verlassen"),
        border,
    ]

    for index, upgrade in enumerate(upgrades):
        lines.append(build_upgrade_item_line(upgrade, shop_open and index == selected_upgrade))
        lines.append(box_line("  " + format_upgrade_description(upgrade)))
        lines.append(box_line())

    lines.append(border)

    return lines


# ============================================================
# DISPLAY: MAIN
# ============================================================

def draw_garden():
    garden_lines = build_garden_lines()

    if manager_open:
        shop_lines = build_manager_lines()
    elif seed_shop_open:
        shop_lines = build_seed_shop_lines()
    elif sell_shop_open:
        shop_lines = build_sell_shop_lines()
    elif shop_open:
        shop_lines = build_upgrade_shop_lines()
    else:
        shop_lines = build_help_lines()

    terminal_width = shutil.get_terminal_size((80, 24)).columns

    if shop_lines and terminal_width >= SHOP_PANEL_WIDTH + 34:
        max_lines = max(len(garden_lines), len(shop_lines))

        for index in range(max_lines):
            left = garden_lines[index] if index < len(garden_lines) else ""
            right = shop_lines[index] if index < len(shop_lines) else ""
            spacing = max(2, terminal_width - SHOP_PANEL_WIDTH - visible_length(left))
            print(left + (" " * spacing) + right)
    else:
        for line in garden_lines:
            print(line)

        if shop_lines:
            print()
            for line in shop_lines:
                print(line)

    print()
    print("> ", end="", flush=True)


# ============================================================
# GARDEN: FIELD SEARCH
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
# GARDEN: PLANTING / GROWTH
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
# GARDEN: BUY / SELL / HARVEST
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


def sell_crop(crop_id, amount):
    global gold

    crop = get_crop(crop_id)
    owned = inventory[crop_id]

    if owned <= 0:
        return

    amount_to_sell = owned if amount == "all" else min(amount, owned)

    inventory[crop_id] -= amount_to_sell
    gold += amount_to_sell * crop["sell_price"]

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
# INPUT HANDLING: SHOPS / MANAGER
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

    if command == "w":
        selected_upgrade = (selected_upgrade - 1) % len(upgrades)
    elif command == "s":
        selected_upgrade = (selected_upgrade + 1) % len(upgrades)
    elif command in ("enter", "space"):
        buy_selected_upgrade()
    elif command == "u":
        shop_open = False

    return True


def handle_seed_shop_command(command):
    global seed_shop_open, selected_seed

    unlocked_crops = get_unlocked_crops()

    if not unlocked_crops:
        seed_shop_open = False
        return True

    selected_seed = selected_seed % len(unlocked_crops)

    if command == "w":
        selected_seed = (selected_seed - 1) % len(unlocked_crops)
    elif command == "s":
        selected_seed = (selected_seed + 1) % len(unlocked_crops)
    elif command in ("enter", "space"):
        crop_id = unlocked_crops[selected_seed]
        buy_seed(crop_id)
    elif command == "b":
        seed_shop_open = False

    return True


def handle_sell_shop_command(command):
    global sell_shop_open, selected_sell_crop, selected_sell_amount

    unlocked_crops = get_unlocked_crops()

    if not unlocked_crops:
        sell_shop_open = False
        return True

    selected_sell_crop = selected_sell_crop % len(unlocked_crops)

    if command == "w":
        selected_sell_crop = (selected_sell_crop - 1) % len(unlocked_crops)
    elif command == "s":
        selected_sell_crop = (selected_sell_crop + 1) % len(unlocked_crops)
    elif command == "a":
        selected_sell_amount = (selected_sell_amount - 1) % len(SELL_AMOUNTS)
    elif command == "d":
        selected_sell_amount = (selected_sell_amount + 1) % len(SELL_AMOUNTS)
    elif command in ("enter", "space"):
        crop_id = unlocked_crops[selected_sell_crop]
        amount = get_selected_sell_amount()
        sell_crop(crop_id, amount)
    elif command == "v":
        sell_shop_open = False

    return True


# ============================================================
# INPUT HANDLING: MAIN GAME
# ============================================================

def close_all_shops():
    global seed_shop_open, sell_shop_open, shop_open, manager_open, help_open

    seed_shop_open = False
    sell_shop_open = False
    shop_open = False
    manager_open = False
    help_open = False


def handle_game_command(command):
    global seed_shop_open, sell_shop_open, shop_open, manager_open, selected_manager_garden, help_open

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
    if command == "q":
        return False

    if manager_open:
        return handle_manager_command(command)
    
    if help_open:
        close_all_shops()  # help_open = False
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
    load_game()
    old_terminal_settings = termios.tcgetattr(sys.stdin)

    try:
        tty.setcbreak(sys.stdin)
        running = True

        while running:
            grow_plants()
            run_automation()
            update_shop_unlock()

            clear_screen()
            draw_garden()

            command = read_command()

            if command is not None:
                running = handle_command(command)

    finally:
        save_game()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_terminal_settings)


if __name__ == "__main__":
    args = parse_arguments()

    if args.dev:
        apply_dev_mode()

    main()
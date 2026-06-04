import argparse
import random
import re
import select
import shutil
import sys
import termios
import time
import tty


# ============================================================
# GLOBALS / CONFIG
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
SHOP_PANEL_WIDTH = 42

ACTIVE_CROP = "wheat"


# ============================================================
# CROPS / INVENTORY
# ============================================================

CROPS = {
    "wheat": {
        "name": "Weizen",
        "seed_name": "Weizensaat",
        "seed_price": 3,
        "sell_price": 2,
        "symbol": "Y",
    }
}
CROP_ORDER = ["wheat"]

inventory = {
    "wheat_seed": 5,
    "wheat": 0,
}

gold = 0


def get_crop(crop_id):
    return CROPS[crop_id]


# ============================================================
# GARDEN STATE
# ============================================================

garden = [
    [None, None, None, None, None],
    [None, None, None, None, None],
    [None, None, None, None, None],
    [None, None, None, None, None],
    [None, None, None, None, None],
]


# ============================================================
# UPGRADE STATE
# ============================================================
seed_shop_open = False
selected_seed = 0
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
# TERMINAL / DISPLAY HELPERS
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
# DISPLAY: GARDEN
# ============================================================

def format_garden_row(row):
    cells = []

    for cell in row:
        if cell is None:
            cells.append(".")
        elif cell["stage"] == ",":
            cells.append(",")
        elif cell["stage"] == "i":
            cells.append(GREEN + "i" + RESET)
        elif cell["stage"] == "Y":
            crop = get_crop(cell["crop"])
            cells.append(YELLOW + crop["symbol"] + RESET)

    return " ".join(cells)


def build_garden_lines():
    crop = get_crop(ACTIVE_CROP)

    lines = [
        "=== IDLE GARDEN ===",
        f"Gold: {gold} | {crop['seed_name']}: {inventory['wheat_seed']} | {crop['name']}: {inventory['wheat']}",
        "",
    ]

    for row in garden:
        lines.append(format_garden_row(row))

    lines.extend([
        "",
        f"[p] {crop['name']} pflanzen",
        "[h] Ernten",
        "[b] Saatgut-Shop öffnen",
        f"[v] {crop['name']} verkaufen ({crop['sell_price']} Gold)",
    ])

    if shop_unlocked:
        shop_action = "Fokus verlassen" if shop_open else "bedienen"
        lines.append(f"[u] Upgrade-Shop {shop_action}")

    lines.append("[q] Beenden")

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
                plant_seed(ACTIVE_CROP)
            elif upgrade["id"] == "harvest_helper":
                harvest_one()

        upgrade["next_action"] = now + get_upgrade_interval(upgrade)

# ============================================================
# CROP SHOP
# ============================================================
def build_seed_shop_lines():
    border = "+" + ("-" * (SHOP_PANEL_WIDTH - 2)) + "+"
    lines = [
        border,
        box_line("SAATGUT-SHOP"),
        border,
        box_line("Shop aktiv"),
        box_line("Up/Down oder a/d: Auswahl"),
        box_line("Enter/Space: kaufen"),
        box_line("b: Fokus verlassen"),
        border,
    ]

    for index, crop_id in enumerate(CROP_ORDER):
        crop = get_crop(crop_id)
        is_active = index == selected_seed

        selector = "> " if is_active else "  "
        name = selector + crop["seed_name"]

        if is_active:
            name = CYAN + name + RESET

        price_text = f"{crop['seed_price']}g"

        if gold < crop["seed_price"]:
            missing_gold = crop["seed_price"] - gold
            price_text = RED + f"{price_text} fehlt {missing_gold}g" + RESET

        content_width = SHOP_PANEL_WIDTH - 2
        spacer = " " * max(1, content_width - visible_length(name) - visible_length(price_text))

        lines.append(box_line(name + spacer + price_text))
        lines.append(box_line(f"  Besitz: {inventory[f'{crop_id}_seed']}"))
        lines.append(box_line())

    lines.append(border)

    return lines


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
        missing_gold = price - gold
        return RED + f"{price_text} fehlt {missing_gold}g" + RESET

    return price_text


def format_upgrade_description(upgrade):
    if upgrade["id"] == "harvest_all":
        return "h erntet alle reifen Pflanzen"

    interval = get_upgrade_interval(upgrade)
    action_count = get_upgrade_action_count(upgrade)

    if upgrade["id"] == "saat_boy":
        crop = get_crop(ACTIVE_CROP)
        return f"pflanzt alle {interval}s {action_count}x {crop['name']}"

    action = "Feld" if action_count == 1 else "Felder"
    return f"erntet alle {interval}s {action_count} {action}"


def build_upgrade_item_line(upgrade, is_active):
    selector = "> " if is_active else "  "
    name = selector + format_upgrade_name(upgrade)

    if is_active:
        name = CYAN + name + RESET

    price = format_upgrade_price(upgrade)
    content_width = SHOP_PANEL_WIDTH - 2
    spacer = " " * max(1, content_width - visible_length(name) - visible_length(price))

    return box_line(name + spacer + price)


def build_upgrade_shop_lines():
    border = "+" + ("-" * (SHOP_PANEL_WIDTH - 2)) + "+"
    lines = [
        border,
        box_line("UPGRADE-SHOP"),
        border,
    ]

    if shop_open:
        lines.extend([
            box_line("Shop aktiv"),
            box_line("Up/Down oder a/d: Auswahl"),
            box_line("Enter/Space: kaufen"),
            box_line("u: Fokus verlassen"),
            border,
        ])
    else:
        lines.extend([
            box_line("u: Shop bedienen"),
            box_line(f"Gold: {gold}"),
            border,
        ])

    for index, upgrade in enumerate(upgrades):
        lines.append(build_upgrade_item_line(upgrade, shop_open and index == selected_upgrade))
        lines.append(box_line("  " + format_upgrade_description(upgrade)))
        lines.append(box_line())

    lines.append(border)

    return lines


def draw_garden():
    garden_lines = build_garden_lines()
    shop_lines = []
    if seed_shop_open:
        shop_lines = build_seed_shop_lines()
    elif shop_unlocked:
        shop_lines = build_upgrade_shop_lines()
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
# GARDEN LOGIC: FINDING FIELDS
# ============================================================

def find_empty_fields():
    empty_fields = []

    for row_index, row in enumerate(garden):
        for col_index, cell in enumerate(row):
            if cell is None:
                empty_fields.append((row_index, col_index))

    return empty_fields


def find_ready_fields():
    ready_fields = []

    for row_index, row in enumerate(garden):
        for col_index, cell in enumerate(row):
            if cell is not None and cell["stage"] == "Y":
                ready_fields.append((row_index, col_index))

    return ready_fields


# ============================================================
# GARDEN LOGIC: PLANTING / GROWTH
# ============================================================

def create_plant(crop_id):
    return {
        "crop": crop_id,
        "stage": ",",
        "next_growth": time.time() + random.randint(3, 8),
    }


def plant_seed(crop_id):
    seed_key = f"{crop_id}_seed"

    if inventory[seed_key] <= 0:
        return

    empty_fields = find_empty_fields()

    if not empty_fields:
        return

    row, col = random.choice(empty_fields)
    garden[row][col] = create_plant(crop_id)
    inventory[seed_key] -= 1


def grow_plants():
    now = time.time()

    for row in garden:
        for plant in row:
            if plant is None:
                continue

            if now < plant["next_growth"]:
                continue

            if plant["stage"] == ",":
                plant["stage"] = "i"
                plant["next_growth"] = now + random.randint(4, 10)
            elif plant["stage"] == "i":
                plant["stage"] = "Y"


# ============================================================
# GARDEN LOGIC: BUY / SELL / HARVEST
# ============================================================

def buy_seed(crop_id):
    global gold

    crop = get_crop(crop_id)

    if gold < crop["seed_price"]:
        return

    gold -= crop["seed_price"]
    inventory[f"{crop_id}_seed"] += 1


def sell_crop(crop_id):
    global gold

    crop = get_crop(crop_id)

    if inventory[crop_id] <= 0:
        return

    inventory[crop_id] -= 1
    gold += crop["sell_price"]
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


def harvest_plant(row_index, col_index):
    cell = garden[row_index][col_index]

    if cell is None or cell["stage"] != "Y":
        return False

    crop_id = cell["crop"]
    crop_reward, seed_reward = calculate_harvest_reward()

    garden[row_index][col_index] = None
    inventory[crop_id] += crop_reward
    inventory[f"{crop_id}_seed"] += seed_reward

    return True


def harvest_one():
    ready_fields = find_ready_fields()

    if not ready_fields:
        return False

    row_index, col_index = random.choice(ready_fields)
    return harvest_plant(row_index, col_index)


def harvest_all():
    for row_index, col_index in find_ready_fields():
        harvest_plant(row_index, col_index)


# ============================================================
# INPUT
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
        "A": "up",
        "B": "down",
        "C": "right",
        "D": "left",
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


def handle_shop_command(command):
    global shop_open, selected_upgrade

    if command in ("up", "left", "a"):
        selected_upgrade = (selected_upgrade - 1) % len(upgrades)
    elif command in ("down", "right", "d"):
        selected_upgrade = (selected_upgrade + 1) % len(upgrades)
    elif command in ("enter", "space"):
        buy_selected_upgrade()
    elif command == "u":
        shop_open = False

    return True

def handle_seed_shop_command(command):
    global seed_shop_open, selected_seed

    if command in ("up", "left", "a"):
        selected_seed = (selected_seed - 1) % len(CROP_ORDER)
    elif command in ("down", "right", "d"):
        selected_seed = (selected_seed + 1) % len(CROP_ORDER)
    elif command in ("enter", "space"):
        crop_id = CROP_ORDER[selected_seed]
        buy_seed(crop_id)
    elif command == "b":
        seed_shop_open = False

    return True

def handle_game_command(command):
    global shop_open, seed_shop_open

    if command == "p":
        plant_seed(ACTIVE_CROP)
    elif command == "h":
        if harvest_all_unlocked:
            harvest_all()
        else:
            harvest_one()
    elif command == "b":
        seed_shop_open = True
    elif command == "v":
        sell_crop(ACTIVE_CROP)
    elif command == "u" and shop_unlocked:
        shop_open = True

    return True


def handle_command(command):
    if command == "q":
        return False

    if seed_shop_open:
        return handle_seed_shop_command(command)

    if shop_open:
        return handle_shop_command(command)

    return handle_game_command(command)


# ============================================================
# DEV / MAIN LOOP
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

    gold = 1000
    inventory["wheat_seed"] = 100
    inventory["wheat"] = 100
    shop_unlocked = True


def main():
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
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_terminal_settings)


if __name__ == "__main__":
    args = parse_arguments()

    if args.dev:
        apply_dev_mode()

    main()
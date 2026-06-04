import time
import random
import re
import select
import shutil
import sys
import termios
import tty

GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
RESET = "\033[0m"
ANSI_ESCAPE = re.compile(r"\033\[[0-9;]*m")
SEED_PRICE = 3
BONUS_HARVEST_CHANCE = 0.1
UPGRADE_UNLOCK_GOLD = 10
SAAT_BOY_INTERVAL = 5
HARVEST_HELPER_INTERVAL = 5
MIN_UPGRADE_INTERVAL = 1
MAX_UPGRADE_ACTIONS = 5
SHOP_PANEL_WIDTH = 42

garden = [
    [None, None, None, None, None],
    [None, None, None, None, None],
    [None, None, None, None, None],
    [None, None, None, None, None],
    [None, None, None, None, None],
]

seeds = 5
gold = 0
shop_unlocked = False
shop_open = False
selected_upgrade = 0
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
]


def clear_screen():
    print("\033[H\033[J", end="")

def visible_length(text):
    return len(ANSI_ESCAPE.sub("", text))


def pad_visible(text, width):
    padding = max(0, width - visible_length(text))
    return text + (" " * padding)


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
            cells.append(YELLOW + "Y" + RESET)

    return " ".join(cells)


def build_garden_lines():
    lines = [
        "=== IDLE GARDEN ===",
        f"Samen: {seeds} | Gold: {gold}",
        "",
    ]

    for row in garden:
        lines.append(format_garden_row(row))

    lines.extend([
        "",
        "[p] Samen pflanzen",
        "[h] Ernten",
        f"[b] Samen kaufen ({SEED_PRICE} Gold)",
    ])

    if shop_unlocked:
        shop_action = "Fokus verlassen" if shop_open else "bedienen"
        lines.append(f"[u] Upgrade-Shop {shop_action}")

    lines.append("[q] Beenden")

    return lines


def box_line(content=""):
    content_width = SHOP_PANEL_WIDTH - 2
    return "|" + pad_visible(content, content_width) + "|"


def get_upgrade_max_level(upgrade):
    speed_levels = upgrade["base_interval"] - MIN_UPGRADE_INTERVAL + 1
    power_levels = MAX_UPGRADE_ACTIONS - 1
    return speed_levels + power_levels


def is_upgrade_maxed(upgrade):
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


def build_upgrade_item_line(upgrade, is_active):
    selector = "> " if is_active else "  "
    name = selector + format_upgrade_name(upgrade)

    if is_active:
        name = CYAN + name + RESET

    price = format_upgrade_price(upgrade)
    content_width = SHOP_PANEL_WIDTH - 2
    spacer = " " * max(1, content_width - visible_length(name) - visible_length(price))

    return box_line(name + spacer + price)


def format_upgrade_description(upgrade):
    interval = get_upgrade_interval(upgrade)
    action_count = get_upgrade_action_count(upgrade)

    if upgrade["id"] == "saat_boy":
        action = "Samen" if action_count != 1 else "Samen"
        return f"pflanzt alle {interval}s {action_count} {action}"

    action = "Feld" if action_count == 1 else "Felder"
    return f"erntet alle {interval}s {action_count} {action}"


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
    shop_lines = build_upgrade_shop_lines() if shop_unlocked else []
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


def update_shop_unlock():
    global shop_unlocked

    if gold >= UPGRADE_UNLOCK_GOLD:
        shop_unlocked = True


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


def create_plant():
    return {
        "stage": ",",
        "next_growth": time.time() + random.randint(3, 8)
    }


def plant_seed():
    global seeds

    if seeds <= 0:
        return

    empty_fields = find_empty_fields()

    if not empty_fields:
        return

    row, col = random.choice(empty_fields)
    garden[row][col] = create_plant()
    seeds -= 1


def buy_seed():
    global gold, seeds

    if gold < SEED_PRICE:
        return

    gold -= SEED_PRICE
    seeds += 1


def buy_selected_upgrade():
    global gold

    upgrade = upgrades[selected_upgrade]
    price = get_upgrade_price(upgrade)

    if price is None or gold < price:
        return

    gold -= price
    upgrade["level"] += 1
    upgrade["next_action"] = time.time() + get_upgrade_interval(upgrade)


def grow_plants():
    now = time.time()

    for row in garden:
        for plant in row:
            if plant is None:
                continue

            if now >= plant["next_growth"]:
                if plant["stage"] == ",":
                    plant["stage"] = "i"
                    plant["next_growth"] = now + random.randint(4, 10)
                elif plant["stage"] == "i":
                    plant["stage"] = "Y"


def calculate_harvest_reward():
    gold_reward = 1
    seed_reward = 1

    if random.random() < BONUS_HARVEST_CHANCE:
        bonus_type = random.choice(["gold", "seeds"])

        if bonus_type == "gold":
            gold_reward += 1
        else:
            seed_reward += 1

    return gold_reward, seed_reward


def harvest_plant(row_index, col_index):
    global gold, seeds

    cell = garden[row_index][col_index]

    if cell is None or cell["stage"] != "Y":
        return False

    garden[row_index][col_index] = None
    gold_reward, seed_reward = calculate_harvest_reward()
    gold += gold_reward
    seeds += seed_reward
    update_shop_unlock()

    return True


def harvest():
    for row_index, col_index in find_ready_fields():
        harvest_plant(row_index, col_index)


def harvest_one():
    ready_fields = find_ready_fields()

    if not ready_fields:
        return False

    row_index, col_index = random.choice(ready_fields)
    return harvest_plant(row_index, col_index)


def run_automation():
    now = time.time()

    for upgrade in upgrades:
        if upgrade["level"] <= 0:
            continue

        if upgrade["next_action"] is None:
            upgrade["next_action"] = now + get_upgrade_interval(upgrade)
            continue

        if now < upgrade["next_action"]:
            continue

        for _ in range(get_upgrade_action_count(upgrade)):
            if upgrade["id"] == "saat_boy":
                plant_seed()
            elif upgrade["id"] == "harvest_helper":
                harvest_one()

        upgrade["next_action"] = now + get_upgrade_interval(upgrade)


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


def handle_command(command):
    global shop_open, selected_upgrade

    if command == "q":
        return False

    if shop_open:
        if command in ("up", "left", "a"):
            selected_upgrade = (selected_upgrade - 1) % len(upgrades)
        elif command in ("down", "right", "d"):
            selected_upgrade = (selected_upgrade + 1) % len(upgrades)
        elif command in ("enter", "space"):
            buy_selected_upgrade()
        elif command == "u":
            shop_open = False

        return True

    if command == "p":
        plant_seed()
    elif command == "h":
        harvest()
    elif command == "b":
        buy_seed()
    elif command == "u" and shop_unlocked:
        shop_open = True

    return True


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
                update_shop_unlock()
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_terminal_settings)


if __name__ == "__main__":
    main()

import argparse
import select
import sys
import termios
import time
import tty

from config import *
from data import *
from terminal import *
import state
import savegame
from items import *
from garden import *
from processors import *
from upgrades import *


# ============================================================
# DISPLAY: GARDEN
# ============================================================

def build_inventory_lines():
    lines = [
        f"Gold: {state.gold}",
    ]

    for crop_id in CROP_ORDER:
        if not is_crop_unlocked(crop_id):
            continue

        crop = get_crop(crop_id)
        seed_amount = state.inventory[get_seed_key(crop_id)]
        crop_amount = state.inventory[crop_id]

        lines.append(f"{crop['seed_name']}: {seed_amount} | {crop['name']}: {crop_amount}")

    for product_id in PRODUCT_ORDER:
        if is_product_visible(product_id):
            product = get_product(product_id)
            lines.append(f"{product['name']}: {state.inventory[product_id]}")

    for item_key in ITEM_ORDER:
        if is_inventory_item_visible(item_key):
            lines.append(f"{get_item_name(item_key)}: {state.inventory[item_key]}")

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
        f"Gold {state.gold}",
    ]

    for product_id in PRODUCT_ORDER:
        if is_product_visible(product_id):
            summary_parts.append(f"{get_product(product_id)['name']} {state.inventory[product_id]}")

    for item_key in ITEM_ORDER:
        if is_inventory_item_visible(item_key):
            summary_parts.append(f"{get_item_name(item_key)} {state.inventory[item_key]}")

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
    current = state.stats["harvested"][required_crop]

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

    if garden_index == state.active_garden:
        label = "> " + label
        return CYAN + pad_visible(label, GARDEN_PANEL_WIDTH) + RESET

    return pad_visible("  " + label, GARDEN_PANEL_WIDTH)


def format_garden_row(garden_index, row_index):
    row = state.gardens[garden_index][row_index]
    cells = [format_cell(cell) for cell in row]
    return pad_visible(" ".join(cells), GARDEN_PANEL_WIDTH)


def build_garden_grid_lines():
    lines = []

    for block_start in range(0, len(state.gardens), GARDENS_PER_ROW):
        block_indices = list(range(block_start, min(block_start + GARDENS_PER_ROW, len(state.gardens))))

        lines.append("  ".join(format_garden_header(index) for index in block_indices))

        for row_index in range(GARDEN_SIZE):
            lines.append("  ".join(format_garden_row(index, row_index) for index in block_indices))

        lines.append("")

    if lines and lines[-1] == "":
        lines.pop()

    return lines


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
    active_crop = get_crop(get_garden_crop(state.active_garden))

    lines = [
        fit_visible(
            f"IDLE GARDEN | Feld {state.active_garden + 1}/{len(state.gardens)} | Saatgut: {active_crop['seed_name']}",
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

    for index in range(len(state.gardens)):
        crop_id = get_garden_crop(index)
        crop = get_crop(crop_id)
        is_selected = index == state.selected_manager_garden

        selector = "> " if is_selected else "  "
        active_marker = " aktiv" if index == state.active_garden else ""
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
    active_seed = clamp_shop_selection(state.selected_seed, len(CROP_ORDER))
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
            current = state.stats["harvested"][required_crop]
            locked_text = RED + "gesperrt" + RESET

            lines.append(box_split_line(name, locked_text))
            lines.append(box_line(f"  braucht: {current}/{required_amount} {required_name}"))
            lines.append(box_line())
            continue

        price_text = f"{crop['seed_price']}g"

        if state.gold < crop["seed_price"]:
            price_text = RED + f"{price_text} fehlt {crop['seed_price'] - state.gold}g" + RESET

        lines.append(box_split_line(name, price_text))
        lines.append(box_line(f"  Besitz: {state.inventory[get_seed_key(crop_id)]}"))
        lines.append(box_line())

    lines.append(border)

    return lines


def format_sell_amount_label(amount):
    if amount == "all":
        return "alle"

    return f"{amount}x"


def get_selected_sell_amount():
    return SELL_AMOUNTS[state.selected_sell_amount]


def build_sell_shop_lines():
    sellable_items = get_sellable_items()
    active_sell_crop = clamp_shop_selection(state.selected_sell_crop, len(sellable_items))
    page_items, _, _, page_start = get_shop_page_items(sellable_items, active_sell_crop)
    selected_amount = get_selected_sell_amount()
    border = "+" + ("-" * (SHOP_PANEL_WIDTH - 2)) + "+"

    amount_labels = []

    for index, amount in enumerate(SELL_AMOUNTS):
        label = format_sell_amount_label(amount)

        if index == state.selected_sell_amount:
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

        owned = state.inventory[item_key]
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


def build_upgrade_item_line(upgrade, is_active):
    selector = "> " if is_active else "  "
    name = selector + format_upgrade_name(upgrade)

    if is_active:
        name = CYAN + name + RESET

    price = format_upgrade_price(upgrade)

    return box_split_line(name, price)


def build_upgrade_shop_lines():
    active_upgrade = clamp_shop_selection(state.selected_upgrade, len(state.upgrades))
    page_upgrades, _, _, page_start = get_shop_page_items(state.upgrades, active_upgrade)
    border = "+" + ("-" * (SHOP_PANEL_WIDTH - 2)) + "+"

    lines = [
        border,
        box_line("UPGRADE-SHOP"),
        border,
        box_line("w/s: Auswahl"),
        box_line("Enter/Space: kaufen"),
        box_line("u: Fokus verlassen"),
        build_shop_page_line(active_upgrade, len(state.upgrades)),
        border,
    ]

    for offset, upgrade in enumerate(page_upgrades):
        index = page_start + offset
        lines.append(build_upgrade_item_line(upgrade, state.shop_open and index == active_upgrade))
        lines.append(box_line("  " + format_upgrade_description(upgrade)))
        lines.append(box_line())

    lines.append(border)

    return lines


# ============================================================
# DISPLAY MAIN
# ============================================================

def draw_garden():
    garden_lines = build_garden_lines()

    if state.manager_open:
        menu_lines = build_manager_lines()
    elif state.seed_shop_open:
        menu_lines = build_seed_shop_lines()
    elif state.sell_shop_open:
        menu_lines = build_sell_shop_lines()
    elif state.shop_open:
        menu_lines = build_upgrade_shop_lines()
    else:
        menu_lines = build_help_lines()

    focus_panel_open = (
        state.manager_open
        or state.seed_shop_open
        or state.sell_shop_open
        or state.shop_open
    )

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
    if command == "w":
        state.selected_manager_garden = (state.selected_manager_garden - 1) % len(state.gardens)
    elif command == "s":
        state.selected_manager_garden = (state.selected_manager_garden + 1) % len(state.gardens)
    elif command == "a":
        current_crop = get_garden_crop(state.selected_manager_garden)
        set_garden_crop(state.selected_manager_garden, get_next_crop_id(current_crop, -1))
    elif command == "d":
        current_crop = get_garden_crop(state.selected_manager_garden)
        set_garden_crop(state.selected_manager_garden, get_next_crop_id(current_crop, 1))
    elif command in ("enter", "space"):
        state.active_garden = state.selected_manager_garden
    elif command == "m":
        state.manager_open = False

    return True


def handle_upgrade_shop_command(command):
    state.selected_upgrade = clamp_shop_selection(state.selected_upgrade, len(state.upgrades))

    if command == "w":
        state.selected_upgrade = (state.selected_upgrade - 1) % len(state.upgrades)
    elif command == "s":
        state.selected_upgrade = (state.selected_upgrade + 1) % len(state.upgrades)
    elif command == "q":
        state.selected_upgrade = change_shop_page(state.selected_upgrade, len(state.upgrades), -1)
    elif command == "e":
        state.selected_upgrade = change_shop_page(state.selected_upgrade, len(state.upgrades), 1)
    elif command in ("enter", "space"):
        buy_selected_upgrade(state.selected_upgrade)
    elif command == "u":
        state.shop_open = False

    return True


def handle_seed_shop_command(command):
    crop_ids = CROP_ORDER

    if not crop_ids:
        state.seed_shop_open = False
        return True

    state.selected_seed = clamp_shop_selection(state.selected_seed, len(crop_ids))

    if command == "w":
        state.selected_seed = (state.selected_seed - 1) % len(crop_ids)
    elif command == "s":
        state.selected_seed = (state.selected_seed + 1) % len(crop_ids)
    elif command == "q":
        state.selected_seed = change_shop_page(state.selected_seed, len(crop_ids), -1)
    elif command == "e":
        state.selected_seed = change_shop_page(state.selected_seed, len(crop_ids), 1)
    elif command in ("enter", "space"):
        crop_id = crop_ids[state.selected_seed]
        buy_seed(crop_id)
    elif command == "b":
        state.seed_shop_open = False

    return True


def handle_sell_shop_command(command):
    sellable_items = get_sellable_items()

    if not sellable_items:
        state.sell_shop_open = False
        return True

    state.selected_sell_crop = clamp_shop_selection(state.selected_sell_crop, len(sellable_items))

    if command == "w":
        state.selected_sell_crop = (state.selected_sell_crop - 1) % len(sellable_items)
    elif command == "s":
        state.selected_sell_crop = (state.selected_sell_crop + 1) % len(sellable_items)
    elif command == "q":
        state.selected_sell_crop = change_shop_page(state.selected_sell_crop, len(sellable_items), -1)
    elif command == "e":
        state.selected_sell_crop = change_shop_page(state.selected_sell_crop, len(sellable_items), 1)
    elif command == "a":
        state.selected_sell_amount = (state.selected_sell_amount - 1) % len(SELL_AMOUNTS)
    elif command == "d":
        state.selected_sell_amount = (state.selected_sell_amount + 1) % len(SELL_AMOUNTS)
    elif command in ("enter", "space"):
        item_key = sellable_items[state.selected_sell_crop]
        amount = get_selected_sell_amount()
        sell_item(item_key, amount)
        update_shop_unlock()
    elif command == "v":
        state.sell_shop_open = False

    return True


def close_all_shops():
    state.seed_shop_open = False
    state.sell_shop_open = False
    state.shop_open = False
    state.manager_open = False
    state.help_open = False


def handle_game_command(command):
    if command == "p":
        plant_seed_in_garden(get_garden_crop(state.active_garden), state.active_garden)
    elif command == "h":
        if state.harvest_all_unlocked:
            harvest_all_in_garden(state.active_garden)
        else:
            harvest_one_in_garden(state.active_garden)
    elif command == "f":
        cycle_active_garden()
    elif command == "m":
        close_all_shops()
        state.selected_manager_garden = state.active_garden
        state.manager_open = True
    elif command == "n":
        buy_new_garden()
    elif command == "b":
        close_all_shops()
        state.seed_shop_open = True
    elif command == "v":
        close_all_shops()
        state.sell_shop_open = True
    elif command == "u" and state.shop_unlocked:
        close_all_shops()
        state.shop_open = True

    return True


def handle_command(command):
    if command == "q" and not (state.seed_shop_open or state.sell_shop_open or state.shop_open):
        return False

    if state.manager_open:
        return handle_manager_command(command)

    if state.help_open:
        close_all_shops()
        return True

    if state.seed_shop_open:
        return handle_seed_shop_command(command)

    if state.sell_shop_open:
        return handle_sell_shop_command(command)

    if state.shop_open:
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
    state.gold = 100000

    state.inventory["wheat_seed"] = 100
    state.inventory["wheat"] = 100
    state.inventory["rye_seed"] = 25
    state.inventory["rye"] = 25

    state.stats["harvested"]["wheat"] = 25

    state.shop_unlocked = True


def main():
    (
        state.gold,
        state.active_garden,
        state.shop_unlocked,
        state.harvest_all_unlocked,
    ) = savegame.load_game(
        state.gold,
        state.inventory,
        state.stats,
        state.gardens,
        state.garden_crops,
        state.active_garden,
        state.shop_unlocked,
        state.harvest_all_unlocked,
        state.ensure_inventory_defaults,
        state.ensure_stats_defaults,
        state.merge_saved_upgrades,
        state.merge_saved_processors,
        state.sync_processors_with_upgrades,
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
            state.gold,
            state.inventory,
            state.stats,
            state.gardens,
            state.garden_crops,
            state.active_garden,
            state.shop_unlocked,
            state.harvest_all_unlocked,
            state.upgrades,
            state.processors,
        )
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_terminal_settings)


if __name__ == "__main__":
    args = parse_arguments()

    if args.dev:
        apply_dev_mode()

    main()
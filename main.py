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
from render import *
import menu

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

def reset_game_state():
    state.gold = 0

    state.inventory.clear()
    state.inventory.update({
        "wheat_seed": 5,
        "wheat": 0,
        "rye_seed": 0,
        "rye": 0,
        "hops_seed": 0,
        "hops": 0,
        "grape_seed": 0,
        "grape": 0,
        "flour": 0,
        "yeast": 0,
    })

    state.stats.clear()
    state.stats.update({
        "harvested": {
            "wheat": 0,
            "rye": 0,
            "hops": 0,
            "grape": 0,
            "flour": 0,
            "yeast": 0,
        }
    })

    state.gardens.clear()
    state.gardens.append(state.create_empty_garden())

    state.garden_crops.clear()
    state.garden_crops.append("wheat")

    state.active_garden = 0

    state.seed_shop_open = False
    state.selected_seed = 0

    state.sell_shop_open = False
    state.selected_sell_crop = 0
    state.selected_sell_amount = 0

    state.manager_open = False
    state.selected_manager_garden = 0

    state.help_open = False

    state.shop_unlocked = False
    state.shop_open = False
    state.selected_upgrade = 0
    state.harvest_all_unlocked = False

    state.upgrades.clear()
    state.upgrades.extend([
        {
            "id": "saat_boy",
            "name": "Saat-Boy",
            "type": "automation",
            "base_price": 10,
            "base_interval": SAAT_BOY_INTERVAL,
            "level": 0,
            "next_action": None,
        },
        {
            "id": "harvest_helper",
            "name": "Erntehelfer",
            "type": "automation",
            "base_price": 20,
            "base_interval": HARVEST_HELPER_INTERVAL,
            "level": 0,
            "next_action": None,
        },
        {
            "id": "harvest_all",
            "name": "Erntemaschine",
            "type": "command",
            "base_price": 5000,
            "max_level": 1,
            "level": 0,
            "next_action": None,
        },
    ])

    state.upgrades.extend(
        state.create_processor_upgrade(processor_id)
        for processor_id in PROCESSOR_ORDER
    )

    state.processors.clear()
    state.processors.update({
        processor_id: state.create_processor_state()
        for processor_id in PROCESSOR_ORDER
    })

    state.ensure_inventory_defaults()
    state.ensure_stats_defaults()


def main():
    old_terminal_settings = termios.tcgetattr(sys.stdin)

    try:
        tty.setcbreak(sys.stdin)

        start_action = menu.run_start_menu(read_command)

        if start_action == "quit":
            return

        if start_action == "new_game":
            reset_game_state()
        elif start_action == "load_game":
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
# menu.py

from config import CYAN, RESET
from terminal import clear_screen


LOGO = r"""
  ___ ____  _     _____    ____    _    ____  ____  _____ _   _
 |_ _|  _ \| |   | ____|  / ___|  / \  |  _ \|  _ \| ____| \ | |
  | || | | | |   |  _|   | |  _  / _ \ | |_) | | | |  _| |  \| |
  | || |_| | |___| |___  | |_| |/ ___ \|  _ <| |_| | |___| |\  |
 |___|____/|_____|_____|  \____/_/   \_\_| \_\____/|_____|_| \_|
"""


MENU_ITEMS = [
    ("new_game", "Neues Spiel"),
    ("load_game", "Spiel laden"),
    ("help", "Hilfe"),
    ("quit", "Beenden"),
]


def draw_start_menu(selected_index):
    clear_screen()

    print(LOGO)
    print()

    for index, (_, label) in enumerate(MENU_ITEMS):
        prefix = "> " if index == selected_index else "  "
        line = prefix + label

        if index == selected_index:
            line = CYAN + line + RESET

        print(" " * 26 + line)

    print()
    print(" " * 26 + "w/s: Auswahl")
    print(" " * 26 + "Enter/Space: bestätigen")
    print()
    print("> ", end="", flush=True)


def draw_start_help():
    clear_screen()

    print(LOGO)
    print()
    print(" " * 22 + "HILFE")
    print()
    print(" " * 22 + "[p] Pflanzt im aktiven Feld")
    print(" " * 22 + "[h] Erntet aktives Feld")
    print(" " * 22 + "[f] Wechselt aktives Feld")
    print(" " * 22 + "[m] Feld-Manager")
    print(" " * 22 + "[n] Neues Feld kaufen")
    print(" " * 22 + "[b] Saatgut-Shop")
    print(" " * 22 + "[v] Verkaufsshop")
    print(" " * 22 + "[u] Upgrade-Shop")
    print(" " * 22 + "[q] Speichern und Beenden")
    print()
    print(" " * 22 + "Beliebige Taste: zurück")
    print()
    print("> ", end="", flush=True)


def run_start_menu(read_command):
    selected_index = 0
    # if savegame exists, preselect index 1

    while True:
        draw_start_menu(selected_index)
        command = read_command()

        if command is None:
            continue

        if command == "w":
            selected_index = (selected_index - 1) % len(MENU_ITEMS)
        elif command == "s":
            selected_index = (selected_index + 1) % len(MENU_ITEMS)
        elif command in ("enter", "space"):
            action, _ = MENU_ITEMS[selected_index]

            if action == "help":
                draw_start_help()

                while read_command() is None:
                    pass

                continue

            return action
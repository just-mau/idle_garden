import time
import random
import select
import sys
import termios
import tty

GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"

garden = [
    [None, None, None, None, None],
    [None, None, None, None, None],
    [None, None, None, None, None],
    [None, None, None, None, None],
    [None, None, None, None, None],
]

seeds = 5
gold = 0


def clear_screen():
    print("\033[H\033[J", end="")

def draw_garden():
    print("=== IDLE GARDEN ===")
    print(f"Samen: {seeds} | Gold: {gold}")
    print()

    for row in garden:
        for cell in row:
            if cell is None:
                print(".", end=" ")
            elif cell["stage"] == ",":
                print(",", end=" ")
            elif cell["stage"] == "i":
                print(GREEN + "i" + RESET, end=" ")
            elif cell["stage"] == "Y":
                print(YELLOW + "Y" + RESET, end=" ")
        print()

    print()
    print("[p] Samen pflanzen")
    print("[h] Ernten")
    print("[q] Beenden")
    print()
    print("> ", end="", flush=True)

def create_plant():
    return {
        "stage": ",",
        "next_growth": time.time() + random.randint(3, 8)
    }


def plant_seed():
    global seeds

    if seeds <= 0:
        return

    empty_fields = []

    for row_index, row in enumerate(garden):
        for col_index, cell in enumerate(row):
            if cell is None:
                empty_fields.append((row_index, col_index))

    if not empty_fields:
        return

    row, col = random.choice(empty_fields)
    garden[row][col] = create_plant()
    seeds -= 1

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


def harvest():
    global gold, seeds

    for row_index, row in enumerate(garden):
        for col_index, cell in enumerate(row):
            if cell is not None and cell["stage"] == "Y":
                garden[row_index][col_index] = None
                gold += 1
                seeds += 1


def read_command(timeout=0.25):
    ready, _, _ = select.select([sys.stdin], [], [], timeout)

    if not ready:
        return None

    return sys.stdin.read(1).lower()


def handle_command(command):
    if command == "p":
        plant_seed()
    elif command == "h":
        harvest()
    elif command == "q":
        return False

    return True


def main():
    old_terminal_settings = termios.tcgetattr(sys.stdin)

    try:
        tty.setcbreak(sys.stdin)
        running = True

        while running:
            grow_plants()
            clear_screen()
            draw_garden()

            command = read_command()

            if command is not None:
                running = handle_command(command)
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_terminal_settings)


if __name__ == "__main__":
    main()

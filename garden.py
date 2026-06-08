# garden.py

import random
import time
import state

from config import (
    BONUS_HARVEST_CHANCE,
    GARDEN_SIZE,
    MAX_GARDENS,
)

from data import CROPS

from state import (
    active_garden,
    garden_crops,
    gardens,
    gold,
    inventory,
    stats,
    create_empty_garden,
    get_seed_key,
)

from items import (
    get_crop,
    get_sell_price,
    is_crop_unlocked,
)


def get_garden_crop(garden_index):
    return garden_crops[garden_index]


def set_garden_crop(garden_index, crop_id):
    if is_crop_unlocked(crop_id):
        garden_crops[garden_index] = crop_id


def get_new_garden_price():
    next_garden_number = len(state.gardens) + 1
    return int(100 * (next_garden_number ** 2.4))


def buy_new_garden():
    import state

    if len(gardens) >= MAX_GARDENS:
        return

    price = get_new_garden_price()

    if state.gold < price:
        return

    state.gold -= price
    gardens.append(create_empty_garden())
    garden_crops.append("wheat")


def cycle_active_garden():
    import state

    state.active_garden = (state.active_garden + 1) % len(gardens)


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


def plant_all_in_garden(garden_index):
    crop_id = get_garden_crop(garden_index)
    seed_key = get_seed_key(crop_id)
    planted = 0

    for selected_garden, row, col in find_empty_fields_in_garden(garden_index):
        if inventory[seed_key] <= 0:
            break

        gardens[selected_garden][row][col] = create_plant(crop_id)
        inventory[seed_key] -= 1
        planted += 1

    return planted > 0


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


def buy_seed(crop_id):
    import state

    if not is_crop_unlocked(crop_id):
        return

    crop = get_crop(crop_id)

    if state.gold < crop["seed_price"]:
        return

    state.gold -= crop["seed_price"]
    inventory[get_seed_key(crop_id)] += 1


def sell_item(item_key, amount):
    import state

    owned = inventory[item_key]

    if owned <= 0:
        return

    amount_to_sell = owned if amount == "all" else min(amount, owned)

    inventory[item_key] -= amount_to_sell
    state.gold += amount_to_sell * get_sell_price(item_key)


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

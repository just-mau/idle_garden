# items.py

from data import (
    CROPS,
    CROP_ORDER,
    PRODUCTS,
    PRODUCT_ORDER,
    ITEM_NAMES,
    PROCESSORS,
)

from state import (
    inventory,
    stats,
    processors,
    get_seed_key,
)


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
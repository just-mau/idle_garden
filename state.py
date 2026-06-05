from config import (
    GARDEN_SIZE,
    SAAT_BOY_INTERVAL,
    HARVEST_HELPER_INTERVAL,
)

from data import (
    CROPS,
    PRODUCTS,
    PROCESSORS,
    PROCESSOR_ORDER,
)


def get_seed_key(crop_id):
    return f"{crop_id}_seed"


def create_empty_garden():
    return [
        [None for _ in range(GARDEN_SIZE)]
        for _ in range(GARDEN_SIZE)
    ]


def create_processor_state():
    return {
        "unlocked": False,
        "started_at": None,
        "finish_at": None,
    }


def create_processor_upgrade(processor_id):
    processor = PROCESSORS[processor_id]

    return {
        "id": processor_id,
        "name": processor["name"],
        "type": "processor",
        "processor_id": processor_id,
        "base_price": processor["base_price"],
        "max_level": 1,
        "level": 0,
        "next_action": None,
    }


inventory = {
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
}

stats = {
    "harvested": {
        "wheat": 0,
        "rye": 0,
        "hops": 0,
        "grape": 0,
        "flour": 0,
        "yeast": 0,
    }
}

gold = 0

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
]

upgrades.extend(
    create_processor_upgrade(processor_id)
    for processor_id in PROCESSOR_ORDER
)

processors = {
    processor_id: create_processor_state()
    for processor_id in PROCESSOR_ORDER
}


def ensure_inventory_defaults():
    for crop_id in CROPS.keys():
        inventory.setdefault(get_seed_key(crop_id), 0)
        inventory.setdefault(crop_id, 0)

    for product_id in PRODUCTS.keys():
        inventory.setdefault(product_id, 0)

    for processor in PROCESSORS.values():
        for input_item in processor["inputs"]:
            inventory.setdefault(input_item["item_key"], 0)

        output = processor["output"]

        if output.get("type") == "item":
            inventory.setdefault(output["item_key"], 0)


def ensure_stats_defaults():
    if "harvested" not in stats:
        stats["harvested"] = {}

    for crop_id in CROPS.keys():
        stats["harvested"].setdefault(crop_id, 0)
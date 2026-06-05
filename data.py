from config import (
    MILL_DURATION,
    MILL_PRICE,
    FLOUR_SELL_PRICE,
)

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
    "hops": {
        "name": "Hopfen",
        "seed_name": "Hopfensaat",
        "seed_price": 15,
        "sell_price": 5,
        "symbol": "H",
        "growth_stage_1": 60,
        "growth_stage_2": 60,
        "unlock_crop": "rye",
        "unlock_amount": 100,
    },
    "grape": {
        "name": "Weintrauben",
        "seed_name": "Weinreben",
        "seed_price": 50,
        "sell_price": 25,
        "symbol": "G",
        "growth_stage_1": 90,
        "growth_stage_2": 90,
        "unlock_crop": "hops",
        "unlock_amount": 25,
    },
}

CROP_ORDER = [
    "wheat",
    "rye",
    "hops",
    "grape",
]

PRODUCTS = {
    "flour": {
        "name": "Mehl",
        "sell_price": FLOUR_SELL_PRICE,
    },
}

PRODUCT_ORDER = [
    "flour",
]

ITEM_NAMES = {
    "yeast": "Hefe",
}

ITEM_ORDER = [
    "yeast",
]

PROCESSORS = {
    "mill": {
        "name": "Mühle",
        "base_price": MILL_PRICE,
        "inputs": [
            {
                "item_key": "wheat",
                "amount": 1,
            },
        ],
        "output": {
            "type": "item",
            "item_key": "flour",
            "amount": 2,
        },
        "duration": MILL_DURATION,
    },
    "bakery": {
        "name": "Bäckerei",
        "base_price": 200,
        "inputs": [
            {
                "item_key": "flour",
                "amount": 2,
            },
        ],
        "output": {
            "type": "gold",
            "amount": 15,
        },
        "duration": 300,
    },
    "yeast_farm": {
        "name": "Hefefarm",
        "base_price": 300,
        "inputs": [
            {
                "item_key": "wheat",
                "amount": 2,
            },
        ],
        "output": {
            "type": "item",
            "item_key": "yeast",
            "amount": 5,
        },
        "duration": 300,
    },
    "brewery": {
        "name": "Brauerei",
        "base_price": 500,
        "inputs": [
            {
                "item_key": "hops",
                "amount": 5,
            },
            {
                "item_key": "yeast",
                "amount": 5,
            },
        ],
        "output": {
            "type": "gold",
            "amount": 50,
        },
        "duration": 600,
    },
}

PROCESSOR_ORDER = [
    "mill",
    "bakery",
    "yeast_farm",
    "brewery",
]
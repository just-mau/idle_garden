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
        "growth_stage_1": 20,
        "growth_stage_2": 20,
    },
    "rye": {
        "name": "Roggen",
        "seed_name": "Roggensaat",
        "seed_price": 25,
        "sell_price": 8,
        "symbol": "R",
        "growth_stage_1": 60,
        "growth_stage_2": 60,
        "unlock_crop": "wheat",
        "unlock_amount": 75,
    },
    "hops": {
        "name": "Hopfen",
        "seed_name": "Hopfensaat",
        "seed_price": 80,
        "sell_price": 22,
        "symbol": "H",
        "growth_stage_1": 180,
        "growth_stage_2": 180,
        "unlock_crop": "rye",
        "unlock_amount": 150,
    },
    "grape": {
        "name": "Weintrauben",
        "seed_name": "Weinreben",
        "seed_price": 250,
        "sell_price": 80,
        "symbol": "G",
        "growth_stage_1": 360,
        "growth_stage_2": 360,
        "unlock_crop": "hops",
        "unlock_amount": 100,
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
        "base_price": 750,
        "inputs": [
            {
                "item_key": "wheat",
                "amount": 2,
            },
        ],
        "output": {
            "type": "item",
            "item_key": "flour",
            "amount": 3,
        },
        "duration": 180,
    },
    "bakery": {
        "name": "Bäckerei",
        "base_price": 2500,
        "inputs": [
            {
                "item_key": "flour",
                "amount": 5,
            },
        ],
        "output": {
            "type": "gold",
            "amount": 60,
        },
        "duration": 360,
    },
    "yeast_farm": {
        "name": "Hefefarm",
        "base_price": 300,
        "inputs": [
            {
                "item_key": "rye",
                "amount": 10,
            },
        ],
        "output": {
            "type": "item",
            "item_key": "yeast",
            "amount": 8,
        },
        "duration": 480,
    },
    "brewery": {
        "name": "Brauerei",
        "base_price": 15000,
        "inputs": [
            {
                "item_key": "hops",
                "amount": 15,
            },
            {
                "item_key": "yeast",
                "amount": 8,
            },
        ],
        "output": {
            "type": "gold",
            "amount": 500,
        },
        "duration": 900,
    },
    "winery": {
        "name": "Weinkellerei",
        "base_price": 50000,
        "inputs": [
            {
                "item_key": "grape",
                "amount": 20,
            },
        ],
        "output": {
            "type": "gold",
            "amount": 2000,
        },
        "duration": 1200,
    },
}

PROCESSOR_ORDER = [
    "mill",
    "bakery",
    "yeast_farm",
    "brewery",
    "winery",
]
# processors.py

import time

from config import PROCESSOR_BAR_WIDTH

from data import (
    PROCESSORS,
    PROCESSOR_ORDER,
)

from state import (
    inventory,
    processors,
)

from items import (
    get_item_name,
    get_processor_inputs,
    get_processor_output,
    is_processor_unlocked,
)


def format_item_stack(item_key, amount):
    return f"{amount} {get_item_name(item_key)}"


def format_processor_inputs(processor):
    return " + ".join(
        format_item_stack(input_item["item_key"], input_item["amount"])
        for input_item in get_processor_inputs(processor)
    )


def format_processor_output(processor):
    output = get_processor_output(processor)

    if output.get("type") == "gold":
        return f"{output['amount']} Gold"

    return format_item_stack(output["item_key"], output["amount"])


def format_processor_recipe(processor):
    return f"{format_processor_inputs(processor)} -> {format_processor_output(processor)}"


def get_processor_progress(processor_id, now=None):
    if now is None:
        now = time.time()

    state = processors[processor_id]
    started_at = state["started_at"]
    finish_at = state["finish_at"]

    if started_at is None or finish_at is None:
        return 0

    duration = finish_at - started_at

    if duration <= 0:
        return 1

    return max(0, min(1, (now - started_at) / duration))


def format_progress_bar(progress):
    filled = int(progress * PROCESSOR_BAR_WIDTH)
    empty = PROCESSOR_BAR_WIDTH - filled

    return "[" + ("#" * filled) + ("-" * empty) + "]"


def get_missing_processor_inputs(processor):
    missing_inputs = []

    for input_item in get_processor_inputs(processor):
        item_key = input_item["item_key"]
        required_amount = input_item["amount"]
        owned_amount = inventory.get(item_key, 0)

        if owned_amount < required_amount:
            missing_inputs.append({
                "item_key": item_key,
                "amount": required_amount - owned_amount,
            })

    return missing_inputs


def format_processor_status(processor_id, now):
    processor = PROCESSORS[processor_id]
    state = processors[processor_id]

    if state["started_at"] is not None and state["finish_at"] is not None:
        remaining = max(0, int(state["finish_at"] - now + 0.999))
        return f"noch {remaining}s"

    missing_inputs = get_missing_processor_inputs(processor)

    if not missing_inputs:
        return "bereit"

    missing_text = " + ".join(
        format_item_stack(input_item["item_key"], input_item["amount"])
        for input_item in missing_inputs
    )

    return f"fehlt {missing_text}"


def complete_processor(processor_id):
    import state

    processor = PROCESSORS[processor_id]
    processor_state = processors[processor_id]
    output = get_processor_output(processor)

    if output.get("type") == "gold":
        state.gold += output["amount"]
    else:
        item_key = output["item_key"]
        inventory.setdefault(item_key, 0)
        inventory[item_key] += output["amount"]

    processor_state["started_at"] = None
    processor_state["finish_at"] = None


def start_processor(processor_id, now):
    processor = PROCESSORS[processor_id]
    processor_state = processors[processor_id]

    if get_missing_processor_inputs(processor):
        return False

    for input_item in get_processor_inputs(processor):
        inventory[input_item["item_key"]] -= input_item["amount"]

    processor_state["started_at"] = now
    processor_state["finish_at"] = now + processor["duration"]

    return True


def run_processors():
    now = time.time()

    for processor_id in PROCESSOR_ORDER:
        if not is_processor_unlocked(processor_id):
            continue

        processor_state = processors[processor_id]

        if processor_state["started_at"] is not None and processor_state["finish_at"] is not None:
            if now < processor_state["finish_at"]:
                continue

            complete_processor(processor_id)

        if processor_state["started_at"] is None and processor_state["finish_at"] is None:
            start_processor(processor_id, now)
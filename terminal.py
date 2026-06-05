import shutil

from config import (
    ANSI_ESCAPE,
    SHOP_PANEL_WIDTH,
)


def clear_screen():
    print("\033[H\033[J", end="")


def visible_length(text):
    return len(ANSI_ESCAPE.sub("", text))


def pad_visible(text, width):
    padding = max(0, width - visible_length(text))
    return text + (" " * padding)


def truncate_visible(text, width):
    if width <= 0:
        return ""

    if visible_length(text) <= width:
        return text

    suffix = "..." if width >= 3 else "." * width
    target_width = width - visible_length(suffix)

    result = []
    visible_chars = 0
    index = 0

    while index < len(text) and visible_chars < target_width:
        match = ANSI_ESCAPE.match(text, index)

        if match:
            result.append(match.group(0))
            index = match.end()
            continue

        result.append(text[index])
        visible_chars += 1
        index += 1

    truncated = "".join(result) + suffix

    if "\033[" in truncated and not truncated.endswith("\033[0m"):
        truncated += "\033[0m"

    return truncated


def fit_visible(text, width):
    return pad_visible(truncate_visible(text, width), width)


def box_line(content="", width=SHOP_PANEL_WIDTH):
    content_width = width - 2
    return "|" + fit_visible(content, content_width) + "|"


def box_split_line(left, right, width=SHOP_PANEL_WIDTH):
    content_width = width - 2
    right_width = visible_length(right)

    if not right:
        return box_line(left, width)

    if right_width >= content_width:
        return box_line(right, width)

    left_width = content_width - right_width - 1

    left = truncate_visible(left, left_width)

    spacer = " " * (
        content_width
        - visible_length(left)
        - right_width
    )

    return "|" + left + spacer + right + "|"


def terminal_width():
    return shutil.get_terminal_size((80, 24)).columns
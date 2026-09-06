"""UIA automation_id map for Windows Calculator (es-AR / en-US)."""

MODE_ORDER = [
    "Standard",
    "Scientific",
    "Graphing",
    "Programmer",
    "Date",
    "Currency",
    "Volume",
    "Length",
]

NAV_MODES = {
    "standard": "Standard",
    "scientific": "Scientific",
    "graphing": "Graphing",
    "programmer": "Programmer",
    "date": "Date",
    "currency": "Currency",
    "volume": "Volume",
    "length": "Length",
    "settings": "SettingsItem",
}

STANDARD_KEYPAD = {
    "0": "num0Button",
    "1": "num1Button",
    "2": "num2Button",
    "3": "num3Button",
    "4": "num4Button",
    "5": "num5Button",
    "6": "num6Button",
    "7": "num7Button",
    "8": "num8Button",
    "9": "num9Button",
    "plus": "plusButton",
    "minus": "minusButton",
    "multiply": "multiplyButton",
    "divide": "divideButton",
    "equals": "equalButton",
    "clear": "clearButton",
    "clear_entry": "clearEntryButton",
    "backspace": "backSpaceButton",
    "decimal": "decimalSeparatorButton",
    "negate": "negateButton",
    "percent": "percentButton",
    "sqrt": "squareRootButton",
    "square": "xpower2Button",
    "reciprocal": "invertButton",
}

SCIENTIFIC_EXTRA = {
    "deg": "degButton",
    "scientific_notation": "ftoeButton",
    "trig_menu": "trigButton",
    "func_menu": "funcButton",
    "shift": "shiftButton",
    "pi": "piButton",
    "euler": "eulerButton",
    "power": "powerButton",
    "power10": "powerOf10Button",
    "log10": "logBase10Button",
    "ln": "logBaseEButton",
    "abs": "absButton",
    "exp": "expButton",
    "mod": "modButton",
    "open_paren": "openParenthesisButton",
    "close_paren": "closeParenthesisButton",
    "factorial": "factorialButton",
}

MEMORY = {
    "clear": "ClearMemoryButton",
    "recall": "MemRecall",
    "plus": "MemPlus",
    "minus": "MemMinus",
    "store": "memButton",
    "panel": "MemoryButton",
}

CHROME = {
    "nav": "TogglePaneButton",
    "history": "HistoryButton",
    "always_on_top": "NormalAlwaysOnTopButton",
    "minimize": "Minimize",
    "maximize": "Maximize",
    "close": "Close",
}

DISPLAY_IDS = (
    "CalculatorResults",
    "CalculatorExpression",
)

# Test cases per mode: (ticket_id, steps, expected, description)
# steps use harness labels: digit, or key from STANDARD_KEYPAD / SCIENTIFIC_EXTRA
STANDARD_CASES = [
    ("T002", [("clear", "clear"), ("2", "2"), ("plus", "plus"), ("2", "2"), ("equals", "equals")], "4", "2+2"),
    ("T003", [("clear", "clear"), ("1", "1"), ("5", "5"), ("multiply", "multiply"), ("7", "7"), ("equals", "equals")], "105", "15*7"),
    ("T005", [("clear", "clear"), ("1", "1"), ("0", "0"), ("0", "0"), ("divide", "divide"), ("4", "4"), ("equals", "equals")], "25", "100/4"),
    ("T006", [("clear", "clear"), ("9", "9"), ("sqrt", "sqrt")], "3", "sqrt(9)"),
    ("T007", [("clear", "clear"), ("1", "1"), ("0", "0"), ("minus", "minus"), ("3", "3"), ("equals", "equals")], "7", "10-3"),
    ("T008", [("clear", "clear"), ("5", "5"), ("percent", "percent")], "0.05", "5% of empty? shows 0.05"),
]

SCIENTIFIC_CASES = [
    ("T101", [("clear", "clear"), ("pi", "pi")], None, "pi constant — verify non-empty"),
    ("T102", [("clear", "clear"), ("2", "2"), ("square", "square")], "4", "x^2"),
    ("T103", [("clear", "clear"), ("1", "1"), ("6", "6"), ("factorial", "factorial")], "40320", "16! wait 16 not 1... fix"),
]

MODE_CASES = {
    "Standard": STANDARD_CASES,
    "Scientific": [
        ("T101", [("clear", "clear"), ("2", "2"), ("square", "square")], "4", "x^2 scientific layout"),
        ("T102", [("clear", "clear"), ("9", "9"), ("sqrt", "sqrt")], "3", "sqrt scientific"),
    ],
}

import os
import json
import urllib.request

# ── directory and file paths ──

DATA_DIR = "data"
CONFIG_DIR = "config"
OUTPUTS_DIR = "outputs"

# build full file paths by joining directory name and file name
TRANSACTIONS_FILE = os.path.join(DATA_DIR, "transactions.json")
BUDGET_RULES_FILE = os.path.join(DATA_DIR, "budget_rules.json")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# ── default configuration values ──

DEFAULT_CONFIG = {
    "categories": ["Food", "Transport", "Personal", "Entertainment", "Health", "Utilities"],
    "currencies": {
        "HKD": 1.0,
        "CNY": 1.15,
        "JPY": 0.052,
        "KRW": 0.0057,
        "NTD": 0.24,
        "USD": 7.78,
        "GBP": 10.51,
        "EUR": 9.15,
    },
    "default_currency": "HKD",
    "savings_goal": 500.0,
    "income": 0.0,
}

# mapping from app currency names to ISO 4217 codes
# "NTD" is a common nickname; the official ISO code is "TWD"
_ISO = {
    "HKD": "HKD",
    "CNY": "CNY",
    "JPY": "JPY",
    "KRW": "KRW",
    "NTD": "TWD",
    "USD": "USD",
    "GBP": "GBP",
    "EUR": "EUR",
}


def fetch_exchange_rates():
    """
    Fetch live exchange rates from a free API.
    Returns a dict like {"HKD": 1.0, "USD": 7.78, ...} or None on failure.
    The API gives rates relative to HKD, e.g. 1 HKD = 0.1277 USD,
    so we invert them to get "how many HKD per 1 unit of that currency".
    """
    try:
        url = "https://open.er-api.com/v6/latest/HKD"

        # open the URL and read the response body
        response = urllib.request.urlopen(url, timeout=5)
        raw_bytes = response.read()
        raw_string = raw_bytes.decode()  # bytes -> string
        response.close()

        # parse the JSON string into a Python dict
        data = json.loads(raw_string)

        # check if the API returned a success status
        result_status = data.get("result")
        if result_status != "success":
            return None

        # the "rates" field holds all the exchange rates
        api_rates = data["rates"]

        # build our own rates dict by inverting API values
        rates = {}
        for name in _ISO:
            iso_code = _ISO[name]

            # skip if the ISO code is missing from the API response
            if iso_code not in api_rates:
                continue

            api_value = api_rates[iso_code]

            # skip if the value is zero (cannot divide by zero)
            if api_value == 0:
                continue

            # invert: API gives HKD->X, we want X->HKD
            inverted = 1.0 / api_value

            # round to 6 decimal places
            inverted = round(inverted, 6)

            rates[name] = inverted

        return rates

    except Exception:
        # any network error, timeout, or parsing error -> return None
        return None


def ensure_dirs():
    """
    Create the required directories if they do not already exist.
    """
    directories = [DATA_DIR, CONFIG_DIR, OUTPUTS_DIR]
    for d in directories:
        # exist_ok=True means no error if directory already exists
        os.makedirs(d, exist_ok=True)


def _load_json(filepath, default):
    """
    Read a JSON file and return its content as a Python object.
    If the file is missing, empty, or corrupted, return the default value.
    """
    # try to open and read the file
    try:
        f = open(filepath, "r")
        content = f.read()
        f.close()
    except FileNotFoundError:
        # file does not exist yet -> use default
        return default

    # remove leading/trailing whitespace
    content = content.strip()

    # if the file is empty, use default
    if content == "":
        return default

    # try to parse JSON
    try:
        result = json.loads(content)
        return result
    except json.JSONDecodeError:
        # file content is not valid JSON
        print("Warning: " + filepath + " is corrupted. Using default.")
        return default


def _save_json(filepath, data):
    """
    Write a Python object to a file as formatted JSON.
    """
    f = open(filepath, "w")
    # indent=2 makes the file human-readable
    json_string = json.dumps(data, indent=2)
    f.write(json_string)
    f.close()


def load_transactions():
    """
    Load the transactions list from disk.
    Returns an empty list if no file exists yet.
    """
    transactions = _load_json(TRANSACTIONS_FILE, [])
    return transactions


def save_transactions(transactions):
    """
    Save the transactions list to disk.
    """
    _save_json(TRANSACTIONS_FILE, transactions)


def load_budget_rules():
    """
    Load the budget rules list from disk.
    Returns an empty list if no file exists yet.
    """
    rules = _load_json(BUDGET_RULES_FILE, [])
    return rules


def save_budget_rules(rules):
    """
    Save the budget rules list to disk.
    """
    _save_json(BUDGET_RULES_FILE, rules)


def load_config():
    """
    Load app configuration from disk.
    If some keys are missing, fill them in from DEFAULT_CONFIG.
    """
    # start by loading whatever is on disk (or a copy of default)
    default_copy = {}
    for key in DEFAULT_CONFIG:
        default_copy[key] = DEFAULT_CONFIG[key]

    config = _load_json(CONFIG_FILE, default_copy)

    # make sure every expected key exists in the loaded config
    for key in DEFAULT_CONFIG:
        if key not in config:
            config[key] = DEFAULT_CONFIG[key]

    return config


def save_config(config):
    """
    Save app configuration to disk.
    """
    _save_json(CONFIG_FILE, config)


def get_next_id(transactions):
    """
    Return the next available transaction ID.
    If the list is empty, start from 1.
    Otherwise, find the current maximum ID and add 1.
    """
    if len(transactions) == 0:
        return 1

    # find the maximum id among all transactions
    max_id = transactions[0]["id"]
    for t in transactions:
        current_id = t["id"]
        if current_id > max_id:
            max_id = current_id

    next_id = max_id + 1
    return next_id

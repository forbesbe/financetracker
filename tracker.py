import difflib
from datetime import datetime
from decimal import Decimal, InvalidOperation
import pandas as pd

class RowInvalidError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message
        super().__init__(message)

def clean_account(value):
    if pd.isna(value):
        raise RowInvalidError(status=1, message="Missing value")
    value = value.lower()
    value = value.replace(" ", "")
    if value not in ['creditcard', 'checking', 'chk']:
        raise RowInvalidError(status=2, message="Invalid value")
    if value == 'chk' or value == 'checking':
        value = 'Checking'
    else:
        value = 'Credit Card'
    return value

date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%b %d, %Y']

def clean_date(value):
    if pd.isna(value):
        raise RowInvalidError(status=1, message="Missing value")
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")

    for fmt in date_formats:
        try:
            parsed = datetime.strptime(str(value).strip(), fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue

    raise RowInvalidError(status=3, message=f"Unparseable date: {value!r}")

def clean_amount(value):
    flag = False
    if pd.isna(value):
        raise RowInvalidError(status=1, message="Missing value")
    if isinstance(value, (int, float)):
        value = Decimal(str(value))
        value *= 100
        return int(value)
    else:
        if "(" in value or ")" in value:
            value = value.replace("(", '')
            value = value.replace(")", '')
            flag = True
        value = value.replace("$", "")
        value = value.replace(',', '')
        if flag == True:
            value = "-" + value
        try:
            value = Decimal(value)
            value *= 100
            return int(value)
        except InvalidOperation:
            raise RowInvalidError(status=2, message="Invalid value")

def clean_description(value):
    if pd.isna(value):
        raise RowInvalidError(status=1, message="Missing value")
    value = value.strip()
    value = value.upper()
    if value == '':
        raise RowInvalidError(status=1, message="Missing value")
    return value

def clean_category(value):
    if pd.isna(value):
        raise RowInvalidError(status=1, message="Missing value")
    value = value.lower()
    value = value.replace(" ", "")
    category_aliases = {
        'groceries': 'Groceries',
        'diningout': 'Dining Out',
        'transportation': 'Transportation',
        'utilities': 'Utilities',
        'rent': 'Rent',
        'entertainment': 'Entertainment',
        'shopping': 'Shopping',
        'health&fitness': 'Health & Fitness',
        'subscriptions': 'Subscriptions',
        'travel': 'Travel',
        'income': 'Income',
        'other': 'Other',
    }
    if value in category_aliases:
        return category_aliases[value]
    else:
        matches = difflib.get_close_matches(value, category_aliases.keys(), 1, 0.70)
        if matches:
            return category_aliases[matches[0]]
        else:
            raise RowInvalidError(status=2, message="Invalid value")
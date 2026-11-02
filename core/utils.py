import re
from decimal import Decimal, InvalidOperation

_ODD_CAPS = re.compile(r"\b([A-Z])([A-Z])([a-z]+)")


def fix_caps(value):
    """Repair sheet typos like 'MIlwaukee' -> 'Milwaukee' (two leading capitals, then lowercase)."""
    return _ODD_CAPS.sub(lambda m: m.group(1) + m.group(2).lower() + m.group(3), value or "")


def clean(value):
    return (value or "").strip()


def parse_decimal(value):
    value = clean(value).replace("$", "").replace(",", "")
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def parse_int(value):
    number = parse_decimal(value)
    return int(number) if number is not None else None


def parse_bool(value):
    return clean(value).lower() in {"yes", "true", "y", "1"}


def split_names(value):
    """'Grace, Dad' -> ['Grace', 'Dad']; 'Alone' and blanks are dropped."""
    names = [n.strip() for n in clean(value).split(",") if n.strip()]
    return [n for n in names if n.lower() not in {"alone", "solo", "none"}]


def parse_sheet_date(value):
    from datetime import datetime

    value = clean(value)
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def sheet_reader(header, rows):
    """Return (rows, col) where col(row, 'column name') is a safe cell lookup."""
    header = [h.strip().lower() for h in header]

    def col(row, name, default=""):
        try:
            idx = header.index(name)
        except ValueError:
            return default
        return row[idx] if idx < len(row) else default

    return [r for r in rows if any(r)], col

"""Import concert history from a Google Sheet.

Expects columns (case-insensitive, order doesn't matter):
Date, Artist, Rating, Attended With, Openers, Tour Name, Show Type, Sit Ins,
Venue, Outdoor/Indoor, City, State, Seats, Price, Setlist FM,
Setlist Highlights, Sound Quality, View Quality, Crowd Rating, Poster,
Set Length, Merch Spent, Notes, Venue Notes

Re-running is safe: events are matched on (date, location) and existing
performances on (event, artist, role), so already-imported rows are updated in
place rather than duplicated. Rows are never deleted, so performances you added
by hand in the admin are left alone.
"""

import re
from datetime import timedelta

from concerts.models import Event, Performance
from core.models import Location, Person
from core.sheets import SheetImportCommand
from core.utils import (
    clean,
    fix_caps,
    parse_bool,
    parse_decimal,
    parse_sheet_date,
    sheet_reader,
    split_names,
)

SHOW_TYPE_MAP = {
    "concert": Event.EventType.CONCERT,
    "festival": Event.EventType.FESTIVAL,
    "stand up": Event.EventType.STAND_UP,
    "live event": Event.EventType.LIVE_EVENT,
    "acoustic": Event.EventType.ACOUSTIC,
}


def _parse_duration(value):
    value = clean(value)
    if not value:
        return None
    try:
        parts = [int(p) for p in value.split(":")]
    except ValueError:
        return None
    while len(parts) < 3:
        parts.insert(0, 0)
    hours, minutes, seconds = parts[-3:]
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def _split_bulleted(value):
    """Openers/highlights arrive as '- Name - Name' or newline-bulleted text."""
    value = clean(value)
    if not value:
        return []
    value = value.replace("\\-", "\n-")
    items = []
    for line in re.split(r"\n+", value):
        line = re.sub(r"^-\s*", "", line.strip())
        if line:
            items.append(line)
    return items


def _map_setting(value):
    return {"indoor": Location.Setting.INDOOR, "outdoor": Location.Setting.OUTDOOR}.get(clean(value).lower(), "")


def import_rows(header, rows, log=lambda msg: None, dry_run=False):
    """Create/update Events and Performances. Returns (created, updated) event counts."""
    rows, col = sheet_reader(header, rows)
    created = updated = 0

    for row in rows:
        date = parse_sheet_date(col(row, "date"))
        if not date:
            log(f"Skipping row, unparseable date: {row}")
            continue
        venue_name = clean(col(row, "venue"))
        if not venue_name:
            log(f"Skipping row, no venue: {row}")
            continue

        location, _ = Location.objects.get_or_create(
            name=fix_caps(venue_name),
            city=fix_caps(clean(col(row, "city"))),
            state=clean(col(row, "state")),
            defaults={"setting": _map_setting(col(row, "outdoor/indoor"))},
        ) if not dry_run else (None, False)

        raw_type = clean(col(row, "show type")).lower()
        event_type = SHOW_TYPE_MAP.get(raw_type, Event.EventType.CONCERT)
        notes = clean(col(row, "notes"))
        if clean(col(row, "sit ins")):
            notes = f"{notes}\nSit-ins: {clean(col(row, 'sit ins'))}".strip()
        if raw_type and raw_type not in SHOW_TYPE_MAP:
            notes = f"{notes}\n[Original show type: {col(row, 'show type')}]".strip()

        if dry_run:
            log(f"Would import: {date} — {col(row, 'artist')} @ {venue_name}")
            continue

        event, event_created = Event.objects.update_or_create(
            date=date,
            location=location,
            defaults={
                "event_type": event_type,
                "seats": clean(col(row, "seats")),
                "price": parse_decimal(col(row, "price")),
                "merch_spent": parse_decimal(col(row, "merch spent")),
                "sound_quality": parse_decimal(col(row, "sound quality")),
                "view_quality": parse_decimal(col(row, "view quality")),
                "crowd_rating": parse_decimal(col(row, "crowd rating")),
                "poster_taken": parse_bool(col(row, "poster")),
                "notes": notes,
                "venue_notes": clean(col(row, "venue notes")),
            },
        )
        created += event_created
        updated += not event_created

        for name in split_names(col(row, "attended with")):
            person, _ = Person.objects.get_or_create(name=name)
            event.attendees.add(person)

        headliner = clean(col(row, "artist"))
        if headliner:
            Performance.objects.update_or_create(
                event=event,
                artist=headliner,
                role=Performance.Role.HEADLINER,
                defaults={
                    "tour_name": clean(col(row, "tour name")),
                    "rating": parse_decimal(col(row, "rating")),
                    "set_length": _parse_duration(col(row, "set length")),
                    "setlist_fm_url": clean(col(row, "setlist fm")),
                    "setlist_highlights": "\n".join(_split_bulleted(col(row, "setlist highlights"))),
                    "order": 0,
                },
            )

        for i, opener in enumerate(_split_bulleted(col(row, "openers")), start=1):
            Performance.objects.get_or_create(
                event=event, artist=opener, role=Performance.Role.OPENER, defaults={"order": i}
            )

    return created, updated


class Command(SheetImportCommand):
    help = "Import concert history from a Google Sheet."
    sheet_env = "CONCERTS_SHEET_ID"

    def run_import(self, header, rows, log, dry_run, options):
        return import_rows(header, rows, log=log, dry_run=dry_run)

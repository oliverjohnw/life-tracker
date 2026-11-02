"""Import sporting events from a Google Sheet.

Columns: Date, League, Game Type, Home, Away, Winner, Team Win, Score, Venue, City,
State, Seats, Attended With, Rating, Notes. An optional "My Team" column wins if present.

The old sheet only recorded whether "my team" won (Team Win = Yes/No), so when there's no
explicit My Team column it's inferred: Yes -> the winner, No -> whoever didn't win.

Re-running is safe: games are matched on (date, home, away).
"""

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
from sports.models import SportingEvent


def _my_team(row, col, home, away, winner):
    explicit = fix_caps(clean(col(row, "my team")))
    if explicit:
        return explicit
    if not winner or not clean(col(row, "team win")):
        return ""
    if parse_bool(col(row, "team win")):
        return winner
    return away if winner == home else home


def import_rows(header, rows, log=lambda msg: None, dry_run=False):
    rows, col = sheet_reader(header, rows)
    created = updated = 0
    for row in rows:
        date = parse_sheet_date(col(row, "date"))
        home = fix_caps(clean(col(row, "home")))
        away = fix_caps(clean(col(row, "away")))
        venue = clean(col(row, "venue"))
        if not (date and home and away and venue):
            log(f"Skipping incomplete row: {row}")
            continue
        if dry_run:
            log(f"Would import: {date} — {away} @ {home}")
            continue

        winner = fix_caps(clean(col(row, "winner")))
        location, _ = Location.objects.get_or_create(
            name=fix_caps(venue),
            city=fix_caps(clean(col(row, "city"))),
            state=clean(col(row, "state")),
        )
        game, was_created = SportingEvent.objects.update_or_create(
            date=date,
            home_team=home,
            away_team=away,
            defaults={
                "league": clean(col(row, "league")),
                "game_type": clean(col(row, "game type")) or "Regular Season",
                "winner": winner,
                "my_team": _my_team(row, col, home, away, winner),
                "score": clean(col(row, "score")),
                "location": location,
                "seats": clean(col(row, "seats")),
                "rating": parse_decimal(col(row, "rating")),
                "notes": clean(col(row, "notes")),
            },
        )
        created += was_created
        updated += not was_created
        for name in split_names(col(row, "attended with")):
            person, _ = Person.objects.get_or_create(name=name)
            game.attendees.add(person)
    return created, updated


class Command(SheetImportCommand):
    help = "Import sporting events from a Google Sheet."
    sheet_env = "SPORTS_SHEET_ID"

    def run_import(self, header, rows, log, dry_run, options):
        return import_rows(header, rows, log=log, dry_run=dry_run)

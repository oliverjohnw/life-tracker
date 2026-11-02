"""Import the movie diary (and optionally the watchlist tab) from a Google Sheet.

Diary columns: Date, Title, Year, Rewatches, Platform, City, Viewed With, Rating,
Notes, Quotes (Genre is optional). Watchlist columns: Title, Recomendee, Watched.

Re-running is safe: viewings are matched on (title, date).
"""

from core.models import Person
from core.sheets import SheetImportCommand, fetch_table
from core.utils import (
    clean,
    fix_caps,
    parse_bool,
    parse_decimal,
    parse_int,
    parse_sheet_date,
    sheet_reader,
    split_names,
)
from movies.models import Movie, WatchlistItem


def import_rows(header, rows, log=lambda msg: None, dry_run=False):
    rows, col = sheet_reader(header, rows)
    created = updated = 0
    for row in rows:
        date = parse_sheet_date(col(row, "date"))
        title = clean(col(row, "title"))
        if not date or not title:
            log(f"Skipping row without a date and title: {row}")
            continue
        if dry_run:
            log(f"Would import: {date} — {title}")
            continue

        movie, was_created = Movie.objects.update_or_create(
            title=title,
            date=date,
            defaults={
                "year": parse_int(col(row, "year")),
                "genre": clean(col(row, "genre")),
                "rewatches": parse_int(col(row, "rewatches")) or 0,
                "platform": clean(col(row, "platform")),
                "city": fix_caps(clean(col(row, "city"))),
                "rating": parse_decimal(col(row, "rating")),
                "notes": clean(col(row, "notes")),
                "quotes": clean(col(row, "quotes")),
            },
        )
        created += was_created
        updated += not was_created
        for name in split_names(col(row, "viewed with")):
            person, _ = Person.objects.get_or_create(name=name)
            movie.watched_with.add(person)
    return created, updated


def import_watchlist(header, rows, log=lambda msg: None, dry_run=False):
    rows, col = sheet_reader(header, rows)
    created = updated = 0
    for row in rows:
        title = clean(col(row, "title"))
        if not title:
            continue
        if dry_run:
            log(f"Would import watchlist item: {title}")
            continue
        item, was_created = WatchlistItem.objects.update_or_create(
            title=title,
            defaults={
                "recommended_by": clean(col(row, "recomendee") or col(row, "recommended by")),
                "watched": parse_bool(col(row, "watched")),
            },
        )
        created += was_created
        updated += not was_created
    return created, updated


class Command(SheetImportCommand):
    help = "Import the movie diary from a Google Sheet."
    sheet_env = "MOVIES_SHEET_ID"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("--watchlist-worksheet", default=None, help="Tab holding the watchlist, if any.")

    def run_import(self, header, rows, log, dry_run, options):
        created, updated = import_rows(header, rows, log=log, dry_run=dry_run)
        if options["watchlist_worksheet"]:
            table = fetch_table(options["sheet_id"], options["watchlist_worksheet"])
            if table:
                wc, wu = import_watchlist(table[0], table[1:], log=log, dry_run=dry_run)
                log(f"Watchlist: {wc} created, {wu} updated.")
        return created, updated

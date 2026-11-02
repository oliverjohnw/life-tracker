"""Shared plumbing for the Google Sheets import commands."""

import json

from django.core.management.base import BaseCommand, CommandError
from google.oauth2 import service_account
from googleapiclient.discovery import build

from config.env import env

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def _credentials():
    raw = env("GOOGLE_SERVICE_ACCOUNT_JSON", default=None)
    if raw:
        return service_account.Credentials.from_service_account_info(json.loads(raw), scopes=SCOPES)
    path = env("GOOGLE_APPLICATION_CREDENTIALS", default=None)
    if path:
        return service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
    raise CommandError(
        "Set GOOGLE_SERVICE_ACCOUNT_JSON (the service account key, as JSON) or "
        "GOOGLE_APPLICATION_CREDENTIALS (a path to the key file) in your .env, and share "
        "the sheet with the service account's client_email."
    )


def fetch_table(sheet_id, worksheet=None):
    """Return every row of one tab as a list of lists (header first). Defaults to the first tab."""
    service = build("sheets", "v4", credentials=_credentials())
    if not worksheet:
        meta = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        worksheet = meta["sheets"][0]["properties"]["title"]
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=f"'{worksheet}'!A1:AA2000")
        .execute()
    )
    return result.get("values", [])


class SheetImportCommand(BaseCommand):
    """Subclasses set `sheet_env` and implement `run_import(header, rows, log, dry_run)`."""

    sheet_env = ""

    def add_arguments(self, parser):
        parser.add_argument(
            "--sheet-id",
            default=env(self.sheet_env, default=None),
            help=f"Google Sheet ID (from its URL). Falls back to {self.sheet_env} in .env.",
        )
        parser.add_argument("--worksheet", default=None, help="Tab name. Defaults to the first tab.")
        parser.add_argument("--dry-run", action="store_true", help="Parse and report; write nothing.")

    def handle(self, *args, **options):
        sheet_id = options["sheet_id"]
        if not sheet_id:
            raise CommandError(f"Pass --sheet-id or set {self.sheet_env} in .env")

        rows = fetch_table(sheet_id, options["worksheet"])
        if not rows:
            self.stdout.write(self.style.WARNING("Sheet is empty."))
            return

        def log(message):
            self.stdout.write(self.style.WARNING(message))

        created, updated = self.run_import(rows[0], rows[1:], log, options["dry_run"], options)
        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS("Dry run complete — nothing written."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Done. {created} created, {updated} updated."))

    def run_import(self, header, rows, log, dry_run, options):
        raise NotImplementedError

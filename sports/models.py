from django.db import models

from core.models import Location, Person

COMBAT_LEAGUES = {"ufc", "pfl", "bellator", "boxing", "wwe", "aew"}


class SportingEvent(models.Model):
    """A game, match or fight card you attended in person."""

    date = models.DateField()
    league = models.CharField(max_length=60, help_text="NBA, MLB, NFL, UFC, NCAA Mens Hockey…")
    game_type = models.CharField(max_length=60, default="Regular Season")
    home_team = models.CharField(max_length=120, help_text="Home team (or first fighter)")
    away_team = models.CharField(max_length=120, help_text="Away team (or second fighter)")
    winner = models.CharField(max_length=120, blank=True)
    my_team = models.CharField(
        max_length=120,
        blank=True,
        help_text="Who you were rooting for — used to work out your record. Blank = neutral.",
    )
    score = models.CharField(max_length=80, blank=True, help_text="e.g. BOS 116 - MIL 108, or TKO")
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="sporting_events")
    seats = models.CharField(max_length=200, blank=True)
    attendees = models.ManyToManyField(Person, blank=True, related_name="games_attended")
    rating = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date"]

    @property
    def is_combat(self):
        return self.league.strip().lower() in COMBAT_LEAGUES

    @property
    def matchup(self):
        if self.is_combat:
            return f"{self.home_team} vs {self.away_team}"
        return f"{self.away_team} @ {self.home_team}"

    @property
    def result(self):
        """'W' / 'L' from the point of view of my_team, or None if neutral/unknown."""
        if not (self.my_team and self.winner):
            return None
        return "W" if self.my_team == self.winner else "L"

    def __str__(self):
        return f"{self.date} — {self.matchup}"

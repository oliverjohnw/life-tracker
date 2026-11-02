from django.db import models

from core.models import Location, Person


class Round(models.Model):
    """One round of golf or disc golf. Same shape for both; `game` switches the views."""

    class Game(models.TextChoices):
        GOLF = "golf", "Golf"
        DISC_GOLF = "disc_golf", "Disc Golf"

    class Transport(models.TextChoices):
        WALKING = "walking", "Walking"
        CART = "cart", "Cart"

    game = models.CharField(max_length=12, choices=Game.choices, default=Game.GOLF)
    date = models.DateField()
    course = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="rounds")
    layout = models.CharField(
        max_length=120, blank=True, help_text="Tees played (Blue, White…) or disc golf layout"
    )
    holes = models.PositiveSmallIntegerField(default=18, help_text="9, 12, 18…")
    score = models.PositiveSmallIntegerField(help_text="Total strokes / throws")
    par = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Par for the holes played")

    course_rating = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True, help_text="Golf only — for handicap differential"
    )
    slope = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Golf only — slope rating")

    transport = models.CharField(max_length=10, choices=Transport.choices, blank=True, help_text="Golf only")
    weather = models.CharField(max_length=120, blank=True, help_text="Sunny and 75, windy, light rain…")
    played_with = models.ManyToManyField(Person, blank=True, related_name="rounds_played")
    rating = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True, help_text="How much you enjoyed it, 0–10"
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date"]

    @property
    def to_par(self):
        return self.score - self.par if self.par else None

    @property
    def differential(self):
        """World Handicap System score differential (18-hole golf rounds with rating + slope)."""
        if self.game != self.Game.GOLF or not (self.slope and self.course_rating):
            return None
        return round(float(113 / self.slope * (self.score - float(self.course_rating))), 1)

    def __str__(self):
        return f"{self.get_game_display()} — {self.course.name} ({self.date})"

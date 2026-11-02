from django.db import models

from core.models import Person


class Movie(models.Model):
    """One viewing in the diary. Rewatches counts extra viewings of the same film."""

    date = models.DateField(help_text="When you watched it")
    title = models.CharField(max_length=250)
    year = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Release year")
    genre = models.CharField(max_length=100, blank=True)
    rewatches = models.PositiveSmallIntegerField(default=0)
    platform = models.CharField(
        max_length=100, blank=True, help_text="Theater, Netflix, Max, DVD, Rented…"
    )
    city = models.CharField(max_length=120, blank=True)
    watched_with = models.ManyToManyField(Person, blank=True, related_name="movies_watched")
    rating = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    quotes = models.TextField(blank=True, help_text="Favorite lines")

    class Meta:
        ordering = ["-date", "title"]
        unique_together = [["title", "date"]]

    @property
    def in_theater(self):
        return self.platform.strip().lower() in {"theater", "theatre", "cinema"}

    @property
    def decade(self):
        return f"{self.year // 10 * 10}s" if self.year else ""

    def __str__(self):
        return f"{self.title} ({self.year})" if self.year else self.title


class WatchlistItem(models.Model):
    title = models.CharField(max_length=250)
    recommended_by = models.CharField(max_length=120, blank=True)
    watched = models.BooleanField(default=False)
    notes = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["watched", "title"]

    def __str__(self):
        return self.title

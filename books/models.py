from django.db import models

from core.models import Person


class Book(models.Model):
    class Status(models.TextChoices):
        READING = "reading", "Reading"
        FINISHED = "finished", "Finished"
        ABANDONED = "abandoned", "Abandoned"
        TO_READ = "to_read", "Want to read"

    class Format(models.TextChoices):
        PHYSICAL = "physical", "Physical"
        EBOOK = "ebook", "E-book"
        AUDIOBOOK = "audiobook", "Audiobook"

    class Category(models.TextChoices):
        FICTION = "fiction", "Fiction"
        NONFICTION = "nonfiction", "Non-fiction"

    title = models.CharField(max_length=250)
    author = models.CharField(max_length=200)
    series = models.CharField(max_length=200, blank=True, help_text="e.g. 'The Stormlight Archive #2'")
    category = models.CharField(max_length=12, choices=Category.choices, default=Category.FICTION)
    genre = models.CharField(max_length=100, blank=True)
    format = models.CharField(max_length=12, choices=Format.choices, default=Format.PHYSICAL)
    pages = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.FINISHED)
    date_started = models.DateField(null=True, blank=True)
    date_finished = models.DateField(null=True, blank=True)
    rating = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    re_read = models.BooleanField(default=False, help_text="A re-read of something you've finished before")
    recommended_by = models.ForeignKey(
        Person, null=True, blank=True, on_delete=models.SET_NULL, related_name="book_recommendations"
    )
    cover_image = models.ImageField(upload_to="covers/", blank=True)
    notes = models.TextField(blank=True)
    quotes = models.TextField(blank=True, help_text="Favorite passages")

    class Meta:
        ordering = ["-date_finished", "-date_started", "title"]

    @property
    def activity_date(self):
        return self.date_finished or self.date_started

    @property
    def days_to_finish(self):
        if self.date_started and self.date_finished and self.date_finished >= self.date_started:
            return (self.date_finished - self.date_started).days + 1
        return None

    def __str__(self):
        return f"{self.title} — {self.author}"

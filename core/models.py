from django.db import models


class Person(models.Model):
    """Someone you did things with — reused across concerts, sports, etc."""

    name = models.CharField(max_length=200, unique=True)
    relationship = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional tag, e.g. 'Dad', 'Friend', 'Coworker'",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "people"

    def __str__(self):
        return self.name


class Location(models.Model):
    """A venue, course, theater, stadium, or other place — reused everywhere."""

    class Setting(models.TextChoices):
        INDOOR = "indoor", "Indoor"
        OUTDOOR = "outdoor", "Outdoor"
        MIXED = "mixed", "Mixed"

    name = models.CharField(max_length=200)
    city = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=120, blank=True)
    setting = models.CharField(
        max_length=10, choices=Setting.choices, blank=True
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        unique_together = [["name", "city", "state"]]

    def __str__(self):
        location_bits = ", ".join(bit for bit in [self.city, self.state] if bit)
        return f"{self.name} ({location_bits})" if location_bits else self.name

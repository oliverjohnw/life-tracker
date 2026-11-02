from django.db import models

from core.models import Location, Person


class Event(models.Model):
    """A single outing — a solo show, a festival day, a stand-up set, etc.

    Holds everything that applies to the whole outing. The individual acts
    (headliner, openers) live on Performance so festivals with several
    artists — each with their own genre and rating — fit naturally.
    """

    class EventType(models.TextChoices):
        CONCERT = "concert", "Concert"
        FESTIVAL = "festival", "Festival"
        STAND_UP = "stand_up", "Stand Up"
        LIVE_EVENT = "live_event", "Live Event"
        ACOUSTIC = "acoustic", "Acoustic"

    date = models.DateField()
    name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional — e.g. 'Summerfest'. Leave blank for a plain solo show.",
    )
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    location = models.ForeignKey(
        Location, on_delete=models.PROTECT, related_name="concert_events"
    )
    attendees = models.ManyToManyField(Person, blank=True, related_name="concerts_attended")

    seats = models.CharField(max_length=200, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    merch_spent = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    sound_quality = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    view_quality = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    crowd_rating = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    poster_taken = models.BooleanField(default=False, help_text="Did you come home with a poster?")
    poster_image = models.ImageField(
        upload_to="posters/%Y/", blank=True, help_text="A photo of the concert poster"
    )

    notes = models.TextField(blank=True)
    venue_notes = models.TextField(blank=True, help_text="Tips for next time at this venue")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]

    # These read self.performances.all() so a prefetch_related("performances")
    # makes the list page a constant number of queries.
    @property
    def lineup(self):
        return sorted(self.performances.all(), key=lambda p: p.order)

    @property
    def headliner(self):
        acts = self.lineup
        for act in acts:
            if act.role == Performance.Role.HEADLINER:
                return act
        return acts[0] if acts else None

    @property
    def title(self):
        if self.name:
            return self.name
        head = self.headliner
        return head.artist if head else str(self.location)

    @property
    def support_acts(self):
        head = self.headliner
        return [a for a in self.lineup if a is not head]

    @property
    def featured_acts(self):
        """Who to name under the title: everyone for a named festival, else just the support."""
        return self.lineup if self.name else self.support_acts

    @property
    def genres(self):
        seen = []
        for act in self.lineup:
            if act.genre and act.genre not in seen:
                seen.append(act.genre)
        return seen

    @property
    def display_rating(self):
        head = self.headliner
        if head and head.rating is not None:
            return head.rating
        rated = [a.rating for a in self.lineup if a.rating is not None]
        return max(rated) if rated else None

    @property
    def total_spend(self):
        return (self.price or 0) + (self.merch_spent or 0)

    def __str__(self):
        return f"{self.date} — {self.title}"


class Performance(models.Model):
    """One artist's set within an Event."""

    class Role(models.TextChoices):
        HEADLINER = "headliner", "Headliner"
        CO_HEADLINER = "co_headliner", "Co-Headliner"
        OPENER = "opener", "Opener"

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="performances")
    artist = models.CharField(max_length=200)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.HEADLINER)
    genre = models.CharField(max_length=100, blank=True)
    tour_name = models.CharField(max_length=200, blank=True)
    rating = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    set_length = models.DurationField(null=True, blank=True)
    setlist_fm_url = models.URLField(blank=True, verbose_name="setlist.fm link")
    setlist_highlights = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(
        default=0, help_text="Display order within the event — 0 is listed first (usually the headliner)"
    )

    class Meta:
        ordering = ["event__date", "order"]

    @property
    def highlight_lines(self):
        return [line.strip() for line in self.setlist_highlights.splitlines() if line.strip()]

    def __str__(self):
        return f"{self.artist} ({self.get_role_display()})"

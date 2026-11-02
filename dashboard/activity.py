"""Cross-tracker activity: the data behind the home page feed and calendar."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from math import ceil

from django.urls import reverse

from books.models import Book
from concerts.models import Event
from core.categories import BY_SLUG
from golf.models import Round
from movies.models import Movie
from sports.models import SportingEvent


@dataclass
class Item:
    date: date
    cat: str
    title: str
    sub: str

    @property
    def color(self):
        return BY_SLUG[self.cat].color

    @property
    def icon(self):
        return BY_SLUG[self.cat].icon

    @property
    def url(self):
        return reverse(BY_SLUG[self.cat].url_name)


def gather():
    items = []
    for e in Event.objects.select_related("location").prefetch_related("performances"):
        items.append(Item(e.date, "concerts", e.title, f"{e.location.name} · {e.get_event_type_display()}"))
    for m in Movie.objects.all():
        items.append(Item(m.date, "movies", m.title, m.platform or "Movie night"))
    for g in SportingEvent.objects.select_related("location"):
        items.append(Item(g.date, "sports", g.matchup, f"{g.league} · {g.location.name}"))
    for r in Round.objects.select_related("course"):
        items.append(Item(r.date, "golf", r.course.name, f"{r.get_game_display()} · shot {r.score}"))
    for b in Book.objects.filter(status=Book.Status.FINISHED, date_finished__isnull=False):
        items.append(Item(b.date_finished, "books", b.title, f"Finished · {b.author}"))
    return sorted(items, key=lambda i: i.date, reverse=True)


def _background(colors):
    if len(colors) == 1:
        return colors[0]
    step = 100 / len(colors)
    stops = ", ".join(f"{c} {i * step:.0f}% {(i + 1) * step:.0f}%" for i, c in enumerate(colors))
    return f"linear-gradient(135deg, {stops})"


def build_calendar(items, start, end):
    """GitHub-style grid: 7 rows (Sun-Sat) of week columns between start and end."""
    first = start - timedelta(days=(start.weekday() + 1) % 7)
    columns = ceil(((end - first).days + 1) / 7)

    by_day = defaultdict(list)
    for item in items:
        if start <= item.date <= end:
            by_day[item.date].append(item)

    cells = []
    for i in range(columns * 7):
        day = first + timedelta(days=i)
        if day < start or day > end:
            cells.append({"pad": True})
            continue
        acts = by_day.get(day, [])
        cats = list(dict.fromkeys(a.cat for a in acts))
        cells.append({
            "pad": False,
            "on": bool(acts),
            "today": day == date.today(),
            "style": f"background: {_background([BY_SLUG[c].color for c in cats])}" if acts else "",
            "title": f"{day:%a, %b} {day.day}, {day.year}" + ("".join(f"\n• {a.title}" for a in acts) if acts else ""),
        })

    months, previous = [], None
    for c in range(columns):
        column_start = first + timedelta(days=7 * c)
        anchor = max(column_start, start)
        if anchor.month != previous and anchor <= end:
            months.append({"col": c + 1, "label": f"{anchor:%b}"})
            previous = anchor.month
    return {"cells": cells, "months": months, "columns": columns}

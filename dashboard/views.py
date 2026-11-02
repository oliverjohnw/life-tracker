from datetime import date, timedelta

from django.shortcuts import render
from django.urls import reverse
from django.utils.html import format_html

from books.models import Book
from concerts.models import Event
from core.categories import CATEGORIES
from golf.models import Round
from movies.models import Movie
from sports.models import SportingEvent

from .activity import build_calendar, gather


def _cards(items):
    """One summary card per tracker: a big number and a line of color commentary."""
    today = date.today()
    by_cat = {c.slug: [i for i in items if i.cat == c.slug] for c in CATEGORIES}

    def latest(slug):
        rows = by_cat[slug]
        return format_html("Latest: <b>{}</b>", rows[0].title) if rows else "Nothing logged yet"

    games = list(SportingEvent.objects.all())
    wins = sum(1 for g in games if g.result == "W")
    losses = sum(1 for g in games if g.result == "L")
    golf = Round.objects.filter(game=Round.Game.GOLF).count()
    disc = Round.objects.filter(game=Round.Game.DISC_GOLF).count()
    reading = Book.objects.filter(status=Book.Status.READING).first()

    data = {
        "concerts": (Event.objects.count(), latest("concerts")),
        "movies": (Movie.objects.count(), latest("movies")),
        "sports": (
            len(games),
            format_html("Record: <b>{}–{}</b>", wins, losses) if wins + losses else latest("sports"),
        ),
        "golf": (golf + disc, format_html("<b>{}</b> golf · <b>{}</b> disc golf", golf, disc)),
        "books": (
            Book.objects.filter(status=Book.Status.FINISHED).count(),
            format_html("Reading: <b>{}</b>", reading.title) if reading else latest("books"),
        ),
    }
    cards = []
    for c in CATEGORIES:
        count, line = data[c.slug]
        this_year = sum(1 for i in by_cat[c.slug] if i.date.year == today.year)
        cards.append({"cat": c, "count": count, "line": line, "this_year": this_year, "year": today.year,
                      "add_url": reverse("quicklog:form", args=[_LOG_KIND[c.slug]])})
    return cards


_LOG_KIND = {"concerts": "concert", "movies": "movie", "sports": "game", "golf": "golf", "books": "book"}


def home(request):
    items = gather()
    today = date.today()

    years = sorted({i.date.year for i in items}, reverse=True)
    selected = request.GET.get("year")
    if selected and selected.isdigit() and int(selected) in years:
        year = int(selected)
        start, end = date(year, 1, 1), date(year, 12, 31)
    else:
        year = None
        start, end = today - timedelta(days=364), today

    calendar = build_calendar(items, start, end)
    in_window = [i for i in items if start <= i.date <= end]
    active_days = len({i.date for i in in_window})

    context = {
        "cards": _cards(items),
        "calendar": calendar,
        "years": years,
        "selected_year": year,
        "window_count": len(in_window),
        "active_days": active_days,
        "feed": [i for i in items if i.date <= today][:9],
        "total": len(items),
        "latest": next((i for i in items if i.date <= today), None),
    }
    return render(request, "dashboard/home.html", context)

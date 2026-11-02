from datetime import date

from django.shortcuts import render
from django.urls import reverse

from core import charts
from core.categories import BY_SLUG

from .models import Movie, WatchlistItem

CAT = BY_SLUG["movies"]
TABS = [("log", "Logbook", "list"), ("insights", "Insights", "chart"), ("watchlist", "Watchlist", "bookmark")]


def index(request):
    movies = list(Movie.objects.prefetch_related("watched_with"))
    watchlist = list(WatchlistItem.objects.all())
    for m in movies:
        m.year_watched = m.date.year
        m.search_blob = " ".join(
            [m.title, m.platform, m.city, m.genre, m.notes, m.quotes, str(m.year or "")]
            + [p.name for p in m.watched_with.all()]
        ).lower()

    context = {
        "has_charts": True,
        "has_data": bool(movies),
        "tabs": TABS,
        "movies": movies,
        "watchlist": watchlist,
        "add_url": reverse("quicklog:form", args=["movie"]),
        "add_label": "Log a movie",
        "empty_title": "The diary is empty",
        "empty_text": "Log a movie you watched, or import your sheet to bring in the whole diary.",
    }
    if not movies:
        return render(request, "movies/index.html", context)

    accent = CAT.color
    ratings = [m.rating for m in movies]
    avg = charts.average(ratings)
    theater = [m for m in movies if m.in_theater]
    best = max((m for m in movies if m.rating is not None), key=lambda m: m.rating, default=None)
    this_year = date.today().year
    unseen = [w for w in watchlist if not w.watched]

    context["years"] = sorted({m.year_watched for m in movies}, reverse=True)
    platforms = sorted({m.platform for m in movies if m.platform})
    context["platform_options"] = [(p, p) for p in platforms]
    context["tiles"] = [
        {"label": "Films logged", "value": len(movies),
         "sub": f"{sum(m.rewatches for m in movies)} rewatches · {len(theater)} in theaters"},
        {"label": "Avg rating", "value": f"{avg:.1f}" if avg is not None else "—",
         "sub": f"best: {best.title}" if best else ""},
        {"label": f"Watched in {this_year}", "value": sum(1 for m in movies if m.year_watched == this_year),
         "sub": f"{sum(1 for m in movies if m.year_watched == this_year - 1)} in {this_year - 1}"},
        {"label": "Watchlist", "value": len(unseen),
         "sub": f"up next: {unseen[0].title}" if unseen else "all caught up"},
    ]

    month_labels, month_counts = charts.per_month(m.date for m in movies)
    rating_labels, rating_counts = charts.rating_buckets(ratings)
    decade_counts = sorted(charts.tally([m.decade for m in movies]))
    platform_counts = charts.tally([m.platform for m in movies])
    genre_counts = charts.tally([m.genre for m in movies])
    company = charts.tally([p.name for m in movies for p in m.watched_with.all()], 8)
    solo = sum(1 for m in movies if not m.watched_with.all())

    cards = [
        charts.card("Movie nights by month", charts.column_chart(month_labels, month_counts, accent, unit="films"),
                    "A film diary, month by month", wide=True),
        charts.card("Where I watch",
                    charts.donut(platform_counts, center=len(movies), center_label="films"),
                    "Theater vs the couch"),
        charts.card("How good were they?", charts.column_chart(rating_labels, rating_counts, accent, unit="films"),
                    "Distribution of ratings"),
        charts.card("Release decade", charts.column_chart([d for d, _ in decade_counts], [c for _, c in decade_counts],
                                                           accent, unit="films"),
                    "When the films I watch were made"),
    ]
    if genre_counts:
        cards.append(charts.card("Genres", charts.donut(genre_counts, center=len(genre_counts), center_label="genres")))
    else:
        cards.append(charts.empty_card("Genres", "Add a genre to your movies in the admin and this lights up."))
    if company:
        cards.append(charts.card("Movie buddies", charts.row_chart(company, accent, unit="films"),
                                 f"Who I watch with — {solo} watched solo", wide=True))
    context["charts"] = cards

    rated = sorted((m for m in movies if m.rating is not None), key=lambda m: m.rating, reverse=True)
    context["top_rated"] = rated[:6]
    context["bottom_rated"] = list(reversed(rated[-5:]))
    return render(request, "movies/index.html", context)

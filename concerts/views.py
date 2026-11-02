from django.shortcuts import redirect, render
from django.urls import reverse

from core import charts
from core.categories import BY_SLUG

from .models import Event

CAT = BY_SLUG["concerts"]
TABS = [("log", "Logbook", "list"), ("insights", "Insights", "chart")]


def stats_redirect(request):
    """The old /concerts/stats/ URL now lives on the Insights tab."""
    return redirect(reverse("concerts:index") + "#insights")


def _search_blob(event):
    bits = [event.title, event.name, str(event.location), event.notes, event.seats]
    bits += [a.artist for a in event.lineup]
    bits += [a.genre for a in event.lineup]
    bits += [p.name for p in event.attendees.all()]
    return " ".join(b for b in bits if b).lower()


def index(request):
    events = list(
        Event.objects.select_related("location").prefetch_related("performances", "attendees")
    )
    for e in events:
        e.search_blob = _search_blob(e)
        e.year = e.date.year

    context = {
        "has_charts": True,
        "has_data": bool(events),
        "tabs": TABS,
        "add_url": reverse("quicklog:form", args=["concert"]),
        "add_label": "Log a show",
        "empty_title": "No shows yet",
        "empty_text": "Log your first concert — or run the Sheets importer to bring in your history.",
        "events": events,
    }
    if not events:
        return render(request, "concerts/index.html", context)

    performances = [p for e in events for p in e.lineup]
    artist_counts = charts.tally([p.artist for p in performances])
    venue_counts = charts.tally([e.location.name for e in events])
    ratings = [e.display_rating for e in events]
    avg_rating = charts.average(ratings)
    spent = sum(e.total_spend for e in events)
    paid = [e for e in events if e.price]
    years = sorted({e.year for e in events}, reverse=True)

    top_artist = artist_counts[0] if artist_counts else None
    top_venue = venue_counts[0] if venue_counts else None
    best = max((e for e in events if e.display_rating is not None), key=lambda e: e.display_rating, default=None)

    context["tiles"] = [
        {"label": "Shows", "value": len(events),
         "sub": f"since {min(e.date for e in events):%b %Y}"},
        {"label": "Artists", "value": len({p.artist.lower() for p in performances}),
         "sub": f"most seen: {top_artist[0]} ×{top_artist[1]}" if top_artist else ""},
        {"label": "Venues", "value": len({e.location_id for e in events}),
         "sub": f"home turf: {top_venue[0]}" if top_venue else ""},
        {"label": "Spent", "value": f"${spent:,.0f}",
         "sub": f"avg ${sum(e.price for e in paid) / len(paid):,.0f} a ticket" if paid else ""},
        {"label": "Avg rating", "value": f"{avg_rating:.1f}" if avg_rating is not None else "—",
         "sub": f"best: {best.title}" if best else ""},
    ]
    context["years"] = years
    context["type_options"] = [
        (value, label) for value, label in Event.EventType.choices if any(e.event_type == value for e in events)
    ]

    # ── charts ──────────────────────────────────────────────
    accent = CAT.color
    year_labels, year_counts = charts.per_year(e.date for e in events)
    spend_tickets = [sum(float(e.price or 0) for e in events if e.year == y) for y in year_labels]
    spend_merch = [sum(float(e.merch_spent or 0) for e in events if e.year == y) for y in year_labels]
    month_names, month_counts = charts.per_month_of_year(e.date for e in events)
    rating_labels, rating_counts = charts.rating_buckets(ratings)
    type_counts = charts.tally([e.get_event_type_display() for e in events])
    genre_counts = charts.tally([p.genre for p in performances])
    company = charts.tally([p.name for e in events for p in e.attendees.all()], 8)

    cards = [
        charts.card("Shows per year", charts.column_chart(year_labels, year_counts, accent, unit="shows"),
                    "How often I get out"),
        charts.card("Spend per year",
                    charts.stacked_columns(year_labels, [("Tickets", spend_tickets, accent),
                                                         ("Merch", spend_merch, "#8b93a7")], prefix="$"),
                    "Tickets and merch"),
        charts.card("Most-seen artists", charts.row_chart(artist_counts[:8], accent, unit="shows"),
                    "Headliners and openers"),
        charts.card("Home venues", charts.row_chart(venue_counts[:8], accent, unit="visits"),
                    "Where I spend my nights"),
        charts.card("Type of night", charts.donut(type_counts, center=len(events), center_label="shows")),
    ]
    if genre_counts:
        cards.append(charts.card("Genres", charts.donut(genre_counts, center=len(genre_counts), center_label="genres")))
    else:
        cards.append(charts.empty_card("Genres", "Add a genre to your performances in the admin and this lights up."))
    cards += [
        charts.card("How good were they?", charts.column_chart(rating_labels, rating_counts, accent, unit="shows"),
                    "Distribution of ratings"),
        charts.card("Concert season", charts.column_chart(month_names, month_counts, accent, unit="shows"),
                    "Shows by month of the year"),
    ]
    if company:
        cards.append(charts.card("Concert crew", charts.row_chart(company, accent, unit="shows"),
                                 "Who I go with most", wide=True))
    context["charts"] = cards

    rated = sorted((e for e in events if e.display_rating is not None), key=lambda e: e.display_rating, reverse=True)
    context["top_rated"] = rated[:6]
    context["averages"] = [
        ("Sound", charts.average(e.sound_quality for e in events)),
        ("View", charts.average(e.view_quality for e in events)),
        ("Crowd", charts.average(e.crowd_rating for e in events)),
    ]
    return render(request, "concerts/index.html", context)

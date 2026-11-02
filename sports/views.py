from django.shortcuts import render
from django.urls import reverse

from core import charts
from core.categories import BY_SLUG

from .models import SportingEvent

CAT = BY_SLUG["sports"]
TABS = [("log", "Game log", "list"), ("insights", "Insights", "chart")]
LOSS_GRAY = "#5b6377"


def index(request):
    games = list(SportingEvent.objects.select_related("location").prefetch_related("attendees"))
    for g in games:
        g.year = g.date.year
        g.search_blob = " ".join(
            [g.league, g.home_team, g.away_team, g.winner, g.my_team, g.score, g.notes, str(g.location)]
            + [p.name for p in g.attendees.all()]
        ).lower()

    context = {
        "has_charts": True,
        "has_data": bool(games),
        "tabs": TABS,
        "games": games,
        "add_url": reverse("quicklog:form", args=["game"]),
        "add_label": "Log a game",
        "empty_title": "No games yet",
        "empty_text": "Log the next game you go to, or import your sporting events sheet.",
    }
    if not games:
        return render(request, "sports/index.html", context)

    accent = CAT.color
    wins = sum(1 for g in games if g.result == "W")
    losses = sum(1 for g in games if g.result == "L")
    league_counts = charts.tally([g.league for g in games])
    venue_counts = charts.tally([g.location.name for g in games])
    avg = charts.average(g.rating for g in games)

    context["years"] = sorted({g.year for g in games}, reverse=True)
    context["league_options"] = [(name, name) for name, _ in sorted(league_counts)]
    context["tiles"] = [
        {"label": "Games", "value": len(games), "sub": f"since {min(g.date for g in games):%b %Y}"},
        {"label": "Record", "value": f"{wins}–{losses}",
         "sub": f"{wins / (wins + losses):.0%} win rate" if wins + losses else "no results logged"},
        {"label": "Leagues", "value": len(league_counts),
         "sub": f"most: {league_counts[0][0]} ×{league_counts[0][1]}"},
        {"label": "Venues", "value": len({g.location_id for g in games}),
         "sub": f"home turf: {venue_counts[0][0]}"},
        {"label": "Avg rating", "value": f"{avg:.1f}" if avg is not None else "—", "sub": ""},
    ]

    year_labels, year_counts = charts.per_year(g.date for g in games)
    rating_labels, rating_counts = charts.rating_buckets(g.rating for g in games)
    team_counts = charts.tally([g.my_team for g in games], 8)
    company = charts.tally([p.name for g in games for p in g.attendees.all()], 8)

    record_leagues = [name for name, _ in league_counts if any(g.league == name and g.result for g in games)]
    cards = [
        charts.card("Games per year", charts.column_chart(year_labels, year_counts, accent, unit="games")),
        charts.card("By league", charts.row_chart(league_counts[:8], accent, unit="games"), "What I go to see"),
    ]
    if record_leagues:
        cards.append(charts.card(
            "Record by league",
            charts.stacked_columns(
                record_leagues,
                [("Wins", [sum(1 for g in games if g.league == lg and g.result == "W") for lg in record_leagues], accent),
                 ("Losses", [sum(1 for g in games if g.league == lg and g.result == "L") for lg in record_leagues], LOSS_GRAY)],
                unit="games"),
            "Results from the seats"))
    cards.append(charts.card("Home venues", charts.row_chart(venue_counts[:8], accent, unit="games"),
                             "Where the games happen"))
    cards.append(charts.card("How good were they?", charts.column_chart(rating_labels, rating_counts, accent, unit="games"),
                             "Distribution of ratings"))
    if team_counts:
        cards.append(charts.card("Teams I back", charts.row_chart(team_counts, accent, unit="games"),
                                 "Rooting interest by games attended"))
    if company:
        cards.append(charts.card("Game-day crew", charts.row_chart(company, accent, unit="games"),
                                 "Who I go with most", wide=True))
    context["charts"] = cards

    rated = sorted((g for g in games if g.rating is not None), key=lambda g: g.rating, reverse=True)
    context["top_rated"] = rated[:5]
    return render(request, "sports/index.html", context)

from django.shortcuts import render
from django.urls import reverse

from core import charts
from core.categories import BY_SLUG

from .models import Round

CAT = BY_SLUG["golf"]
TABS = [("log", "Rounds", "list"), ("insights", "Insights", "chart")]


def index(request):
    game = request.GET.get("game", Round.Game.GOLF)
    if game not in Round.Game.values:
        game = Round.Game.GOLF
    game_label = Round.Game(game).label

    rounds = list(
        Round.objects.filter(game=game).select_related("course").prefetch_related("played_with")
    )
    for r in rounds:
        r.year = r.date.year
        r.course_name = r.course.name
        r.search_blob = " ".join(
            [r.course.name, r.course.city, r.layout, r.weather, r.notes] + [p.name for p in r.played_with.all()]
        ).lower()

    add_url = reverse("quicklog:form", args=["golf" if game == Round.Game.GOLF else "disc-golf"])
    context = {
        "has_charts": True,
        "has_data": bool(rounds),
        "tabs": TABS,
        "rounds": rounds,
        "game": game,
        "game_label": game_label,
        "games": [(value, label) for value, label in Round.Game.choices],
        "add_url": add_url,
        "add_label": "Log a round",
        "empty_title": f"No {game_label.lower()} rounds yet",
        "empty_text": "Log your first round — course, score and par are all you need. "
                      "Everything else (weather, who you played with, handicap numbers) is optional.",
    }
    if not rounds:
        return render(request, "golf/index.html", context)

    accent = CAT.color
    with_par = [r for r in rounds if r.to_par is not None]
    best = min(with_par, key=lambda r: r.to_par, default=None) or min(rounds, key=lambda r: r.score)
    avg_to_par = charts.average(r.to_par for r in with_par)
    avg_rating = charts.average(r.rating for r in rounds)
    course_counts = charts.tally([r.course_name for r in rounds])
    full_rounds = [r for r in rounds if r.holes == 18]
    diffs = [r.differential for r in rounds if r.differential is not None]

    context["years"] = sorted({r.year for r in rounds}, reverse=True)
    context["course_options"] = [(name, name) for name, _ in sorted(course_counts)]
    context["tiles"] = [
        {"label": "Rounds", "value": len(rounds),
         "sub": f"{len(full_rounds)} full · {len(rounds) - len(full_rounds)} short"},
        {"label": "Best round",
         "value": f"{best.score}" + (f" ({best.to_par:+d})" if best.to_par else (" (E)" if best.to_par == 0 else "")),
         "sub": f"{best.course_name} · {best.date:%b %Y}"},
        {"label": "Avg vs par", "value": f"{avg_to_par:+.1f}" if avg_to_par is not None else "—",
         "sub": f"avg score {sum(r.score for r in rounds) / len(rounds):.1f}"},
        {"label": "Courses", "value": len(course_counts), "sub": f"most played: {course_counts[0][0]}"},
        {"label": "Avg differential" if diffs else "Enjoyment",
         "value": f"{sum(diffs) / len(diffs):.1f}" if diffs else (f"{avg_rating:.1f}" if avg_rating is not None else "—"),
         "sub": "handicap differential" if diffs else "average rating"},
    ]

    year_labels, year_counts = charts.per_year(r.date for r in rounds)
    rating_labels, rating_counts = charts.rating_buckets(r.rating for r in rounds)
    company = charts.tally([p.name for r in rounds for p in r.played_with.all()], 8)
    holes_counts = charts.tally([f"{r.holes} holes" for r in rounds])
    trend = sorted(with_par, key=lambda r: r.date)

    cards = []
    if len(trend) >= 2:
        cards.append(charts.card(
            "Score vs par over time",
            charts.line_chart([r.date.isoformat() for r in trend], [r.to_par for r in trend], accent,
                              unit="vs par", zero_line=True, y_title="strokes over par",
                              hover_text=[f"{r.course_name} · {r.date:%b %d, %Y}" for r in trend]),
            "Lower is better — the line you want sinking", wide=True))
    else:
        cards.append(charts.empty_card("Score vs par over time",
                                       "Log a few rounds that include par and your trend line appears here.", wide=True))
    cards += [
        charts.card("Rounds per year", charts.column_chart(year_labels, year_counts, accent, unit="rounds")),
        charts.card("Courses played", charts.row_chart(course_counts[:8], accent, unit="rounds"),
                    "Where I play"),
        charts.card("Round length", charts.donut(holes_counts, center=len(rounds), center_label="rounds")),
        charts.card("Enjoyment", charts.column_chart(rating_labels, rating_counts, accent, unit="rounds"),
                    "How much I liked each round") if rating_labels
        else charts.empty_card("Enjoyment", "Rate your rounds 0–10 to see how they feel."),
    ]
    if company:
        cards.append(charts.card("Playing partners", charts.row_chart(company, accent, unit="rounds"), wide=True))
    context["charts"] = cards
    return render(request, "golf/index.html", context)

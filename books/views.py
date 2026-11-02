from datetime import date

from django.shortcuts import render
from django.urls import reverse

from core import charts
from core.categories import BY_SLUG

from .models import Book

CAT = BY_SLUG["books"]
TABS = [("log", "Shelf", "book"), ("insights", "Insights", "chart")]


def index(request):
    books = list(Book.objects.select_related("recommended_by"))
    for b in books:
        b.year = b.activity_date.year if b.activity_date else ""
        b.search_blob = " ".join(
            [b.title, b.author, b.series, b.genre, b.notes, b.quotes, b.get_status_display()]
        ).lower()

    context = {
        "has_charts": True,
        "has_data": bool(books),
        "tabs": TABS,
        "books": books,
        "add_url": reverse("quicklog:form", args=["book"]),
        "add_label": "Add a book",
        "empty_title": "The shelf is empty",
        "empty_text": "Add the book you're reading now — or the ones you've finished — and your reading stats appear here.",
    }
    if not books:
        return render(request, "books/index.html", context)

    accent = CAT.color
    finished = [b for b in books if b.status == Book.Status.FINISHED]
    reading = [b for b in books if b.status == Book.Status.READING]
    to_read = [b for b in books if b.status == Book.Status.TO_READ]
    this_year = date.today().year
    finished_dates = [b.date_finished for b in finished if b.date_finished]
    pages = sum(b.pages or 0 for b in finished)
    paged = [b.pages for b in finished if b.pages]
    avg = charts.average(b.rating for b in finished)

    context["years"] = sorted({b.year for b in books if b.year}, reverse=True)
    context["status_options"] = [(v, l) for v, l in Book.Status.choices if any(b.status == v for b in books)]
    context["tiles"] = [
        {"label": "Books finished", "value": len(finished),
         "sub": f"{sum(1 for b in finished if b.date_finished and b.date_finished.year == this_year)} in {this_year}"},
        {"label": "Pages read", "value": f"{pages:,}",
         "sub": f"avg {sum(paged) // len(paged)} pages a book" if paged else ""},
        {"label": "Avg rating", "value": f"{avg:.1f}" if avg is not None else "—", "sub": ""},
        {"label": "Reading now", "value": len(reading), "sub": reading[0].title if reading else "nothing on the go"},
        {"label": "Want to read", "value": len(to_read), "sub": to_read[0].title if to_read else ""},
    ]

    year_labels, year_counts = charts.per_year(finished_dates)
    page_by_year = [sum(b.pages or 0 for b in finished if b.date_finished and b.date_finished.year == y) for y in year_labels]
    rating_labels, rating_counts = charts.rating_buckets(b.rating for b in finished)
    genre_counts = charts.tally([b.genre for b in finished])
    format_counts = charts.tally([b.get_format_display() for b in finished])
    category_counts = charts.tally([b.get_category_display() for b in finished])
    authors = charts.tally([b.author for b in finished], 8)

    cards = [
        charts.card("Books per year", charts.column_chart(year_labels, year_counts, accent, unit="books"),
                    "Finished"),
        charts.card("Pages per year", charts.column_chart(year_labels, page_by_year, accent, unit="pages"),
                    "Finished books only"),
        charts.card("Fiction vs non-fiction",
                    charts.donut(category_counts, center=len(finished), center_label="books")),
        charts.card("How I read", charts.donut(format_counts, center=len(finished), center_label="books"),
                    "Physical, e-book or audio"),
    ]
    if genre_counts:
        cards.append(charts.card("Genres", charts.donut(genre_counts, center=len(genre_counts), center_label="genres")))
    else:
        cards.append(charts.empty_card("Genres", "Add a genre to your books in the admin and this lights up."))
    cards.append(charts.card("How good were they?",
                             charts.column_chart(rating_labels, rating_counts, accent, unit="books"),
                             "Distribution of ratings") if rating_labels
                 else charts.empty_card("How good were they?", "Rate a finished book to see the spread."))
    if authors and authors[0][1] > 1:
        cards.append(charts.card("Favorite authors", charts.row_chart(authors, accent, unit="books"), wide=True))
    context["charts"] = cards

    rated = sorted((b for b in finished if b.rating is not None), key=lambda b: b.rating, reverse=True)
    context["top_rated"] = rated[:5]
    return render(request, "books/index.html", context)

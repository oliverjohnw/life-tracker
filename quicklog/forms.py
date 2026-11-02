"""Quick-log forms: one short, friendly form per tracker.

Unlike the admin these resolve venues and people by *name* — type "Fiserv Forum" and it
finds (or creates) the Location; type "Grace, Dad" and it finds (or creates) both Persons.
Each form lists its `rows` (always visible) and `more_rows` (tucked under "More details").
"""

from datetime import date

from django import forms
from django.forms import formset_factory
from django.utils.html import format_html, format_html_join

from books.models import Book
from concerts.models import Event, Performance
from core.models import Location, Person
from core.utils import fix_caps
from golf.models import Round
from movies.models import Movie, WatchlistItem
from sports.models import SportingEvent

PLATFORMS = ["Theater", "Netflix", "Max", "Prime", "Hulu", "Disney+", "Peacock", "Paramount", "Apple TV", "Rented", "DVD", "Purchased"]
LEAGUES = ["NBA", "MLB", "NFL", "NHL", "MLS", "UFC", "PFL", "NCAA Football", "NCAA Mens Basketball", "NCAA Mens Hockey"]


# ── widgets ──────────────────────────────────────────────────────────────────

class DatalistInput(forms.TextInput):
    """A text box that suggests (but doesn't force) known values."""

    def __init__(self, suggestions=(), attrs=None):
        super().__init__(attrs)
        self.suggestions = list(suggestions)

    def render(self, name, value, attrs=None, renderer=None):
        attrs = dict(attrs or {})
        list_id = f"{attrs.get('id', name)}_options"
        attrs["list"] = list_id
        field = super().render(name, value, attrs, renderer)
        options = format_html_join("", '<option value="{}">', ((s,) for s in self.suggestions))
        return format_html('{}<datalist id="{}">{}</datalist>', field, list_id, options)


class PeopleWidget(forms.TextInput):
    """Chip input: type a name, Enter adds it. Submits as one comma-separated string."""

    suggestions = ()

    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        list_id = f"{attrs.get('id', name)}_options"
        options = format_html_join("", '<option value="{}">', ((s,) for s in self.suggestions))
        return format_html(
            '<div class="chips" data-chips><div class="chips-list" data-chips-list></div>'
            '<input type="hidden" name="{}" value="{}" data-chips-value>'
            '<input type="text" class="chips-input" list="{}" placeholder="Type a name, press Enter" '
            'autocomplete="off" data-chips-input id="{}"><datalist id="{}">{}</datalist></div>',
            name, value or "", list_id, attrs.get("id", name), list_id, options,
        )


class PeopleField(forms.CharField):
    widget = PeopleWidget

    def __init__(self, **kwargs):
        kwargs.setdefault("required", False)
        kwargs.setdefault("label", "Who was with you?")
        super().__init__(**kwargs)

    def clean(self, value):
        return [n.strip() for n in super().clean(value).split(",") if n.strip()]


def rating_field(label="Rating", help_text=""):
    return forms.DecimalField(
        label=label, required=False, min_value=0, max_value=10, max_digits=4, decimal_places=2,
        help_text=help_text,
        widget=forms.NumberInput(attrs={"step": "0.1", "inputmode": "decimal", "placeholder": "0–10"}),
    )


def money_field(label):
    return forms.DecimalField(
        label=label, required=False, min_value=0, max_digits=8, decimal_places=2,
        widget=forms.NumberInput(attrs={"step": "0.01", "inputmode": "decimal", "placeholder": "$"}),
    )


def date_field(label="Date", required=True):
    return forms.DateField(
        label=label, required=required, initial=date.today if required else None,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )


def style_fields(form):
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            cls = "check"
        elif isinstance(widget, forms.Select):
            cls = "select"
        elif isinstance(widget, forms.Textarea):
            cls = "input textarea"
        elif isinstance(widget, (forms.ClearableFileInput, forms.FileInput)):
            cls = "file"
        else:
            cls = "input"
        if not isinstance(widget, PeopleWidget):
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {cls}".strip()


def notes_field(label="Notes", rows=3, placeholder=""):
    return forms.CharField(
        label=label, required=False,
        widget=forms.Textarea(attrs={"rows": rows, "placeholder": placeholder}),
    )


# ── base classes ─────────────────────────────────────────────────────────────

class QuickForm(forms.Form):
    rows = []
    more_rows = []
    visible_if = {}  # {"field": "other_field=value|value"}
    has_location = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)
        if "people" in self.fields:
            self.fields["people"].widget.suggestions = list(Person.objects.values_list("name", flat=True))

    def _bound(self, rows):
        out = []
        for row in rows:
            cells = []
            for name in row:
                if name not in self.fields:
                    continue
                cond = self.visible_if.get(name)
                attrs = format_html(' data-visible-if="{}"', cond) if cond else ""
                cells.append({"bf": self[name], "attrs": attrs})
            if cells:
                out.append(cells)
        return out

    @property
    def essential(self):
        return self._bound(self.rows)

    @property
    def more(self):
        return self._bound(self.more_rows)

    @property
    def more_has_errors(self):
        return any(cell["bf"].errors for row in self.more for cell in row)

    def location_map(self):
        return [
            {"name": l.name, "city": l.city, "state": l.state, "setting": l.setting}
            for l in Location.objects.all()
        ]

    def people_objects(self, names):
        people = []
        for name in names:
            person = Person.objects.filter(name__iexact=name).first() or Person.objects.create(name=name)
            people.append(person)
        return people

    def one_person(self, name):
        name = (name or "").strip()
        if not name:
            return None
        return Person.objects.filter(name__iexact=name).first() or Person.objects.create(name=name)


class LocationMixin(forms.Form):
    """venue / city / state — resolved to an existing Location by name, or a new one."""

    has_location = True
    venue = forms.CharField(max_length=200, label="Venue", widget=DatalistInput())
    city = forms.CharField(max_length=120, required=False)
    state = forms.CharField(max_length=120, required=False, widget=forms.TextInput(attrs={"placeholder": "WI"}))
    setting = forms.ChoiceField(
        required=False, label="Indoor / outdoor", choices=[("", "—")] + Location.Setting.choices,
        help_text="Only used when this is a new place",
    )

    def init_location(self, label="Venue"):
        self.fields["venue"].label = label
        self.fields["venue"].widget.suggestions = list(
            Location.objects.order_by("name").values_list("name", flat=True).distinct()
        )

    def resolve_location(self):
        cd = self.cleaned_data
        name = fix_caps(cd["venue"].strip())
        city = fix_caps((cd.get("city") or "").strip())
        state = (cd.get("state") or "").strip()
        state = state.upper() if len(state) == 2 else state
        matches = Location.objects.filter(name__iexact=name)
        if city:
            found = matches.filter(city__iexact=city).first()
        else:
            found = matches.first()
        return found or Location.objects.create(name=name, city=city, state=state, setting=cd.get("setting") or "")


# ── concerts ─────────────────────────────────────────────────────────────────

class ActForm(forms.Form):
    artist = forms.CharField(required=False, label="Artist", widget=forms.TextInput(attrs={"placeholder": "Opener or other act"}))
    role = forms.ChoiceField(
        label="Role", initial=Performance.Role.OPENER,
        choices=[(Performance.Role.OPENER, "Opener"), (Performance.Role.CO_HEADLINER, "Co-headliner")],
    )
    genre = forms.CharField(required=False, label="Genre")
    rating = rating_field()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)


ActFormSet = formset_factory(ActForm, extra=0)


class ConcertForm(LocationMixin, QuickForm):
    label = "Concert"
    date = date_field()
    artist = forms.CharField(max_length=200, label="Who did you see?", widget=forms.TextInput(attrs={"placeholder": "Artist or headliner"}))
    event_type = forms.ChoiceField(label="Type", choices=Event.EventType.choices, initial=Event.EventType.CONCERT)
    rating = rating_field()
    genre = forms.CharField(max_length=100, required=False, widget=DatalistInput())
    people = PeopleField()
    name = forms.CharField(max_length=200, required=False, label="Event name", help_text="Festival or event, e.g. Summerfest")
    tour_name = forms.CharField(max_length=200, required=False, label="Tour")
    price = money_field("Ticket price")
    merch_spent = money_field("Merch")
    seats = forms.CharField(max_length=200, required=False)
    sound_quality = rating_field("Sound")
    view_quality = rating_field("View")
    crowd_rating = rating_field("Crowd")
    setlist_fm_url = forms.URLField(required=False, label="setlist.fm link", widget=forms.URLInput(attrs={"placeholder": "https://www.setlist.fm/…"}))
    poster_taken = forms.BooleanField(required=False, label="I got a poster")
    poster_image = forms.ImageField(required=False, label="Poster photo")
    notes = notes_field(placeholder="How was it?")
    venue_notes = notes_field("Tip for next time at this venue", rows=2)

    rows = [["date", "event_type"], ["artist"], ["venue"], ["city", "state"], ["rating", "genre"], ["people"]]
    more_rows = [["name", "tour_name"], ["price", "merch_spent", "seats"], ["sound_quality", "view_quality", "crowd_rating"],
                 ["setlist_fm_url"], ["poster_taken", "poster_image"], ["notes"], ["venue_notes"], ["setting"]]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_location("Venue")
        self.fields["genre"].widget.suggestions = list(
            Performance.objects.exclude(genre="").values_list("genre", flat=True).distinct().order_by("genre")
        )
        self.acts = ActFormSet(self.data if self.is_bound else None, self.files if self.is_bound else None, prefix="acts")

    def is_valid(self):
        main, acts = super().is_valid(), self.acts.is_valid()
        return main and acts

    def save(self):
        cd = self.cleaned_data
        event = Event.objects.create(
            date=cd["date"], name=cd["name"], event_type=cd["event_type"], location=self.resolve_location(),
            seats=cd["seats"], price=cd["price"], merch_spent=cd["merch_spent"],
            sound_quality=cd["sound_quality"], view_quality=cd["view_quality"], crowd_rating=cd["crowd_rating"],
            poster_taken=cd["poster_taken"] or bool(cd["poster_image"]), poster_image=cd["poster_image"] or "",
            notes=cd["notes"], venue_notes=cd["venue_notes"],
        )
        event.attendees.set(self.people_objects(cd["people"]))
        Performance.objects.create(
            event=event, artist=cd["artist"].strip(), role=Performance.Role.HEADLINER, genre=cd["genre"],
            tour_name=cd["tour_name"], rating=cd["rating"], setlist_fm_url=cd["setlist_fm_url"], order=0,
        )
        order = 1
        for act in self.acts.cleaned_data:
            if act.get("artist", "").strip():
                Performance.objects.create(
                    event=event, artist=act["artist"].strip(), role=act["role"], genre=act.get("genre", ""),
                    rating=act.get("rating"), order=order,
                )
                order += 1
        self.message = f"{cd['artist'].strip()} at {event.location.name}"
        return event


# ── movies ───────────────────────────────────────────────────────────────────

class MovieForm(QuickForm):
    label = "Movie"
    date = date_field("Date watched")
    title = forms.CharField(max_length=250, widget=forms.TextInput(attrs={"placeholder": "What did you watch?"}))
    year = forms.IntegerField(required=False, min_value=1880, max_value=2100, label="Release year", widget=forms.NumberInput(attrs={"placeholder": "2024"}))
    platform = forms.CharField(max_length=100, required=False, label="Where?", widget=DatalistInput())
    rating = rating_field()
    people = PeopleField(label="Watched with")
    genre = forms.CharField(max_length=100, required=False, widget=DatalistInput())
    city = forms.CharField(max_length=120, required=False)
    rewatches = forms.IntegerField(required=False, min_value=0, label="Rewatches", help_text="Times you'd seen it before")
    notes = notes_field("Thoughts")
    quotes = notes_field("Favorite lines", rows=2)

    rows = [["date"], ["title"], ["year", "platform"], ["rating"], ["people"]]
    more_rows = [["genre", "city", "rewatches"], ["notes"], ["quotes"]]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        used = list(Movie.objects.exclude(platform="").values_list("platform", flat=True).distinct())
        self.fields["platform"].widget.suggestions = sorted(set(used) | set(PLATFORMS))
        self.fields["genre"].widget.suggestions = list(
            Movie.objects.exclude(genre="").values_list("genre", flat=True).distinct().order_by("genre")
        )
        self.fields["city"].widget.attrs["placeholder"] = "Where you watched"

    def clean(self):
        cd = super().clean()
        if cd.get("title") and cd.get("date") and Movie.objects.filter(title__iexact=cd["title"].strip(), date=cd["date"]).exists():
            self.add_error("title", "You already logged this one for that date.")
        return cd

    def save(self):
        cd = self.cleaned_data
        title = cd["title"].strip()
        movie = Movie.objects.create(
            date=cd["date"], title=title, year=cd["year"], genre=cd["genre"], rewatches=cd["rewatches"] or 0,
            platform=cd["platform"], city=fix_caps(cd["city"]), rating=cd["rating"], notes=cd["notes"], quotes=cd["quotes"],
        )
        movie.watched_with.set(self.people_objects(cd["people"]))
        ticked = WatchlistItem.objects.filter(title__iexact=title, watched=False).update(watched=True)
        self.message = title + (" — and ticked it off your watchlist" if ticked else "")
        return movie


# ── sports ───────────────────────────────────────────────────────────────────

class GameForm(LocationMixin, QuickForm):
    label = "Sporting event"
    date = date_field()
    league = forms.CharField(max_length=60, widget=DatalistInput(), help_text="NBA, MLB, UFC…")
    game_type = forms.ChoiceField(
        label="Type", initial="Regular Season",
        choices=[(c, c) for c in ["Regular Season", "Postseason", "Preseason", "Exhibition", "Tournament"]],
    )
    home_team = forms.CharField(max_length=120, label="Home team", widget=forms.TextInput(attrs={"placeholder": "Home team (or fighter 1)"}))
    away_team = forms.CharField(max_length=120, label="Away team", widget=forms.TextInput(attrs={"placeholder": "Away team (or fighter 2)"}))
    rooting = forms.ChoiceField(
        label="Who were you rooting for?", required=False,
        choices=[("", "Nobody in particular"), ("home", "Home"), ("away", "Away")],
        widget=forms.Select(attrs={"data-team-select": "1"}),
    )
    winner_side = forms.ChoiceField(
        label="Who won?", required=False,
        choices=[("", "Not sure / didn't finish"), ("home", "Home"), ("away", "Away")],
        widget=forms.Select(attrs={"data-team-select": "1"}),
    )
    score = forms.CharField(max_length=80, required=False, widget=forms.TextInput(attrs={"placeholder": "BOS 116 – MIL 108, or TKO"}))
    rating = rating_field()
    people = PeopleField()
    seats = forms.CharField(max_length=200, required=False)
    notes = notes_field()

    rows = [["date", "league"], ["home_team"], ["away_team"], ["rooting", "winner_side"], ["score"], ["venue"], ["city", "state"], ["rating"], ["people"]]
    more_rows = [["game_type", "seats"], ["notes"], ["setting"]]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_location("Venue")
        used = list(SportingEvent.objects.values_list("league", flat=True).distinct())
        self.fields["league"].widget.suggestions = sorted(set(used) | set(LEAGUES))

    def save(self):
        cd = self.cleaned_data
        home, away = fix_caps(cd["home_team"].strip()), fix_caps(cd["away_team"].strip())
        side = {"home": home, "away": away}
        game = SportingEvent.objects.create(
            date=cd["date"], league=cd["league"].strip(), game_type=cd["game_type"], home_team=home, away_team=away,
            winner=side.get(cd["winner_side"], ""), my_team=side.get(cd["rooting"], ""), score=cd["score"],
            location=self.resolve_location(), seats=cd["seats"], rating=cd["rating"], notes=cd["notes"],
        )
        game.attendees.set(self.people_objects(cd["people"]))
        self.message = game.matchup + (f" ({'won' if game.result == 'W' else 'lost'})" if game.result else "")
        return game


# ── golf / disc golf ─────────────────────────────────────────────────────────

class RoundForm(LocationMixin, QuickForm):
    date = date_field()
    holes = forms.IntegerField(min_value=1, max_value=36, initial=18, label="Holes")
    score = forms.IntegerField(min_value=1, label="Score", help_text="Total strokes or throws", widget=forms.NumberInput(attrs={"inputmode": "numeric"}))
    par = forms.IntegerField(required=False, min_value=1, label="Par", widget=forms.NumberInput(attrs={"inputmode": "numeric"}))
    rating = rating_field("Enjoyment")
    people = PeopleField(label="Played with")
    layout = forms.CharField(max_length=120, required=False, label="Tees / layout", widget=forms.TextInput(attrs={"placeholder": "Blue tees, Gold layout…"}))
    weather = forms.CharField(max_length=120, required=False, widget=forms.TextInput(attrs={"placeholder": "Sunny and 75, windy…"}))
    transport = forms.ChoiceField(required=False, label="Walking or cart?", choices=[("", "—")] + Round.Transport.choices)
    course_rating = forms.DecimalField(required=False, max_digits=4, decimal_places=1, label="Course rating", widget=forms.NumberInput(attrs={"step": "0.1"}))
    slope = forms.IntegerField(required=False, min_value=55, max_value=155, label="Slope")
    notes = notes_field()

    rows = [["date", "holes"], ["venue"], ["city", "state"], ["score", "par"], ["rating"], ["people"]]
    more_rows = [["weather", "layout"], ["transport"], ["course_rating", "slope"], ["notes"], ["setting"]]

    def __init__(self, *args, game=Round.Game.GOLF, **kwargs):
        super().__init__(*args, **kwargs)
        self.game = game
        self.init_location("Course")
        if game == Round.Game.DISC_GOLF:
            for name in ("transport", "course_rating", "slope"):
                del self.fields[name]
            self.fields["layout"].widget.attrs["placeholder"] = "Layout (e.g. Gold, Blue)"
        self.fields["score"].help_text = "Total throws" if game == Round.Game.DISC_GOLF else "Total strokes"

    def save(self):
        cd = self.cleaned_data
        golf = self.game == Round.Game.GOLF
        rnd = Round.objects.create(
            game=self.game, date=cd["date"], course=self.resolve_location(), layout=cd["layout"], holes=cd["holes"],
            score=cd["score"], par=cd["par"], weather=cd["weather"], rating=cd["rating"], notes=cd["notes"],
            transport=cd.get("transport", "") if golf else "", course_rating=cd.get("course_rating") if golf else None,
            slope=cd.get("slope") if golf else None,
        )
        rnd.played_with.set(self.people_objects(cd["people"]))
        extra = f" ({rnd.to_par:+d})" if rnd.to_par else (" (even par)" if rnd.to_par == 0 else "")
        self.message = f"{cd['score']}{extra} at {rnd.course.name}"
        return rnd


# ── books ────────────────────────────────────────────────────────────────────

class BookForm(QuickForm):
    label = "Book"
    title = forms.CharField(max_length=250, widget=forms.TextInput(attrs={"placeholder": "Title"}))
    author = forms.CharField(max_length=200)
    status = forms.ChoiceField(label="Where are you with it?", choices=Book.Status.choices, initial=Book.Status.FINISHED)
    date_started = date_field("Started", required=False)
    date_finished = date_field("Finished", required=False)
    rating = rating_field()
    format = forms.ChoiceField(choices=Book.Format.choices)
    category = forms.ChoiceField(choices=Book.Category.choices)
    genre = forms.CharField(max_length=100, required=False, widget=DatalistInput())
    pages = forms.IntegerField(required=False, min_value=1)
    series = forms.CharField(max_length=200, required=False, widget=forms.TextInput(attrs={"placeholder": "e.g. The Stormlight Archive #2"}))
    recommended_by = forms.CharField(max_length=200, required=False, label="Recommended by", widget=DatalistInput())
    cover_image = forms.ImageField(required=False, label="Cover photo")
    re_read = forms.BooleanField(required=False, label="This is a re-read")
    notes = notes_field("Thoughts")
    quotes = notes_field("Favorite passages", rows=2)

    rows = [["title"], ["author"], ["status"], ["date_started", "date_finished"], ["rating"]]
    more_rows = [["format", "category"], ["genre", "pages"], ["series"], ["recommended_by"], ["cover_image"], ["re_read"], ["notes"], ["quotes"]]
    visible_if = {
        "date_started": "status=reading|finished|abandoned",
        "date_finished": "status=finished|abandoned",
        "rating": "status=finished|abandoned|reading",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date_finished"].help_text = "Leave blank for today"
        self.fields["genre"].widget.suggestions = list(
            Book.objects.exclude(genre="").values_list("genre", flat=True).distinct().order_by("genre")
        )
        self.fields["recommended_by"].widget.suggestions = list(Person.objects.values_list("name", flat=True))

    def save(self):
        cd = self.cleaned_data
        status = cd["status"]
        started, finished = cd["date_started"], cd["date_finished"]
        if status == Book.Status.FINISHED and not finished:
            finished = date.today()
        if status == Book.Status.READING and not started:
            started = date.today()
        if status == Book.Status.TO_READ:
            started = finished = None
        book = Book.objects.create(
            title=cd["title"].strip(), author=cd["author"].strip(), series=cd["series"], category=cd["category"],
            genre=cd["genre"], format=cd["format"], pages=cd["pages"], status=status, date_started=started,
            date_finished=finished, rating=cd["rating"], re_read=cd["re_read"], cover_image=cd["cover_image"] or "",
            recommended_by=self.one_person(cd["recommended_by"]), notes=cd["notes"], quotes=cd["quotes"],
        )
        self.message = f"{book.title} — {book.get_status_display().lower()}"
        return book

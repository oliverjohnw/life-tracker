"""What can be logged — the dropdown options, in the order they appear."""

from dataclasses import dataclass, field

from django.urls import reverse

from core.categories import BY_SLUG
from golf.models import Round

from .forms import BookForm, ConcertForm, GameForm, MovieForm, RoundForm


@dataclass
class Spec:
    slug: str
    label: str
    category: str
    form_cls: type
    kwargs: dict = field(default_factory=dict)
    view_query: str = ""

    def make(self, *args, **kwargs):
        return self.form_cls(*args, **self.kwargs, **kwargs)

    @property
    def cat(self):
        return BY_SLUG[self.category]

    @property
    def color(self):
        return self.cat.color

    @property
    def rgb(self):
        return self.cat.rgb

    @property
    def icon(self):
        return self.cat.icon

    @property
    def view_url(self):
        return reverse(self.cat.url_name) + self.view_query

    @property
    def form_url(self):
        return reverse("quicklog:form", args=[self.slug])


SPEC_LIST = [
    Spec("concert", "Concert or show", "concerts", ConcertForm),
    Spec("movie", "Movie", "movies", MovieForm),
    Spec("game", "Sporting event", "sports", GameForm),
    Spec("golf", "Golf round", "golf", RoundForm, {"game": Round.Game.GOLF}),
    Spec("disc-golf", "Disc golf round", "golf", RoundForm, {"game": Round.Game.DISC_GOLF}, "?game=disc_golf"),
    Spec("book", "Book", "books", BookForm),
]
SPECS = {s.slug: s for s in SPEC_LIST}

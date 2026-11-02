"""The trackers that make up the dashboard — one place for names, colors and icons."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    slug: str
    label: str
    color: str
    icon: str
    tagline: str

    @property
    def url_name(self):
        return f"{self.slug}:index"

    @property
    def rgb(self):
        h = self.color.lstrip("#")
        return ", ".join(str(int(h[i : i + 2], 16)) for i in (0, 2, 4))


CATEGORIES = [
    Category("concerts", "Concerts", "#ff4f9a", "music", "Live music, comedy & shows"),
    Category("movies", "Movies", "#ffc233", "film", "Everything on the screen"),
    Category("sports", "Sports", "#4da3ff", "trophy", "Games I've been in the building for"),
    Category("golf", "Golf", "#5fd068", "flag", "Golf & disc golf rounds"),
    Category("books", "Books", "#a58bff", "book", "The reading list"),
]

BY_SLUG = {c.slug: c for c in CATEGORIES}

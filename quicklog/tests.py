import io
import tempfile
from datetime import date

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from books.models import Book
from concerts.models import Event, Performance
from core.models import Location, Person
from golf.models import Round
from movies.models import Movie, WatchlistItem
from sports.models import SportingEvent

AJAX = {"HTTP_X_REQUESTED_WITH": "fetch"}


class QuickLogTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user("tester", password="x")
        self.client.force_login(user)

    def post(self, kind, data, **extra):
        return self.client.post(reverse("quicklog:form", args=[kind]), data, **AJAX, **extra)

    def test_every_form_renders_as_a_fragment(self):
        for kind in ["concert", "movie", "game", "golf", "disc-golf", "book"]:
            response = self.client.get(reverse("quicklog:form", args=[kind]), **AJAX)
            self.assertEqual(response.status_code, 200, kind)
            self.assertContains(response, "data-qform")

    def test_unknown_kind_is_404(self):
        self.assertEqual(self.client.get("/log/nonsense/").status_code, 404)

    def test_concert_creates_event_acts_people_and_new_venue(self):
        Person.objects.create(name="Grace Mergen")
        response = self.post("concert", {
            "date": "2026-06-01", "event_type": "festival", "artist": "Tyler Childers", "venue": "Summerfest",
            "city": "milwaukee", "state": "wi", "rating": "9.1", "genre": "Country",
            "people": "grace mergen, New Friend", "name": "Summerfest Day 3", "price": "95",
            "acts-TOTAL_FORMS": "2", "acts-INITIAL_FORMS": "0",
            "acts-0-artist": "Charles Wesley Godwin", "acts-0-role": "opener", "acts-0-genre": "Country", "acts-0-rating": "8",
            "acts-1-artist": "", "acts-1-role": "opener",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        event = Event.objects.get()
        self.assertEqual(event.name, "Summerfest Day 3")
        self.assertEqual(event.location.state, "WI")
        self.assertEqual([p.artist for p in event.lineup], ["Tyler Childers", "Charles Wesley Godwin"])
        self.assertEqual(event.headliner.genre, "Country")
        self.assertEqual(Person.objects.count(), 2, "Grace is matched case-insensitively, not duplicated")
        self.assertEqual(event.attendees.count(), 2)

    def test_second_concert_reuses_existing_venue(self):
        base = {"event_type": "concert", "artist": "A", "venue": "The Rave", "acts-TOTAL_FORMS": "0", "acts-INITIAL_FORMS": "0"}
        self.post("concert", {**base, "date": "2026-01-01", "city": "Milwaukee", "state": "WI"})
        self.post("concert", {**base, "date": "2026-02-01", "venue": "the rave"})
        self.assertEqual(Location.objects.count(), 1)
        self.assertEqual(Event.objects.count(), 2)

    def test_concert_poster_upload(self):
        buffer = io.BytesIO()
        Image.new("RGB", (20, 30), (255, 79, 154)).save(buffer, "PNG")
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            self.post("concert", {
                "date": "2026-03-03", "event_type": "concert", "artist": "A", "venue": "V",
                "acts-TOTAL_FORMS": "0", "acts-INITIAL_FORMS": "0",
                "poster_image": SimpleUploadedFile("poster.png", buffer.getvalue(), content_type="image/png"),
            })
            event = Event.objects.get()
            self.assertTrue(event.poster_image)
            self.assertTrue(event.poster_taken)

    def test_concert_missing_artist_shows_errors_and_saves_nothing(self):
        response = self.post("concert", {
            "date": "2026-06-01", "event_type": "concert", "venue": "V", "acts-TOTAL_FORMS": "0", "acts-INITIAL_FORMS": "0",
        })
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "This field is required", status_code=400)
        self.assertEqual(Event.objects.count(), 0)

    def test_movie_ticks_watchlist_and_blocks_duplicates(self):
        WatchlistItem.objects.create(title="Heat")
        data = {"date": "2026-05-05", "title": "heat", "year": "1995", "platform": "Max", "rating": "9", "people": "Grace"}
        self.assertTrue(self.post("movie", data).json()["ok"])
        self.assertTrue(WatchlistItem.objects.get().watched)
        self.assertEqual(Movie.objects.get().watched_with.get().name, "Grace")
        self.assertEqual(self.post("movie", data).status_code, 400)

    def test_game_derives_my_team_and_result(self):
        response = self.post("game", {
            "date": "2026-04-28", "league": "MLB", "game_type": "Regular Season", "home_team": "Milwaukee Brewers",
            "away_team": "Arizona Diamondbacks", "rooting": "home", "winner_side": "home", "score": "ARI 2 - MIL 13",
            "venue": "American Family Field", "city": "Milwaukee", "state": "WI",
        })
        self.assertIn("won", response.json()["message"])
        game = SportingEvent.objects.get()
        self.assertEqual((game.my_team, game.winner, game.result), ("Milwaukee Brewers", "Milwaukee Brewers", "W"))

    def test_golf_and_disc_golf_share_a_model(self):
        self.post("golf", {"date": "2026-06-01", "holes": "18", "score": "88", "par": "72", "venue": "Meadow", "slope": "125", "course_rating": "71.2"})
        self.post("disc-golf", {"date": "2026-06-02", "holes": "18", "score": "55", "par": "54", "venue": "Pine Ridge"})
        golf, disc = Round.objects.order_by("date")
        self.assertEqual((golf.game, golf.to_par, golf.slope), ("golf", 16, 125))
        self.assertEqual((disc.game, disc.to_par, disc.slope), ("disc_golf", 1, None))
        form = self.client.get(reverse("quicklog:form", args=["disc-golf"]), **AJAX)
        self.assertNotContains(form, 'name="slope"')

    def test_book_defaults_finish_date_to_today(self):
        self.post("book", {"title": "Dune", "author": "Frank Herbert", "status": "finished", "format": "physical",
                           "category": "fiction", "rating": "9", "recommended_by": "Dad"})
        book = Book.objects.get()
        self.assertEqual(book.date_finished, date.today())
        self.assertEqual(book.recommended_by.name, "Dad")

    def test_full_page_fallback_without_javascript(self):
        response = self.client.post(reverse("quicklog:form", args=["movie"]),
                                    {"date": "2026-05-05", "title": "Heat"})
        self.assertContains(response, "Logged!")
        self.assertEqual(Movie.objects.count(), 1)

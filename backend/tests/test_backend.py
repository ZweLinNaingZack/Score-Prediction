import asyncio
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db.models import Fixture, PredictionRecord
from app.main import app
from app.services import sync


def api_item(fid, status="SCHEDULED", home=None, away=None, code="PL", date="2026-10-17T15:00:00Z", minute=None):
    return {
        "id": fid,
        "utcDate": date,
        "status": status,
        "minute": minute,
        "competition": {"code": code, "name": "Premier League"},
        "homeTeam": {"name": "Manchester City FC", "shortName": "Man City", "tla": "MCI", "crest": "https://crests.football-data.org/65.png"},
        "awayTeam": {"name": "Arsenal FC", "shortName": "Arsenal", "tla": "ARS"},
        "score": {"fullTime": {"home": home, "away": away}},
    }


def naive_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def add_fixture(db, fid, status="UPCOMING", kickoff=None, home=None, away=None, league_id=39):
    db.add(
        Fixture(
            id=fid, league_id=league_id, league="Premier League", home_team="Home FC", away_team="Away FC",
            home_short="HOM", away_short="AWA", kickoff=kickoff or naive_now(), status=status,
            home_goals=home, away_goals=away,
        )
    )
    db.commit()


def add_pred(db, fid, source, home, away, conf=0.6):
    db.add(PredictionRecord(fixture_id=fid, source=source, outcome="X", home_goals=home, away_goals=away, confidence=conf))
    db.commit()


def test_status_mapping_and_skips():
    live = sync.to_values(api_item(1, "IN_PLAY", 1, 0, minute=67))
    assert (live["status"], live["minute"]) == ("LIVE", 67)
    assert sync.to_values(api_item(1, "PAUSED", 1, 0))["status"] == "LIVE"
    fin = sync.to_values(api_item(2, "FINISHED", 2, 1))
    assert (fin["status"], fin["minute"], fin["home_goals"]) == ("FINISHED", None, 2)
    assert sync.to_values(api_item(3, "TIMED"))["status"] == "UPCOMING"
    assert sync.to_values(api_item(4, "POSTPONED")) is None
    assert sync.to_values(api_item(5, "SCHEDULED", code="XYZ")) is None  # untracked competition


def test_values_map_to_frontend_league_ids_and_names():
    v = sync.to_values(api_item(1))
    assert v["league_id"] == 39
    assert (v["home_team"], v["home_short"], v["away_short"]) == ("Man City", "MCI", "ARS")
    assert v["home_crest"] == "https://crests.football-data.org/65.png" and v["away_crest"] is None
    assert v["kickoff"] == datetime(2026, 10, 17, 15, 0)  # naive UTC
    assert sync.to_values(api_item(1, code="CL"))["league_id"] == 2
    assert sync.to_values(api_item(1, "SCHEDULED", date="2026-10-17T17:00:00+02:00"))["kickoff"].hour == 15


def test_missing_tla_and_score_are_tolerated():
    item = api_item(1)
    item["homeTeam"] = {"name": "Brighton & Hove Albion FC"}
    item["score"] = {}
    v = sync.to_values(item)
    assert v["home_team"] == "Brighton & Hove Albion FC" and v["home_short"] == "BRI"
    assert v["home_goals"] is None


def test_upsert_updates_existing_row(db):
    sync.upsert(db, [api_item(1, "SCHEDULED")])
    sync.upsert(db, [api_item(1, "IN_PLAY", 0, 0, minute=5)])
    rows = db.query(Fixture).all()
    assert len(rows) == 1 and rows[0].status == "LIVE" and rows[0].minute == 5


def test_postponed_match_is_removed(db):
    sync.upsert(db, [api_item(1, "SCHEDULED")])
    add_pred(db, 1, "my_model", 1, 0)
    sync.upsert(db, [api_item(1, "POSTPONED")])
    assert db.query(Fixture).count() == 0 and db.query(PredictionRecord).count() == 0


def test_live_window(db):
    now = naive_now()
    assert not sync.live_window_open(db)
    add_fixture(db, 1, kickoff=now + timedelta(hours=2))  # future
    add_fixture(db, 2, kickoff=now - timedelta(hours=5))  # long past, never updated
    assert not sync.live_window_open(db)
    add_fixture(db, 3, kickoff=now - timedelta(minutes=30))  # should be underway
    assert sync.live_window_open(db)


def test_finished_match_dropping_out_of_live_feed_gets_final_score(db, monkeypatch):
    add_fixture(db, 9, status="LIVE", kickoff=naive_now() - timedelta(hours=2), home=1, away=1)

    async def no_live():
        return []

    async def final(ids):
        assert ids == [9]
        return [api_item(9, "FINISHED", 2, 1)]

    monkeypatch.setattr(sync, "get_live", no_live)
    monkeypatch.setattr(sync, "get_matches_by_ids", final)
    asyncio.run(sync.refresh_live(db))
    f = db.get(Fixture, 9)
    assert (f.status, f.home_goals, f.away_goals) == ("FINISHED", 2, 1)


def test_refresh_if_stale_does_nothing_without_key(db, monkeypatch):
    called = []

    async def boom(*a, **k):
        called.append(1)

    monkeypatch.setattr(sync, "get_matches_between", boom)
    asyncio.run(sync.refresh_if_stale(db))
    assert called == []


def test_matches_endpoint_shape(db):
    now = naive_now()
    add_fixture(db, 1, status="LIVE", kickoff=now - timedelta(minutes=30), home=1, away=0)
    add_fixture(db, 2, kickoff=now + timedelta(days=1))
    add_fixture(db, 3, status="FINISHED", kickoff=now - timedelta(days=10), home=0, away=0)  # too old
    add_pred(db, 1, "my_model", 2, 1)
    add_pred(db, 1, "my_model", 1, 1, conf=0.7)  # newer prediction replaces the first
    add_pred(db, 1, "gemini", 1, 0)  # retired source: never shown

    with TestClient(app) as client:
        r = client.get("/api/matches")
    assert r.status_code == 200
    data = r.json()
    assert [m["id"] for m in data] == [1, 2]
    live = data[0]
    assert live["leagueId"] == 39 and live["status"] == "LIVE"
    assert live["home"] == {"name": "Home FC", "short": "HOM", "crest": None}
    assert live["score"] == {"home": 1, "away": 0}
    assert live["kickoff"].endswith("Z")
    # signed-out visitors see who predicted, but not the predictions
    assert live["predictions"] == [] and live["unlocked"] is False
    assert live["predictionModels"] == ["ml"]
    assert data[1]["score"] is None and data[1]["predictions"] == [] and data[1]["predictionModels"] == []


def test_leaderboard(db):
    now = naive_now() - timedelta(days=1)
    add_fixture(db, 1, status="FINISHED", kickoff=now, home=2, away=1)
    add_fixture(db, 2, status="FINISHED", kickoff=now, home=0, away=0)
    add_fixture(db, 3, kickoff=now)  # unfinished: ignored
    add_fixture(db, 4, status="FINISHED", kickoff=now, home=1, away=0)
    add_pred(db, 1, "my_model", 2, 1)  # exact
    add_pred(db, 2, "my_model", 1, 1)  # right outcome, wrong score
    add_pred(db, 4, "my_model", 0, 3)  # wrong
    add_pred(db, 3, "my_model", 1, 0)  # unfinished match: not counted
    add_pred(db, 1, "gemini", 2, 1)  # retired source: not counted

    with TestClient(app) as client:
        rows = {r["model"]: r for r in client.get("/api/leaderboard").json()}
    assert set(rows) == {"ml"}  # only our own model is ranked
    assert rows["ml"] == {"model": "ml", "played": 3, "exactScores": 1, "correctOutcomes": 2}


def test_http_error_body_message_is_surfaced(monkeypatch):
    import httpx
    import pytest

    from app.services import football_data

    class FakeResp:
        status_code = 403
        text = ""

        def json(self):
            return {"message": "The resource you are looking for is restricted", "errorCode": 403}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def get(self, *a, **k):
            return FakeResp()

    monkeypatch.setattr(football_data.httpx, "AsyncClient", FakeClient)
    with pytest.raises(httpx.HTTPError, match="restricted"):
        asyncio.run(football_data.get_live())


# ---- ML model ----
def _games():
    from app.ml.model import Game

    # Strong beats Weak at home and away; Mid sits between. Repeated so every team has history.
    results = [("Strong", "Weak", 3, 0), ("Weak", "Strong", 0, 2), ("Strong", "Mid", 2, 1),
               ("Mid", "Strong", 1, 1), ("Mid", "Weak", 2, 0), ("Weak", "Mid", 1, 2)]
    return [Game(h, a, hg, ag, day=19000.0 + i) for i, (h, a, hg, ag) in enumerate(results * 4)]


def test_model_ranks_teams_and_predicts_consistent_score():
    from app.ml.model import PoissonModel

    m = PoissonModel.fit(_games())
    assert m.attack["Strong"] > m.attack["Weak"] and m.defence["Strong"] < m.defence["Weak"]
    p = m.predict("Strong", "Weak")
    assert p.outcome == "HOME" and p.home_goals > p.away_goals and 0 < p.confidence <= 1
    assert "Strong" in p.reason and "%" in p.reason  # explanation is built from model numbers
    assert m.predict("Strong", "Nobody") is None  # unknown team


def test_model_save_load_roundtrip(tmp_path):
    from app.ml.model import PoissonModel

    m = PoissonModel.fit(_games())
    path = tmp_path / "model.json"
    m.save(path)
    again = PoissonModel.load(path)
    assert again.predict("Mid", "Weak") == m.predict("Mid", "Weak")
    assert PoissonModel.load(tmp_path / "missing.json") is None


# ---- accounts and unlock ----
def _signup(client, email="fan@example.com", password="Correct-horse1"):
    r = client.post("/api/auth/register", json={"email": email, "password": password, "name": "Fan Tester"})
    assert r.status_code == 201, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def test_register_login_and_me(db):
    with TestClient(app) as client:
        headers = _signup(client, "Fan@Example.com")  # email is case-insensitive
        assert client.get("/api/auth/me", headers=headers).json() == {"email": "fan@example.com", "name": "Fan Tester"}
        assert client.post("/api/auth/register", json={"email": "fan@example.com", "password": "Another-pass1", "name": "Test Name"}).status_code == 409
        ok = client.post("/api/auth/login", json={"email": "FAN@example.com", "password": "Correct-horse1"})
        assert ok.status_code == 200 and ok.json()["token"]
        bad = client.post("/api/auth/login", json={"email": "fan@example.com", "password": "wrong"})
        unknown = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "x"})
        assert bad.status_code == unknown.status_code == 401 and bad.json() == unknown.json()
        assert client.post("/api/auth/register", json={"email": "not-an-email", "password": "Long-enough1", "name": "Test Name"}).status_code == 422
        assert client.get("/api/auth/me").status_code == 401
        assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_tokens_expire_and_cannot_be_forged():
    from app import auth

    token = auth.make_token(7, now=1_000_000)
    assert auth.read_token(token, now=1_000_100) == 7
    assert auth.read_token(token, now=1_000_000 + 31 * 86400) is None  # expired
    payload, sig = token.split(".")
    forged = auth._b64(b'{"sub": 8, "exp": 9999999999}') + "." + sig
    assert auth.read_token(forged, now=1_000_100) is None


def test_predictions_withheld_until_unlocked(db):
    add_fixture(db, 1, kickoff=naive_now() + timedelta(days=1))
    add_fixture(db, 2, kickoff=naive_now() + timedelta(days=2))
    add_pred(db, 1, "my_model", 2, 1)
    with TestClient(app) as client:
        assert client.post("/api/matches/1/unlock").status_code == 401  # must sign in
        me = _signup(client)
        other = _signup(client, "other@example.com")

        before = {m["id"]: m for m in client.get("/api/matches", headers=me).json()}
        assert before[1]["predictions"] == [] and before[1]["unlocked"] is False

        assert client.post("/api/matches/1/unlock", headers=me).json() == {"unlocked": True}
        assert client.post("/api/matches/1/unlock", headers=me).status_code == 200  # idempotent
        assert client.post("/api/matches/99/unlock", headers=me).status_code == 404

        mine = {m["id"]: m for m in client.get("/api/matches", headers=me).json()}
        assert mine[1]["unlocked"] and [p["model"] for p in mine[1]["predictions"]] == ["ml"]
        assert mine[2]["unlocked"] is False  # unlocking one match does not unlock the rest

        for headers in (other, {}):  # another user and a signed-out visitor still see nothing
            seen = {m["id"]: m for m in client.get("/api/matches", headers=headers).json()}
            assert seen[1]["predictions"] == [] and seen[1]["unlocked"] is False


# ---- password rules and login rate limit ----
def test_password_rules():
    from app.auth import password_problem

    assert password_problem("Sh0rt!") == "Password must be at least 8 characters"
    assert "lowercase" in password_problem("ALLCAPS123!")
    assert "capital" in password_problem("alllower123!")
    assert "number" in password_problem("NoNumbers!!")
    assert "symbol" in password_problem("NoSymbol123")
    assert password_problem("Good-pass1") is None

    with TestClient(app) as client:
        weak = client.post("/api/auth/register", json={"email": "w@example.com", "password": "nosymbol1A", "name": "Weak Pass"})
        assert weak.status_code == 422 and "symbol" in weak.json()["detail"]


def test_login_locks_for_five_minutes_after_five_wrong_tries(monkeypatch):
    from app import auth

    clock = [1000.0]
    monkeypatch.setattr(auth, "_now", lambda: clock[0])
    with TestClient(app) as client:
        _signup(client)
        login = lambda pw, email="fan@example.com": client.post(  # noqa: E731
            "/api/auth/login", json={"email": email, "password": pw}
        )
        for _ in range(5):
            assert login("Wrong-pass1").status_code == 401  # five wrong tries are allowed
        locked = login("Correct-horse1")  # the right password is refused while locked
        assert locked.status_code == 429 and "5 minutes" in locked.json()["detail"]
        assert locked.headers["retry-after"] == "300"

        assert login("Correct-horse1", "other@example.com").status_code == 401  # other emails are not locked

        clock[0] += 150
        assert "3 minutes" in login("Correct-horse1").json()["detail"]  # time left shrinks
        clock[0] += 151  # just past 5 minutes
        assert login("Correct-horse1").status_code == 200
        for _ in range(4):  # a good login resets the count
            assert login("Wrong-pass1").status_code == 401
        assert login("Correct-horse1").status_code == 200


def test_login_lock_by_address_across_many_emails(monkeypatch):
    from app import auth

    monkeypatch.setattr(auth, "_now", lambda: 5000.0)
    with TestClient(app) as client:
        for i in range(20):  # guessing across many emails from one address
            assert client.post("/api/auth/login", json={"email": f"u{i}@example.com", "password": "x"}).status_code == 401
        assert client.post("/api/auth/login", json={"email": "new@example.com", "password": "x"}).status_code == 429


# ---- league tables ----
def _table_item(position, name, tla, played, won, draw, lost, gf, ga, points):
    return {
        "position": position, "team": {"name": name + " FC", "shortName": name, "tla": tla, "crest": f"https://c/{tla}.png"},
        "playedGames": played, "won": won, "draw": draw, "lost": lost, "goalsFor": gf, "goalsAgainst": ga, "points": points,
    }


def test_standings_endpoint_with_form(db, monkeypatch):
    from app.config import settings
    from app.services import sync

    now = naive_now()
    add_fixture(db, 1, status="FINISHED", kickoff=now - timedelta(days=3), home=2, away=0)  # Home FC beat Away FC
    add_fixture(db, 2, status="FINISHED", kickoff=now - timedelta(days=1), home=1, away=1)  # draw
    monkeypatch.setattr(settings, "football_data_key", "x")
    calls = []

    async def fake(code):
        calls.append(code)
        return [{"type": "TOTAL", "group": None, "table": [
            _table_item(1, "Home FC", "HOM", 2, 1, 1, 0, 3, 1, 4),
            _table_item(2, "Away FC", "AWA", 2, 0, 1, 1, 1, 3, 1),
        ]}]

    monkeypatch.setattr(sync, "get_standings", fake)
    sync._standings_last.clear()
    with TestClient(app) as client:
        r = client.get("/api/standings/39")
        assert r.status_code == 200
        body = r.json()
        assert body["leagueId"] == 39 and len(body["groups"]) == 1 and body["groups"][0]["name"] is None
        top, second = body["groups"][0]["rows"]
        assert (top["position"], top["team"], top["points"], top["goalDifference"]) == (1, "Home FC", 4, 2)
        assert top["form"] == "WD" and second["form"] == "LD"  # oldest first
        assert top["crest"] == "https://c/HOM.png"
        client.get("/api/standings/39")  # cached: no second request
        assert calls == ["PL"]
        assert client.get("/api/standings/3").status_code == 404  # Europa League is not covered


def test_standings_keeps_old_table_when_api_fails(db, monkeypatch):
    import httpx

    from app.config import settings
    from app.db.models import StandingRow
    from app.services import sync

    db.add(StandingRow(league_id=39, group="", position=1, team="Old FC", short="OLD", played=1, won=1, draw=0,
                       lost=0, goals_for=1, goals_against=0, points=3))
    db.commit()
    monkeypatch.setattr(settings, "football_data_key", "x")

    async def boom(code):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(sync, "get_standings", boom)
    sync._standings_last.clear()
    with TestClient(app) as client:
        r = client.get("/api/standings/39")
    assert r.status_code == 200 and r.json()["groups"][0]["rows"][0]["team"] == "Old FC"


def test_home_advantage_is_learned_per_team_and_shrunk():
    from app.ml.model import Game, PoissonModel

    games = []
    day = 19000.0
    for _ in range(12):  # Fortress wins big at home but only draws away; Visitor is the mirror image
        games += [
            Game("Fortress", "Visitor", 4, 0, day), Game("Visitor", "Fortress", 1, 1, day + 1),
            Game("Fortress", "Other", 3, 0, day + 2), Game("Other", "Fortress", 1, 1, day + 3),
            Game("Visitor", "Other", 1, 1, day + 4), Game("Other", "Visitor", 1, 1, day + 5),
        ]
        day += 7
    m = PoissonModel.fit(games)
    assert m.home_adv["Fortress"] > 1.0 > m.home_adv["Other"]
    shrunk = PoissonModel.fit(games, home_prior=1e9)  # a huge prior pulls everyone to exactly 1.0
    assert all(abs(v - 1.0) < 0.01 for v in shrunk.home_adv.values())
    none = PoissonModel.fit(games, home_prior=None)
    assert none.home_adv == {}
    round_trip = PoissonModel.fit(games)
    assert round_trip.expected_goals("Fortress", "Other")[0] > none.expected_goals("Fortress", "Other")[0]


def test_name_is_required_cleaned_and_returned(db):
    from app.db.models import User

    with TestClient(app) as client:
        body = {"email": "n@example.com", "password": "Good-pass1"}
        assert client.post("/api/auth/register", json=body).status_code == 422  # name missing
        assert client.post("/api/auth/register", json={**body, "name": "A"}).status_code == 422  # too short
        assert client.post("/api/auth/register", json={**body, "name": "x" * 41}).status_code == 422  # too long
        ok = client.post("/api/auth/register", json={**body, "name": "  Zwe   Lin  "})
        assert ok.status_code == 201 and ok.json()["name"] == "Zwe Lin"
        assert client.post("/api/auth/login", json=body).json()["name"] == "Zwe Lin"
        # an account made before names existed shows the part of the email before the @
        old = User(email="old.timer@example.com", password_hash="x")
        db.add(old)
        db.commit()
        from app.api.routes import display_name

        assert display_name(old) == "old.timer"


# ---- market odds ----
def _event(home, away, when, books):
    """books: list of (home_odds, draw_odds, away_odds), one per bookmaker."""
    return {
        "home_team": home, "away_team": away, "commence_time": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bookmakers": [
            {"key": f"b{i}", "title": f"Book {i}", "markets": [
                {"key": "h2h", "outcomes": [{"name": home, "price": h}, {"name": "Draw", "price": d}, {"name": away, "price": a}]}
            ]}
            for i, (h, d, a) in enumerate(books)
        ],
    }


def test_consensus_removes_margin_and_averages():
    from app.services.odds import consensus

    c = consensus(_event("A", "B", naive_now(), [(2.0, 3.5, 4.0), (2.2, 3.4, 3.6)]))
    assert c["bookmakers"] == 2
    assert abs(c["prob_home"] + c["prob_draw"] + c["prob_away"] - 1.0) < 1e-9  # margin is gone
    assert abs(c["home_odds"] - 2.1) < 1e-9 and abs(c["away_odds"] - 3.8) < 1e-9  # plain averages
    assert c["prob_home"] > c["prob_draw"]
    assert consensus(_event("A", "B", naive_now(), [])) is None
    assert consensus(_event("A", "B", naive_now(), [(0.9, 3.0, 4.0)])) is None  # nonsense odds are ignored


def test_team_names_match_across_sources():
    from app.services.odds import similarity

    good = [("Man City", "Manchester City"), ("Brighton Hove", "Brighton and Hove Albion"),
            ("M'gladbach", "Borussia Monchengladbach"), ("Alavés", "Deportivo Alaves"), ("PSG", "Paris Saint-Germain"),
            ("Stuttgart", "VfB Stuttgart"), ("Atletico Madrid", "Club Atlético de Madrid"),
            ("Barça", "Barcelona"), ("HSV", "Hamburger SV"), ("Stade Rennais", "Rennes"),  # seen in real odds data
            ("SC Paderborn", "SC Paderborn")]
    for ours, theirs in good:
        assert similarity(ours, theirs) >= 0.6, (ours, theirs)
    for ours, theirs in [("Man United", "Manchester City"), ("Real Madrid", "Real Betis"), ("Arsenal", "Chelsea")]:
        assert similarity(ours, theirs) < 0.6, (ours, theirs)


def test_refresh_odds_saves_matches_and_reports_the_rest(db, monkeypatch):
    from app.db.models import OddsRow
    from app.services import odds

    when = naive_now() + timedelta(days=1)
    db.add(Fixture(id=1, league_id=39, league="PL", home_team="Man City", away_team="Arsenal", home_short="MCI",
                   away_short="ARS", kickoff=when, status="UPCOMING"))
    db.add(Fixture(id=2, league_id=39, league="PL", home_team="Chelsea", away_team="Everton", home_short="CHE",
                   away_short="EVE", kickoff=when + timedelta(hours=1), status="UPCOMING"))  # no odds for this one
    db.commit()
    asked = []

    async def fake_get_odds(key):
        asked.append(key)
        return [_event("Manchester City", "Arsenal", when + timedelta(minutes=30), [(1.8, 3.8, 4.5)])], "480"

    monkeypatch.setattr(odds, "get_odds", fake_get_odds)
    summary = asyncio.run(odds.refresh_odds(db))
    assert asked == ["soccer_epl"]  # only leagues with upcoming matches cost a credit
    assert summary["saved"] == 1 and summary["unmatched"] == ["Chelsea v Everton"] and summary["remaining"] == "480"
    row = db.get(OddsRow, 1)
    assert row.bookmakers == 1 and abs(row.prob_home + row.prob_draw + row.prob_away - 1) < 1e-9


def test_odds_public_but_model_chances_only_after_unlock(db):
    from app.db.models import OddsRow

    add_fixture(db, 1, kickoff=naive_now() + timedelta(days=1))
    db.add(OddsRow(fixture_id=1, home_odds=2.0, draw_odds=3.4, away_odds=3.9, prob_home=0.47, prob_draw=0.27,
                   prob_away=0.26, bookmakers=12))
    db.add(PredictionRecord(fixture_id=1, source="my_model", outcome="HOME", home_goals=2, away_goals=1,
                            confidence=0.5, prob_home=0.5, prob_draw=0.25, prob_away=0.25))
    db.commit()
    with TestClient(app) as client:
        anon = client.get("/api/matches").json()[0]
        assert anon["odds"] == {"home": 2.0, "draw": 3.4, "away": 3.9, "chances": {"home": 0.47, "draw": 0.27, "away": 0.26}, "bookmakers": 12}
        assert anon["predictions"] == []  # the model's chances stay locked
        me = _signup(client)
        client.post("/api/matches/1/unlock", headers=me)
        mine = client.get("/api/matches", headers=me).json()[0]
        assert mine["predictions"][0]["chances"] == {"home": 0.5, "draw": 0.25, "away": 0.25}


# ---- deployment settings ----
def test_database_urls_are_normalised_for_psycopg():
    from app.db.database import normalize_database_url as norm

    assert norm("postgresql://u:p@host/db?sslmode=require") == "postgresql+psycopg://u:p@host/db?sslmode=require"
    assert norm("postgres://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
    assert norm("postgresql+psycopg://u:p@host/db") == "postgresql+psycopg://u:p@host/db"  # already fine
    assert norm("sqlite:///./data/app.db") == "sqlite:///./data/app.db"


def test_cors_origins_come_from_settings():
    with TestClient(app) as client:
        r = client.get("/api/health", headers={"Origin": "https://example.vercel.app"})
        assert r.headers.get("access-control-allow-origin") in ("*", "https://example.vercel.app")


def test_database_url_paste_mistakes_are_forgiven():
    import pytest

    from app.db.database import normalize_database_url as norm

    good = "postgresql+psycopg://u:p@host/db?sslmode=require"
    for pasted in (
        "postgresql://u:p@host/db?sslmode=require",
        "  postgresql://u:p@host/db?sslmode=require\n",
        "'postgresql://u:p@host/db?sslmode=require'",
        '"postgresql://u:p@host/db?sslmode=require"',
        "psql 'postgresql://u:p@host/db?sslmode=require'",
        "DATABASE_URL=postgresql://u:p@host/db?sslmode=require",
    ):
        assert norm(pasted) == good, pasted
    with pytest.raises(RuntimeError, match="empty"):
        norm("   ")


def test_cors_origins_are_parsed_forgivingly():
    from app.main import parse_origins

    assert parse_origins("*") == ["*"]
    assert parse_origins("") == ["*"]
    assert parse_origins("https://a.vercel.app/") == ["https://a.vercel.app"]
    assert parse_origins('"https://a.vercel.app", https://b.com/ ') == ["https://a.vercel.app", "https://b.com"]


def test_cors_origin_without_scheme_gets_https():
    from app.main import parse_origins

    assert parse_origins("score-prediction-tau.vercel.app") == ["https://score-prediction-tau.vercel.app"]
    assert parse_origins("http://localhost:3000, app.example.com") == ["http://localhost:3000", "https://app.example.com"]

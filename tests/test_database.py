import bot


class TestInitDb:
    def test_creates_tables(self, tmp_db):
        import sqlite3
        conn = sqlite3.connect(str(tmp_db))
        tables = [row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )]
        conn.close()
        assert "event_dates" in tables
        assert "seen_posts" in tables
        assert "bt_config" in tables


class TestIsNewPost:
    def test_new_post_returns_true(self, tmp_db):
        assert bot.is_new_post("post_1") is True

    def test_duplicate_post_returns_false(self, tmp_db):
        bot.is_new_post("post_1")
        assert bot.is_new_post("post_1") is False

    def test_different_posts_unique(self, tmp_db):
        assert bot.is_new_post("post_a") is True
        assert bot.is_new_post("post_b") is True
        assert bot.is_new_post("post_a") is False


class TestEventDates:
    def test_set_and_get(self, tmp_db):
        bot.set_event_date("bt", "2026-07-20")
        assert bot.get_event_date("bt") == "2026-07-20"

    def test_get_unset_returns_none(self, tmp_db):
        assert bot.get_event_date("nonexistent") is None

    def test_overwrite_existing(self, tmp_db):
        bot.set_event_date("bt", "2026-07-20")
        bot.set_event_date("bt", "2026-07-27")
        assert bot.get_event_date("bt") == "2026-07-27"

    def test_multiple_event_types(self, tmp_db):
        bot.set_event_date("bt", "2026-07-20")
        bot.set_event_date("gt", "2026-07-24")
        assert bot.get_event_date("bt") == "2026-07-20"
        assert bot.get_event_date("gt") == "2026-07-24"


class TestBtStartDateWrappers:
    def test_get_bt_start_date_delegates(self, tmp_db):
        bot.set_event_date("bt", "2026-07-20")
        assert bot.get_bt_start_date() == "2026-07-20"

    def test_set_bt_start_date_delegates(self, tmp_db):
        bot.set_bt_start_date("2026-07-20")
        assert bot.get_event_date("bt") == "2026-07-20"

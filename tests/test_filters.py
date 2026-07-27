import bot


class TestCleanHtml:
    def test_empty_string(self):
        assert bot.clean_html("") == ""

    def test_none(self):
        assert bot.clean_html(None) == ""  # noqa: PLC0415

    def test_simple_text(self):
        assert bot.clean_html("hello world") == "hello world"

    def test_strips_html_tags(self):
        result = bot.clean_html("<p>Hello <b>World</b></p>")
        assert result == "Hello World"

    def test_collapses_whitespace(self):
        result = bot.clean_html("<div>  Hello   World  </div>")
        assert result == "Hello World"

    def test_truncates_long_text(self):
        long = "a" * 350
        result = bot.clean_html(long)
        assert len(result) == 303
        assert result.endswith("...")
        assert result.startswith("a" * 300)

    def test_short_text_not_truncated(self):
        short = "a" * 200
        result = bot.clean_html(short)
        assert result == short
        assert not result.endswith("...")

    def test_handles_complex_html(self):
        html = """
        <div class="post">
            <h2>New Gift Code</h2>
            <p>Redeem your code at <a href="#">EA site</a></p>
        </div>
        """
        result = bot.clean_html(html)
        assert "New Gift Code" in result
        assert "Redeem your code" in result
        assert "EA site" in result


class TestRssFiltering:
    """Test the inline RSS filtering logic used in scan_feeds."""

    # Equivalent of the scan_feeds filtering for a single title
    def _is_question(self, title: str) -> bool:
        return title.strip().endswith("?")

    def _has_ally(self, title: str) -> bool:
        return "ally" in title.lower()

    def _has_blacklist_word(self, title: str) -> bool:
        return any(b in title.lower() for b in bot.BLACKLIST)

    def _has_keyword(self, title: str, keywords: list) -> bool:
        return any(k in title.lower() for k in keywords)

    def test_question_title_filtered(self):
        assert self._is_question("How do I redeem this?")

    def test_non_question_title_passes(self):
        assert not self._is_question("New promo code available")

    def test_ally_code_filtered(self):
        assert self._has_ally("Share your ally code here")
        assert self._has_ally("My Ally Code is 123")

    def test_blacklist_words_filtered(self):
        assert self._has_blacklist_word("Need help with roster")
        assert self._has_blacklist_word("How to get starkiller")
        assert self._has_blacklist_word("Purchase bundle now")

    def test_clean_title_passes_blacklist(self):
        assert not self._has_blacklist_word("Free gift code for everyone")

    def test_keyword_matching(self):
        keywords = ["promo code", "gift code", "redeem", "free gift"]
        assert self._has_keyword("New promo code available", keywords)
        assert self._has_keyword("Free gift inside!", keywords)
        assert not self._has_keyword("Just a regular post", keywords)

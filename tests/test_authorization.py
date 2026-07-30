import bot


class _MockUser:
    def __init__(self, user_id: int):
        self.id = user_id


class _MockPermissions:
    def __init__(
        self, admin=False, manage_guild=False, ban_members=False, kick_members=False
    ):
        self.administrator = admin
        self.manage_guild = manage_guild
        self.ban_members = ban_members
        self.kick_members = kick_members


class _MockMember:
    def __init__(self, user_id: int, perms: _MockPermissions):
        self.id = user_id
        self.guild_permissions = perms


class _MockCtx:
    """Simula un contexto de comando de Discord."""

    def __init__(self, guild: object | None, author: _MockUser | _MockMember):
        self.guild = guild
        self.author = author


class TestIsAuthorizedInDm:
    def test_dm_authorized_user(self, monkeypatch):
        monkeypatch.setattr(bot, "ADMIN_USER_IDS", {12345, 67890})
        ctx = _MockCtx(guild=None, author=_MockUser(user_id=12345))
        assert bot.is_authorized(ctx) is True

    def test_dm_unauthorized_user(self, monkeypatch):
        monkeypatch.setattr(bot, "ADMIN_USER_IDS", {12345, 67890})
        ctx = _MockCtx(guild=None, author=_MockUser(user_id=99999))
        assert bot.is_authorized(ctx) is False

    def test_dm_empty_admin_list(self, monkeypatch):
        monkeypatch.setattr(bot, "ADMIN_USER_IDS", set())
        ctx = _MockCtx(guild=None, author=_MockUser(user_id=12345))
        assert bot.is_authorized(ctx) is False


class TestIsAuthorizedInGuild:
    def test_guild_admin_allowed(self):
        ctx = _MockCtx(
            guild=object(),
            author=_MockMember(user_id=1, perms=_MockPermissions(admin=True)),
        )
        assert bot.is_authorized(ctx) is True

    def test_guild_manage_guild_allowed(self):
        ctx = _MockCtx(
            guild=object(),
            author=_MockMember(user_id=1, perms=_MockPermissions(manage_guild=True)),
        )
        assert bot.is_authorized(ctx) is True

    def test_guild_ban_members_allowed(self):
        ctx = _MockCtx(
            guild=object(),
            author=_MockMember(user_id=1, perms=_MockPermissions(ban_members=True)),
        )
        assert bot.is_authorized(ctx) is True

    def test_guild_kick_members_allowed(self):
        ctx = _MockCtx(
            guild=object(),
            author=_MockMember(user_id=1, perms=_MockPermissions(kick_members=True)),
        )
        assert bot.is_authorized(ctx) is True

    def test_guild_no_perms_denied(self):
        ctx = _MockCtx(
            guild=object(),
            author=_MockMember(user_id=1, perms=_MockPermissions()),
        )
        assert bot.is_authorized(ctx) is False

    def test_guild_dm_whitelist_ignored_in_guild(self, monkeypatch):
        monkeypatch.setattr(bot, "ADMIN_USER_IDS", {1})
        ctx = _MockCtx(
            guild=object(),
            author=_MockMember(user_id=1, perms=_MockPermissions()),
        )
        assert bot.is_authorized(ctx) is False

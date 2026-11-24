from types import SimpleNamespace

import bot as _bot


class _MockCtx:
    """Contexto mínimo que captura mensajes y embeds enviados por los comandos."""

    def __init__(self):
        self.messages = []
        self.embeds = []
        self.author = SimpleNamespace(id=1)
        self.guild = None

    async def send(self, msg=None, embed=None):
        if msg is not None:
            self.messages.append(msg)
        if embed is not None:
            self.embeds.append(embed)


def _embed_text(embed):
    parts = [embed.title or "", embed.description or ""]
    parts.extend(str(field.value or "") for field in embed.fields)
    return "\n".join(parts)


class TestVisibleScheduleTexts:
    async def test_estado_shows_the_new_gt_hours(self, tmp_db, monkeypatch):
        ctx = _MockCtx()

        await _bot.estado.callback(ctx)

        text = "\n".join(_embed_text(embed) for embed in ctx.embeds)
        assert "GT slots 19/20/21 según fase" in text
        assert "20:00 hora de España (base; ver slots)" in text
        assert "Día  6" in text and "21:00 hora de España" in text
        assert "Día 12" in text and "19:00 hora de España" in text
        assert "17:00" not in text
        assert "18:00" not in text

    async def test_ayuda_shows_the_new_gt_hours(self, tmp_db, monkeypatch):
        monkeypatch.setattr(_bot, "ADMIN_USER_IDS", {1})
        ctx = _MockCtx()

        await _bot.ayuda.callback(ctx)

        text = "\n".join(_embed_text(embed) for embed in ctx.embeds)
        assert "Dom/Lun 21:00" in text
        assert "Mar/Mié/Jue/Vie 20:00" in text
        assert "Sáb/Dom 19:00 hora de España" in text
        assert "20:00 hora de España" in text
        assert "17:00" not in text
        assert "18:00" not in text

    async def test_avisos_iniciar_shows_the_new_gt_hours(self, tmp_db, monkeypatch):
        monkeypatch.setattr(_bot, "ADMIN_USER_IDS", {1})
        ctx = _MockCtx()

        await _bot._avisos_cmd(ctx, "iniciar", "2027-01-11")

        text = "\n".join(ctx.messages)
        assert "GT según slots (19:00/20:00/21:00)" in text
        assert "base manual 20:00 hora de España" in text
        assert "18:00" not in text

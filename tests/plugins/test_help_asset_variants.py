"""Locale/theme asset variants: the resolution chain and its fail-closed rule.

Shipped help bodies reference ONE literal asset path per figure; every locale
reads the same bytes, so a Russian page shows an English screenshot. The
resolver therefore derives variants from the same literal path:

    assets/<locale>/<theme>/<name>  ->  assets/<locale>/<name>
    ->  assets/<theme>/<name>  ->  assets/<name>  ->  None

The base path is today's behaviour and must keep working (a single-variant
recipe ships flat). A variant the manifest *declares* but that is absent is a
content bug: returning the base image there would silently show the wrong
language/theme, so the resolver returns ``None`` (the dialog's existing
placeholder path) instead.
"""

from __future__ import annotations

from pathlib import Path

from plugins.help.tree import resolve_help_asset


def _body_and_assets(tmp_path: Path) -> tuple[Path, Path]:
    """A minimal help package: ``<tmp>/help/en/page.md`` + ``<tmp>/help/assets``."""
    help_root = tmp_path / "resources" / "help"
    body = help_root / "en" / "page.md"
    body.parent.mkdir(parents=True)
    body.write_text("## Page\n", encoding="utf-8")
    assets = help_root / "assets"
    assets.mkdir()
    return body, assets


def _write(path: Path, payload: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload.encode("utf-8"))
    return path


def test_locale_variant_wins_over_the_base_image(tmp_path):
    """RED-BEFORE: the resolver ignored ``locale`` and returned the base file."""
    body, assets = _body_and_assets(tmp_path)
    base = _write(assets / "shot.png", "base")
    variant = _write(assets / "ru" / "shot.png", "ru")

    resolved = resolve_help_asset(
        "../assets/shot.png", body, locale="ru", theme="dark"
    )

    assert resolved == variant
    assert resolved != base

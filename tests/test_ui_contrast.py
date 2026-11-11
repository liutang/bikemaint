"""Design-token checks for the stylesheet (specs/002-modern-ui and specs/003-cockpit-theme).

Parses the CSS custom properties out of `app/static/styles.css` and verifies WCAG contrast in
both themes, plus the presence of the rules the UI contract requires.
"""

import re
from pathlib import Path

import pytest

STATIC = Path(__file__).parent.parent / "app" / "static"
CSS = (STATIC / "styles.css").read_text()


def _blocks(css: str) -> list[str]:
    return re.findall(r":root\s*\{([^}]*)\}", css)


def _tokens(block: str) -> dict[str, str]:
    return dict(re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", block))


def _themes() -> dict[str, dict[str, str]]:
    blocks = _blocks(CSS)
    assert len(blocks) >= 2, "expected a light :root block and a dark override block"
    light = _tokens(blocks[0])
    dark = {**light, **_tokens(blocks[1])}
    return {"light": light, "dark": dark}


def _luminance(hex_color: str) -> float:
    value = hex_color.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    channels = [int(value[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(fg: str, bg: str) -> float:
    lighter, darker = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


TEXT_PAIRS = [
    ("--text", "--bg"),
    ("--text", "--surface"),
    ("--text", "--surface-2"),
    ("--text-muted", "--surface"),
    ("--text-muted", "--bg"),
    ("--primary-text", "--primary"),
    ("--danger-text", "--danger"),
    ("--danger", "--surface"),
    ("--link", "--surface"),
    ("--link", "--bg"),
    ("--badge-overdue-fg", "--badge-overdue-bg"),
    ("--badge-soon-fg", "--badge-soon-bg"),
    ("--badge-ok-fg", "--badge-ok-bg"),
    ("--badge-low-fg", "--badge-low-bg"),
]

GRAPHIC_PAIRS = [
    ("--ring-overdue", "--surface"),
    ("--ring-soon", "--surface"),
    ("--ring-ok", "--surface"),
]


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("fg,bg", TEXT_PAIRS)
def test_text_contrast_meets_wcag_aa(theme, fg, bg):
    tokens = _themes()[theme]
    ratio = contrast(tokens[fg], tokens[bg])
    assert ratio >= 4.5, f"{theme}: {fg} on {bg} is {ratio:.2f}:1 (needs 4.5:1)"


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("fg,bg", GRAPHIC_PAIRS)
def test_ring_colors_are_visible_graphics(theme, fg, bg):
    tokens = _themes()[theme]
    assert contrast(tokens[fg], tokens[bg]) >= 3.0, f"{theme}: {fg} on {bg}"


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_ring_track_is_distinguishable_from_the_surface(theme):
    tokens = _themes()[theme]
    assert contrast(tokens["--ring-track"], tokens["--surface"]) >= 1.15


def _hue(hex_color: str) -> float:
    import colorsys

    value = hex_color.strip().lstrip("#")
    r, g, b = (int(value[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return colorsys.rgb_to_hls(r, g, b)[0] * 360


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_due_soon_gold_is_visibly_different_from_the_brand_accent(theme):
    tokens = _themes()[theme]
    assert abs(_hue(tokens["--ring-soon"]) - _hue(tokens["--primary"])) >= 8


def test_brand_accent_and_dark_charcoal_values():
    light, dark = _themes()["light"], _themes()["dark"]
    assert light["--primary"].lower() == dark["--primary"].lower() == "#ffa800"
    assert dark["--bg"].lower() == "#1b1e25"  # softened charcoal, never near-black
    assert _luminance(dark["--bg"]) > _luminance("#0d0f12")
    assert light["--bg"].lower() == "#f2f4f8"
    assert contrast(light["--primary-text"], light["--primary"]) >= 7


def test_fonts_are_self_hosted():
    assert CSS.count("@font-face") >= 2
    assert "http://" not in CSS and "https://" not in CSS
    assert "Space Grotesk" in CSS and "Inter" in CSS
    for name in re.findall(r"url\(['\"]?([^'\")]+)['\"]?\)", CSS):
        assert (STATIC / name.removeprefix("/static/")).exists(), f"missing font file {name}"


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_focus_ring_is_visible_against_the_page(theme):
    tokens = _themes()[theme]
    assert contrast(tokens["--focus"], tokens["--bg"]) >= 3.0
    assert contrast(tokens["--focus"], tokens["--surface"]) >= 3.0


def test_design_token_families_exist():
    light = _themes()["light"]
    for name in ("--space-1", "--space-2", "--space-4", "--radius", "--shadow", "--font-size-base",
                 "--font-size-lg", "--font-size-sm", "--tap-min"):
        assert name in light, f"missing token {name}"


def test_required_rules_are_present():
    assert "color-scheme: light dark" in CSS
    assert "@media (prefers-color-scheme: dark)" in CSS
    assert "@media (prefers-reduced-motion: reduce)" in CSS
    assert ":focus-visible" in CSS


def test_tap_targets_use_the_minimum_size_token():
    light = _themes()["light"]
    assert float(light["--tap-min"].replace("rem", "")) >= 2.75
    for selector in (r"\.btn\s*\{", r"\.app-header nav a\s*\{"):
        match = re.search(selector + r"([^}]*)\}", CSS)
        assert match, f"no rule for {selector}"
        assert "min-height: var(--tap-min)" in match.group(1)


def test_long_text_wraps_instead_of_breaking_the_layout():
    assert "overflow-wrap: anywhere" in CSS
    assert "min-width: 0" in CSS


def test_asset_budget():
    css_size = (STATIC / "styles.css").stat().st_size
    font_size = sum(p.stat().st_size for p in (STATIC / "fonts").glob("*.woff2"))
    assert css_size <= 40 * 1024
    assert css_size + font_size <= 250 * 1024

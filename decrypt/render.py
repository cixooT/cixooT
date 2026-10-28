import random
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from xml.sax.saxutils import escape, quoteattr

from .contributions import Day
from .themes import Theme

CELL = 14
GAP = 3
STEP = CELL + GAP
PADDING = 24
TITLE_BAR = 28
GRID_TOP = 74
FOOTER = 58
WEEKDAYS = 7

HEX_DIGITS = "0123456789ABCDEF"
FLICKER_PERIOD = 0.9
WINDOW_CONTROLS = ("#ff5f56", "#ffbd2e", "#27c93f")
FONT_STACK = "'JetBrains Mono','Fira Code',Consolas,monospace"

BANNER_WIDTH = 300
BANNER_HEIGHT = 64


@dataclass(frozen=True, slots=True)
class Timeline:
    duration: float = 12.0
    wave_start: float = 1.5
    wave_end: float = 6.5
    banner_start: float = 7.0
    banner_end: float = 10.6
    reset: float = 11.0
    fade: float = 0.6
    cipher_fade: float = 0.15
    flash: float = 0.08
    settle: float = 0.45

    def at(self, seconds: float) -> str:
        return f"{seconds / self.duration * 100:.2f}%"

    def reveal(self, column: int, columns: int) -> float:
        progress = column / max(columns - 1, 1)
        return self.wave_start + (self.wave_end - self.wave_start) * progress


def element(tag: str, content: str = "", **attributes: object) -> str:
    attrs = "".join(
        f" {name.rstrip('_').replace('_', '-')}={quoteattr(str(value))}"
        for name, value in attributes.items()
    )
    return f"<{tag}{attrs}>{content}</{tag}>" if content else f"<{tag}{attrs}/>"


def keyframes(name: str, frames: Mapping[str, str]) -> str:
    body = "".join(f"{offset}{{{style}}}" for offset, style in frames.items())
    return f"@keyframes {name}{{{body}}}"


class DecryptAnimation:
    def __init__(
        self,
        user: str,
        days: list[Day],
        theme: Theme,
        timeline: Timeline | None = None,
        seed: str | None = None,
    ) -> None:
        self.user = user
        self.days = days
        self.theme = theme
        self.timeline = timeline or Timeline()
        self.random = random.Random(seed)
        self.columns = max(day.column for day in days) + 1
        self.width = PADDING * 2 + self.columns * STEP - GAP
        self.grid_height = WEEKDAYS * STEP - GAP
        self.height = GRID_TOP + self.grid_height + FOOTER

    def render(self) -> str:
        body = "".join(
            (
                self._style(),
                self._window(),
                self._header(),
                self._grid(),
                self._scanner(),
                self._footer(),
                self._banner(),
            )
        )
        return element(
            "svg",
            body,
            xmlns="http://www.w3.org/2000/svg",
            width=self.width,
            height=self.height,
            viewBox=f"0 0 {self.width} {self.height}",
        )

    def _animation(self, name: str, timing: str = "linear") -> str:
        return f"animation:{name} {self.timeline.duration}s {timing} infinite"

    def _style(self) -> str:
        theme = self.theme
        rules = [
            f"text{{font-family:{FONT_STACK}}}",
            f".cipher{{font-size:10px;font-weight:700;fill:{theme.cipher};text-anchor:middle}}",
            f".flicker{{animation:flicker {FLICKER_PERIOD}s steps(1) infinite}}",
            ".flicker.alt{animation-direction:reverse}",
            keyframes("flicker", {"0%": "opacity:1", "50%": "opacity:0"}),
            ".cursor{animation:blink 1s steps(1) infinite}",
            keyframes("blink", {"0%,49%": "opacity:1", "50%,100%": "opacity:0"}),
            *self._column_rules(),
            *self._scanner_rules(),
            *self._progress_rules(),
            *self._status_rules(),
            *self._banner_rules(),
        ]
        return element("style", "".join(rules))

    def _column_rules(self) -> Iterator[str]:
        tl = self.timeline
        restore = f"{tl.at(tl.reset + tl.fade)},100%"
        for column in range(self.columns):
            start = tl.reveal(column, self.columns)
            yield keyframes(
                f"hide{column}",
                {
                    f"0%,{tl.at(start)}": "opacity:1",
                    f"{tl.at(start + tl.cipher_fade)},{tl.at(tl.reset)}": "opacity:0",
                    restore: "opacity:1",
                },
            )
            yield keyframes(
                f"show{column}",
                {
                    f"0%,{tl.at(start)}": "opacity:0",
                    tl.at(start + tl.flash): "opacity:1;filter:brightness(2.2)",
                    f"{tl.at(start + tl.settle)},{tl.at(tl.reset)}": "opacity:1;filter:none",
                    restore: "opacity:0",
                },
            )
            yield f".hide{column}{{{self._animation(f'hide{column}')}}}"
            yield f".show{column}{{{self._animation(f'show{column}')}}}"

    def _scanner_rules(self) -> Iterator[str]:
        tl = self.timeline
        start = f"translateX({PADDING}px)"
        end = f"translateX({PADDING + (self.columns - 1) * STEP + CELL}px)"
        yield keyframes(
            "scan",
            {
                f"0%,{tl.at(tl.wave_start)}": f"transform:{start};opacity:0",
                tl.at(tl.wave_start + 0.1): "opacity:1",
                tl.at(tl.wave_end): f"transform:{end};opacity:1",
                f"{tl.at(tl.wave_end + 0.2)},100%": f"transform:{end};opacity:0",
            },
        )
        yield f".scanner{{{self._animation('scan')}}}"

    def _progress_rules(self) -> Iterator[str]:
        tl = self.timeline
        yield keyframes(
            "progress",
            {
                f"0%,{tl.at(tl.wave_start)}": "transform:scaleX(0)",
                f"{tl.at(tl.wave_end)},{tl.at(tl.reset)}": "transform:scaleX(1)",
                f"{tl.at(tl.reset + tl.fade)},100%": "transform:scaleX(0)",
            },
        )
        yield f".progress{{transform-origin:{PADDING}px 0;{self._animation('progress')}}}"

    def _status_rules(self) -> Iterator[str]:
        tl = self.timeline
        done = f"{tl.at(tl.wave_end + 0.1)},{tl.at(tl.reset + 0.5)}"
        running = f"0%,{tl.at(tl.wave_end)}"
        restart = f"{tl.at(tl.reset + tl.fade)},100%"
        for name, visible in (("running", True), ("done", False)):
            shown, hidden = ("opacity:1", "opacity:0") if visible else ("opacity:0", "opacity:1")
            yield keyframes(f"status-{name}", {running: shown, done: hidden, restart: shown})
            yield f".status-{name}{{{self._animation(f'status-{name}', 'steps(1)')}}}"

    def _banner_rules(self) -> Iterator[str]:
        tl = self.timeline
        yield keyframes(
            "banner",
            {
                f"0%,{tl.at(tl.banner_start)}": "opacity:0;transform:scale(1.25)",
                tl.at(tl.banner_start + 0.25): "opacity:1;transform:scale(1)",
                tl.at(tl.banner_start + 0.45): "opacity:.35",
                tl.at(tl.banner_start + 0.6): "opacity:1",
                tl.at(tl.banner_end): "opacity:1;transform:scale(1)",
                f"{tl.at(tl.banner_end + 0.3)},100%": "opacity:0;transform:scale(1)",
            },
        )
        yield (
            ".banner{transform-box:fill-box;transform-origin:center;"
            f"{self._animation('banner', 'ease-out')}}}"
        )

    def _window(self) -> str:
        theme = self.theme
        width = self.width
        divider = TITLE_BAR + 0.5
        controls = "".join(
            element("circle", cx=18 + 16 * index, cy=15, r=5, fill=color)
            for index, color in enumerate(WINDOW_CONTROLS)
        )
        return "".join(
            (
                element(
                    "rect",
                    x=0.5,
                    y=0.5,
                    width=width - 1,
                    height=self.height - 1,
                    rx=10,
                    fill=theme.background,
                    stroke=theme.border,
                ),
                element(
                    "path",
                    d=f"M.5 10.5a10 10 0 0 1 10-10h{width - 21}a10 10 0 0 1 10 10"
                    f"v{TITLE_BAR - 10}h-{width - 1}z",
                    fill=theme.title_bar,
                ),
                element(
                    "line", x1=0.5, y1=divider, x2=width - 0.5, y2=divider, stroke=theme.border
                ),
                controls,
                element(
                    "text",
                    escape(f"{self.user}@github: ~/contributions"),
                    x=width / 2,
                    y=19,
                    font_size=11,
                    fill=theme.muted,
                    text_anchor="middle",
                ),
            )
        )

    def _header(self) -> str:
        theme = self.theme
        command = element("tspan", "$", fill=theme.accent) + escape(
            f" ./decrypt --key {self.user} contributions.enc"
        )
        running = escape("[*] decrypting AES-256 blocks...") + element(
            "tspan", "_", class_="cursor"
        )
        return "".join(
            (
                element("text", command, x=PADDING, y=50, font_size=12, fill=theme.text),
                element(
                    "text",
                    running,
                    class_="status-running",
                    x=PADDING,
                    y=65,
                    font_size=11,
                    fill=theme.muted,
                ),
                element(
                    "text",
                    "[+] decryption complete — 0 errors",
                    class_="status-done",
                    x=PADDING,
                    y=65,
                    font_size=11,
                    fill=theme.accent,
                ),
            )
        )

    def _grid(self) -> str:
        return "".join(self._cell(day) for day in self.days)

    def _cell(self, day: Day) -> str:
        x = PADDING + day.column * STEP
        y = GRID_TOP + day.row * STEP
        box = {"x": x, "y": y, "width": CELL, "height": CELL, "rx": 3}
        layers = [element("rect", **box, fill=self.theme.levels[0])]
        if day.level:
            layers.append(
                element(
                    "rect", **box, class_=f"show{day.column}", fill=self.theme.levels[day.level]
                )
            )
        layers.append(self._cipher(x + CELL / 2, y + CELL - 3.5, day.column))
        return "".join(layers)

    def _cipher(self, x: float, y: float, column: int) -> str:
        delay = f"animation-delay:-{self.random.random() * FLICKER_PERIOD:.2f}s"
        glyphs = "".join(
            element(
                "text",
                self.random.choice(HEX_DIGITS),
                class_=f"cipher flicker{variant}",
                x=x,
                y=y,
                style=delay,
            )
            for variant in ("", " alt")
        )
        return element("g", glyphs, class_=f"hide{column}")

    def _scanner(self) -> str:
        return element(
            "rect",
            class_="scanner",
            x=0,
            y=GRID_TOP - 4,
            width=3,
            height=self.grid_height + 8,
            fill=self.theme.accent,
            opacity=0,
        )

    def _footer(self) -> str:
        theme = self.theme
        top = GRID_TOP + self.grid_height + 18
        track = {"x": PADDING, "y": top, "width": self.width - PADDING * 2, "height": 6, "rx": 3}
        return "".join(
            (
                element("rect", **track, fill=theme.levels[0]),
                element("rect", **track, class_="progress", fill=theme.accent),
                element(
                    "text",
                    escape(f"cipher: AES-256-GCM · source: github.com/{self.user}"),
                    x=PADDING,
                    y=top + 24,
                    font_size=10,
                    fill=theme.muted,
                ),
            )
        )

    def _banner(self) -> str:
        theme = self.theme
        center = self.width / 2
        left = (self.width - BANNER_WIDTH) / 2
        top = GRID_TOP + (self.grid_height - BANNER_HEIGHT) / 2
        content = "".join(
            (
                element(
                    "rect",
                    x=left,
                    y=top,
                    width=BANNER_WIDTH,
                    height=BANNER_HEIGHT,
                    rx=8,
                    fill=theme.background,
                    fill_opacity=0.92,
                    stroke=theme.accent,
                    stroke_width=2,
                ),
                element(
                    "text",
                    "ACCESS GRANTED",
                    x=center,
                    y=top + 32,
                    font_size=24,
                    font_weight=700,
                    fill=theme.accent,
                    text_anchor="middle",
                    letter_spacing=3,
                ),
                element(
                    "text",
                    "welcome, visitor · identity verified",
                    x=center,
                    y=top + 51,
                    font_size=10,
                    fill=theme.muted,
                    text_anchor="middle",
                ),
            )
        )
        return element("g", content, class_="banner", opacity=0)

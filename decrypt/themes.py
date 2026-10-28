from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Theme:
    background: str
    border: str
    title_bar: str
    text: str
    muted: str
    accent: str
    cipher: str
    levels: tuple[str, str, str, str, str]


DARK = Theme(
    background="#0d1117",
    border="#30363d",
    title_bar="#161b22",
    text="#c9d1d9",
    muted="#8b949e",
    accent="#39d353",
    cipher="#2ea043",
    levels=("#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"),
)

LIGHT = Theme(
    background="#ffffff",
    border="#d0d7de",
    title_bar="#f6f8fa",
    text="#24292f",
    muted="#57606a",
    accent="#1a7f37",
    cipher="#1a7f37",
    levels=("#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"),
)

import argparse
import sys
from datetime import date
from pathlib import Path

from .contributions import CalendarError, fetch_calendar
from .render import DecryptAnimation
from .themes import DARK, LIGHT

OUTPUTS = {
    "decrypt.svg": LIGHT,
    "decrypt-dark.svg": DARK,
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="decrypt",
        description="Render a decrypt-style animation of a GitHub contribution calendar.",
    )
    parser.add_argument("user", help="GitHub username")
    parser.add_argument("-o", "--output", type=Path, default=Path("dist"), help="output directory")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        days = fetch_calendar(args.user)
    except CalendarError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    args.output.mkdir(parents=True, exist_ok=True)
    seed = f"{args.user}:{date.today().isoformat()}"
    for filename, theme in OUTPUTS.items():
        svg = DecryptAnimation(args.user, days, theme, seed=seed).render()
        (args.output / filename).write_text(svg, encoding="utf-8")

    print(f"Rendered {len(days)} days for {args.user} into {args.output}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())

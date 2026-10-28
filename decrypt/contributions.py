import re
import urllib.request
from dataclasses import dataclass

CALENDAR_URL = "https://github.com/users/{user}/contributions"
USER_AGENT = "decrypt-animation"

DAY_TAG = re.compile(r"<td[^>]*ContributionCalendar-day[^>]*>")
DAY_POSITION = re.compile(r'id="contribution-day-component-(\d+)-(\d+)"')
DAY_LEVEL = re.compile(r'data-level="([0-4])"')


class CalendarError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Day:
    row: int
    column: int
    level: int


def fetch_calendar(user: str, timeout: float = 30.0) -> list[Day]:
    request = urllib.request.Request(
        CALENDAR_URL.format(user=user),
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        html = response.read().decode("utf-8")

    days = parse_calendar(html)
    if not days:
        raise CalendarError(f"No contribution data found for '{user}'")
    return days


def parse_calendar(html: str) -> list[Day]:
    days = []
    for tag in DAY_TAG.findall(html):
        position = DAY_POSITION.search(tag)
        level = DAY_LEVEL.search(tag)
        if position and level:
            days.append(Day(row=int(position[1]), column=int(position[2]), level=int(level[1])))
    return sorted(days, key=lambda day: (day.column, day.row))

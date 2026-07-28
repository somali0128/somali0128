#!/usr/bin/env python3
"""Generate a dependency-free GitHub contribution streak SVG."""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


API_URL = "https://api.github.com/graphql"
QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
      }
    }
  }
}
"""
YEARS_QUERY = """
query($login: String!) {
  user(login: $login) { contributionsCollection { contributionYears } }
}
"""


def fetch_years(login: str, token: str) -> list[int]:
    payload = json.dumps({"query": YEARS_QUERY, "variables": {"login": login}}).encode()
    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "profile-streak-generator",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError(result["errors"])
    return result["data"]["user"]["contributionsCollection"]["contributionYears"]


def fetch_year(login: str, token: str, year: int) -> tuple[dict[date, int], int]:
    start = datetime(year, 1, 1, tzinfo=timezone.utc)
    end = min(datetime(year + 1, 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1), datetime.now(timezone.utc))
    payload = json.dumps(
        {
            "query": QUERY,
            "variables": {
                "login": login,
                "from": start.isoformat().replace("+00:00", "Z"),
                "to": end.isoformat().replace("+00:00", "Z"),
            },
        }
    ).encode()
    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "profile-streak-generator",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError(result["errors"])
    calendar = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = {
        date.fromisoformat(day["date"]): day["contributionCount"]
        for week in calendar["weeks"]
        for day in week["contributionDays"]
    }
    return days, calendar["totalContributions"]


def streaks(days: dict[date, int]) -> tuple[int, date | None, date | None, int, date | None, date | None]:
    active = sorted(day for day, count in days.items() if count > 0)
    if not active:
        return 0, None, None, 0, None, None

    longest = 1
    longest_start = longest_end = run_start = previous = active[0]
    run_length = 1
    for day in active[1:]:
        if day == previous + timedelta(days=1):
            run_length += 1
        else:
            run_start = day
            run_length = 1
        if run_length > longest:
            longest = run_length
            longest_start, longest_end = run_start, day
        previous = day

    today = date.today()
    current_end = today if days.get(today, 0) > 0 else today - timedelta(days=1)
    cursor = current_end
    current = 0
    while days.get(cursor, 0) > 0:
        current += 1
        cursor -= timedelta(days=1)
    current_start = cursor + timedelta(days=1) if current else None
    return current, current_start, current_end if current else None, longest, longest_start, longest_end


def date_range(start: date | None, end: date | None) -> str:
    if not start or not end:
        return "No active streak"
    if start.year == end.year:
        return f"{start:%b} {start.day} - {end:%b} {end.day}, {end.year}"
    return f"{start:%b} {start.day}, {start.year} - {end:%b} {end.day}, {end.year}"


def render(total: int, current: int, current_dates: str, longest: int, longest_dates: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="495" height="195" viewBox="0 0 495 195" role="img" aria-label="GitHub contribution streak">
  <style>
    .value {{ fill: #ffffff; font: 600 28px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; text-anchor: middle }}
    .label {{ fill: #60a5fa; font: 600 14px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; text-anchor: middle }}
    .date {{ fill: #8b949e; font: 11px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; text-anchor: middle }}
  </style>
  <rect width="495" height="195" rx="6" fill="#0D1117"/>
  <path d="M165 35v125M330 35v125" stroke="#30363d"/>
  <g transform="translate(82.5 0)">
    <text class="value" y="82">{total:,}</text>
    <text class="label" y="110">Total Contributions</text>
    <text class="date" y="132">Public contributions</text>
  </g>
  <g transform="translate(247.5 0)">
    <circle cx="0" cy="75" r="38" fill="none" stroke="#3b82f6" stroke-width="3"/>
    <text class="value" y="84">{current}</text>
    <text class="label" y="130">Current Streak</text>
    <text class="date" y="151">{current_dates}</text>
  </g>
  <g transform="translate(412.5 0)">
    <text class="value" y="82">{longest}</text>
    <text class="label" y="110">Longest Streak</text>
    <text class="date" y="132">{longest_dates}</text>
  </g>
</svg>
'''


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: generate_streak.py OUTPUT.svg")
    login = os.environ["GITHUB_USER"]
    token = os.environ["GH_TOKEN"]
    all_days: dict[date, int] = {}
    total = 0
    for year in fetch_years(login, token):
        days, year_total = fetch_year(login, token, year)
        all_days.update(days)
        total += year_total
    current, current_start, current_end, longest, longest_start, longest_end = streaks(all_days)
    output = Path(sys.argv[1])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        render(total, current, date_range(current_start, current_end), longest, date_range(longest_start, longest_end)),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

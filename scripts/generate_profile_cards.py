#!/usr/bin/env python3
"""Generate lightweight profile SVG cards from GitHub's public REST API."""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from collections import Counter
from html import escape
from pathlib import Path


API_URL = "https://api.github.com"
LANGUAGE_COLORS = {
    "TypeScript": "#3178c6",
    "JavaScript": "#f1e05a",
    "Python": "#3572A5",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Vue": "#41b883",
    "Shell": "#89e051",
}


def github_get(path: str) -> object:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "somali0128-profile-assets",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{API_URL}{path}", headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def svg_shell(width: int, height: int, body: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img">
<style>
  text {{ font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
  .title {{ font-size: 18px; font-weight: 600; fill: #70a5fd; }}
  .label {{ font-size: 14px; fill: #c3e88d; }}
  .value {{ font-size: 14px; font-weight: 600; fill: #ffffff; }}
  .muted {{ font-size: 12px; fill: #a9b1d6; }}
</style>
<rect width="100%" height="100%" rx="8" fill="#1a1b27" stroke="#2f3549"/>
{body}
</svg>
"""


def stats_card(user: dict[str, object], repos: list[dict[str, object]]) -> str:
    stars = sum(int(repo.get("stargazers_count", 0)) for repo in repos)
    values = [
        ("Public repositories", int(user["public_repos"])),
        ("Followers", int(user["followers"])),
        ("Total stars", stars),
        ("Following", int(user["following"])),
    ]
    rows = "\n".join(
        f'<text x="28" y="{72 + index * 27}" class="label">{escape(label)}</text>'
        f'<text x="455" y="{72 + index * 27}" text-anchor="end" class="value">{value:,}</text>'
        for index, (label, value) in enumerate(values)
    )
    body = (
        '<text x="28" y="38" class="title">GitHub Stats</text>'
        f'<text x="467" y="38" text-anchor="end" class="muted">@{escape(str(user["login"]))}</text>'
        f"{rows}"
    )
    return svg_shell(495, 195, body)


def languages_card(repos: list[dict[str, object]]) -> str:
    counts = Counter(
        str(repo["language"])
        for repo in repos
        if repo.get("language") and not repo.get("fork")
    )
    languages = counts.most_common(5)
    total = sum(count for _, count in languages) or 1
    rows: list[str] = []
    for index, (language, count) in enumerate(languages):
        y = 67 + index * 25
        width = max(8, round(190 * count / total))
        color = LANGUAGE_COLORS.get(language, "#7aa2f7")
        rows.append(
            f'<circle cx="24" cy="{y - 5}" r="5" fill="{color}"/>'
            f'<text x="38" y="{y}" class="label">{escape(language)}</text>'
            f'<rect x="142" y="{y - 12}" width="{width}" height="9" rx="4" fill="{color}"/>'
            f'<text x="338" y="{y}" text-anchor="end" class="muted">{count} repos</text>'
        )
    body = '<text x="24" y="36" class="title">Top Languages</text>' + "\n".join(rows)
    return svg_shell(360, 200, body)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    user = github_get(f"/users/{args.username}")
    repos = github_get(f"/users/{args.username}/repos?per_page=100&type=owner&sort=updated")
    if not isinstance(user, dict) or not isinstance(repos, list):
        raise RuntimeError("GitHub returned an unexpected response")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "github-stats.svg").write_text(
        stats_card(user, repos), encoding="utf-8"
    )
    (args.output_dir / "top-languages.svg").write_text(
        languages_card(repos), encoding="utf-8"
    )


if __name__ == "__main__":
    main()

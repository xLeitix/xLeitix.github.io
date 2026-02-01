#!/usr/bin/env python3
"""Generate _pages/bibliometrics.md from scholar_profile_cleaned.csv."""

import csv
import json
import os
from collections import defaultdict
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(SCRIPT_DIR, "scholar_profile_cleaned.csv")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", "_pages", "bibliometrics.md")
OVERRIDES_PATH = os.path.join(SCRIPT_DIR, "data", "conference_ranking_overrides.json")


def load_ranking_overrides():
    """Load CORE ranking overrides from JSON file."""
    try:
        with open(OVERRIDES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k.lower(): v for k, v in data.get("overrides", {}).items()}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def apply_ranking_overrides(rows, overrides):
    """Apply ranking overrides to rows in-place based on venue substring match."""
    for r in rows:
        venue_lower = r.get("venue", "").lower()
        for substr, ranking in overrides.items():
            if substr in venue_lower:
                r["ranking"] = ranking
                break


def read_csv():
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def compute_metrics(rows):
    total_pubs = len(rows)
    citations = [int(r["citations"]) if r["citations"].strip() else 0 for r in rows]
    total_citations = sum(citations)

    # h-index
    sorted_desc = sorted(citations, reverse=True)
    h_index = 0
    for i, c in enumerate(sorted_desc, 1):
        if c >= i:
            h_index = i
        else:
            break

    # i10-index
    i10_index = sum(1 for c in citations if c >= 10)

    return total_pubs, total_citations, h_index, i10_index


def citations_by_year(rows):
    by_year = defaultdict(int)
    for r in rows:
        yr = r["year"].strip()
        if yr:
            cites = int(r["citations"]) if r["citations"].strip() else 0
            by_year[int(yr)] += cites
    return dict(sorted(by_year.items()))


def pubs_by_year(rows):
    by_year = defaultdict(int)
    for r in rows:
        yr = r["year"].strip()
        if yr:
            by_year[int(yr)] += 1
    return dict(sorted(by_year.items()))


def type_distribution(rows):
    counts = defaultdict(int)
    for r in rows:
        t = r["type"].strip()
        if t:
            counts[t] += 1
    order = ["Conference", "Journal", "Workshop", "Book Chapter"]
    return {k: counts.get(k, 0) for k in order if counts.get(k, 0) > 0}


def venue_ranking_distribution(rows):
    counts = defaultdict(int)
    for r in rows:
        if r["type"].strip() == "Conference":
            rank = r["ranking"].strip()
            if rank in ("A*", "A", "B", "C"):
                counts[rank] += 1
            else:
                counts["Unranked"] += 1
    order = ["A*", "A", "B", "C", "Unranked"]
    return {k: counts.get(k, 0) for k in order}


def top_cited(rows, n=10):
    papers = []
    for r in rows:
        cites = int(r["citations"]) if r["citations"].strip() else 0
        title = r["title"].strip()
        yr = r["year"].strip()
        papers.append((title, yr, cites))
    papers.sort(key=lambda x: x[2], reverse=True)
    result = []
    for title, yr, cites in papers[:n]:
        if len(title) > 45:
            title = title[:42] + "..."
        label = f"{title} ({yr})"
        result.append((label, cites))
    return result


def format_number(n):
    """Format number with commas: 7768 -> 7,768."""
    return f"{n:,}"


def generate_markdown(rows):
    total_pubs, total_citations, h_index, i10_index = compute_metrics(rows)
    cit_year = citations_by_year(rows)
    pub_year = pubs_by_year(rows)
    type_dist = type_distribution(rows)
    venue_dist = venue_ranking_distribution(rows)
    top10 = top_cited(rows)

    today = date.today().strftime("%B %Y")
    conf_count = type_dist.get("Conference", 0)

    # Chart data helpers
    def bar_chart(labels, data, dataset_label, bg, border, y_title, x_title, extra_y=None):
        y_opts = {"beginAtZero": True, "title": {"display": True, "text": y_title}}
        if extra_y:
            y_opts.update(extra_y)
        chart = {
            "type": "bar",
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": dataset_label,
                    "data": data,
                    "backgroundColor": bg,
                    "borderColor": border,
                    "borderWidth": 1,
                }],
            },
            "options": {
                "responsive": True,
                "plugins": {"legend": {"display": False}},
                "scales": {
                    "y": y_opts,
                    "x": {"title": {"display": True, "text": x_title}},
                },
            },
        }
        return json.dumps(chart, indent=2)

    cit_labels = [str(y) for y in cit_year]
    cit_data = list(cit_year.values())
    cit_chart = bar_chart(
        cit_labels, cit_data, "Total Citations",
        "rgba(54, 162, 235, 0.7)", "rgba(54, 162, 235, 1)",
        "Citations", "Publication Year",
    )

    pub_labels = [str(y) for y in pub_year]
    pub_data = list(pub_year.values())
    pub_chart = bar_chart(
        pub_labels, pub_data, "Publications",
        "rgba(75, 192, 192, 0.7)", "rgba(75, 192, 192, 1)",
        "Number of Papers", "Year",
        extra_y={"ticks": {"stepSize": 2}},
    )

    # Doughnut chart for type distribution
    type_labels = list(type_dist.keys())
    type_data = list(type_dist.values())
    type_bg = [
        "rgba(54, 162, 235, 0.8)",
        "rgba(255, 99, 132, 0.8)",
        "rgba(255, 206, 86, 0.8)",
        "rgba(153, 102, 255, 0.8)",
    ][:len(type_labels)]
    type_border = [
        "rgba(54, 162, 235, 1)",
        "rgba(255, 99, 132, 1)",
        "rgba(255, 206, 86, 1)",
        "rgba(153, 102, 255, 1)",
    ][:len(type_labels)]
    type_chart = json.dumps({
        "type": "doughnut",
        "data": {
            "labels": type_labels,
            "datasets": [{
                "data": type_data,
                "backgroundColor": type_bg,
                "borderColor": type_border,
                "borderWidth": 1,
            }],
        },
        "options": {
            "responsive": True,
            "plugins": {"legend": {"position": "bottom"}},
        },
    }, indent=2)

    # Venue ranking bar chart
    venue_labels = list(venue_dist.keys())
    venue_data = list(venue_dist.values())
    venue_bg = [
        "rgba(255, 99, 132, 0.8)",
        "rgba(255, 159, 64, 0.8)",
        "rgba(255, 206, 86, 0.8)",
        "rgba(75, 192, 192, 0.8)",
        "rgba(201, 203, 207, 0.8)",
    ]
    venue_border = [
        "rgba(255, 99, 132, 1)",
        "rgba(255, 159, 64, 1)",
        "rgba(255, 206, 86, 1)",
        "rgba(75, 192, 192, 1)",
        "rgba(201, 203, 207, 1)",
    ]
    venue_chart = json.dumps({
        "type": "bar",
        "data": {
            "labels": venue_labels,
            "datasets": [{
                "label": "Papers",
                "data": venue_data,
                "backgroundColor": venue_bg,
                "borderColor": venue_border,
                "borderWidth": 1,
            }],
        },
        "options": {
            "responsive": True,
            "plugins": {"legend": {"display": False}},
            "scales": {
                "y": {"beginAtZero": True, "title": {"display": True, "text": "Number of Papers"}},
                "x": {"title": {"display": True, "text": "CORE Ranking"}},
            },
        },
    }, indent=2)

    # Top 10 horizontal bar
    top_labels = [t[0] for t in top10]
    top_data = [t[1] for t in top10]
    top_chart = json.dumps({
        "type": "bar",
        "data": {
            "labels": top_labels,
            "datasets": [{
                "label": "Citations",
                "data": top_data,
                "backgroundColor": "rgba(255, 99, 132, 0.7)",
                "borderColor": "rgba(255, 99, 132, 1)",
                "borderWidth": 1,
            }],
        },
        "options": {
            "indexAxis": "y",
            "responsive": True,
            "plugins": {"legend": {"display": False}},
            "scales": {
                "x": {"beginAtZero": True, "title": {"display": True, "text": "Citations"}},
            },
        },
    }, indent=2)

    md = f"""---
layout: page
permalink: /bibliometrics/
title: bibliometrics
description: Bibliometric analysis based on Google Scholar data.
nav: false
nav_order: 3
chart:
  chartjs: true
---

The following is a bibliometric summary of my research output, based on data from [Google Scholar](https://scholar.google.com/citations?user=OGkMwEoAAAAJ) as of {today}. Bibliometrics provide a quantitative lens on research impact, productivity, and collaboration patterns. While no single metric captures the full picture, together they offer a useful overview of how research has been received and where it has had the most influence.

## Key Metrics

<div class="row row-cols-2 row-cols-md-4 g-3 mb-4">
  <div class="col">
    <div class="card text-center h-100">
      <div class="card-body">
        <h5 class="card-title" style="font-size: 2rem; font-weight: 700;">{format_number(total_pubs)}</h5>
        <p class="card-text text-muted">Publications</p>
      </div>
    </div>
  </div>
  <div class="col">
    <div class="card text-center h-100">
      <div class="card-body">
        <h5 class="card-title" style="font-size: 2rem; font-weight: 700;">{format_number(total_citations)}</h5>
        <p class="card-text text-muted">Total Citations</p>
      </div>
    </div>
  </div>
  <div class="col">
    <div class="card text-center h-100">
      <div class="card-body">
        <h5 class="card-title" style="font-size: 2rem; font-weight: 700;">{format_number(h_index)}</h5>
        <p class="card-text text-muted">H-Index</p>
      </div>
    </div>
  </div>
  <div class="col">
    <div class="card text-center h-100">
      <div class="card-body">
        <h5 class="card-title" style="font-size: 2rem; font-weight: 700;">{format_number(i10_index)}</h5>
        <p class="card-text text-muted">i10-Index</p>
      </div>
    </div>
  </div>
</div>

## Citations by Publication Year

This chart shows the total citations accumulated by papers published in each year. It highlights which "vintages" of papers have had the most impact so far.

```chartjs
{cit_chart}
```

## Publications per Year

Research output over time, showing the number of peer-reviewed papers published each year from {pub_labels[0]} to {pub_labels[-1]}.

```chartjs
{pub_chart}
```

## Publication Type Distribution

Breakdown of all {total_pubs} publications by type.

```chartjs
{type_chart}
```

## Venue Ranking Distribution

Distribution of the {conf_count} conference papers by [CORE conference ranking](https://www.core.edu.au/conference-portal).

```chartjs
{venue_chart}
```

## Top 10 Most-Cited Papers

The ten most-cited publications by total Google Scholar citation count.

```chartjs
{top_chart}
```
"""
    return md


def main():
    rows = read_csv()
    overrides = load_ranking_overrides()
    if overrides:
        apply_ranking_overrides(rows, overrides)
    md = generate_markdown(rows)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Generated {OUTPUT_PATH} from {len(rows)} publications.")


if __name__ == "__main__":
    main()

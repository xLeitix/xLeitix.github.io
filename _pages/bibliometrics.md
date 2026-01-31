---
layout: page
permalink: /bibliometrics/
title: bibliometrics
description: Bibliometric analysis based on Google Scholar data.
nav: true
nav_order: 3
chart:
  chartjs: true
---

The following is a bibliometric summary of my research output, based on data from [Google Scholar](https://scholar.google.com/citations?user=OGkMwEoAAAAJ) as of January 2026. Bibliometrics provide a quantitative lens on research impact, productivity, and collaboration patterns. While no single metric captures the full picture, together they offer a useful overview of how research has been received and where it has had the most influence.

## Key Metrics

<div class="row row-cols-2 row-cols-md-4 g-3 mb-4">
  <div class="col">
    <div class="card text-center h-100">
      <div class="card-body">
        <h5 class="card-title" style="font-size: 2rem; font-weight: 700;">146</h5>
        <p class="card-text text-muted">Publications</p>
      </div>
    </div>
  </div>
  <div class="col">
    <div class="card text-center h-100">
      <div class="card-body">
        <h5 class="card-title" style="font-size: 2rem; font-weight: 700;">7,768</h5>
        <p class="card-text text-muted">Total Citations</p>
      </div>
    </div>
  </div>
  <div class="col">
    <div class="card text-center h-100">
      <div class="card-body">
        <h5 class="card-title" style="font-size: 2rem; font-weight: 700;">48</h5>
        <p class="card-text text-muted">H-Index</p>
      </div>
    </div>
  </div>
  <div class="col">
    <div class="card text-center h-100">
      <div class="card-body">
        <h5 class="card-title" style="font-size: 2rem; font-weight: 700;">106</h5>
        <p class="card-text text-muted">i10-Index</p>
      </div>
    </div>
  </div>
</div>

## Citations by Publication Year

This chart shows the total citations accumulated by papers published in each year. It highlights which "vintages" of papers have had the most impact so far.

```chartjs
{
  "type": "bar",
  "data": {
    "labels": ["2006", "2007", "2008", "2009", "2010", "2011", "2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025"],
    "datasets": [
      {
        "label": "Total Citations",
        "data": [4, 18, 235, 1007, 569, 268, 314, 473, 434, 439, 821, 1466, 389, 593, 301, 108, 148, 36, 127, 18],
        "backgroundColor": "rgba(54, 162, 235, 0.7)",
        "borderColor": "rgba(54, 162, 235, 1)",
        "borderWidth": 1
      }
    ]
  },
  "options": {
    "responsive": true,
    "plugins": {
      "legend": { "display": false }
    },
    "scales": {
      "y": {
        "beginAtZero": true,
        "title": { "display": true, "text": "Citations" }
      },
      "x": {
        "title": { "display": true, "text": "Publication Year" }
      }
    }
  }
}
```

## Publications per Year

Research output over time, showing the number of peer-reviewed papers published each year from 2006 to 2025.

```chartjs
{
  "type": "bar",
  "data": {
    "labels": ["2006", "2007", "2008", "2009", "2010", "2011", "2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025"],
    "datasets": [
      {
        "label": "Publications",
        "data": [1, 2, 7, 10, 9, 8, 9, 12, 8, 13, 7, 9, 7, 11, 4, 5, 9, 4, 7, 4],
        "backgroundColor": "rgba(75, 192, 192, 0.7)",
        "borderColor": "rgba(75, 192, 192, 1)",
        "borderWidth": 1
      }
    ]
  },
  "options": {
    "responsive": true,
    "plugins": {
      "legend": { "display": false }
    },
    "scales": {
      "y": {
        "beginAtZero": true,
        "title": { "display": true, "text": "Number of Papers" },
        "ticks": { "stepSize": 2 }
      },
      "x": {
        "title": { "display": true, "text": "Year" }
      }
    }
  }
}
```

## Publication Type Distribution

Breakdown of all 146 publications by type.

```chartjs
{
  "type": "doughnut",
  "data": {
    "labels": ["Conference", "Journal", "Workshop", "Book Chapter"],
    "datasets": [
      {
        "data": [84, 40, 14, 8],
        "backgroundColor": [
          "rgba(54, 162, 235, 0.8)",
          "rgba(255, 99, 132, 0.8)",
          "rgba(255, 206, 86, 0.8)",
          "rgba(153, 102, 255, 0.8)"
        ],
        "borderColor": [
          "rgba(54, 162, 235, 1)",
          "rgba(255, 99, 132, 1)",
          "rgba(255, 206, 86, 1)",
          "rgba(153, 102, 255, 1)"
        ],
        "borderWidth": 1
      }
    ]
  },
  "options": {
    "responsive": true,
    "plugins": {
      "legend": {
        "position": "bottom"
      }
    }
  }
}
```

## Venue Ranking Distribution

Distribution of publications by [CORE conference ranking](https://www.core.edu.au/conference-portal). Unranked includes workshop papers, book chapters, and venues not listed in CORE.

```chartjs
{
  "type": "bar",
  "data": {
    "labels": ["A*", "A", "B", "C", "Unranked"],
    "datasets": [
      {
        "label": "Papers",
        "data": [8, 21, 43, 11, 63],
        "backgroundColor": [
          "rgba(255, 99, 132, 0.8)",
          "rgba(255, 159, 64, 0.8)",
          "rgba(255, 206, 86, 0.8)",
          "rgba(75, 192, 192, 0.8)",
          "rgba(201, 203, 207, 0.8)"
        ],
        "borderColor": [
          "rgba(255, 99, 132, 1)",
          "rgba(255, 159, 64, 1)",
          "rgba(255, 206, 86, 1)",
          "rgba(75, 192, 192, 1)",
          "rgba(201, 203, 207, 1)"
        ],
        "borderWidth": 1
      }
    ]
  },
  "options": {
    "responsive": true,
    "plugins": {
      "legend": { "display": false }
    },
    "scales": {
      "y": {
        "beginAtZero": true,
        "title": { "display": true, "text": "Number of Papers" }
      },
      "x": {
        "title": { "display": true, "text": "CORE Ranking" }
      }
    }
  }
}
```

## Top 10 Most-Cited Papers

The ten most-cited publications by total Google Scholar citation count.

```chartjs
{
  "type": "bar",
  "data": {
    "labels": [
      "Optimized IoT service placement in the fog (2017)",
      "Extraction of microservices from monolithic... (2017)",
      "Patterns in the chaos—performance variation... (2016)",
      "Resource provisioning for IoT services in the fog (2016)",
      "Monitoring, prediction and prevention of SLA... (2010)",
      "An empirical analysis of the Docker container... (2017)",
      "Comparing and combining predictive business... (2014)",
      "A mixed-method empirical study of FaaS... (2019)",
      "Monitoring and analyzing influential factors... (2009)",
      "Runtime prediction of SLA violations... (2009)"
    ],
    "datasets": [
      {
        "label": "Citations",
        "data": [462, 389, 306, 279, 217, 210, 200, 198, 188, 172],
        "backgroundColor": "rgba(255, 99, 132, 0.7)",
        "borderColor": "rgba(255, 99, 132, 1)",
        "borderWidth": 1
      }
    ]
  },
  "options": {
    "indexAxis": "y",
    "responsive": true,
    "plugins": {
      "legend": { "display": false }
    },
    "scales": {
      "x": {
        "beginAtZero": true,
        "title": { "display": true, "text": "Citations" }
      }
    }
  }
}
```

## Collaboration Network

Based on an analysis of 114 papers published between 2014 and 2025, my research has involved **160 unique co-authors** across institutions in Europe, North America, and Asia, with an average of roughly 3 co-authors per paper.

**Top collaborators** (10+ joint papers since 2014): J. Cito (20), J. Scheuner (16), H.C. Gall (15), and G. Schermann (13) — reflecting long-standing ties to the University of Zurich and shared interests in cloud computing, DevOps, and software performance engineering.

**Frequent collaborators** (5–9 papers): C. Laaber, S. Dustdar, S. Schulte, F.G. de Oliveira Neto, R. Hebig, and M.H. Chehreghani, spanning performance testing, cloud/IoT, microservices, and machine learning.

Recent collaborations with R. Khojah, M. Mohamad, and others reflect an emerging focus on LLMs and AI-assisted software engineering.

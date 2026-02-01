#!/usr/bin/env python3
"""
Clean and enrich Google Scholar profile CSV.
Uses philippleitner.net/publications as ground truth for valid papers.
Adds publication type (Journal/Conference/Workshop) and CORE ranking/Impact Factor.
"""

import csv
import json
import os
import re
from difflib import SequenceMatcher
from dataclasses import dataclass, field
from typing import Optional

# Ground truth papers from philippleitner.net/publications
GROUND_TRUTH_PAPERS = [
    "Let's Trace It: Fine-Grained Serverless Benchmarking for Synchronous and Asynchronous Applications",
    "LLM Company Policies and Policy Implications in Software Organizations",
    "BLAFS: A Bloat-Aware Container File System",
    "The Impact of Prompt Programming on Function-Level Code Generation",
    "A Unified Active Learning Framework for Annotating Graph Data for Regression Tasks",
    "From Human-to-Human to Human-to-Bot Conversations in Software Engineering",
    "Beyond Code Generation: An Observational Study of ChatGPT Usage in Software Engineering Practice",
    "An Empirical Investigation on the Competences and Roles of Practitioners in Microservices-Based Architectures",
    "The Roles, Responsibilities, and Skills of Engineers in the Era of Microservices-Based Architectures",
    "The Impact of Compiler Warnings on Code Quality in C++ Projects",
    "Machine Learning Systems are Bloated and Vulnerable",
    "Batch Mode Deep Active Learning for Regression on Graph Data",
    "The Perceived Impact and Sequence of Activities When Transitioning to Microservices",
    "Towards Continuous Performance Assessment of Java Applications With PerfBot",
    "An Empirical Study of the Systemic and Technical Migration Towards Microservices",
    "CrossFit: Fine-grained Benchmarking of Serverless Application Performance across Cloud Providers",
    "Using Microbenchmark Suites to Detect Application Performance Changes",
    "TEP-GNN: Accurate Execution Time Prediction of Functional Tests using Graph Neural Networks",
    "TriggerBench: A Performance Benchmark for Serverless Function Triggers",
    "Automated Generation and Evaluation of JMH Microbenchmark Suites from Unit Tests",
    "Empirical Analysis of Microservices Systems Using Consumer-Driven Contract Testing",
    "Using Benchmarking Bots for Continuous Performance Assessment",
    "A Systematic Mapping Study of Source Code Representation for Deep Learning in Software Engineering",
    "Dependency Management Bots in Open-Source Systems - Prevalence and Adoption",
    "A Grounded Theory study on the migration journey towards microservices",
    "Applying test case prioritization to software microbenchmarks",
    "Facing the Giant: a Grounded Theory Study of Decision-Making in Microservices Migrations",
    "Using application benchmark call graphs to quantify and improve the practical relevance of microbenchmark suites",
    "An Exploratory Study of the Impact of Parameterization on JMH Measurement Results in Open-Source Projects",
    "What's Wrong with My Benchmark Results? Studying Bad Practices in JMH Benchmarks",
    "Topology-Aware Continuous Experimentation in Microservice-Based Applications",
    "Function-as-a-Service performance evaluation: A multivocal literature review",
    "Dynamically Reconfiguring Software Microbenchmarks: Reducing Execution Time without Sacrificing Result Quality",
    "An Empirical Study of Bots in Software Development: Characteristics and Challenges from a Practitioner's Perspective",
    "Emerging Trends, Challenges, and Experiences in DevOps and Microservice APIs",
    "Studying the impact of CI on pull request delivery time in open source projects — a conceptual replication",
    "Transpiling Applications into Optimized Serverless Orchestrations",
    "Tutorial - Performance Benchmarking of Infrastructure-as-a-Service (IaaS) Clouds with Cloud WorkBench",
    "Current and Future Bots in Software Development",
    "Tutorial: Performance Benchmarking of Infrastructure-as-a-Service (IaaS) Clouds with Cloud WorkBench",
    "Cloud Futurology",
    "Software Microbenchmarking in the Cloud. How Bad is it Really?",
    "A Mixed-Method Empirical Study of Function-as-a-Service Software Development in Industrial Practice",
    "Interactive Production Performance Feedback in the IDE",
    "Cachematic - Automatic Invalidation in Application-Level Caching Systems",
    "Search-Based Scheduling of Experiments in Continuous Deployment",
    "Estimating Cloud Application Performance Based on Micro-Benchmark Profiling",
    "An Evaluation of Open-source Software Microbenchmark Suites for Continuous Performance Assessment",
    "We're doing it live: A multi-method empirical study on continuous experimentation",
    "A Cloud Benchmark Suite Combining Micro and Applications Benchmarks",
    "PerformanceHat: Augmenting Source Code with Runtime Performance Traces in the IDE",
    "Continuous Experimentation: Challenges, Implementation Techniques, and Current Research",
    "Report from GI-Dagstuhl Seminar 16394: Software Performance Engineering in the DevOps World",
    "Optimized IoT service placement in the fog",
    "A Tale of CI Build Failures: an Open Source and a Financial Organization Perspective",
    "Extraction of Microservices from Monolithic Software Architectures",
    "An Empirical Analysis of Build Failures in the Continuous Integration Workflows of Java-Based Open-Source Software",
    "An Empirical Analysis of the Docker Container Ecosystem on GitHub",
    "(h | g)opper: Performance History Mining and Analysis",
    "An Approach and Case Study of Cloud Instance Type Selection for Multi-Tier Web Applications",
    "Context-Based Analytics – Establishing Explicit Links between Runtime Traces and Source Code",
    "An Exploratory Study of the State of Practice of Performance Testing in Java-Based Open Source Projects",
    "Resource Provisioning for IoT Services in the Fog",
    "Modelling and Managing Deployment Costs of Microservice-Based Cloud Applications",
    "Bifrost - Supporting Continuous Deployment with Automated Enactment of Multi-Phase Live Testing Strategies",
    "TemPerf: Temporal Correlation Between Performance Metrics and Source Code",
    "Towards Quality Gates in Continuous Delivery and Deployment",
    "Patterns in the Chaos - A Study of Performance Variation and Predictability in Public IaaS Clouds",
    "All the Services Large and Micro: Revisiting Industrial Practice in Services Computing",
    "A Framework for a Cost-Efficient Cloud Ecosystem",
    "Bursting With Possibilities – an Empirical Study of Credit-Based Bursting Cloud Instance Types",
    "Intent, Tests, and Release Dependencies: Pragmatic Recipes for Source Code Integration",
    "CloudWave - Leveraging DevOps for Cloud Management and Application Development",
    "JCloudScale: Closing the Gap Between IaaS and PaaS",
    "The Making of Cloud Applications – An Empirical Study on Software Development for the Cloud",
    "Runtime Metric Meets Developer - Building Better Cloud Applications Using Feedback",
    "Identifying Web Performance Degradations Through Synthetic and Real-user Monitoring",
    "SPEEDL - A Declarative Event-Based Language for Cloud Scaling Definition",
    "Profile-based View Composition in Development Dashboards",
    "Discovering Loners and Phantoms in Commit and Issue Data",
    "Cloud WorkBench: Benchmarking IaaS Providers Based on Infrastructure-as-Code",
    "SQA-Profiles: Rule-Based Activity Profiles for Continuous Integration Environments",
    "Comparing and Combining Predictive Business Process Monitoring Techniques",
    "Cloud WorkBench - Infrastructure-as-Code Based Cloud Benchmarking",
    "WPress: Benchmarking Infrastructure-as-a-Service Cloud Computing Systems for On-line Transaction Processing Applications",
    "Profiling-Based Task Scheduling for Factory-Worker Applications in Infrastructure-as-a-Service Clouds",
    "CloudWave: where Adaptive Cloud Management Meets DevOps",
    "Identifying Root Causes of Web Performance Degradation Using Changepoint Analysis",
    "A Note on Software Tools and Techniques for Monitoring and Prediction of Cloud Services",
    "Building Elastic Java Applications in the Cloud: A Middleware Framework",
    "Generic Event-based Monitoring and Adaptation Methodology for Heterogeneous Distributed Systems",
    "A Framework and Middleware for Application-Level Cloud Bursting on Top of Infrastructure-as-a-Service Clouds",
    "Data-driven and automated prediction of service level agreement violations in service compositions",
    "Testing of Data-Centric and Event-Based Dynamic Service Compositions",
    "Winds of Change: From Vendor Lock-In to the Meta Cloud",
    "Cost-Based Optimization of Service Compositions",
    "Decisions, Models, and Monitoring - A Lifecycle Model for the Evolution of Service-Based Systems",
    "The Dark Side of SOA Testing: Towards Testing Contemporary SOAs Based on Criticality Metrics",
    "Dynamic Program Code Distribution in Infrastructure-as-a-Service Clouds",
    "Fifty Shades of Grey in SOA Testing",
    "Position Paper: Model-Based Adaptation of Cloud Computing Applications",
    "Identifying Incompatible Service Implementations Using Pooled Decision Trees",
    "Mining Lifecycle Event Logs for Enhancing Service-based Applications",
    "Design by Units: Abstractions for Human and Compute Resources for Elastic Systems",
    "Application-Level Performance Monitoring of Cloud Services Based on the Complex Event Processing Paradigm",
    "Towards Identifying Root Causes of Faults in Service-Based Applications",
    "Deriving a Unified Fault Taxonomy for Event-Based Systems",
    "Cost-Efficient and Application SLA-Aware Client Side Request Scheduling in an Infrastructure-as-a-Service Cloud",
    "A Monitoring Data Set for Evaluating QoS-Aware Service-Based Systems",
    "Cost-Based Prevention of Violations of Service Level Agreements in Composed Services Using Self-Adaptation",
    "CloudScale: a Novel Middleware for Building Transparently Scaling Cloud Applications",
    "Non-Intrusive Policy Optimization for Dependable and Adaptive Service-Oriented Systems",
    "VRESCo - Vienna Runtime Environment for Service-oriented Computing",
    "SEPL - a Domain-Specific Language and Execution Environment for Protocols of Stateful Web Services",
    "Identifying Influential Factors of Business Process Performance Using Dependency Analysis",
    "Stepwise and Asynchronous Runtime Optimization of Web Service Compositions",
    "Distributed Continuous Queries Over Web Service Event Streams",
    "Dynamic Migration of Processing Elements for Optimized Query Execution in Event-Based Systems",
    "Esc: Towards an Elastic Stream Computing Platform for the Cloud",
    "Test Coverage of Data-Centric Dynamic Compositions in Service-Based Systems",
    "WS-Aggregation: Distributed Aggregation of Web Services Data",
    "On Preventing Violations of Service Level Agreements in Composed Services using Self-Adaptation",
    "Event Processing in Web Service Runtime Environments",
    "A Mediator-Based Approach to Resolving Interface Heterogeneity of Web Services",
    "End-to-End Support for QoS-Aware Service Selection, Binding, and Mediation in VRESCo",
    "Selective Service Provenance in the VRESCo Runtime",
    "A Step-by-Step Debugging Technique to Facilitate Mashup Development and Maintenance",
    "Preventing SLA Violations in Service Compositions Using Aspect-Based Fragment Substitution",
    "Monitoring, Prediction and Prevention of SLA Violations in Composite Services",
    "Metaheuristic Optimization of Large-Scale QoS-aware Service Compositions",
    "Daios: Efficient Dynamic Web Service Invocation",
    "Ensuring Cost-Optimal SLA Conformance for Composite Service Providers",
    "Runtime Prediction of Service Level Agreement Violations for Composite Services",
    "Comprehensive QoS Monitoring of Web Services and Event-Based SLA Violation Detection",
    "Selecting Web Services Based on Past User Experiences",
    "VieSLAF Framework: Enabling Adaptive and Versatile SLA-Management",
    "Monitoring and Analyzing Influential Factors of Business Process Performance",
    "An End-to-End Approach for QoS-Aware Service Composition",
    "Service Provenance in QoS-Aware Web Service Runtimes",
    "Towards Composition as a Service - A Quality of Service Driven Approach",
    "Modelling Behaviour and Distribution for the Management of Next Generation Networks",
    "Integrated Metadata Support for Web Service Runtimes",
    "Advanced Event Processing and Notifications in Service Runtime Environments",
    "Publish/Subscribe in the VRESCo SOA Runtime",
    "End-to-End Versioning Support for Web Services",
    "Securing the Madeira Network Management System",
    "Fault Management Based on Peer-to-Peer Paradigms; a Case Study Report From the CELTIC Project Madeira",
    "The Daios Framework - Dynamic, Asynchronous and Message-oriented Invocation of Web Services",
    "A Distributed Policy Based Solution in a Fault Management Scenario",
    "An Experimental Study of Real-Life LLM-Proposed Performance Improvements",
    "A unified active learning framework for annotating graph data with application to software source code performance prediction",
    "Analysing the Behaviour of Tree-Based Neural Networks in Regression Tasks",
    "Towards flexible interface mediation for dynamic service invocations",
    "Service composition",
    "The migration journey towards microservices",
    "Fault Management Based on Peer-to-Peer Paradigms; a Case Study Report From the CELTIC Project Madeira",
    "CloudWave-Leveraging DevOps for Cloud Management and Application Development",
    "Profile-based View Composition in Development Dashboards",
    "Model-based adaptation of cloud computing applications",
    "Performance Benchmarking of Infrastructure-as-a-Service (IaaS) Clouds with Cloud WorkBench",
    "Building Elastic Java Applications in the Cloud: A Middleware Framework",
    "SPEEDL-a declarative event-based language to define the scaling behavior of cloud applications",
]


# CORE rankings for conferences (pattern -> ranking)
CORE_RANKINGS = {
    # A* conferences
    r'\bICSE\b': 'A*',
    r'\bFSE\b': 'A*',
    r'\bASE\b': 'A*',
    # SoCC — not CORE ranked
    r'foundations of software engineering': 'A*',
    r'international conference on software engineering': 'A*',
    r'automated software engineering': 'A*',
    r'\bSIGMETRICS\b': 'A*',
    r'measurement and analysis of computing': 'A*',
    r'joint meeting.*foundations': 'A*',
    r'european software engineering': 'A*',  # ESEC/FSE

    # A conferences
    r'\bMSR\b': 'A',
    r'\bICSME\b': 'A',
    r'\bICSM\b': 'A',
    r'mining software repositories': 'A',
    r'conference on mining software': 'A',  # MSR when truncated
    r'software maintenance and evolution': 'A',
    r'\bICSO\w*\b': 'A',  # ICSOC
    r'service-oriented computing': 'A',
    r'\bICWS\b': 'A',
    r'web services': 'A',
    r'\bSANER\b': 'A',
    r'software analysis.*evolution.*reengineering': 'A',
    r'\bESEM\b': 'A',
    r'empirical software engineering and measurement': 'A',
    r'symposium on empirical': 'A',
    r'middleware conference': 'A',
    r'\bMIDDLEWARE\b': 'A',
    r'\bICDE\b': 'A',
    r'data engineering': 'A',
    r'\bWWW\b': 'A',
    r'world wide web': 'A',
    r'\bESSOS\b': 'A',
    r'\bESEC\b': 'A*',

    # A conferences (continued)
    r'\bICPC\b': 'A',
    r'program comprehension': 'A',
    r'conference on program': 'A',  # ICPC when truncated

    # B conferences
    r'\bUCC\b': 'B',
    r'utility and cloud': 'B',
    r'(?:conference on|international) cloud computing\b(?!\s+technology)': 'B',
    r'\bEDOC\b': 'B',
    r'enterprise distributed object computing': 'B',
    r'\bICWE\b': 'B',
    r'web engineering': 'B',
    r'\bSAC\b': 'B',
    r'symposium on applied computing': 'B',
    r'\bCCGRID\b': 'B',
    r'cluster.*cloud.*grid': 'B',
    r'\bSRDS\b': 'B',
    r'reliable distributed systems': 'B',
    r'\bICPE\b': 'B',
    r'performance engineering': 'B',
    r'\bWISE\b': 'B',
    r'web information systems': 'B',
    r'\bPROFES\b': 'B',
    r'product.focused software': 'B',
    r'\bIC2E\b': 'B',
    r'cloud engineering': 'B',
    # SOSE — not CORE ranked
    r'\bEUROMICRO\b': 'B',
    r'euromicro': 'B',
    r'\bCOOPIS\b': 'B',
    r'on the move': 'B',
    r'\bIM\b.*network management': 'B',
    r'integrated network management': 'B',
    r'(?<!asia-pacific\s)services computing.*\d': 'B',  # IEEE SCC
    r'\bCHASE\b': 'B',
    r'cooperative.*human aspects': 'B',
    r'cooperative and human': 'B',  # CHASE
    r'\bACM/SPEC\b': 'B',
    r'acm.*spec.*performance': 'B',
    # ServiceWave — not CORE ranked
    # AIWARE — not CORE ranked
    r'world congress on services': 'B',

    # C conferences
    r'\bISCC\b': 'C',
    r'\bSCAM\b': 'C',
    r'source code analysis': 'C',
    r'\bNWPT\b': 'C',
    r'\bGLOBECOM\b': 'C',
    r'globecom': 'C',
    r'\bDEBS\b': 'C',
    r'distributed event': 'C',
    r'\bICVS\b': 'C',
    r'\bICST\b': 'C',
    r'software testing.*verification': 'C',
    r'\bOnward\b': 'C',
    r'new ideas.*new paradigms': 'C',
    r'\bBigData\b': 'C',
    r'big data': 'C',
    r'\bAPSCC\b': 'C',
    r'asia-pacific services': 'C',
    r'\bCloudCom\b': 'C',
    r'cloud computing technology': 'C',
}


# Journal Impact Factors (2024 values from Web of Science/JCR where available)
JOURNAL_IMPACT_FACTORS = {
    'ieee transactions on software engineering': '6.8',
    'empirical software engineering': '3.6',
    'journal of systems and software': '5.9',
    'ieee transactions on services computing': '5.8',
    'acm transactions on internet technology': '5.1',
    'information and software technology': '4.3',
    'ieee software': '2.6',
    'ieee internet computing': '5.0',
    'software: practice and experience': '2.7',
    'software practice and experience': '2.7',
    'software-practice': '2.7',
    'future generation computer systems': '6.1',
    'peerj computer science': '3.8',
    'ieee transactions on cloud computing': '5.5',
    'computer': '2.2',
    'distributed and parallel databases': '2.5',
    'enterprise information systems': '3.0',
    'engineering applications of artificial intelligence': '7.5',
    'ieee transactions on systems, man, and cybernetics': '8.6',
    'iet software': '1.5',
    'software testing, verification and reliability': '1.5',
    'international journal of web services research': '1.2',
    'journal of web engineering': '0.8',
    'service oriented computing and applications': '2.1',
}


def load_ranking_overrides() -> dict[str, str]:
    """Load CORE ranking overrides from JSON file.

    Returns a dict mapping lowercase venue substrings to CORE ranks.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, "data", "conference_ranking_overrides.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k.lower(): v for k, v in data.get("overrides", {}).items()}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


RANKING_OVERRIDES = load_ranking_overrides()


def get_impact_factor(venue: str) -> str:
    """Get Impact Factor for a journal venue."""
    if not venue:
        return ''
    venue_lower = venue.lower()
    for journal_pattern, impact_factor in JOURNAL_IMPACT_FACTORS.items():
        if journal_pattern in venue_lower:
            return impact_factor
    return ''


def get_core_ranking(venue: str) -> str:
    """Get CORE ranking for a conference venue.

    Checks manual overrides first (case-insensitive substring match),
    then falls back to the regex-based CORE_RANKINGS dict.
    """
    if not venue:
        return ''
    venue_lower = venue.lower()
    # Check overrides first
    for substr, ranking in RANKING_OVERRIDES.items():
        if substr in venue_lower:
            return ranking
    # Fall back to regex patterns
    for pattern, ranking in CORE_RANKINGS.items():
        if re.search(pattern, venue_lower, re.IGNORECASE):
            return ranking
    return ''


# Author corrections for papers with truncated author lists (keys are normalized titles)
AUTHOR_CORRECTIONS = {
    "triggerbench a performance benchmark for serverless function triggers":
        "J Scheuner, M Bertilsson, O Grönqvist, H Tao, H Lagergren, JP Steghöfer, P Leitner",
    "cloud futurology":
        "B Varghese, P Leitner, S Ray, K Chard, A Barker, Y Elkhatib, H Herry, CH Hong, J Singer, FP Tso, E Yoneki, MF Zhani",
    "a tale of ci build failures an open source and a financial organization perspective":
        "C Vassallo, G Schermann, F Zampetti, D Romano, P Leitner, A Zaidman, M Di Penta, S Panichella",
    "comparing and combining predictive business process monitoring techniques":
        "A Metzger, P Leitner, D Ivanović, E Schmieders, R Franklin, M Carro, S Dustdar, K Pohl",
    "cloudwave where adaptive cloud management meets devops":
        "D Bruneo, T Fritz, S Keidar-Barner, P Leitner, F Longo, C Marquezan, A Metzger, K Pohl, A Puliafito, D Raz, A Roth, E Salant, I Segall, M Villari, Y Wolfsthal, C Woods",
    "fifty shades of grey in soa testing":
        "F Wotawa, M Schulz, I Pill, S Jehan, P Leitner, W Hummer, S Schulte, P Hoenisch, S Dustdar",
    "metaheuristic optimization of large scale qos aware service compositions":
        "F Rosenberg, MB Müller, P Leitner, A Michlmayr, A Bouguettaya, S Dustdar",
    "preventing sla violations in service compositions using aspect based fragment substitution":
        "P Leitner, B Wetzstein, D Karastoyanova, W Hummer, S Dustdar, F Leymann",
    "modelling behaviour and distribution for the management of next generation networks":
        "C Fahy, MP de Leon, S van der Meer, R Marin, J Serrat, P Leitner, S Collins, B Baesjou",
    "cloudwave leveraging devops for cloud management and application development":
        "D Bruneo, A Dadashi, P Leitner, B Moltchanov, FJN De-Santos, A Miron, A Mos, A Puliafito, OR Rocha, E Salant",
    "securing the madeira network management system":
        "R Marín, J Vivero, P Leitner, A Neppach, M Zach, D Ortega, B Baesjou, C Fahy",
    "service composition":
        "G Baryannis, O Danylevych, D Karastoyanova, K Kritikos, P Leitner, F Rosenberg, B Wetzstein",
}


# Manual venue corrections for papers with incomplete venue info (keys are normalized titles)
VENUE_CORRECTIONS = {
    "using microbenchmark suites to detect application performance changes": {
        "venue": "IEEE Transactions on Cloud Computing 11 (3), 2575-2590",
        "type": "Journal",
    },
    "wpress benchmarking infrastructure as a service cloud computing systems for on line transaction processing applications": {
        "venue": "2014 IEEE 18th International Enterprise Distributed Object Computing Conference (EDOC), 101-109",
        "type": "Conference",
        "ranking": "B",
    },
    "the roles responsibilities and skills of engineers in the era of microservices based architectures": {
        "venue": "2024 IEEE/ACM 17th International Conference on Cooperative and Human Aspects of Software Engineering (CHASE)",
        "type": "Conference",
        "ranking": "B",
    },
    "performancehat augmenting source code with runtime performance traces in the ide": {
        "type": "Workshop",
    },
    "distributed continuous queries over web service event streams": {
        "type": "Workshop",
    },
    "towards composition as a service a quality of service driven approach": {
        "type": "Workshop",
    },
}


def normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    # Remove special chars, lowercase, collapse whitespace
    title = title.lower()
    title = re.sub(r'[^\w\s]', ' ', title)
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def title_similarity(t1: str, t2: str) -> float:
    """Calculate similarity between two titles."""
    return SequenceMatcher(None, normalize_title(t1), normalize_title(t2)).ratio()


def find_matching_ground_truth(title: str, threshold: float = 0.85) -> Optional[str]:
    """Find matching paper in ground truth list."""
    best_match = None
    best_score = 0

    for gt_title in GROUND_TRUTH_PAPERS:
        score = title_similarity(title, gt_title)
        if score > best_score:
            best_score = score
            best_match = gt_title

    if best_score >= threshold:
        return best_match
    return None


# Known journal patterns
JOURNAL_PATTERNS = [
    r'journal',
    r'transactions on',
    r'ieee software',
    r'ieee internet computing',
    r'software.+practice.+experience',
    r'empirical software engineering',
    r'information and software technology',
    r'journal of systems and software',
    r'peerj',
    r'future generation computer systems',
    r'engineering applications of artificial intelligence',
    r'distributed and parallel databases',
    r'enterprise information systems',
    r'iet software',
    r'\bcomputer\b.*\d+.*\d+',  # Computer journal with issue numbers
    r'software testing.*verification.*reliability',
    r'service oriented computing and applications',  # SOCA journal
]

# Known conference patterns
CONFERENCE_PATTERNS = [
    r'international conference',
    r'symposium on',
    r'\bICWS\b',
    r'\bICSE\b',
    r'\bFSE\b',
    r'\bICSM\b',
    r'\bASE\b',
    r'\bMSR\b',
    r'\bICSC\b',
    r'\bICSP\b',
    r'\bICSCC\b',
    r'\bICSO\b',
    r'\bICPC\b',
    r'\bICCG\b',
    r'\bESEC\b',
    r'\bICSME\b',
    r'\bICSA\b',
    r'\bISSRE\b',
    r'\bISCC\b',
    r'\bSOCC\b',
    r'\bCLOUD\b',
    r'\bUCC\b',
    r'\bEDOC\b',
    r'\bMIDDLEWARE\b',
    r'\bSERVICE\b',
    r'\bICDE\b',
    r'\bSIGMOD\b',
    r'proceedings of the',
    r'euromicro conference',
    r'joint meeting',
    r'acm/spec',
    r'ieee/acm',
    r'globecom',
    r'echallenges',
    r'working conference',
    r'enterprise distributed object computing',
    r'asia-pacific services computing',
    r'world congress on services',
]

# Preprint/Technical report patterns
PREPRINT_PATTERNS = [
    r'arxiv',
    r'preprint',
    r'technical report',
    r'tech\. rep\.',
    r'university of zurich$',
    r'technische universität',
]

# Book chapter patterns
BOOK_CHAPTER_PATTERNS = [
    r'concepts.*methodologies.*tools',
    r'emerging web services technology',
    r'advanced autonomic networking',
    r'principles and applications of',
    r'service research challenges',
    r'service engineering.*european research',
]

# Known workshop patterns
WORKSHOP_PATTERNS = [
    r'workshop',
    r'\bWEWST\b',
    r'\bBotSE\b',
    r'\bPESW\b',
    r'\bQRSA\b',
    r'\bWOSA\b',
    r'special session',
    r'phd symposium',
]

# German journal patterns
GERMAN_JOURNAL_PATTERNS = [
    r'softwaretechnik-trends',
]


def classify_venue(venue: str) -> str:
    """Classify venue as Journal, Conference, Workshop, Preprint, or Book Chapter."""
    if not venue:
        return "Unknown"

    venue_lower = venue.lower()

    # Check preprint first
    for pattern in PREPRINT_PATTERNS:
        if re.search(pattern, venue_lower, re.IGNORECASE):
            return "Preprint"

    # Check book chapter
    for pattern in BOOK_CHAPTER_PATTERNS:
        if re.search(pattern, venue_lower, re.IGNORECASE):
            return "Book Chapter"

    # Check workshop (more specific than conference)
    for pattern in WORKSHOP_PATTERNS:
        if re.search(pattern, venue_lower, re.IGNORECASE):
            return "Workshop"

    # Check journal
    for pattern in JOURNAL_PATTERNS:
        if re.search(pattern, venue_lower, re.IGNORECASE):
            return "Journal"

    # Check German journals
    for pattern in GERMAN_JOURNAL_PATTERNS:
        if re.search(pattern, venue_lower, re.IGNORECASE):
            return "Journal"

    # Check conference
    for pattern in CONFERENCE_PATTERNS:
        if re.search(pattern, venue_lower, re.IGNORECASE):
            return "Conference"

    return "Unknown"


@dataclass
class Paper:
    title: str
    authors: str
    venue: str
    year: Optional[float]
    citations: Optional[int]
    existing_ranking: str
    pub_type: str = ""
    ranking: str = ""
    impact_factor: str = ""
    ground_truth_match: str = ""


def load_csv(filepath: str) -> list[Paper]:
    """Load papers from CSV file."""
    papers = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            year_str = row.get('year', '')
            year = None
            if year_str:
                try:
                    year = float(year_str)
                except ValueError:
                    pass

            citations = None
            cit_str = row.get('citations', '')
            if cit_str:
                try:
                    citations = int(float(cit_str))
                except ValueError:
                    pass

            paper = Paper(
                title=row.get('title', ''),
                authors=row.get('authors', ''),
                venue=row.get('venue', ''),
                year=year,
                citations=citations,
                existing_ranking=row.get('ranking', ''),
            )
            papers.append(paper)
    return papers


def filter_and_classify(papers: list[Paper]) -> list[Paper]:
    """Filter papers against ground truth and classify them."""
    filtered = []

    for paper in papers:
        # Skip entries with no title
        if not paper.title.strip():
            continue

        # Skip replication packages, datasets, etc.
        title_lower = paper.title.lower()
        if 'replication package' in title_lower or 'replication-package' in title_lower:
            continue

        # Skip preprints (arXiv, tech reports, etc.)
        venue_lower = (paper.venue or '').lower()
        is_preprint = any(p in venue_lower for p in ['arxiv', 'preprint', 'technical report', 'tech. rep.', 'university of zurich', 'technische universität'])
        if is_preprint:
            continue

        # Check against ground truth
        match = find_matching_ground_truth(paper.title)
        if not match:
            continue

        paper.ground_truth_match = match

        # Apply manual author corrections
        norm_title = normalize_title(paper.title)
        if norm_title in AUTHOR_CORRECTIONS:
            paper.authors = AUTHOR_CORRECTIONS[norm_title]

        # Apply manual venue corrections
        if norm_title in VENUE_CORRECTIONS:
            correction = VENUE_CORRECTIONS[norm_title]
            paper.venue = correction.get("venue", paper.venue)
            paper.pub_type = correction.get("type", classify_venue(paper.venue))
            if correction.get("ranking"):
                paper.ranking = correction["ranking"]
        else:
            paper.pub_type = classify_venue(paper.venue)

        # Keep existing CORE ranking if present (conferences only, unless already set by correction)
        if paper.existing_ranking and not paper.ranking and paper.pub_type == 'Conference':
            paper.ranking = paper.existing_ranking

        # Try to find CORE ranking for conferences without one
        if paper.pub_type == 'Conference' and not paper.ranking:
            paper.ranking = get_core_ranking(paper.venue)

        # Try to find Impact Factor for journals
        if paper.pub_type == 'Journal' and not paper.impact_factor:
            paper.impact_factor = get_impact_factor(paper.venue)

        filtered.append(paper)

    return filtered


def deduplicate(papers: list[Paper]) -> list[Paper]:
    """Remove duplicate papers using fuzzy matching, keeping the one with highest citations."""
    from difflib import SequenceMatcher

    result = []
    for paper in papers:
        norm_title = normalize_title(paper.title)

        # Check if similar paper already exists
        found_similar = False
        for i, existing in enumerate(result):
            existing_norm = normalize_title(existing.title)
            similarity = SequenceMatcher(None, norm_title, existing_norm).ratio()

            if similarity > 0.85:  # Fuzzy match threshold
                found_similar = True
                # Keep the one with more citations, or prefer non-preprint
                paper_score = (paper.citations or 0) + (100 if paper.pub_type not in ['Preprint'] else 0)
                existing_score = (existing.citations or 0) + (100 if existing.pub_type not in ['Preprint'] else 0)

                if paper_score > existing_score:
                    result[i] = paper
                break

        if not found_similar:
            result.append(paper)

    return result


def save_csv(papers: list[Paper], filepath: str):
    """Save papers to CSV file."""
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['title', 'authors', 'venue', 'year', 'citations', 'type', 'ranking', 'impact_factor'])

        for paper in papers:
            writer.writerow([
                paper.title,
                paper.authors,
                paper.venue,
                int(paper.year) if paper.year else '',
                paper.citations if paper.citations else '',
                paper.pub_type,
                paper.ranking,
                paper.impact_factor,
            ])


def main():
    input_file = 'scholar_full_profile.csv'
    output_file = 'scholar_profile_cleaned.csv'

    print(f"Loading {input_file}...")
    papers = load_csv(input_file)
    print(f"Loaded {len(papers)} entries")

    print("Filtering against ground truth and classifying...")
    filtered = filter_and_classify(papers)
    print(f"Found {len(filtered)} papers matching ground truth")

    print("Removing duplicates...")
    deduped = deduplicate(filtered)
    print(f"After deduplication: {len(deduped)} papers")

    # Sort by year (descending), then citations (descending)
    deduped.sort(key=lambda p: (-(p.year or 0), -(p.citations or 0)))

    # Report on classification
    types = {}
    for p in deduped:
        types[p.pub_type] = types.get(p.pub_type, 0) + 1
    print(f"Classification breakdown: {types}")

    # Report on existing rankings
    with_ranking = sum(1 for p in deduped if p.ranking)
    print(f"Papers with existing CORE ranking: {with_ranking}")

    # Papers needing ranking lookup
    conferences_no_rank = [p for p in deduped if p.pub_type == 'Conference' and not p.ranking]
    journals_no_if = [p for p in deduped if p.pub_type == 'Journal' and not p.impact_factor]
    journals_with_if = sum(1 for p in deduped if p.pub_type == 'Journal' and p.impact_factor)
    print(f"Conferences needing CORE ranking: {len(conferences_no_rank)}")
    print(f"Journals with Impact Factor: {journals_with_if}")
    print(f"Journals without Impact Factor: {len(journals_no_if)}")

    # Papers with truncated authors
    truncated = [p for p in deduped if '...' in p.authors]
    print(f"Papers with truncated authors: {len(truncated)}")

    print(f"\nSaving initial cleaned file to {output_file}...")
    save_csv(deduped, output_file)

    print("\n=== Papers needing attention ===")
    print("\nConferences needing CORE ranking:")
    for p in conferences_no_rank[:10]:  # Show first 10
        print(f"  - {p.title[:60]}... ({p.venue[:40]}...)")

    print("\nPapers with truncated authors:")
    for p in truncated[:10]:  # Show first 10
        print(f"  - {p.title[:60]}...")

    print(f"\nDone! Review {output_file} and run additional enrichment as needed.")


if __name__ == '__main__':
    main()

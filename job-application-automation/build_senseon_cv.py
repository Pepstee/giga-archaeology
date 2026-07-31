from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)


OUT = Path(__file__).parent / "applications" / "rank-19-senseon"
OUT.mkdir(parents=True, exist_ok=True)
PDF = OUT / "Artiom_Gutu_CV_SenseOn.pdf"

FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
pdfmetrics.registerFont(TTFont("Arial", FONT))
pdfmetrics.registerFont(TTFont("Arial-Bold", BOLD))

INK = colors.HexColor("#111827")
BLUE = colors.HexColor("#174E75")
MUTED = colors.HexColor("#4B5563")
LIGHT = colors.HexColor("#CBD5E1")

styles = getSampleStyleSheet()
name = ParagraphStyle(
    "Name",
    parent=styles["Normal"],
    fontName="Arial-Bold",
    fontSize=22,
    leading=25,
    textColor=INK,
    alignment=TA_CENTER,
    spaceAfter=3,
)
headline = ParagraphStyle(
    "Headline",
    parent=styles["Normal"],
    fontName="Arial",
    fontSize=10.5,
    leading=13,
    textColor=BLUE,
    alignment=TA_CENTER,
    spaceAfter=4,
)
contact = ParagraphStyle(
    "Contact",
    parent=styles["Normal"],
    fontName="Arial",
    fontSize=8.7,
    leading=11,
    textColor=MUTED,
    alignment=TA_CENTER,
    spaceAfter=7,
)
section = ParagraphStyle(
    "Section",
    parent=styles["Heading2"],
    fontName="Arial-Bold",
    fontSize=10.5,
    leading=13,
    textColor=BLUE,
    spaceBefore=7,
    spaceAfter=3,
    keepWithNext=True,
)
body = ParagraphStyle(
    "Body",
    parent=styles["Normal"],
    fontName="Arial",
    fontSize=9.2,
    leading=12,
    textColor=INK,
    spaceAfter=4,
)
role = ParagraphStyle(
    "Role",
    parent=body,
    fontName="Arial-Bold",
    fontSize=9.6,
    leading=12,
    spaceBefore=3,
    spaceAfter=1,
    keepWithNext=True,
)
meta = ParagraphStyle(
    "Meta",
    parent=body,
    fontSize=8.8,
    leading=11,
    textColor=MUTED,
    spaceAfter=2,
)
bullet = ParagraphStyle(
    "Bullet",
    parent=body,
    leftIndent=4.5 * mm,
    firstLineIndent=-3.2 * mm,
    bulletIndent=0,
    spaceAfter=2,
)
small = ParagraphStyle(
    "Small",
    parent=body,
    fontSize=8.6,
    leading=11,
    spaceAfter=3,
)


def heading(text):
    return [
        Paragraph(text.upper(), section),
        HRFlowable(width="100%", thickness=0.6, color=LIGHT, spaceAfter=4),
    ]


def bullets(items):
    return [Paragraph(f"• {item}", bullet) for item in items]


story = [
    Paragraph("ARTIOM GUTU", name),
    Paragraph(
        "Graduate AI Automation Engineer | Python, Agentic Systems and Reliable Workflows",
        headline,
    ),
    Paragraph(
        "Wolverhampton, United Kingdom &nbsp;|&nbsp; +44 7561 447187 &nbsp;|&nbsp; "
        "gutu.artiom444@gmail.com &nbsp;|&nbsp; "
        '<link href="https://github.com/Pepstee" color="#174E75">github.com/Pepstee</link>',
        contact,
    ),
]

story += heading("Profile")
story += [
    Paragraph(
        "First-Class BSc (Hons) Computer Science graduate focused on AI automation, agentic systems and dependable "
        "Python workflows. I design systems that separate probabilistic model work from deterministic "
        "validation, persistence and reporting. My projects cover API integration, structured data "
        "pipelines, test and review gates, resumable execution, observability and security-conscious "
        "defaults. Earlier teaching, administration and direct-sales work developed clear written "
        "communication and practical commercial judgement. Eligible to work in the UK without sponsorship; "
        "available from October 2026.",
        body,
    )
]

story += heading("Technical skills")
story += [
    Paragraph(
        "<b>Languages and data:</b> Python, SQL, SQLite, JSON/JSONL, YAML, XML/RSS, REST APIs",
        small,
    ),
    Paragraph(
        "<b>AI and automation:</b> LLM orchestration, agent workflows, schema-bound extraction, prompt and "
        "input caching, deterministic validation, evaluation gates, retries and resumable pipelines",
        small,
    ),
    Paragraph(
        "<b>Engineering:</b> Git, automated testing, concurrent ingestion, HTTP failure handling, process "
        "supervision, structured logging, content hashing and audit trails",
        small,
    ),
    Paragraph(
        "<b>Cloud and security:</b> AWS Lambda, CloudWatch telemetry, serverless systems, privacy, adversarial "
        "testing, least-privilege and safe-secret principles",
        small,
    ),
]

story += heading("Selected projects")
story += [
    KeepTogether(
        [
            Paragraph("Market Aligner | Python job-intelligence and automation system", role),
            Paragraph(
                "Python, SQLite, REST APIs, RSS/XML, LLM orchestration, structured data, testing",
                meta,
            ),
            *bullets(
                [
                    "Designed and operated a multi-source job-intelligence pipeline with 18 API and feed adapters, concurrent collection, append-preserving SQLite storage and raw-response caching.",
                    "Confined LLM use to schema-bound semantic extraction and evidence-led judgement; kept collection, filtering, canonicalisation, arithmetic, caching, persistence and reporting deterministic and testable.",
                    "Added retries, structured validation, model-backend routing, usage logging, resumability and auditable XLSX/PNG reporting.",
                ]
            ),
        ]
    ),
    KeepTogether(
        [
            Paragraph("Three-generation multi-agent software factory | AI-assisted software delivery", role),
            Paragraph(
                "Codex, Claude Code, executable governance, certified isolation, evidence and recovery",
                meta,
            ),
            *bullets(
                [
                    "Iterated the factory across three generations. V1 proved unattended multi-agent coordination but exposed the limits of prose-only rules; V2 converted core rules into executable checks, import boundaries and a self-certification ladder.",
                    "Designed V3 around a durable plan, build, test, independent-judge, certify, improve and recertify loop with revision-bound evidence, disposable isolated worktrees, restart recovery and fail-closed dispatch.",
                    "Directed an independent deep audit, used its P0/P1 findings to repair false-success and unsafe-runtime paths, and completed a live end-to-end canary. The verified V3 suite reached 3,482 passing tests with four skips and no failures.",
                    "Own the requirements, architecture, model routing, governance and acceptance decisions. AI agents generate substantial implementation code; the current generation remains under commercial hardening rather than being presented as finished production software.",
                ]
            ),
        ]
    ),
    KeepTogether(
        [
            Paragraph("SCAFAD | First-Class Computer Science dissertation", role),
            Paragraph(
                "Python, AWS Lambda, CloudWatch, anomaly detection, graph methods and security evaluation",
                meta,
            ),
            *bullets(
                [
                    "Explored behavioural anomaly detection for serverless workloads using AWS Lambda telemetry.",
                    "Worked across telemetry collection, graph-based analysis, privacy, adversarial testing, explainability and research evaluation.",
                ]
            ),
        ]
    ),
]

story.append(PageBreak())
story += heading("Selected engineering contributions")
story += bullets(
    [
        "<b>Market Aligner:</b> I designed and implemented the boundary that confines LLMs to semantic extraction and evidence-led judgement while deterministic Python handles collection, filtering, deduplication, scoring, persistence and reporting.",
        "<b>Market Aligner:</b> I implemented an uncapped concurrent collector spanning 18 API and feed adapters, append-preserving SQLite storage, raw-response caching, structured validation, retries and resumable processing.",
        "<b>Orchestrator V1 to V2:</b> I identified that prose rules allowed architectural drift, then redesigned the next generation so dependency laws, capability boundaries and assurance requirements could fail the build instead of relying on agents to remember instructions.",
        "<b>Orchestrator V3:</b> I designed the factory control loop, scoped task contracts, cross-provider model routing, independent review, revision-bound certification, disposable worktree isolation, crash recovery and evidence receipts. I operated the agents, commissioned adversarial audits and decided whether each build passed.",
        "<b>SCAFAD:</b> I designed my dissertation around behavioural anomaly detection for AWS Lambda workloads and developed its evaluation across CloudWatch telemetry, graph methods, privacy, adversarial testing and explainability.",
    ]
)

story += heading("Education")
story += [
    Paragraph("BSc (Hons) Computer Science, First-Class Honours", role),
    Paragraph("Birmingham Newman University | Graduated 2 July 2026", meta),
    Paragraph(
        "Dissertation: SCAFAD, a serverless anomaly-detection project using AWS Lambda telemetry. "
        "Relevant work included Python, CloudWatch data, graph methods, adversarial testing, privacy and "
        "research evaluation.",
        body,
    ),
]

story += heading("Additional experience")
story += [
    Paragraph("Founder and Managing Director | Excellence Exalted Limited", role),
    *bullets(
        [
            "Founded and registered a UK language-teaching company; defined the initial service model, recruited the first teacher and managed early administration and service planning.",
        ]
    ),
    Paragraph("Paid Online English Tutor", role),
    *bullets(
        [
            "Planned and delivered one-to-one conversation-led lessons, adapting explanations and exercises to each learner's level and recurring weaknesses.",
        ]
    ),
    Paragraph("Direct Sales Agent | Appco UK", role),
    *bullets(
        [
            "Developed practical experience in prospecting, objection handling and communicating clearly with unfamiliar customers.",
        ]
    ),
]

story += heading("Languages")
story += [
    Paragraph(
        "Fluent in English, Romanian and Russian",
        body,
    )
]


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Arial", 8)
    canvas.setFillColor(MUTED)
    canvas.drawCentredString(A4[0] / 2, 10 * mm, f"Artiom Gutu | Page {doc.page}")
    canvas.restoreState()


doc = SimpleDocTemplate(
    str(PDF),
    pagesize=A4,
    rightMargin=15 * mm,
    leftMargin=15 * mm,
    topMargin=13 * mm,
    bottomMargin=16 * mm,
    title="Artiom Gutu - CV - SenseOn",
    author="Artiom Gutu",
    subject="Application for Go-to-Market Engineer (AI-first GTM Engineering)",
)
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(PDF)

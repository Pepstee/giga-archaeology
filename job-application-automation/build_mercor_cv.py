from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate


OUT = Path(__file__).parent / "applications" / "rank-18-mercor"
OUT.mkdir(parents=True, exist_ok=True)
PDF = OUT / "Artiom_Gutu_CV_Mercor.pdf"

pdfmetrics.registerFont(TTFont("Arial", "/System/Library/Fonts/Supplemental/Arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"))

INK = colors.HexColor("#111827")
BLUE = colors.HexColor("#174E75")
MUTED = colors.HexColor("#4B5563")
LIGHT = colors.HexColor("#CBD5E1")

styles = getSampleStyleSheet()
name = ParagraphStyle("Name", parent=styles["Normal"], fontName="Arial-Bold", fontSize=22,
                      leading=25, textColor=INK, alignment=TA_CENTER, spaceAfter=3)
headline = ParagraphStyle("Headline", parent=styles["Normal"], fontName="Arial", fontSize=10.5,
                          leading=13, textColor=BLUE, alignment=TA_CENTER, spaceAfter=4)
contact = ParagraphStyle("Contact", parent=styles["Normal"], fontName="Arial", fontSize=8.7,
                         leading=11, textColor=MUTED, alignment=TA_CENTER, spaceAfter=7)
section = ParagraphStyle("Section", parent=styles["Heading2"], fontName="Arial-Bold",
                         fontSize=10.5, leading=13, textColor=BLUE, spaceBefore=7,
                         spaceAfter=3, keepWithNext=True)
body = ParagraphStyle("Body", parent=styles["Normal"], fontName="Arial", fontSize=9.2,
                      leading=12, textColor=INK, spaceAfter=4)
role = ParagraphStyle("Role", parent=body, fontName="Arial-Bold", fontSize=9.6,
                      leading=12, spaceBefore=3, spaceAfter=1, keepWithNext=True)
meta = ParagraphStyle("Meta", parent=body, fontSize=8.8, leading=11, textColor=MUTED,
                      spaceAfter=2)
bullet = ParagraphStyle("Bullet", parent=body, leftIndent=4.5 * mm,
                        firstLineIndent=-3.2 * mm, bulletIndent=0, spaceAfter=2)
small = ParagraphStyle("Small", parent=body, fontSize=8.6, leading=11, spaceAfter=3)


def heading(text):
    return [
        Paragraph(text.upper(), section),
        HRFlowable(width="100%", thickness=0.6, color=LIGHT, spaceAfter=4),
    ]


def bullets(items):
    return [Paragraph(f"• {item}", bullet) for item in items]


story = [
    Paragraph("ARTIOM GUTU", name),
    Paragraph("Python Automation Engineer | APIs, Agentic Systems and Reliable Workflows", headline),
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
        "First-Class BSc (Hons) Computer Science graduate who builds Python automation and "
        "agentic systems around explicit interfaces, persistent state and deterministic checks. "
        "I have designed concurrent API and feed collectors, SQLite-backed pipelines, schema-bound "
        "model integrations, restart recovery, test gates and auditable reporting. I am comfortable "
        "debugging failures across HTTP requests, structured data, process execution and configuration. "
        "My closest evidence for MCP-style tool integration is the explicit tool and capability "
        "architecture I designed for a three-generation multi-agent software factory. Eligible to work "
        "as a UK-based independent contractor without sponsorship and available from October 2026.",
        body,
    )
]

story += heading("Technical skills")
story += [
    Paragraph("<b>Python and data:</b> Python, SQL, SQLite, JSON/JSONL, YAML, XML/RSS, REST APIs", small),
    Paragraph(
        "<b>Backend and automation:</b> concurrent ingestion, API integration, schema validation, "
        "HTTP failure handling, retries, caching, resumable pipelines and process supervision",
        small,
    ),
    Paragraph(
        "<b>Engineering:</b> Git, automated testing, configuration-driven workflows, structured "
        "logging, content hashing, audit trails and local CLI validation",
        small,
    ),
    Paragraph(
        "<b>AI systems:</b> model routing, agent workflows, scoped tool capabilities, independent "
        "review gates and deterministic validation around probabilistic outputs",
        small,
    ),
]

story += heading("Selected projects")
story += [
    KeepTogether([
        Paragraph("Market Aligner | Python job-intelligence pipeline", role),
        Paragraph("Python, SQLite, REST APIs, RSS/XML, structured data and testing", meta),
        *bullets([
            "I designed and implemented an uncapped concurrent collector spanning 18 API and feed adapters, with append-preserving SQLite storage and raw-response caching.",
            "I implemented structured validation, retries, resumable processing and model-backend routing so interrupted collection and analysis can continue from stored state.",
            "I kept collection, eligibility filtering, deduplication, arithmetic scoring, persistence and reporting deterministic while confining LLMs to schema-bound extraction and evidence-led judgement.",
        ]),
    ]),
    KeepTogether([
        Paragraph("Three-generation multi-agent software factory | Tool-driven software delivery", role),
        Paragraph("Python control plane, capability boundaries, isolated execution, evidence and recovery", meta),
        *bullets([
            "I evolved the system through three generations. V1 proved unattended multi-agent coordination; after prose-only rules drifted, I redesigned V2 around executable dependency checks, capability boundaries and staged self-certification.",
            "I designed V3's plan, build, test, independent-judge, certify, improve and recertify loop, including scoped task contracts, cross-provider model routing, revision-bound evidence, disposable worktrees and restart recovery.",
            "I directed an adversarial audit, repaired false-success and unsafe-runtime paths from its P0/P1 findings, and completed a live end-to-end canary. The verified suite reached 3,482 passing tests, four skips and no failures.",
            "I own the requirements, architecture, governance, model routing and acceptance decisions. AI agents produced substantial implementation code; I do not claim personal authorship of every component.",
        ]),
    ]),
    KeepTogether([
        Paragraph("SCAFAD | First-Class Computer Science dissertation", role),
        Paragraph("Python, AWS Lambda, CloudWatch, anomaly detection and security evaluation", meta),
        *bullets([
            "I designed a serverless anomaly-detection study around AWS Lambda telemetry.",
            "I evaluated telemetry collection, graph methods, privacy, adversarial testing and explainability.",
        ]),
    ]),
]

story.append(PageBreak())
story += heading("Evidence relevant to this role")
story += bullets([
    "<b>API and backend work:</b> I implemented collectors against multiple APIs and feeds, normalized heterogeneous responses, stored raw and structured records, and handled HTTP failures without discarding prior data.",
    "<b>State and reproducibility:</b> I designed resumable stages, raw-response caching, append-preserving storage and content-addressed evidence so a failed or restarted run can recover without repeating trusted work.",
    "<b>Tool and capability design:</b> I designed explicit capability contracts and minimum-context tool access for agents, with fail-closed dispatch when requirements or evidence are missing.",
    "<b>Testing and debugging:</b> I use deterministic test gates, structured logs, isolated workspaces and real canary runs to distinguish a passing unit suite from a workflow that actually completes.",
    "<b>Configuration and deployment boundaries:</b> I designed configuration-driven model routing and executable architecture checks for local Python control planes, with failures surfaced through deterministic gates rather than silently accepted.",
])

story += heading("Education")
story += [
    Paragraph("BSc (Hons) Computer Science, First-Class Honours", role),
    Paragraph("Birmingham Newman University | Graduated 2 July 2026", meta),
    Paragraph(
        "Dissertation: SCAFAD, a serverless anomaly-detection project using AWS Lambda telemetry. "
        "Relevant work included Python, CloudWatch data, graph methods, adversarial testing, privacy "
        "and research evaluation.",
        body,
    ),
]

story += heading("Additional experience")
story += [
    Paragraph("Founder and Managing Director | Excellence Exalted Limited", role),
    *bullets([
        "I registered a UK language-teaching company, defined the initial service, recruited the first teacher and managed its early administration.",
    ]),
    Paragraph("Paid Online English Tutor", role),
    *bullets([
        "I planned and delivered one-to-one lessons and adapted explanations to each learner's recurring weaknesses.",
    ]),
    Paragraph("Direct Sales Agent | Appco UK", role),
    *bullets([
        "I developed practical experience in prospecting, objection handling and clear communication with unfamiliar customers.",
    ]),
]

story += heading("Languages")
story += [Paragraph("Fluent in English, Romanian and Russian", body)]


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
    title="Artiom Gutu - CV - Mercor Software Engineer Expert",
    author="Artiom Gutu",
    subject="Application for Software Engineer Expert",
)
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(PDF)

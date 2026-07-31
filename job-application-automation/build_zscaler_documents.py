from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer


OUT = Path(__file__).parent / "applications" / "rank-17-zscaler"
OUT.mkdir(parents=True, exist_ok=True)
CV = OUT / "Artiom_Gutu_CV_Zscaler.pdf"
LETTER = OUT / "Artiom_Gutu_Cover_Letter_Zscaler.pdf"

pdfmetrics.registerFont(TTFont("Arial", "/System/Library/Fonts/Supplemental/Arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"))

INK = colors.HexColor("#111827")
BLUE = colors.HexColor("#174E75")
MUTED = colors.HexColor("#4B5563")
LIGHT = colors.HexColor("#CBD5E1")
base = getSampleStyleSheet()
name = ParagraphStyle("name", parent=base["Normal"], fontName="Arial-Bold", fontSize=22,
                      leading=25, alignment=TA_CENTER, textColor=INK, spaceAfter=3)
headline = ParagraphStyle("headline", parent=base["Normal"], fontName="Arial", fontSize=10.5,
                          leading=13, alignment=TA_CENTER, textColor=BLUE, spaceAfter=4)
contact = ParagraphStyle("contact", parent=base["Normal"], fontName="Arial", fontSize=8.7,
                         leading=11, alignment=TA_CENTER, textColor=MUTED, spaceAfter=7)
section = ParagraphStyle("section", parent=base["Heading2"], fontName="Arial-Bold", fontSize=10.5,
                         leading=13, textColor=BLUE, spaceBefore=7, spaceAfter=3)
body = ParagraphStyle("body", parent=base["Normal"], fontName="Arial", fontSize=9.3,
                      leading=12.2, textColor=INK, spaceAfter=4)
role = ParagraphStyle("role", parent=body, fontName="Arial-Bold", fontSize=9.7,
                      leading=12, spaceBefore=3, spaceAfter=1)
meta = ParagraphStyle("meta", parent=body, fontSize=8.8, leading=11, textColor=MUTED, spaceAfter=2)
bullet = ParagraphStyle("bullet", parent=body, leftIndent=4.5*mm, firstLineIndent=-3.2*mm, spaceAfter=2)
letter_body = ParagraphStyle("letter", parent=base["Normal"], fontName="Arial", fontSize=10.3,
                             leading=15, textColor=INK, spaceAfter=10)


def heading(text):
    return [Paragraph(text.upper(), section),
            HRFlowable(width="100%", thickness=.6, color=LIGHT, spaceAfter=4)]


def bullets(items):
    return [Paragraph("• " + item, bullet) for item in items]


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Arial", 8)
    canvas.setFillColor(MUTED)
    canvas.drawCentredString(A4[0]/2, 10*mm, f"Artiom Gutu | Page {doc.page}")
    canvas.restoreState()


story = [
    Paragraph("ARTIOM GUTU", name),
    Paragraph("Associate Sales Engineering Candidate | AI Automation, Technical Discovery and Demonstration", headline),
    Paragraph(
        "Wolverhampton, United Kingdom &nbsp;|&nbsp; +44 7561 447187 &nbsp;|&nbsp; "
        "gutu.artiom444@gmail.com &nbsp;|&nbsp; "
        '<link href="https://github.com/Pepstee" color="#174E75">github.com/Pepstee</link>',
        contact),
]
story += heading("Profile")
story += [Paragraph(
    "First-Class BSc (Hons) Computer Science graduate combining hands-on AI automation with customer-facing "
    "sales and teaching experience. I design technical systems, investigate what users need and explain complex "
    "workflows in concrete terms. My work includes Python, APIs, HTTP-based services, sandboxed agent execution, "
    "structured demonstrations, testing and reusable technical documentation. UK work-authorised without "
    "sponsorship, available from October 2026 and willing to travel regionally.", body)]
story += heading("Relevant capabilities")
story += [
    Paragraph("<b>Technical:</b> Python, REST APIs, HTTP, DNS and TCP/IP fundamentals, SQL, SQLite, JSON, YAML, "
              "AWS Lambda, CloudWatch, Git, automated testing and structured logging", body),
    Paragraph("<b>AI and demonstrations:</b> LLM workflows, agent systems, model routing, schema validation, "
              "sandbox-style isolated execution, evidence-led review and technical walkthroughs", body),
    Paragraph("<b>Customer-facing:</b> discovery questions, objection handling, one-to-one teaching, adapting "
              "explanations, service design and written instructional material", body),
]
story += heading("Selected projects")
story += [
    Paragraph("Market Aligner | Python job-intelligence and decision system", role),
    Paragraph("Python, APIs, SQLite, concurrent collection, LLM workflows and reporting", meta),
    *bullets([
        "I designed and implemented a pipeline spanning 18 API and feed adapters, with concurrent collection, raw-response caching and append-preserving SQLite storage.",
        "I translated ambiguous vacancy requirements into structured evidence while keeping filtering, deduplication, scoring and reporting deterministic.",
        "I designed auditable reports and resumable stages so users can understand why a job was recommended and recover interrupted work.",
    ]),
    Paragraph("Three-generation multi-agent software factory", role),
    Paragraph("Technical architecture, isolated environments, governance, testing and demonstrations", meta),
    *bullets([
        "I evolved the system across three generations, converting prose-only rules into executable dependency checks, capability boundaries and staged certification.",
        "I designed V3's plan, build, test, independent-review, certify and recovery loop, including isolated worktrees and fail-closed dispatch.",
        "I directed an adversarial audit and live end-to-end canary. The verified suite reached 3,482 passing tests, four skips and no failures.",
        "I own requirements, architecture, model routing and acceptance decisions; AI agents produced substantial implementation code.",
    ]),
    Paragraph("SCAFAD | First-Class Computer Science dissertation", role),
    *bullets([
        "I designed a serverless anomaly-detection study using AWS Lambda and CloudWatch telemetry.",
        "I evaluated graph methods, privacy, adversarial testing and explainability in a security context.",
    ]),
]
story.append(PageBreak())
story += heading("Commercial and communication experience")
story += [
    Paragraph("Founder and Managing Director | Excellence Exalted Limited", role),
    *bullets(["I defined the initial language-teaching service, recruited the first teacher and managed early operational and customer decisions."]),
    Paragraph("Paid Online English Tutor", role),
    *bullets(["I plan and deliver one-to-one lessons, identify the learner's actual difficulty and change the explanation until it becomes usable."]),
    Paragraph("Direct Sales Agent | Appco UK", role),
    *bullets(["I approached unfamiliar customers, asked discovery questions, handled objections and learned to connect a service to the customer's priorities."]),
]
story += heading("Evidence for sales engineering")
story += bullets([
    "I can move between business language and implementation detail: Market Aligner turns broad job-market questions into traceable technical outputs.",
    "I design demonstrations around observable evidence rather than claims, using canary runs, logs and deterministic checks to show whether a workflow works.",
    "I have built reusable explanations and documentation for technical and non-technical audiences through software projects and paid teaching.",
    "My current gaps are product-specific Zscaler knowledge and commercial cybersecurity pre-sales; this associate role is the correct environment in which to develop them.",
])
story += heading("Education")
story += [
    Paragraph("BSc (Hons) Computer Science, First-Class Honours", role),
    Paragraph("Birmingham Newman University | Graduated 2 July 2026", meta),
]
story += heading("Languages")
story += [Paragraph("Fluent in English, Romanian and Russian", body)]

doc = SimpleDocTemplate(str(CV), pagesize=A4, rightMargin=15*mm, leftMargin=15*mm,
                        topMargin=13*mm, bottomMargin=16*mm,
                        title="Artiom Gutu - CV - Zscaler Associate Sales Engineer",
                        author="Artiom Gutu")
doc.build(story, onFirstPage=footer, onLaterPages=footer)

letter = [
    Paragraph("ARTIOM GUTU", name),
    Paragraph("Wolverhampton, United Kingdom | +44 7561 447187 | gutu.artiom444@gmail.com", contact),
    Spacer(1, 8*mm),
    Paragraph("23 July 2026", letter_body),
    Paragraph("<b>Zscaler Hiring Team</b><br/>Re: Associate Sales Engineer – Solutions Center", letter_body),
    Paragraph("Dear Zscaler Hiring Team,", letter_body),
    Paragraph(
        "I am applying for the Associate Sales Engineer position because it combines three areas in which "
        "I already have practical experience: explaining technical systems clearly, understanding what a "
        "user actually needs, and turning that need into a working solution.", letter_body),
    Paragraph(
        "I recently graduated with First-Class Honours in Computer Science. My main technical work has focused "
        "on Python automation, AI systems and dependable software workflows. I designed Market Aligner, a system "
        "that collects vacancies from multiple APIs and feeds, standardises their requirements and produces an "
        "evidence-backed application queue. I also designed and operate a three-generation multi-agent software "
        "factory with isolated execution, automated testing, independent review and certification gates. These "
        "projects required me to break complicated architectures into understandable components, investigate "
        "failures and demonstrate why a proposed solution could be trusted.", letter_body),
    Paragraph(
        "My commercial experience is also relevant. As a direct sales agent at Appco UK, I learned how to "
        "approach unfamiliar customers, ask questions, handle objections and adapt an explanation to the person "
        "in front of me. As an online English tutor, I regularly translate difficult concepts into clear, "
        "practical explanations and change my approach when the first explanation does not work. I later founded "
        "Excellence Exalted Limited, where I defined the initial service and recruited its first teacher.", letter_body),
    Paragraph(
        "I do not yet have professional experience selling enterprise cybersecurity products. I do understand "
        "core networking concepts, HTTP-based systems, AI-assisted workflows and the discipline required to "
        "learn a technical platform properly. I am particularly interested in building that knowledge through "
        "Zscaler's Solution Center, supporting demonstrations and sandbox environments, and learning from "
        "experienced Sales Engineers during real partner engagements.", letter_body),
    Paragraph(
        "I would bring technical curiosity, direct customer-facing experience and a habit of testing claims "
        "against working evidence. I am eligible to work in the UK without sponsorship, based in Wolverhampton "
        "and willing to travel when required.", letter_body),
    Paragraph("Yours faithfully,<br/><br/><b>Artiom Gutu</b>", letter_body),
]
letter_doc = SimpleDocTemplate(str(LETTER), pagesize=A4, rightMargin=22*mm, leftMargin=22*mm,
                               topMargin=18*mm, bottomMargin=18*mm,
                               title="Artiom Gutu - Cover Letter - Zscaler",
                               author="Artiom Gutu")
letter_doc.build(letter)
print(CV)
print(LETTER)

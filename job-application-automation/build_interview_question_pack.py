import json
import re
from collections import Counter
from pathlib import Path


SOURCE = Path("/Users/admin/Claude/Projects/Korea Job Scraper/skeleton/data_overnight/jobs_scored.jsonl")
OUT = Path("/Users/admin/Documents/giga-user/job-application-automation/interview-preparation")
OUT.mkdir(parents=True, exist_ok=True)

# Each tuple is: category, question, comma-separated evidence signals, what the interviewer tests.
QUESTIONS = [
    ("Python", "Walk me through the most substantial Python system you have built. What did you personally design and implement?", "python", "Implementation depth and truthful ownership"),
    ("Python", "How would you structure a production Python service so that it remains testable and maintainable as it grows?", "python,testing,maintainability", "Software structure and engineering judgement"),
    ("Python", "Explain Python's concurrency options. When would you choose threads, processes or asyncio?", "python,concurrency,async", "Concurrency fundamentals"),
    ("Python", "Describe a difficult Python bug you diagnosed. How did you isolate the cause?", "python,debugging,troubleshoot", "Debugging method"),
    ("Python", "How do you validate untrusted or malformed input in a Python pipeline?", "python,validation,schema,pydantic", "Boundary validation"),
    ("Python", "How would you make a long-running Python job resumable after interruption?", "python,resumable,retry,checkpoint", "State and recovery design"),
    ("Python", "What makes an API client reliable in production?", "python,api,retry,http", "HTTP reliability"),
    ("Python", "How do you design useful exceptions and error handling without hiding failures?", "python,error,exception,debug", "Failure semantics"),
    ("Python", "How do you profile and improve a slow Python workflow?", "python,performance,profil", "Performance diagnosis"),
    ("Python", "How would you package, configure and deploy a Python application?", "python,deploy,configuration", "Delivery fundamentals"),
    ("Python", "What testing pyramid would you use for a Python integration service?", "python,testing,unit,integration", "Testing strategy"),
    ("Python", "How do type hints, dataclasses and schemas change the reliability of Python code?", "python,type,pydantic,schema", "Static and runtime contracts"),
    ("Python", "Explain a case where caching improved a system, and how you prevented stale or incorrect results.", "python,cache,caching", "Caching correctness"),
    ("Python", "How would you process thousands of independent records efficiently without losing failed items?", "python,batch,concurrency,queue", "Bulk-processing architecture"),
    ("Python", "What would you inspect first if a Python service works locally but fails in its runtime environment?", "python,environment,permission,deploy", "Environment debugging"),

    ("Backend & APIs", "Design an API for submitting work, checking status and retrieving results.", "api,backend,rest", "API and state-machine design"),
    ("Backend & APIs", "How do you make a POST endpoint idempotent?", "api,idempotent,backend", "Duplicate prevention"),
    ("Backend & APIs", "Explain authentication versus authorization and where each should be enforced.", "api,authentication,authorization,security", "Access-control fundamentals"),
    ("Backend & APIs", "How would you version an API without breaking existing clients?", "api,version,backward", "Compatibility planning"),
    ("Backend & APIs", "What data would you log for an API request, and what must never be logged?", "api,logging,security,privacy", "Observability and privacy"),
    ("Backend & APIs", "How would you diagnose intermittent 5xx errors across multiple services?", "api,debug,observability,service", "Distributed debugging"),
    ("Backend & APIs", "When should work be synchronous, asynchronous or queue-backed?", "api,queue,asynchronous,backend", "Workload design"),
    ("Backend & APIs", "Explain rate limiting and backpressure. How would you implement them?", "api,rate limit,backpressure", "Traffic protection"),
    ("Backend & APIs", "How would you integrate a third-party API that is slow, unreliable and poorly documented?", "api,integration,retry,third-party", "Integration resilience"),
    ("Backend & APIs", "How do webhooks work, and how would you make webhook processing safe and idempotent?", "api,webhook,idempotent", "Event integration"),
    ("Backend & APIs", "What are the trade-offs between REST, GraphQL and event-driven interfaces?", "api,rest,graphql,event", "Interface selection"),
    ("Backend & APIs", "How would you design health checks and readiness checks for a service?", "api,health,deploy,service", "Operational readiness"),

    ("Databases & Data", "How would you choose between PostgreSQL, SQLite and a NoSQL store for a new service?", "sql,sqlite,postgres,database", "Storage selection"),
    ("Databases & Data", "Explain indexes and a case where the wrong index makes performance worse.", "sql,index,database", "Database performance"),
    ("Databases & Data", "How do transactions and isolation levels prevent inconsistent data?", "sql,transaction,database", "Consistency fundamentals"),
    ("Databases & Data", "How would you model jobs, applications, evidence and status history in a relational database?", "sql,database,data model", "Schema design"),
    ("Databases & Data", "How do you perform a safe schema migration on a live system?", "sql,migration,database", "Change safety"),
    ("Databases & Data", "How would you deduplicate records arriving from multiple sources?", "data,dedup,canonical", "Entity resolution"),
    ("Databases & Data", "What checks would you use to detect corrupt, incomplete or drifting data?", "data,quality,validation", "Data quality"),
    ("Databases & Data", "Explain ETL versus ELT and where validation belongs in each.", "data,etl,pipeline", "Pipeline architecture"),
    ("Databases & Data", "How would you preserve raw source data while producing a clean analytical model?", "data,raw,provenance,pipeline", "Provenance and reproducibility"),
    ("Databases & Data", "How would you calculate and communicate confidence in an extracted field?", "data,confidence,extraction", "Uncertainty handling"),

    ("Cloud & DevOps", "Describe how you would deploy a containerised service to AWS.", "aws,docker,deploy,cloud", "Cloud deployment"),
    ("Cloud & DevOps", "What problem does Docker solve, and what belongs in an effective Dockerfile?", "docker,container", "Container fundamentals"),
    ("Cloud & DevOps", "Explain Kubernetes pods, deployments, services and ingress.", "kubernetes,container,cloud", "Kubernetes fundamentals"),
    ("Cloud & DevOps", "When is Kubernetes unnecessary?", "kubernetes,architecture,cloud", "Complexity judgement"),
    ("Cloud & DevOps", "How would you debug a container that starts locally but crashes in production?", "docker,debug,container,production", "Runtime diagnosis"),
    ("Cloud & DevOps", "Explain infrastructure as code and how you would review an infrastructure change.", "terraform,infrastructure as code,cloud", "Infrastructure governance"),
    ("Cloud & DevOps", "How do CI and continuous delivery differ?", "ci/cd,continuous integration,deploy", "Delivery concepts"),
    ("Cloud & DevOps", "Design a CI pipeline for a Python service from commit to deployment.", "ci/cd,python,testing,deploy", "Delivery pipeline"),
    ("Cloud & DevOps", "What is a safe rollback strategy after a bad deployment?", "deploy,rollback,release", "Release recovery"),
    ("Cloud & DevOps", "How would you manage secrets across local development, CI and production?", "secret,security,cloud,ci/cd", "Secret lifecycle"),
    ("Cloud & DevOps", "Explain horizontal versus vertical scaling and the bottlenecks each can expose.", "scalability,cloud,performance", "Scaling judgement"),
    ("Cloud & DevOps", "How would you design a highly available service across failure zones?", "availability,aws,cloud,reliability", "Resilience architecture"),
    ("Cloud & DevOps", "Compare AWS Lambda with a long-running container service.", "aws,lambda,serverless,container", "Compute-model trade-offs"),
    ("Cloud & DevOps", "What Linux commands and signals do you use first when diagnosing a failing service?", "linux,debug,service", "Linux operations"),
    ("Cloud & DevOps", "Explain DNS resolution and what you would inspect when a hostname intermittently fails.", "dns,network,debug", "Networking diagnosis"),
    ("Cloud & DevOps", "Explain TCP, HTTP and TLS at the level needed to debug a failed request.", "tcp,http,tls,network", "Protocol understanding"),
    ("Cloud & DevOps", "Which metrics, logs and traces would you add before calling a service production-ready?", "observability,metrics,logging,tracing", "Operational visibility"),

    ("AI & ML", "Describe an AI or ML system you built and the exact boundary between model behaviour and deterministic code.", "ai,ml,llm,model", "AI-system architecture"),
    ("AI & ML", "How do you evaluate an LLM feature beyond showing a few convincing examples?", "llm,evaluation,ai", "Evaluation rigour"),
    ("AI & ML", "How would you detect and reduce hallucinations in a production workflow?", "llm,hallucination,validation", "Reliability controls"),
    ("AI & ML", "When should you use retrieval, fine-tuning or prompt engineering?", "rag,retrieval,fine-tun,prompt", "Technique selection"),
    ("AI & ML", "Design a RAG pipeline and explain where retrieval quality can fail.", "rag,retrieval,embedding,vector", "RAG architecture"),
    ("AI & ML", "How would you choose an embedding model and evaluate semantic search?", "embedding,vector,retrieval", "Retrieval evaluation"),
    ("AI & ML", "How do temperature, sampling and context affect LLM output?", "llm,temperature,context,prompt", "Model behaviour"),
    ("AI & ML", "How would you enforce a structured JSON contract on model output?", "llm,json,schema,structured", "Schema-bound generation"),
    ("AI & ML", "What should be cached in an LLM pipeline, and what invalidates that cache?", "llm,cache,prompt", "Cost and correctness"),
    ("AI & ML", "How would you route work between different models?", "llm,model routing,ai", "Cost-capability routing"),
    ("AI & ML", "Explain precision, recall and F1 using a real decision threshold.", "machine learning,precision,recall,f1", "ML metrics"),
    ("AI & ML", "How do you prevent train-test leakage?", "machine learning,training,test,leakage", "Evaluation validity"),
    ("AI & ML", "What causes model drift and how would you monitor it?", "machine learning,drift,monitor", "Post-deployment ML"),
    ("AI & ML", "How would you turn a notebook experiment into a reliable service?", "machine learning,deploy,mlops,notebook", "MLOps transition"),
    ("AI & ML", "What does reproducibility require in an ML experiment?", "machine learning,reproducibility,experiment", "Experiment discipline"),
    ("AI & ML", "How would you explain an ML model's decision to a non-technical stakeholder?", "machine learning,explainability,communication", "Technical communication"),

    ("Agentic Systems", "What makes an agent different from a scripted workflow, and when is an agent the wrong choice?", "agent,agentic,workflow,llm", "Agent judgement"),
    ("Agentic Systems", "How would you constrain an agent's tools and permissions?", "agent,tool,permission,security", "Capability security"),
    ("Agentic Systems", "How do you stop an agent loop from wasting time or tokens?", "agent,loop,token,cost", "Runaway-loop control"),
    ("Agentic Systems", "How would you make an agent workflow resumable and auditable?", "agent,resumable,audit,evidence", "Durable orchestration"),
    ("Agentic Systems", "What evidence should an independent reviewer require before certifying an agent's work?", "agent,review,certif,evidence", "Assurance design"),
    ("Agentic Systems", "How do you defend an agent from prompt injection in external content?", "agent,prompt injection,security,untrusted", "Agent security"),
    ("Agentic Systems", "How would you evaluate whether a multi-agent design is better than one strong agent?", "multi-agent,agent,evaluation", "Architecture evidence"),
    ("Agentic Systems", "Describe a failure in your orchestrator and the concrete control you added because of it.", "orchestrator,agent,failure,governance", "Learning from failure"),

    ("Security", "Explain least privilege and how you applied it in a system.", "security,least privilege,permission", "Security design"),
    ("Security", "How do you threat-model a new API or automation workflow?", "security,threat model,api", "Threat analysis"),
    ("Security", "How would you handle a suspected secret leak in a repository?", "security,secret,incident", "Incident response"),
    ("Security", "What are the main web application risks you would check before release?", "security,owasp,web", "Application security breadth"),
    ("Security", "How would you validate and sandbox untrusted files or web content?", "security,sandbox,untrusted,input", "Untrusted-input handling"),
    ("Security", "What is Zero Trust, and how is it different from trusting an internal network?", "zero trust,security,network", "Zscaler-relevant security understanding"),
    ("Security", "Explain secure web gateways, ZTNA, DLP and CASB in practical terms.", "ztna,secure web gateway,dlp,casb,security", "Cloud-security product concepts"),
    ("Security", "How would you investigate anomalous behaviour in a serverless workload?", "security,anomaly,serverless,cloudwatch", "Security analytics"),

    ("Behavioural & Delivery", "Tell me about the most ambiguous project you owned. How did you turn it into executable work?", "ambiguity,ownership,startup", "Operating under ambiguity"),
    ("Behavioural & Delivery", "Tell me about a time you received difficult feedback and changed your approach.", "feedback,coachable,communication", "Coachability"),
    ("Behavioural & Delivery", "Describe a time you disagreed with a technical decision. What did you do?", "disagree,communication,decision", "Constructive challenge"),
    ("Behavioural & Delivery", "Tell me about a deadline you were at risk of missing. How did you respond?", "deadline,delivery,time", "Reliability"),
    ("Behavioural & Delivery", "Give an example of a mistake you made and how you prevented recurrence.", "mistake,failure,learning", "Accountability"),
    ("Behavioural & Delivery", "How do you decide what to automate and what to keep manual?", "automation,priority,decision", "Automation judgement"),
    ("Behavioural & Delivery", "How do you prioritise when several urgent tasks compete?", "priority,urgent,delivery", "Execution discipline"),
    ("Behavioural & Delivery", "Tell me about a process you improved. What measurable change resulted?", "improvement,process,impact", "Outcome orientation"),
    ("Behavioural & Delivery", "How do you communicate uncertainty or bad news early?", "communication,uncertainty,problem", "Transparency"),
    ("Behavioural & Delivery", "Describe a project where the evidence contradicted your original plan.", "evidence,decision,change", "Evidence-led adaptation"),
    ("Behavioural & Delivery", "What part of a recent project did AI produce, and what did you personally own?", "ai,ownership,agent", "Authorship integrity"),
    ("Behavioural & Delivery", "Why this role, and why this company rather than another AI or software employer?", "motivation,company,role", "Specific motivation"),

    ("Customer & Sales Engineering", "How would you run a first technical discovery call with a customer?", "customer,discovery,sales,stakeholder", "Discovery structure"),
    ("Customer & Sales Engineering", "Explain one of your technical projects to a non-technical buyer in two minutes.", "customer,communication,present,explain", "Clarity and relevance"),
    ("Customer & Sales Engineering", "How would you prepare and deliver a reliable live product demonstration?", "demo,demonstration,sales,presentation", "Demo planning"),
    ("Customer & Sales Engineering", "A customer says the product is too complex. How do you respond?", "customer,objection,sales,communication", "Objection handling"),
    ("Customer & Sales Engineering", "How do you translate a customer's business problem into technical requirements?", "customer,requirements,architecture,sales", "Solution mapping"),
    ("Customer & Sales Engineering", "What would you do if a live demo failed in front of a customer?", "demo,failure,customer,troubleshoot", "Composure and recovery"),
    ("Customer & Sales Engineering", "How would you create reusable enablement material after solving a partner's problem?", "partner,documentation,training,enablement", "Knowledge reuse"),
    ("Customer & Sales Engineering", "Tell me about a time you changed your explanation because the listener was not convinced.", "communication,teaching,customer,objection", "Adaptive communication"),
    ("Customer & Sales Engineering", "How would you prove that a proposed automation produces business value?", "customer,automation,value,metric", "Value engineering"),
    ("Customer & Sales Engineering", "What questions would you ask before recommending a cloud or security architecture?", "customer,discovery,cloud,security,architecture", "Consultative judgement"),
]

assert len(QUESTIONS) >= 100, len(QUESTIONS)

jobs = [json.loads(line) for line in SOURCE.read_text().splitlines() if line.strip()]

def normalise(value):
    if isinstance(value, list):
        value = " ".join(map(str, value))
    return re.sub(r"[_/\\-]+", " ", str(value or "")).lower()

for job in jobs:
    job["_text"] = normalise([
        job.get("job_title"), job.get("mapped_career"), job.get("job_description"),
        job.get("required_skills"), job.get("preferred_skills"), job.get("required_software"),
        job.get("responsibilities"), job.get("skills_to_learn"),
    ])

CATEGORY_EVIDENCE = {
    "Python": "Market Aligner: personally designed and implemented Python collectors, validation, caching, SQLite persistence, retries and resumability.",
    "Backend & APIs": "Market Aligner provides API-integration evidence. Keep claims at pipeline/integration level unless you can point to a verified server implementation.",
    "Databases & Data": "Use Market Aligner's raw-plus-structured SQLite design, deduplication, provenance, caching and ranked reporting.",
    "Cloud & DevOps": "Use SCAFAD for AWS Lambda/CloudWatch research exposure and the orchestrator for isolated execution and assurance. Do not claim production Kubernetes or Docker ownership without new evidence.",
    "AI & ML": "Use SCAFAD for anomaly-detection research and Market Aligner for schema-bound LLM judgement, model routing and deterministic evaluation boundaries.",
    "Agentic Systems": "Use the three-generation orchestrator: requirements, architecture, capability boundaries, model routing, audits, canary and 3,482-pass suite. State that agents wrote substantial implementation code.",
    "Security": "Use SCAFAD, prompt-injection boundaries in Market Aligner, least-privilege capability design and adversarial audits. Separate research exposure from production security employment.",
    "Behavioural & Delivery": "Answer with one concrete incident, decision, result and lesson. Prefer orchestrator failures, Market Aligner recovery, teaching or direct-sales examples.",
    "Customer & Sales Engineering": "Use Appco objection handling, paid tutoring, Excellence Exalted service design and technical demonstrations. Do not imply enterprise pre-sales experience.",
}

records = []
for idx, (category, question, signal_csv, tests) in enumerate(QUESTIONS, 1):
    signals = [normalise(x).strip() for x in signal_csv.split(",") if x.strip()]
    matched = []
    for job in jobs:
        hits = sum(
            1 for signal in signals
            if re.search(r"(?<![a-z0-9])" + re.escape(signal) + r"(?![a-z0-9])", job["_text"])
        )
        if hits:
            matched.append((hits, float(job.get("final") or 0), job))
    matched.sort(key=lambda x: (x[0], x[1]), reverse=True)
    support_jobs = {m[2].get("job_id") or m[2].get("url") for m in matched}
    companies = []
    roles = []
    urls = []
    for _, _, job in matched:
        company = str(job.get("company") or "").strip()
        role = str(job.get("job_title") or "").strip()
        url = str(job.get("url") or "").strip()
        if company and company not in companies:
            companies.append(company)
        if role and role not in roles:
            roles.append(role)
        if url and url not in urls:
            urls.append(url)
        if len(companies) >= 5 and len(roles) >= 5 and len(urls) >= 3:
            break
    count = len(support_jobs)
    prevalence = count / len(jobs)
    records.append({
        "draft_order": idx,
        "category": category,
        "question": question,
        "tests": tests,
        "signals": ", ".join(signals),
        "supporting_jobs": count,
        "prevalence": prevalence,
        "top_companies": "; ".join(companies[:5]),
        "example_roles": "; ".join(roles[:5]),
        "source_urls": "\n".join(urls[:3]),
        "evidence_prompt": CATEGORY_EVIDENCE[category],
        "answer_framework": "Situation/context → your exact action/design → observable result/evidence → limitation or lesson",
        "target_minutes": 3,
        "status": "Not started",
        "answer_notes": "",
    })

# Rank primarily by corpus support, retaining category coverage through a modest curated-order prior.
for r in records:
    r["priority_score"] = round(100 * r["prevalence"] + max(0, 12 - r["draft_order"] * 0.04), 2)
records.sort(key=lambda r: (r["priority_score"], r["supporting_jobs"]), reverse=True)
records = records[:100]
for rank, record in enumerate(records, 1):
    record["rank"] = rank

category_summary = []
for category in dict.fromkeys(q[0] for q in QUESTIONS):
    rows = [r for r in records if r["category"] == category]
    category_summary.append({
        "category": category,
        "question_count": len(rows),
        "minutes": sum(r["target_minutes"] for r in rows),
        "avg_supporting_jobs": round(sum(r["supporting_jobs"] for r in rows) / len(rows), 1),
        "top_rank": min(r["rank"] for r in rows),
        "evidence_boundary": CATEGORY_EVIDENCE[category],
    })

job_summary = [{
    "company": j.get("company"),
    "job_title": j.get("job_title"),
    "mapped_career": j.get("mapped_career"),
    "fit": j.get("fit"),
    "opportunity": j.get("opportunity"),
    "final": j.get("final"),
    "location": j.get("location"),
    "url": j.get("url"),
    "why_it_fits": j.get("why_it_fits"),
} for j in sorted(jobs, key=lambda j: float(j.get("final") or 0), reverse=True)]

(OUT / "questions.json").write_text(json.dumps(records, ensure_ascii=False, indent=2))
(OUT / "category_summary.json").write_text(json.dumps(category_summary, ensure_ascii=False, indent=2))
(OUT / "source_jobs.json").write_text(json.dumps(job_summary, ensure_ascii=False, indent=2))
print(f"questions={len(records)} jobs={len(jobs)} total_minutes={sum(r['target_minutes'] for r in records)}")
print(Counter(r["category"] for r in records))

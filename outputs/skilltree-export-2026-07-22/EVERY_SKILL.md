# Every skill in the SkillTree graph

This is an exhaustive inventory of every skill-like object in the exported graph. The source uses three distinct concepts, so all three are listed rather than silently collapsing them:

- **79 named skill files** — deployable skill-file references; 78 have public preview text.
- **291 atomic capabilities** — implementation-level abilities attached to jobs.
- **137 jobs** — the visible AI-workforce nodes in the map.

The preview page does not expose the paid runnable skill-file contents. This inventory records every public title, path, explanation, requirement, mapping, and preview-availability flag without bypassing access controls.

## 1. Named skill files

| # | Skill | File reference | Preview | Department(s) | Mapped job(s) | Public explanation | Requirements |
|---:|---|---|:---:|---|---|---|---|
| 1 | Billing Manager | `skills/billing-manager.md` | Yes | Back Office | Collections; Invoice Generation; Payment Tracking | The Billing Manager owns the path from 'deal closed' to 'money in the bank.' It generates branded invoices from your deal records · correct entity, correct currency, correct tax treatment, every time. | Stripe, Wise_Api (optional · degrades gracefully) |
| 2 | Brand Deal Producer | `skills/brand-deal-producer.md` | Yes | Marketing | Approval Docs; Deal Scripting | The Brand Deal Producer handles the production paperwork of sponsored content · the part that stalls deals for weeks. | No API keys |
| 3 | Brand Visual Designer | `skills/brand-visual-designer.md` | Yes | Marketing | Image Generation; Thumbnail & Cover Design | Brand Image Generator | Fal (optional · degrades gracefully) |
| 4 | Business Data Analyst | `skills/business-data-analyst.md` | Yes | Intelligence | Data Visualization | Ask your data a plain-English question and get the answer first, then the exact calculation behind it. Profiles data quality before concluding, runs a weekly KPI digest, and is honest when the data can't answer. | Supabase / Postgres, Google Sheets (optional · read-only) |
| 5 | Buying Signals Analyst | `skills/buying-signals-analyst.md` | Yes | Sales | Trigger Detection | The Buying Signals Analyst watches your target accounts for the events that turn a cold company into a warm one · hiring sprees, funding rounds, tech stack changes, leadership moves. | Apify, Apollo, Exa (optional · degrades gracefully) |
| 6 | Call Prep Researcher | `skills/call-prep-researcher.md` | Yes | Deals | Pre-Call Briefing | The Call Prep Researcher builds a one-page brief before every meeting: who you’re talking to, what their company does, the full history of your relationship pulled from your knowledge files and past outputs, every open thread that might come up, and a suggested objectiv… | Cal (optional · degrades gracefully) |
| 7 | Campaign Operations Manager | `skills/campaign-operations-manager.md` | Yes | Sales | Campaign Launch; Campaign Orchestration; Send Optimization | The Campaign Operations Manager takes finished copy and a verified list and gets the campaign live · correctly. | Heyreach, Instantly (optional · degrades gracefully) |
| 8 | Carousel Designer | `skills/carousel-designer.md` | Yes | Marketing | Carousel Production | The Carousel Designer turns any idea · a topic, a script, a case study, a winning post · into a complete carousel architecture: slide-by-slide copy, swipe logic, and layout notes ready to drop into your design system, Figma template, or Canva file. | No API keys |
| 9 | Case Study Curator | `skills/case-study-curator.md` | Yes | Sales | Proof Matching | The Case Study Curator maintains your proof library and matches the right case study to each prospect’s industry and problem. Generic proof ('we’ve helped dozens of companies') converts nobody; a prospect believes the story about someone who looks like them. | No API keys |
| 10 | Client Onboarding Manager | `skills/client-onboarding-manager.md` | Yes | Operations | Access Collection; Kickoff Pack; Project Scaffolding | The Client Onboarding Manager compresses the gap between 'deal closed' and 'work started' into a single working day. | No API keys |
| 11 | Client Portal Manager | `skills/client-portal-manager.md` | Yes | Operations | Portal Provisioning; Portal Sync | The Client Portal Manager gives every client a single place to see their project moving: what shipped, what’s in progress, what’s needed from them, and what’s next. | No API keys |
| 12 | Cold Email Copywriter | `skills/cold-email-copywriter.md` | Yes | Sales | Cold Email Drafting | The Cold Email Copywriter writes personalized cold email sequences that get replies. | Exa, Firecrawl, Hunter, Instantly (optional · degrades gracefully) |
| 13 | Community Manager | `skills/community-manager.md` | Yes | Customer | Engagement & Replies; Event Coordination; Member Spotlights; Moderation | The Community Manager keeps your community · Slack, Discord, Skool, Circle, forum, comment section · alive and clean. | No API keys |
| 14 | Company Knowledge Base | `skills/knowledge-base.md` | Yes | ; Operations | Company Knowledge Base; Context Maintenance | A company knowledge base is the single place your AI agents read from and write to. It is not software you buy · it is a set of plain-text files with a strict convention, living next to your work. | No API keys |
| 15 | Company Research Analyst | `skills/company-research-analyst.md` | Yes | Intelligence | Company Deep-Dive; Funding & Financials Lookup; Tech-Stack Detection | The Company Research Analyst builds deep intelligence reports on target companies. | Apify, Exa, Firecrawl (optional · degrades gracefully) |
| 16 | Competitive Intelligence Analyst | `skills/competitive-intelligence-analyst.md` | Yes | Intelligence | Competitor Teardown; Pricing Research | The Competitive Intelligence Analyst builds competitive intelligence reports. | Exa, Firecrawl (optional · degrades gracefully) |
| 17 | Content Performance Analyst | `skills/content-performance-analyst.md` | Yes | Marketing | Audience Analysis; Performance Mining | The Content Performance Analyst turns your own posting history into a content strategy. | Apify_Api (optional · degrades gracefully) |
| 18 | Content Repurposing Manager | `skills/content-repurposing-manager.md` | Yes | Marketing | Cross-Platform Adaptation | Adapts one finished piece into platform-native versions across every channel, rewritten to each platform's format and limits. | Exa, Openai (optional · degrades gracefully) |
| 19 | Contracts Coordinator | `skills/contracts-coordinator.md` | Yes | Back Office; Deals | Agreement Drafting; Contract Lifecycle | The Contracts Coordinator produces the services agreement the moment a deal closes verbally · so the signature happens while the yes is still warm. | No API keys |
| 20 | Conversion Copywriter | `skills/conversion-copywriter.md` | Yes | Marketing | Landing Page Copy | Writes landing-page and sales-page copy that converts · builds the whole page in the order that sells: hero promise, problem, mechanism, proof, offer with risk reversal, FAQ, and one clear CTA, in your brand voice. | No API keys (optional Exa / Firecrawl for proof) |
| 21 | Creative Strategist | `skills/creative-strategist.md` | Yes | Marketing | Ad Creative; Hook Writing | The Creative Strategist is an elite marketing strategist that analyzes any business and generates platform-specific viral hooks. | Exa, Firecrawl (optional · degrades gracefully) |
| 22 | Customer Success Manager | `skills/customer-success-manager.md` | Yes | Customer | Advocacy & Referrals; Churn Prediction; Health Scoring; Onboarding Journeys; QBR Prep; Renewals & Expansion | The Customer Success Manager runs the post-sale lifecycle end to end. | No API keys |
| 23 | Data Enrichment Specialist | `skills/data-enrichment-specialist.md` | Yes | Sales | Account Enrichment; Contact Enrichment; Email Verification | The Data Enrichment Specialist takes a raw lead list and returns campaign-ready records in one pass: decision-maker contacts found and appended (emails, phones, LinkedIn profiles), every email verified before it can ever receive a send, and account-level context layered… | Apollo, Exa, Millionverifier, Neverbounce (optional · degrades gracefully) |
| 24 | Deal Debrief Analyst | `skills/deal-debrief-analyst.md` | Yes | Deals | Follow-Up Drafting; Objection Library; Post-Call Debrief | The Deal Debrief Analyst processes a call the moment it ends. | Fireflies (optional · degrades gracefully) |
| 25 | Deal Room Producer | `skills/deal-room-producer.md` | Yes | Deals | Deal Room Assembly | The Deal Room Producer assembles everything a prospect needs to say yes · proposal, scope, proof, pricing, FAQ · into one shareable, organized package per deal. | No API keys |
| 26 | Deliverability Manager | `skills/deliverability-manager.md` | Yes | Sales | Deliverability | The Deliverability Manager keeps your sending infrastructure healthy so the campaigns everyone else built actually reach an inbox. | Instantly (optional · degrades gracefully) |
| 27 | Delivery Status Reporter | `skills/delivery-status-reporter.md` | Yes | Operations | Status Updates | The Delivery Status Reporter sends progress to clients before they think to ask for it. | Resend (optional · degrades gracefully) |
| 28 | DM Fulfillment Specialist | `skills/dm-fulfillment-specialist.md` | Yes | Deals | Comment-CTA Fulfillment | The DM Fulfillment Specialist closes the loop on comment-CTA content. | Instagram (optional · degrades gracefully) |
| 29 | Document Extraction Engineer | `skills/document-extraction-engineer.md` | Yes | Operations | Document Extraction | The Document Extraction Engineer turns piles of documents · forms, reports, invoices, case files, contracts · into structured data you can actually use. | No API keys |
| 30 | Executive Assistant | `skills/executive-assistant.md` | Yes | Back Office | Calendar Management | The Executive Assistant takes the two daily time sinks · calendar and inbox · and handles them like a sharp human EA would. | Cal (optional · degrades gracefully) |
| 31 | Finance Operations Analyst | `skills/finance-operations-analyst.md` | Yes | Back Office | Budget Tracking; Cash-Flow Forecasting | The forward-looking money role · projects cash in and out, calculates runway, runs scenario planning, and tracks spend against budget by category, flagging overruns early. | Xero, Stripe (optional · works off pasted numbers or CSV) |
| 32 | Financial Reporting Analyst | `skills/financial-reporting-analyst.md` | Yes | Back Office | Expense Categorization; Goal Pacing; Revenue Reporting | The Financial Reporting Analyst gives you one version of the financial truth. | Stripe, Wise_Api (optional · degrades gracefully) |
| 33 | Follow-Up Coordinator | `skills/followup-coordinator.md` | Yes | Operations | Meeting Follow-Ups | The Follow-Up Coordinator turns a meeting into a closed loop. Give it a transcript or notes and it extracts every action item with an owner, a deadline, and the exact quote it came from · then separates what YOUR side committed to from what THEIR side committed to. | Fireflies (optional · degrades gracefully) |
| 34 | Help Content Writer | `skills/help-content-writer.md` | Yes | Customer | FAQ & Self-Serve | The Help Content Writer turns your support history into a self-serve layer that answers questions before they become tickets. | No API keys |
| 35 | ICP Strategist | `skills/icp-strategist.md` | Yes | Sales | ICP Definition | The ICP Strategist turns your win/loss history into ideal customer profiles that agents can actually act on. | No API keys |
| 36 | Inbound Response Manager | `skills/inbound-response-manager.md` | Yes | Deals | Inbox Triage; Lead Qualification; Referral Capture; Speed-to-Lead | The Inbound Response Manager owns the front door. Every inbound lead · form fill, email, DM · gets an acknowledgment drafted within minutes, gets parsed and scored on budget, fit, and urgency, and lands in a sorted queue before a human ever opens the inbox. | No API keys |
| 37 | Inbox Manager | `skills/inbox-manager.md` | Yes | Back Office | Email Triage | Triages your inbox into what needs you now vs noise, ranks by real urgency, and drafts replies in your voice. Never sends, deletes, or commits you to anything · every draft waits for approval. | Gmail (optional · read + draft only, never send) |
| 38 | Instagram Content Analyst | `skills/instagram-content-analyst.md` | Yes | Marketing | Competitor Analysis | The Instagram Content Analyst scrapes Instagram reels from competitors and your own profile, transcribes the audio to extract spoken hooks, analyzes engagement patterns, and generates data-driven content ideas. | Apify, Deepgram (optional · degrades gracefully) |
| 39 | Integration Engineer | `skills/integration-engineer.md` | Yes | Operations | Data Migration; Integration Builds | The Integration Engineer connects the systems a business actually runs on · CRMs, calendars, transcription tools, payment processors, email platforms · with direct API integrations built like production software. | No API keys |
| 40 | Lead Magnet Producer | `skills/lead-magnet-producer.md` | Yes | Marketing | Lead-Magnet Builds | The Lead Magnet Producer turns content that already performed into gated assets that capture the demand it proved. | Beehiiv, Resend (optional · degrades gracefully) |
| 41 | Lead Scoring Analyst | `skills/lead-scoring-analyst.md` | Yes | Sales | Fit Scoring; Lookalike Modeling | The Lead Scoring Analyst scores every lead on a list against your ICP files and sorts the output into tiers: A-tier gets the personalized, multi-touch treatment; B-tier gets the standard sequence; C-tier gets disqualified · with the reason written down. | No API keys |
| 42 | Lead Sourcing Manager | `skills/lead-sourcing-manager.md` | Yes | Sales | Database Mining; List Building; Web & Maps Scraping | The Lead Sourcing Manager builds targeted lead lists · both companies and people. Tell it what you’re looking for (industry, size, location, role) and it will find matching leads using the best method available based on your API keys. | Apify, Apollo, Exa, Hunter (optional · degrades gracefully) |
| 43 | LinkedIn Outreach Specialist | `skills/linkedin-outreach-specialist.md` | Yes | Sales | LinkedIn Messaging | The LinkedIn Outreach Specialist writes personalized LinkedIn outreach · connection requests and DM sequences. | Heyreach (optional · degrades gracefully) |
| 44 | Market Mapper | `skills/market-mapper.md` | Yes | Intelligence; Sales | Market Mapping; TAM / Market Sizing | The Market Mapper runs a census of every company that fits your ICP in a target vertical · before a single email gets written. | Apify, Apollo, Exa (optional · degrades gracefully) |
| 45 | Meeting Booking Coordinator | `skills/meeting-booking-coordinator.md` | Yes | Deals | Meeting Booking | The Meeting Booking Coordinator turns 'yes, let’s talk' into a calendar invite with the fewest possible messages. | Cal (optional · degrades gracefully) |
| 46 | Meeting Intelligence Engineer | `skills/meeting-intelligence-engineer.md` | Yes | Deals; Operations | Call Capture; Transcript Processing | The Meeting Intelligence Engineer makes sure no call evaporates. | Fireflies, Grain, Otter (optional · degrades gracefully) |
| 47 | Newsletter Editor | `skills/newsletter-editor.md` | Yes | Marketing | Newsletter & Broadcast | The Newsletter Editor assembles and writes the weekly email. | Beehiiv (optional · degrades gracefully) |
| 48 | Outbound Inbox Manager | `skills/outbound-inbox-manager.md` | Yes | Deals | Hot-Lead Routing; Objection Response; Reply Classification | The Outbound Inbox Manager reads every reply to your outbound campaigns, classifies each one · interested, objection, referral, not-now, never, auto-reply · and drafts the response. Interested replies get a booking message with your calendar link. | Instantly (optional · degrades gracefully) |
| 49 | Outbound Scriptwriter | `skills/outbound-scriptwriter.md` | Yes | Sales | Cold-Call Scripting; Video Prospecting | Writes the spoken and video side of outbound · cold-call and voicemail scripts with branching objection handling, and sub-90-second personalized video prospecting scripts, all matched to the offer and the prospect. | No API keys (optional Exa / Firecrawl to personalize) |
| 50 | People Operations Assistant | `skills/people-operations-assistant.md` | Yes | Back Office | HR & Policy Assistant | The first HR hire a small company never makes · answers staff questions straight from the company policy docs (with a citation), runs new-hire onboarding admin, keeps the handbook current, and escalates anything sensitive. | No API keys (optional HRIS / Workspace) |
| 51 | Personal Brand Designer | `skills/personal-brand-designer.md` | Yes | Marketing | Image Generation | Turns your reference photos into consistent, identity-matched personal brand images via fal.ai's consistent-character model. | Fal (optional · degrades gracefully) |
| 52 | Pipeline Operations Manager | `skills/pipeline-operations-manager.md` | Yes | Deals | CRM Hygiene; Forecasting; Pipeline Reporting | The Pipeline Operations Manager keeps your deal data honest and turns it into decisions. | No API keys |
| 53 | Playbook Writer | `skills/playbook-writer.md` | Yes | Operations | Handoff Docs; SOP Generation | The Playbook Writer captures the most expensive thing a business produces and usually throws away: how the work actually got done. It handles two jobs. | No API keys |
| 54 | Presentation Designer | `skills/presentation-designer.md` | Yes | Marketing | Deck Production | The Presentation Designer builds a complete webinar or talk deck in one sitting: the narrative arc, slide-by-slide content, speaker notes, and design direction in your brand’s visual language. | No API keys |
| 55 | Pricing Analyst | `skills/pricing-analyst.md` | Yes | Deals | Pricing Support | The Pricing Analyst builds the numbers case for each deal before you quote it. | No API keys |
| 56 | Proposal Writer | `skills/proposal-writer.md` | Yes | Deals | Proposal Generation | The Proposal Writer turns a sales call into a proposal draft · same day, structured the way deals actually close. | No API keys |
| 57 | Prospect Research Analyst | `skills/prospect-research-analyst.md` | Yes | Intelligence; Sales | Person Research; Personalization Research | The Prospect Research Analyst builds deep, actionable intelligence reports on target prospects. | Apify, Exa, Firecrawl (optional · degrades gracefully) |
| 58 | Publishing Manager | `skills/publishing-manager.md` | Yes | Marketing | Publishing | The Publishing Manager takes finished content and gets it live. | Instagram, Linkedin, X (optional · degrades gracefully) |
| 59 | QA Engineer | `skills/qa-engineer.md` | Yes | Operations | Agent Evaluation; QA & Verification | The QA Engineer is the last gate before anything reaches a client. It verifies every build against real data · running the actual system on actual inputs and checking the actual outputs, not reading the code and nodding. | No API keys |
| 60 | Reactivation Specialist | `skills/reactivation-specialist.md` | Yes | Deals | Reactivation; Win/Loss Analysis | The Reactivation Specialist works the deals everyone else gave up on. | No API keys |
| 61 | Records Administrator | `skills/records-administrator.md` | Yes | Back Office | CRM Sync; Document Filing & Retrieval; Entity Compliance | The Records Administrator keeps your sources of truth from drifting apart. | Attio, Hubspot (optional · degrades gracefully) |
| 62 | Red Team Reviewer | `skills/red-team-reviewer.md` | Yes | Intelligence | Adversarial Verification | The Red Team Reviewer takes any report, claim, plan, or proposal and attacks it before you act on it. It checks sources, hunts contradictions, surfaces hidden assumptions, and stress-tests the logic · then issues a verdict per claim: verified, shaky, or refuted. | Exa (optional · degrades gracefully) |
| 63 | Relationship Mapper | `skills/relationship-mapper.md` | Yes | Intelligence | Buying-Committee Mapping; Network Mapping; Warm-Path Finding | The Relationship Mapper finds the warm path into any target account. | Exa (optional · degrades gracefully) |
| 64 | Reliability Engineer | `skills/reliability-engineer.md` | Yes | Operations | Cost & Usage Tracking; Incident Response; Monitoring & Alerting | The on-call engineer for your AI stack · monitors every automation for failures and silent stalls, tracks token and API spend against budget, and runs incident response when something breaks. | Inngest + provider usage dashboards (optional · degrades to log-parsing) |
| 65 | Research Reporter | `skills/research-reporter.md` | No | Intelligence | Research Reports | Referenced by the graph, but no public metadata or preview was exposed. | Not publicly exposed |
| 66 | Scriptwriter | `skills/scriptwriter.md` | Yes | Marketing | Script Writing | The Scriptwriter turns an idea into a complete, ready-to-film reel or video script · hook, tension, payoff, CTA · written in your voice, not a generic creator voice. | No API keys |
| 67 | SEO Engineer | `skills/seo-engineer.md` | Yes | Marketing | OG & Share Surface; SEO & GEO | The SEO Engineer makes your site legible to the two things that now decide whether you get found: search engines and language models. | No API keys |
| 68 | Signal Monitoring Analyst | `skills/signal-monitoring-analyst.md` | Yes | Intelligence | Account Monitoring; Alert Routing; News & Mention Tracking | Watches a list of target accounts, competitors, and topics on an ongoing basis and surfaces what changed · funding, hiring, leadership moves, tech changes, mentions · scores each for relevance and routes the ones that matter. | Exa, Firecrawl, Slack/Resend for routing (all optional · degrades gracefully) |
| 69 | SkillTree Audit | `skills/skilltree-audit.md` | Yes |  | Company Knowledge Base | The SkillTree map (altari.ai/skilltree) charts every AI job-to-be-done in a business across 7 departments. You can mark your own deployment status by hand · or you can run this audit and let an agent compute it. | No API keys |
| 70 | Social Copywriter | `skills/social-copywriter.md` | Yes | Marketing | Caption Writing | The Social Copywriter writes the caption layer · the text that decides whether a post converts attention into action. | No API keys |
| 71 | Social Prospecting Specialist | `skills/social-prospecting-specialist.md` | Yes | Sales | Social Mining | The Social Prospecting Specialist scrapes commenters from viral LinkedIn posts, enriches their profiles, scores them against your ICP, and writes personalized DMs for the best fits · all in one shot. | Apify, Heyreach (optional · degrades gracefully) |
| 72 | Solutions Engineer | `skills/solutions-engineer.md` | Yes | Deals | Demo Prototyping | The Solutions Engineer turns discovery calls into visual prototypes · same day, before the follow-up. | Fireflies (optional · degrades gracefully) |
| 73 | Support Answerer | `skills/support-answerer.md` | Yes | Customer | FAQ & Self-Serve | Drafts customer-support replies from ONLY your help docs and past tickets, cites every claim, escalates what it can't source, and logs the gaps so you know which doc to write next. Drafts only · never sends. | Intercom / Zendesk / Gmail (optional · degrades gracefully) |
| 74 | Support Operations Manager | `skills/support-operations-manager.md` | Yes | Customer | Escalations; Macro Authoring; Ticket Triage | The Support Operations Manager runs the front door of your support queue. | No API keys |
| 75 | Talent Coordinator | `skills/talent-coordinator.md` | Yes | Back Office | Candidate Sourcing; Onboarding & Training; Screening & Scheduling | The Talent Coordinator runs the hiring pipeline end to end. | No API keys |
| 76 | TikTok Content Analyst | `skills/tiktok-content-analyst.md` | Yes | Marketing | Competitor Analysis | Analyzes a competitor's TikTok catalog to surface the working hooks, formats, and patterns you can adapt. | Apify, Deepgram (optional · degrades gracefully) |
| 77 | Trend Analyst | `skills/trend-analyst.md` | Yes | Marketing | Trend Monitoring | Monitors your space for breaking news and turns it into ranked, timely content angles tied to real sources. | Exa, Firecrawl (optional · degrades gracefully) |
| 78 | Vertical Analyst | `skills/vertical-analyst.md` | Yes | Intelligence | Vertical Analysis | The Vertical Analyst answers one question: is this vertical worth entering? It investigates demand signals, budget authority, buying behavior, and competitor saturation for any market you’re considering · then delivers a go/no-go verdict with the reasoning attached. | Exa (optional · degrades gracefully) |
| 79 | Video Editor | `skills/video-editor.md` | Yes | Marketing | Clip Extraction; Video Production | The Video Editor turns raw recordings into publishable content · without you sitting in a timeline for hours. It works two jobs. | Deepgram (optional · degrades gracefully) |

## 2. Atomic capabilities

| # | Capability | Department(s) | Function(s) | Mapped job(s) |
|---:|---|---|---|---|
| 1 | `access-checklister` | Operations | Onboarding | Kickoff Pack |
| 2 | `access-verifier` | Operations | Onboarding | Access Collection |
| 3 | `account-watcher` | Intelligence | Monitoring | Account Monitoring |
| 4 | `accuracy-benchmarker` | Operations | Build Ops | Document Extraction |
| 5 | `action-assigner` | Operations | Client Comms | Meeting Follow-Ups |
| 6 | `action-extractor` | Deals | Call Cycle | Post-Call Debrief |
| 7 | `activation-tracker` | Customer | Success | Onboarding Journeys |
| 8 | `ad-variation-builder` | Marketing | Creation | Ad Creative |
| 9 | `advocate-finder` | Customer | Success | Advocacy & Referrals |
| 10 | `alert-router` | Intelligence | Monitoring | Alert Routing |
| 11 | `anchor-calculator` | Deals | Deal Artifacts | Pricing Support |
| 12 | `angle-tester` | Marketing | Creation | Ad Creative |
| 13 | `api-integrator` | Operations | Build Ops | Integration Builds |
| 14 | `api-publisher` | Marketing | Distribution | Publishing |
| 15 | `apollo-query-builder` | Sales | Lead Sourcing | Database Mining |
| 16 | `approval-doc-generator` | Marketing | Brand Deals | Approval Docs |
| 17 | `attendee-researcher` | Deals | Call Cycle | Pre-Call Briefing |
| 18 | `auto-labeler` | Deals | Reply Handling | Reply Classification |
| 19 | `brand-image-generator` | Marketing | Creation | Image Generation |
| 20 | `brand-script-writer` | Marketing | Brand Deals | Deal Scripting |
| 21 | `broadcast-sender` | Marketing | Distribution | Newsletter & Broadcast |
| 22 | `budget-detector` | Deals | Inbound | Lead Qualification |
| 23 | `budget-guard` | Operations | Reliability | Cost & Usage Tracking |
| 24 | `budget-tracker` | Back Office | Finance Ops | Budget Tracking |
| 25 | `cadence-builder` | Sales | Sequencing & Send | Campaign Orchestration |
| 26 | `cal-booker` | Deals | Reply Handling | Meeting Booking |
| 27 | `calendar-manager` | Back Office | Office | Calendar Management |
| 28 | `call-scripter` | Sales | Outreach Writing | Cold-Call Scripting |
| 29 | `candidate-finder` | Back Office | Talent | Candidate Sourcing |
| 30 | `caption-syncer` | Marketing | Creation | Video Production |
| 31 | `caption-writer` | Marketing | Creation | Caption Writing |
| 32 | `carousel-builder` | Marketing | Creation | Carousel Production |
| 33 | `case-study-matcher` | Sales | Outreach Writing | Proof Matching |
| 34 | `cashflow-projector` | Back Office | Finance Ops | Cash-Flow Forecasting |
| 35 | `catch-all-detector` | Sales | Enrichment | Email Verification |
| 36 | `change-detector` | Intelligence | Monitoring | Account Monitoring |
| 37 | `channel-router` | Sales | Sequencing & Send | Campaign Orchestration |
| 38 | `character-consistency` | Marketing | Creation | Image Generation |
| 39 | `chart-builder` | Intelligence | Synthesis | Data Visualization |
| 40 | `churn-modeler` | Customer | Success | Churn Prediction |
| 41 | `churn-predictor` | Customer | Success | Health Scoring |
| 42 | `claim-fact-checker` | Marketing | Brand Deals | Deal Scripting |
| 43 | `claim-verifier` | Intelligence | Synthesis | Adversarial Verification |
| 44 | `clip-finder` | Marketing | Repurposing | Clip Extraction |
| 45 | `close-probability-scorer` | Deals | Pipeline Ops | Forecasting |
| 46 | `comment-harvester` | Sales | Lead Sourcing | Social Mining |
| 47 | `comment-miner` | Marketing | Insights | Audience Analysis |
| 48 | `commitment-tracker` | Deals | Call Cycle | Post-Call Debrief |
| 49 | `committee-mapper` | Intelligence | Companies | Buying-Committee Mapping |
| 50 | `common-ground-scanner` | Sales | Outreach Writing | Personalization Research |
| 51 | `community-responder` | Customer | Community | Engagement & Replies |
| 52 | `company-profiler` | Intelligence | Companies | Company Deep-Dive |
| 53 | `competitor-teardown` | Intelligence | Markets | Competitor Teardown |
| 54 | `compliance-calendar` | Back Office | Records | Entity Compliance |
| 55 | `conduct-monitor` | Customer | Community | Moderation |
| 56 | `conflict-resolver` | Back Office | Office | Calendar Management |
| 57 | `connection-mapper` | Intelligence | People | Network Mapping |
| 58 | `connection-note-writer` | Sales | Outreach Writing | LinkedIn Messaging |
| 59 | `content-trail-scanner` | Intelligence | People | Person Research |
| 60 | `context-updater` | Operations | Knowledge | Context Maintenance |
| 61 | `context-writer` | Operations | Onboarding | Project Scaffolding |
| 62 | `contract-generator` | Deals | Deal Artifacts | Agreement Drafting |
| 63 | `contract-tracker` | Back Office | Records | Contract Lifecycle |
| 64 | `corpus-ranker` | Marketing | Insights | Performance Mining |
| 65 | `cover-tester` | Marketing | Creation | Thumbnail & Cover Design |
| 66 | `credential-chaser` | Operations | Onboarding | Access Collection |
| 67 | `crm-promoter` | Deals | Reply Handling | Hot-Lead Routing |
| 68 | `crm-syncer` | Back Office | Records | CRM Sync |
| 69 | `csv-normalizer` | Sales | Lead Sourcing | List Building |
| 70 | `cta-placer` | Marketing | Creation | Caption Writing |
| 71 | `currency-normalizer` | Back Office | Reporting | Revenue Reporting |
| 72 | `deal-updater` | Deals | Call Cycle | Post-Call Debrief |
| 73 | `deck-builder` | Marketing | Creation | Deck Production |
| 74 | `dedupe-validator` | Operations | Build Ops | Data Migration |
| 75 | `deliverable-publisher` | Operations | Client Comms | Portal Sync |
| 76 | `diagram-generator` | Intelligence | Synthesis | Data Visualization; Research Reports |
| 77 | `directory-harvester` | Sales | Lead Sourcing | Web & Maps Scraping |
| 78 | `disqualifier` | Sales | Enrichment | Fit Scoring |
| 79 | `dm-fulfiller` | Deals | Inbound | Comment-CTA Fulfillment |
| 80 | `dm-sequencer` | Sales | Outreach Writing | LinkedIn Messaging |
| 81 | `document-filer` | Back Office | Records | Document Filing & Retrieval |
| 82 | `domain-health-auditor` | Sales | Sequencing & Send | Deliverability |
| 83 | `dormant-deal-reviver` | Deals | Pipeline Ops | Reactivation |
| 84 | `draft-responder` | Back Office | Office | Email Triage |
| 85 | `dream-prototyper` | Deals | Deal Artifacts | Demo Prototyping |
| 86 | `email-finder` | Sales | Enrichment | Contact Enrichment |
| 87 | `email-triager` | Back Office | Office | Email Triage |
| 88 | `engagement-miner` | Sales | Lead Sourcing | Social Mining |
| 89 | `engagement-tracker` | Deals | Deal Artifacts | Deal Room Assembly |
| 90 | `entity-extractor` | Operations | Knowledge | Transcript Processing |
| 91 | `entity-router` | Back Office | Money In | Invoice Generation |
| 92 | `era-analyzer` | Marketing | Insights | Performance Mining |
| 93 | `escalation-router` | Customer | Support | Escalations |
| 94 | `escalation-sequencer` | Back Office | Money In | Collections |
| 95 | `esign-preparer` | Deals | Deal Artifacts | Agreement Drafting |
| 96 | `eval-harness` | Operations | Build Ops | Agent Evaluation |
| 97 | `event-scheduler` | Customer | Community | Event Coordination |
| 98 | `expansion-spotter` | Customer | Success | Renewals & Expansion |
| 99 | `expense-categorizer` | Back Office | Records | Expense Categorization |
| 100 | `extraction-pipeline` | Operations | Build Ops | Document Extraction |
| 101 | `failure-alerter` | Operations | Reliability | Monitoring & Alerting |
| 102 | `faq-responder` | Customer | Support | FAQ & Self-Serve |
| 103 | `field-mapper` | Operations | Build Ops | Data Migration |
| 104 | `field-normalizer` | Deals | Pipeline Ops | CRM Hygiene |
| 105 | `filing-tracker` | Back Office | Records | Entity Compliance |
| 106 | `financials-reader` | Intelligence | Companies | Funding & Financials Lookup |
| 107 | `firmographic-appender` | Sales | Enrichment | Account Enrichment |
| 108 | `fit-scorer` | Sales | Enrichment | Fit Scoring |
| 109 | `followup-processor` | Operations | Client Comms | Meeting Follow-Ups |
| 110 | `format-adapter` | Marketing | Repurposing | Cross-Platform Adaptation |
| 111 | `format-spotter` | Marketing | Insights | Trend Monitoring |
| 112 | `funding-tracker` | Intelligence; Sales | Companies; Targeting | Funding & Financials Lookup; Trigger Detection |
| 113 | `funnel-analyzer` | Deals | Pipeline Ops | Pipeline Reporting |
| 114 | `gap-analyzer` | Intelligence | Companies | Tech-Stack Detection |
| 115 | `gated-page-generator` | Marketing | Repurposing | Lead-Magnet Builds |
| 116 | `goal-pacer` | Back Office | Reporting | Goal Pacing |
| 117 | `growth-signal-scorer` | Sales | Enrichment | Account Enrichment |
| 118 | `guide-builder` | Marketing | Repurposing | Lead-Magnet Builds |
| 119 | `handbook-keeper` | Back Office | Talent | HR & Policy Assistant |
| 120 | `handoff-writer` | Operations | Knowledge | Handoff Docs |
| 121 | `health-scorer` | Customer | Success | Health Scoring |
| 122 | `help-article-writer` | Customer | Support | FAQ & Self-Serve |
| 123 | `heyreach-syncer` | Sales | Sequencing & Send | Campaign Launch |
| 124 | `highlight-extractor` | Marketing | Repurposing | Clip Extraction |
| 125 | `hire-onboarder` | Back Office | Talent | Onboarding & Training |
| 126 | `hiring-signal-watcher` | Sales | Targeting | Trigger Detection |
| 127 | `hook-finder` | Sales | Outreach Writing | Personalization Research |
| 128 | `hook-generator` | Marketing | Creation | Hook Writing |
| 129 | `hook-pattern-miner` | Marketing | Insights | Competitor Analysis |
| 130 | `hook-ranker` | Marketing | Creation | Hook Writing |
| 131 | `hot-lead-alerter` | Deals | Reply Handling | Hot-Lead Routing |
| 132 | `icp-profiler` | Sales | Targeting | ICP Definition |
| 133 | `inbox-triager` | Deals | Inbound | Inbox Triage |
| 134 | `incident-triager` | Operations | Reliability | Incident Response |
| 135 | `instant-responder` | Deals | Inbound | Speed-to-Lead |
| 136 | `instantly-syncer` | Sales | Sequencing & Send | Campaign Launch |
| 137 | `intake-acknowledger` | Deals | Inbound | Speed-to-Lead |
| 138 | `intake-parser` | Deals | Inbound | Lead Qualification |
| 139 | `intent-classifier` | Deals | Reply Handling | Reply Classification |
| 140 | `interview-scheduler` | Back Office | Talent | Screening & Scheduling |
| 141 | `intro-drafter` | Intelligence | People | Warm-Path Finding |
| 142 | `intro-router` | Deals | Reply Handling | Referral Capture |
| 143 | `invoice-generator` | Back Office | Money In | Invoice Generation |
| 144 | `journey-sequencer` | Customer | Success | Onboarding Journeys |
| 145 | `keyword-listener` | Deals | Inbound | Comment-CTA Fulfillment |
| 146 | `kickoff-generator` | Operations | Onboarding | Kickoff Pack |
| 147 | `linkedin-matcher` | Sales | Enrichment | Contact Enrichment |
| 148 | `list-deduper` | Sales | Lead Sourcing | List Building |
| 149 | `llms-txt-maintainer` | Marketing | Distribution | SEO & GEO |
| 150 | `lookalike-builder` | Sales | Targeting | Lookalike Modeling |
| 151 | `loss-tagger` | Deals | Pipeline Ops | Win/Loss Analysis |
| 152 | `macro-writer` | Customer | Support | Macro Authoring |
| 153 | `magic-link-issuer` | Deals | Deal Artifacts | Deal Room Assembly |
| 154 | `maps-scraper` | Sales | Lead Sourcing | Web & Maps Scraping |
| 155 | `meeting-filer` | Deals | Call Cycle | Call Capture |
| 156 | `memory-writer` | Operations | Knowledge | Context Maintenance |
| 157 | `mention-tracker` | Intelligence | Monitoring | News & Mention Tracking |
| 158 | `mention-watcher` | Customer | Community | Engagement & Replies |
| 159 | `migration-runner` | Operations | Build Ops | Data Migration |
| 160 | `milestone-notifier` | Operations | Client Comms | Status Updates |
| 161 | `news-watcher` | Intelligence; Marketing | Insights; Monitoring | News & Mention Tracking; Trend Monitoring |
| 162 | `newsletter-builder` | Marketing | Distribution | Newsletter & Broadcast |
| 163 | `next-step-drafter` | Deals | Call Cycle | Follow-Up Drafting |
| 164 | `no-show-recoverer` | Deals | Reply Handling | Meeting Booking |
| 165 | `objection-brancher` | Sales | Outreach Writing | Cold-Call Scripting |
| 166 | `objection-library` | Deals | Reply Handling | Objection Response |
| 167 | `objection-miner` | Deals | Call Cycle | Objection Library |
| 168 | `offer-framer` | Marketing | Creation | Landing Page Copy |
| 169 | `og-image-generator` | Marketing | Distribution | OG & Share Surface |
| 170 | `opportunity-scorer` | Intelligence | Markets | Vertical Analysis |
| 171 | `output-verifier` | Operations | Build Ops | QA & Verification |
| 172 | `overdue-nudger` | Back Office | Money In | Collections |
| 173 | `overlay-animator` | Marketing | Creation | Video Production |
| 174 | `packaging-analyzer` | Intelligence | Markets | Pricing Research |
| 175 | `page-copywriter` | Marketing | Creation | Landing Page Copy |
| 176 | `pain-pattern-library` | Sales | Targeting | ICP Definition |
| 177 | `path-finder` | Intelligence | People | Warm-Path Finding |
| 178 | `pattern-extractor` | Sales | Targeting | Lookalike Modeling |
| 179 | `pattern-miner` | Deals | Pipeline Ops | Win/Loss Analysis |
| 180 | `payment-watcher` | Back Office | Money In | Payment Tracking |
| 181 | `pdf-renderer` | Deals | Deal Artifacts | Proposal Generation |
| 182 | `person-profiler` | Intelligence | People | Person Research |
| 183 | `personalization-writer` | Sales | Outreach Writing | Video Prospecting |
| 184 | `phase-structurer` | Deals | Deal Artifacts | Pricing Support |
| 185 | `phone-appender` | Sales | Enrichment | Contact Enrichment |
| 186 | `pipeline-reporter` | Deals | Pipeline Ops | Pipeline Reporting |
| 187 | `platform-translator` | Marketing | Repurposing | Cross-Platform Adaptation |
| 188 | `playbook-extractor` | Operations | Knowledge | SOP Generation |
| 189 | `policy-answerer` | Back Office | Talent | HR & Policy Assistant |
| 190 | `portal-provisioner` | Operations | Build Ops | Portal Provisioning |
| 191 | `portal-syncer` | Operations | Client Comms | Portal Sync |
| 192 | `portal-theming` | Operations | Build Ops | Portal Provisioning |
| 193 | `positioning-mapper` | Intelligence | Markets | Competitor Teardown |
| 194 | `post-scheduler` | Marketing | Distribution | Publishing |
| 195 | `postmortem-writer` | Operations | Reliability | Incident Response |
| 196 | `prep-brief-builder` | Deals | Call Cycle | Pre-Call Briefing |
| 197 | `pricing-scanner` | Intelligence | Markets | Pricing Research |
| 198 | `priority-router` | Customer; Deals | Inbound; Support | Inbox Triage; Ticket Triage |
| 199 | `profile-collector` | Sales | Lead Sourcing | Social Mining |
| 200 | `profile-ranker` | Back Office | Talent | Candidate Sourcing |
| 201 | `proof-point-selector` | Sales | Outreach Writing | Proof Matching |
| 202 | `proposal-writer` | Deals | Deal Artifacts | Proposal Generation |
| 203 | `prospect-dossier` | Sales | Outreach Writing | Personalization Research |
| 204 | `qbr-builder` | Customer | Success | QBR Prep |
| 205 | `qual-scorer` | Deals | Inbound | Lead Qualification |
| 206 | `question-clusterer` | Marketing | Insights | Audience Analysis |
| 207 | `rebuttal-builder` | Deals | Call Cycle | Objection Library |
| 208 | `recap-writer` | Deals | Call Cycle | Follow-Up Drafting |
| 209 | `reconciler` | Back Office | Money In | Payment Tracking |
| 210 | `record-deduper` | Deals | Pipeline Ops | CRM Hygiene |
| 211 | `reel-compositor` | Marketing | Creation | Video Production |
| 212 | `reel-transcriber` | Marketing | Insights | Competitor Analysis |
| 213 | `referral-asker` | Customer | Success | Advocacy & Referrals |
| 214 | `referral-spotter` | Deals | Reply Handling | Referral Capture |
| 215 | `regression-checker` | Operations | Build Ops | Agent Evaluation; QA & Verification |
| 216 | `rehash-finder` | Marketing | Insights | Performance Mining |
| 217 | `renewal-notifier` | Back Office | Records | Contract Lifecycle |
| 218 | `renewal-scheduler` | Customer | Success | Renewals & Expansion |
| 219 | `repo-scaffolder` | Operations | Onboarding | Project Scaffolding |
| 220 | `report-builder` | Intelligence | Synthesis | Research Reports |
| 221 | `response-drafter` | Deals | Reply Handling | Objection Response |
| 222 | `response-templater` | Customer | Support | Macro Authoring |
| 223 | `retrieval-indexer` | Back Office | Records | Document Filing & Retrieval |
| 224 | `revenue-forecaster` | Deals | Pipeline Ops | Forecasting |
| 225 | `revenue-reporter` | Back Office | Reporting | Revenue Reporting |
| 226 | `risk-forecaster` | Customer | Success | Churn Prediction |
| 227 | `roi-modeler` | Deals | Deal Artifacts | Pricing Support |
| 228 | `role-classifier` | Intelligence | Companies | Buying-Committee Mapping |
| 229 | `room-builder` | Deals | Deal Artifacts | Deal Room Assembly |
| 230 | `rootcause-finder` | Operations | Reliability | Incident Response |
| 231 | `runbook-generator` | Operations | Knowledge | Handoff Docs |
| 232 | `runway-calculator` | Back Office | Finance Ops | Cash-Flow Forecasting |
| 233 | `runway-projector` | Back Office | Reporting | Goal Pacing |
| 234 | `sandbox-builder` | Deals | Deal Artifacts | Demo Prototyping |
| 235 | `saved-search-runner` | Sales | Lead Sourcing | Database Mining |
| 236 | `scenario-modeler` | Back Office | Finance Ops | Cash-Flow Forecasting |
| 237 | `schema-mapper` | Operations | Build Ops | Document Extraction |
| 238 | `schema-marker` | Marketing | Distribution | SEO & GEO |
| 239 | `screen-summarizer` | Back Office | Talent | Screening & Scheduling |
| 240 | `script-writer` | Marketing | Creation | Script Writing |
| 241 | `segment-counter` | Intelligence | Markets | TAM / Market Sizing |
| 242 | `segmenter` | Sales | Lead Sourcing | List Building |
| 243 | `sentiment-flagger` | Customer | Support | Escalations |
| 244 | `sentiment-tagger` | Deals | Reply Handling | Reply Classification |
| 245 | `sequence-writer` | Sales | Outreach Writing | Cold Email Drafting |
| 246 | `session-runner` | Customer | Community | Event Coordination |
| 247 | `signal-collector` | Intelligence | Companies | Company Deep-Dive |
| 248 | `signal-scorer` | Intelligence | Monitoring | Alert Routing |
| 249 | `sitemap-builder` | Marketing | Distribution | SEO & GEO |
| 250 | `sla-watcher` | Customer | Support | Ticket Triage |
| 251 | `slide-exporter` | Marketing | Creation | Carousel Production |
| 252 | `slide-templater` | Marketing | Creation | Deck Production |
| 253 | `slot-proposer` | Deals | Reply Handling | Meeting Booking |
| 254 | `smtp-verifier` | Sales | Enrichment | Email Verification |
| 255 | `sop-writer` | Operations | Knowledge | SOP Generation |
| 256 | `source-citer` | Intelligence | Synthesis | Research Reports |
| 257 | `source-cross-checker` | Intelligence | Synthesis | Adversarial Verification |
| 258 | `spam-filter` | Customer | Community | Moderation |
| 259 | `spam-score-tester` | Sales | Sequencing & Send | Deliverability |
| 260 | `spend-tracker` | Operations | Reliability | Cost & Usage Tracking |
| 261 | `spintax-builder` | Sales | Outreach Writing | Cold Email Drafting |
| 262 | `spotlight-writer` | Customer | Community | Member Spotlights |
| 263 | `stack-detector` | Intelligence | Companies | Tech-Stack Detection |
| 264 | `stage-auditor` | Deals | Pipeline Ops | CRM Hygiene |
| 265 | `status-poster` | Operations | Client Comms | Status Updates |
| 266 | `subject-line-generator` | Sales | Outreach Writing | Cold Email Drafting |
| 267 | `tam-mapper` | Sales | Targeting | Market Mapping |
| 268 | `tam-sizer` | Intelligence | Markets | TAM / Market Sizing |
| 269 | `tech-change-detector` | Sales | Targeting | Trigger Detection |
| 270 | `tech-stack-detector` | Sales | Enrichment | Account Enrichment |
| 271 | `thumbnail-designer` | Marketing | Creation | Thumbnail & Cover Design |
| 272 | `ticket-classifier` | Customer | Support | Ticket Triage |
| 273 | `tier-assigner` | Sales | Enrichment | Fit Scoring |
| 274 | `timezone-scheduler` | Sales | Sequencing & Send | Send Optimization |
| 275 | `training-sequencer` | Back Office | Talent | Onboarding & Training |
| 276 | `transcript-ingester` | Deals | Call Cycle | Call Capture |
| 277 | `transcript-structurer` | Operations | Knowledge | Transcript Processing |
| 278 | `two-way-updater` | Back Office | Records | CRM Sync |
| 279 | `uptime-watcher` | Operations | Reliability | Monitoring & Alerting |
| 280 | `value-recap-writer` | Customer | Success | QBR Prep |
| 281 | `variance-flagger` | Back Office | Finance Ops | Budget Tracking |
| 282 | `vertical-analyzer` | Intelligence | Markets | Vertical Analysis |
| 283 | `vertical-census` | Sales | Targeting | Market Mapping |
| 284 | `vertical-scorer` | Sales | Targeting | ICP Definition |
| 285 | `video-scripter` | Sales | Outreach Writing | Video Prospecting |
| 286 | `voice-matcher` | Marketing | Creation | Script Writing |
| 287 | `volume-pacer` | Sales | Sequencing & Send | Send Optimization |
| 288 | `warmup-monitor` | Sales | Sequencing & Send | Deliverability |
| 289 | `webhook-wirer` | Operations | Build Ops | Integration Builds |
| 290 | `win-detector` | Customer | Community | Member Spotlights |
| 291 | `winback-sequencer` | Deals | Pipeline Ops | Reactivation |

## 3. Jobs / visible AI-workforce nodes

| # | Department | Function | Job | Level | Description | Named skill file(s) | Atomic capabilities |
|---:|---|---|---|---|---|---|---|
| 1 | Back Office | Finance Ops | Budget Tracking | autonomous | Spend vs budget by category, with overruns flagged early. | Finance Operations Analyst | budget-tracker; variance-flagger |
| 2 | Back Office | Finance Ops | Cash-Flow Forecasting | assisted | Project cash in and out · know your runway before it becomes an emergency. | Finance Operations Analyst | cashflow-projector; runway-calculator; scenario-modeler |
| 3 | Back Office | Money In | Collections | assisted | Overdue invoices get chased politely and persistently. | Billing Manager | escalation-sequencer; overdue-nudger |
| 4 | Back Office | Money In | Invoice Generation | autonomous | Branded invoices per entity, currency, and tax treatment. | Billing Manager | entity-router; invoice-generator |
| 5 | Back Office | Money In | Payment Tracking | autonomous | Know what’s paid, due, and late · without opening a bank app. | Billing Manager | payment-watcher; reconciler |
| 6 | Back Office | Office | Calendar Management | autonomous | Scheduling, conflicts, buffers, and timezone math handled. | Executive Assistant | calendar-manager; conflict-resolver |
| 7 | Back Office | Office | Email Triage | autonomous | The inbox sorted by what actually needs the human. | Inbox Manager | draft-responder; email-triager |
| 8 | Back Office | Records | Contract Lifecycle | assisted | Renewals, expiries, and obligations tracked so nothing sneaks up. | Contracts Coordinator | contract-tracker; renewal-notifier |
| 9 | Back Office | Records | CRM Sync | autonomous | Deals, contacts, and statuses stay current everywhere. | Records Administrator | crm-syncer; two-way-updater |
| 10 | Back Office | Records | Document Filing & Retrieval | autonomous | Every document named, filed, and findable in ten seconds. | Records Administrator | document-filer; retrieval-indexer |
| 11 | Back Office | Records | Entity Compliance | manual | Filings and obligations per entity, tracked and scheduled. | Records Administrator | compliance-calendar; filing-tracker |
| 12 | Back Office | Records | Expense Categorization | assisted | Spend categorized for the accountant before they ask. | Financial Reporting Analyst | expense-categorizer |
| 13 | Back Office | Reporting | Goal Pacing | autonomous | Tracking against the income target, with pace forecasts. | Financial Reporting Analyst | goal-pacer; runway-projector |
| 14 | Back Office | Reporting | Revenue Reporting | autonomous | Monthly revenue truth across entities and currencies. | Financial Reporting Analyst | currency-normalizer; revenue-reporter |
| 15 | Back Office | Talent | Candidate Sourcing | manual | Find and rank candidates for open roles across platforms. | Talent Coordinator | candidate-finder; profile-ranker |
| 16 | Back Office | Talent | HR & Policy Assistant | assisted | Answer staff policy questions from the real handbook · leave, expenses, onboarding admin. | People Operations Assistant | handbook-keeper; policy-answerer |
| 17 | Back Office | Talent | Onboarding & Training | autonomous | New hires get the playbooks, access, and 30-day plan automatically. | Talent Coordinator | hire-onboarder; training-sequencer |
| 18 | Back Office | Talent | Screening & Scheduling | assisted | First-pass screens and interview logistics, handled. | Talent Coordinator | interview-scheduler; screen-summarizer |
| 19 | Customer | Community | Engagement & Replies | autonomous | Every member question and mention gets a response in the house voice. | Community Manager | community-responder; mention-watcher |
| 20 | Customer | Community | Event Coordination | manual | Run the AMAs, calls, and spotlights on a cadence the community can count on. | Community Manager | event-scheduler; session-runner |
| 21 | Customer | Community | Member Spotlights | manual | Find and celebrate member wins · the retention engine. | Community Manager | spotlight-writer; win-detector |
| 22 | Customer | Community | Moderation | assisted | Keep the space clean · spam, conduct, and noise handled quietly. | Community Manager | conduct-monitor; spam-filter |
| 23 | Customer | Success | Advocacy & Referrals | assisted | Turn your happiest customers into referrals, reviews, and case studies. | Customer Success Manager | advocate-finder; referral-asker |
| 24 | Customer | Success | Churn Prediction | assisted | Predict which accounts are about to slip · before the usage even dips. | Customer Success Manager | churn-modeler; risk-forecaster |
| 25 | Customer | Success | Health Scoring | assisted | Score every account on usage, sentiment, and engagement · before renewal season. | Customer Success Manager | churn-predictor; health-scorer |
| 26 | Customer | Success | Onboarding Journeys | autonomous | Guide every new customer through activation, step by step. | Customer Success Manager | activation-tracker; journey-sequencer |
| 27 | Customer | Success | QBR Prep | autonomous | Build the quarterly business review from real account data. | Customer Success Manager | qbr-builder; value-recap-writer |
| 28 | Customer | Success | Renewals & Expansion | manual | Time renewal conversations and spot upsell openings. | Customer Success Manager | expansion-spotter; renewal-scheduler |
| 29 | Customer | Support | Escalations | assisted | Spot the angry, the churn-risk, and the edge case · and get a human there fast. | Support Operations Manager | escalation-router; sentiment-flagger |
| 30 | Customer | Support | FAQ & Self-Serve | autonomous | Answer the questions that repeat · and turn them into living help content. | Help Content Writer; Support Answerer | faq-responder; help-article-writer |
| 31 | Customer | Support | Macro Authoring | autonomous | Turn the tickets that repeat into canned, on-brand responses agents reuse. | Support Operations Manager | macro-writer; response-templater |
| 32 | Customer | Support | Ticket Triage | assisted | Classify, prioritize, and route every support request the moment it lands. | Support Operations Manager | priority-router; sla-watcher; ticket-classifier |
| 33 | Deals | Call Cycle | Call Capture | autonomous | Record, transcribe, and file every meeting automatically. | Meeting Intelligence Engineer | meeting-filer; transcript-ingester |
| 34 | Deals | Call Cycle | Follow-Up Drafting | autonomous | Draft the recap email with next steps before the prospect forgets the call. | Deal Debrief Analyst | next-step-drafter; recap-writer |
| 35 | Deals | Call Cycle | Objection Library | assisted | Mine every call for the objections that come up · build the rebuttals that win. | Deal Debrief Analyst | objection-miner; rebuttal-builder |
| 36 | Deals | Call Cycle | Post-Call Debrief | autonomous | Extract outcomes, action items, and deal updates from the transcript. | Deal Debrief Analyst | action-extractor; commitment-tracker; deal-updater |
| 37 | Deals | Call Cycle | Pre-Call Briefing | autonomous | Build a brief before every call · who, company, history, objectives, talking points. | Call Prep Researcher | attendee-researcher; prep-brief-builder |
| 38 | Deals | Deal Artifacts | Agreement Drafting | assisted | Produce the services agreement the moment a deal closes verbally. | Contracts Coordinator | contract-generator; esign-preparer |
| 39 | Deals | Deal Artifacts | Deal Room Assembly | autonomous | Spin up tracked, password-gated deal rooms per prospect. | Deal Room Producer | engagement-tracker; magic-link-issuer; room-builder |
| 40 | Deals | Deal Artifacts | Demo Prototyping | autonomous | Turn discovery notes into a working visual prototype before the next meeting. | Solutions Engineer | dream-prototyper; sandbox-builder |
| 41 | Deals | Deal Artifacts | Pricing Support | autonomous | Model anchors, phase structures, and ROI comparisons per deal. | Pricing Analyst | anchor-calculator; phase-structurer; roi-modeler |
| 42 | Deals | Deal Artifacts | Proposal Generation | autonomous | Generate branded proposals rendered to PDF from call context. | Proposal Writer | pdf-renderer; proposal-writer |
| 43 | Deals | Inbound | Comment-CTA Fulfillment | autonomous | Detect keyword comments on content and deliver the promised asset by DM. | DM Fulfillment Specialist | dm-fulfiller; keyword-listener |
| 44 | Deals | Inbound | Inbox Triage | autonomous | Sort inbound email and DMs · client, lead, brand deal, noise. | Inbound Response Manager | inbox-triager; priority-router |
| 45 | Deals | Inbound | Lead Qualification | autonomous | Parse intake forms and score inbound leads before a human looks. | Inbound Response Manager | budget-detector; intake-parser; qual-scorer |
| 46 | Deals | Inbound | Speed-to-Lead | autonomous | Acknowledge and engage every inbound lead within minutes. | Inbound Response Manager | instant-responder; intake-acknowledger |
| 47 | Deals | Pipeline Ops | CRM Hygiene | autonomous | Keep records deduped, fields normalized, stages honest. | Pipeline Operations Manager | field-normalizer; record-deduper; stage-auditor |
| 48 | Deals | Pipeline Ops | Forecasting | assisted | Probability-weight the pipeline into a revenue forecast. | Pipeline Operations Manager | close-probability-scorer; revenue-forecaster |
| 49 | Deals | Pipeline Ops | Pipeline Reporting | autonomous | Weekly pipeline state · what moved, what stalled, what closes next. | Pipeline Operations Manager | funnel-analyzer; pipeline-reporter |
| 50 | Deals | Pipeline Ops | Reactivation | autonomous | Revive dormant deals and win back lost ones on a schedule. | Reactivation Specialist | dormant-deal-reviver; winback-sequencer |
| 51 | Deals | Pipeline Ops | Win/Loss Analysis | manual | Tag why deals close or die; feed patterns back into targeting. | Reactivation Specialist | loss-tagger; pattern-miner |
| 52 | Deals | Reply Handling | Hot-Lead Routing | autonomous | Route interested replies to the calendar and the pipeline instantly. | Outbound Inbox Manager | crm-promoter; hot-lead-alerter |
| 53 | Deals | Reply Handling | Meeting Booking | autonomous | Propose slots, book calls, chase no-shows. | Meeting Booking Coordinator | cal-booker; no-show-recoverer; slot-proposer |
| 54 | Deals | Reply Handling | Objection Response | assisted | Draft responses to common objections from a tuned library. | Outbound Inbox Manager | objection-library; response-drafter |
| 55 | Deals | Reply Handling | Referral Capture | autonomous | Spot the "talk to my colleague" replies and action the warm intro. | Inbound Response Manager | intro-router; referral-spotter |
| 56 | Deals | Reply Handling | Reply Classification | autonomous | Read every reply and tag it · interested, objection, referral, not now, never. | Outbound Inbox Manager | auto-labeler; intent-classifier; sentiment-tagger |
| 57 | Intelligence | Companies | Buying-Committee Mapping | assisted | Who actually decides · economic buyer, champion, blockers, their roles. | Relationship Mapper | committee-mapper; role-classifier |
| 58 | Intelligence | Companies | Company Deep-Dive | autonomous | Financials, growth signals, org structure, strategic posture. | Company Research Analyst | company-profiler; signal-collector |
| 59 | Intelligence | Companies | Funding & Financials Lookup | autonomous | Rounds, investors, revenue estimates, filings · who just got budget. | Company Research Analyst | financials-reader; funding-tracker |
| 60 | Intelligence | Companies | Tech-Stack Detection | autonomous | What a target company runs, and where the gaps are. | Company Research Analyst | gap-analyzer; stack-detector |
| 61 | Intelligence | Markets | Competitor Teardown | autonomous | Pricing, positioning, strengths, weaknesses, exploitable gaps. | Competitive Intelligence Analyst | competitor-teardown; positioning-mapper |
| 62 | Intelligence | Markets | Pricing Research | autonomous | What the market charges, anchors, and packaging patterns. | Competitive Intelligence Analyst | packaging-analyzer; pricing-scanner |
| 63 | Intelligence | Markets | TAM / Market Sizing | autonomous | How many companies actually fit · the real size of the prize. | Market Mapper | segment-counter; tam-sizer |
| 64 | Intelligence | Markets | Vertical Analysis | autonomous | Is this vertical worth entering · demand, budgets, buying behavior. | Vertical Analyst | opportunity-scorer; vertical-analyzer |
| 65 | Intelligence | Monitoring | Account Monitoring | assisted | Watch a target list for funding, hiring, leadership, and tech changes · ongoing. | Signal Monitoring Analyst | account-watcher; change-detector |
| 66 | Intelligence | Monitoring | Alert Routing | autonomous | The signals that matter reach the right person · the noise gets filtered. | Signal Monitoring Analyst | alert-router; signal-scorer |
| 67 | Intelligence | Monitoring | News & Mention Tracking | assisted | Every mention of your brand, competitors, and topics · as it lands. | Signal Monitoring Analyst | mention-tracker; news-watcher |
| 68 | Intelligence | People | Network Mapping | manual | Who knows whom · paths into a target account. | Relationship Mapper | connection-mapper |
| 69 | Intelligence | People | Person Research | autonomous | Background, content trail, interests, mutual ground for any contact. | Prospect Research Analyst | content-trail-scanner; person-profiler |
| 70 | Intelligence | People | Warm-Path Finding | assisted | The shortest real intro path into a target account · who can connect you. | Relationship Mapper | intro-drafter; path-finder |
| 71 | Intelligence | Synthesis | Adversarial Verification | autonomous | Claims get attacked before they get believed. | Red Team Reviewer | claim-verifier; source-cross-checker |
| 72 | Intelligence | Synthesis | Data Visualization | autonomous | Turn a pile of research into charts and diagrams that explain themselves. | Business Data Analyst | chart-builder; diagram-generator |
| 73 | Intelligence | Synthesis | Research Reports | autonomous | Any question → structured, cited report with diagrams. | Research Reporter | diagram-generator; report-builder; source-citer |
| 74 | Marketing | Brand Deals | Approval Docs | autonomous | Brand-safe formatted docs for sponsor sign-off. | Brand Deal Producer | approval-doc-generator |
| 75 | Marketing | Brand Deals | Deal Scripting | autonomous | Sponsored scripts in the proven format, per brand brief. | Brand Deal Producer | brand-script-writer; claim-fact-checker |
| 76 | Marketing | Creation | Ad Creative | assisted | Generate and iterate paid-ad variations · hooks, angles, formats. | Creative Strategist | ad-variation-builder; angle-tester |
| 77 | Marketing | Creation | Caption Writing | autonomous | Platform-correct captions with CTA placement rules baked in. | Social Copywriter | caption-writer; cta-placer |
| 78 | Marketing | Creation | Carousel Production | autonomous | Design and export branded carousel slides. | Carousel Designer | carousel-builder; slide-exporter |
| 79 | Marketing | Creation | Deck Production | autonomous | Webinar and talk decks in the brand design system. | Presentation Designer | deck-builder; slide-templater |
| 80 | Marketing | Creation | Hook Writing | autonomous | Generate and rank hooks per platform from proven patterns. | Creative Strategist | hook-generator; hook-ranker |
| 81 | Marketing | Creation | Image Generation | assisted | Brand-consistent images from reference libraries. | Brand Visual Designer; Personal Brand Designer | brand-image-generator; character-consistency |
| 82 | Marketing | Creation | Landing Page Copy | autonomous | Conversion copy for the whole page · hero, proof, offer, FAQ, CTA. | Conversion Copywriter | offer-framer; page-copywriter |
| 83 | Marketing | Creation | Script Writing | autonomous | Full reel and video scripts in the house voice. | Scriptwriter | script-writer; voice-matcher |
| 84 | Marketing | Creation | Thumbnail & Cover Design | assisted | Scroll-stopping thumbnails and covers tuned to earn the click. | Brand Visual Designer | cover-tester; thumbnail-designer |
| 85 | Marketing | Creation | Video Production | autonomous | Programmatic video · overlays, captions, motion graphics on recordings. | Video Editor | caption-syncer; overlay-animator; reel-compositor |
| 86 | Marketing | Distribution | Newsletter & Broadcast | autonomous | Design and send the weekly email in the brand system. | Newsletter Editor | broadcast-sender; newsletter-builder |
| 87 | Marketing | Distribution | OG & Share Surface | autonomous | Every page ships with share-ready open-graph imagery. | SEO Engineer | og-image-generator |
| 88 | Marketing | Distribution | Publishing | assisted | Schedule and post across platforms via API. | Publishing Manager | api-publisher; post-scheduler |
| 89 | Marketing | Distribution | SEO & GEO | autonomous | Make the site legible to search engines and LLMs. | SEO Engineer | llms-txt-maintainer; schema-marker; sitemap-builder |
| 90 | Marketing | Insights | Audience Analysis | autonomous | Mine comments and DMs for questions, objections, and content ideas. | Content Performance Analyst | comment-miner; question-clusterer |
| 91 | Marketing | Insights | Competitor Analysis | autonomous | Scrape and transcribe competitor content; extract hook patterns. | Instagram Content Analyst; TikTok Content Analyst | hook-pattern-miner; reel-transcriber |
| 92 | Marketing | Insights | Performance Mining | autonomous | Rank your own content corpus · what worked, what to re-hash. | Content Performance Analyst | corpus-ranker; era-analyzer; rehash-finder |
| 93 | Marketing | Insights | Trend Monitoring | autonomous | Watch the niche for breaking topics and rising formats. | Trend Analyst | format-spotter; news-watcher |
| 94 | Marketing | Repurposing | Clip Extraction | assisted | Cut long recordings into short-form clips worth posting. | Video Editor | clip-finder; highlight-extractor |
| 95 | Marketing | Repurposing | Cross-Platform Adaptation | autonomous | One idea → native formats for every platform. | Content Repurposing Manager | format-adapter; platform-translator |
| 96 | Marketing | Repurposing | Lead-Magnet Builds | autonomous | Turn content themes into gated guides and landing pages. | Lead Magnet Producer | gated-page-generator; guide-builder |
| 97 | Operations | Build Ops | Agent Evaluation | assisted | Test agent outputs against a benchmark before they touch real work. | QA Engineer | eval-harness; regression-checker |
| 98 | Operations | Build Ops | Data Migration | assisted | Move and clean data between systems without losing or mangling a row. | Integration Engineer | dedupe-validator; field-mapper; migration-runner |
| 99 | Operations | Build Ops | Document Extraction | autonomous | High-volume structured extraction from client documents. | Document Extraction Engineer | accuracy-benchmarker; extraction-pipeline; schema-mapper |
| 100 | Operations | Build Ops | Integration Builds | autonomous | Wire client systems together · CRMs, calendars, transcripts, payments. | Integration Engineer | api-integrator; webhook-wirer |
| 101 | Operations | Build Ops | Portal Provisioning | autonomous | Spin up client-scoped delivery portals with live status. | Client Portal Manager | portal-provisioner; portal-theming |
| 102 | Operations | Build Ops | QA & Verification | assisted | Verify every build against real data before the client sees it. | QA Engineer | output-verifier; regression-checker |
| 103 | Operations | Client Comms | Meeting Follow-Ups | autonomous | Client call transcripts → action items → assigned and tracked. | Follow-Up Coordinator | action-assigner; followup-processor |
| 104 | Operations | Client Comms | Portal Sync | autonomous | Session summaries and deliverables flow into the client portal automatically. | Client Portal Manager | deliverable-publisher; portal-syncer |
| 105 | Operations | Client Comms | Status Updates | autonomous | Clients see progress without asking for it. | Delivery Status Reporter | milestone-notifier; status-poster |
| 106 | Operations | Knowledge | Context Maintenance | autonomous | Per-client context files stay current as work happens. | Company Knowledge Base | context-updater; memory-writer |
| 107 | Operations | Knowledge | Handoff Docs | assisted | Clean documentation when a system ships to the client. | Playbook Writer | handoff-writer; runbook-generator |
| 108 | Operations | Knowledge | SOP Generation | manual | Turn delivered work into reusable playbooks. | Playbook Writer | playbook-extractor; sop-writer |
| 109 | Operations | Knowledge | Transcript Processing | autonomous | Every meeting becomes searchable, structured context. | Meeting Intelligence Engineer | entity-extractor; transcript-structurer |
| 110 | Operations | Onboarding | Access Collection | assisted | Chase and verify every credential and API key needed to build. | Client Onboarding Manager | access-verifier; credential-chaser |
| 111 | Operations | Onboarding | Kickoff Pack | autonomous | Welcome email, access checklist, and project scaffold the day a deal closes. | Client Onboarding Manager | access-checklister; kickoff-generator |
| 112 | Operations | Onboarding | Project Scaffolding | autonomous | Stand up the repo, context files, and plan for a new engagement. | Client Onboarding Manager | context-writer; repo-scaffolder |
| 113 | Operations | Reliability | Cost & Usage Tracking | autonomous | Token and API spend tracked against budget · no surprise bills. | Reliability Engineer | budget-guard; spend-tracker |
| 114 | Operations | Reliability | Incident Response | assisted | When an automation breaks · triage, root-cause, fix, and write the note. | Reliability Engineer | incident-triager; postmortem-writer; rootcause-finder |
| 115 | Operations | Reliability | Monitoring & Alerting | assisted | Watch every automation for failures and silent stalls · know before the client does. | Reliability Engineer | failure-alerter; uptime-watcher |
| 116 | Sales | Enrichment | Account Enrichment | autonomous | Layer firmographics, tech stack, and headcount trends onto target accounts. | Data Enrichment Specialist | firmographic-appender; growth-signal-scorer; tech-stack-detector |
| 117 | Sales | Enrichment | Contact Enrichment | autonomous | Find and append emails, phones, and LinkedIn profiles to every lead. | Data Enrichment Specialist | email-finder; linkedin-matcher; phone-appender |
| 118 | Sales | Enrichment | Email Verification | autonomous | Validate every address before it ever gets a send. | Data Enrichment Specialist | catch-all-detector; smtp-verifier |
| 119 | Sales | Enrichment | Fit Scoring | autonomous | Score every lead against ICP so outreach spends effort where it converts. | Lead Scoring Analyst | disqualifier; fit-scorer; tier-assigner |
| 120 | Sales | Lead Sourcing | Database Mining | autonomous | Pull targeted company and contact lists from structured databases. | Lead Sourcing Manager | apollo-query-builder; saved-search-runner |
| 121 | Sales | Lead Sourcing | List Building | autonomous | Merge, dedupe, and segment raw leads into campaign-ready lists. | Lead Sourcing Manager | csv-normalizer; list-deduper; segmenter |
| 122 | Sales | Lead Sourcing | Social Mining | autonomous | Harvest engaged audiences · post commenters, followers, group members. | Social Prospecting Specialist | comment-harvester; engagement-miner; profile-collector |
| 123 | Sales | Lead Sourcing | Web & Maps Scraping | autonomous | Scrape local businesses, directories, and niche sources for leads. | Lead Sourcing Manager | directory-harvester; maps-scraper |
| 124 | Sales | Outreach Writing | Cold Email Drafting | autonomous | Write multi-step cold email sequences tuned to the vertical and offer. | Cold Email Copywriter | sequence-writer; spintax-builder; subject-line-generator |
| 125 | Sales | Outreach Writing | Cold-Call Scripting | autonomous | Call and voicemail scripts with branching objection handling that read human. | Outbound Scriptwriter | call-scripter; objection-brancher |
| 126 | Sales | Outreach Writing | LinkedIn Messaging | autonomous | Draft connection notes and DM sequences that read human. | LinkedIn Outreach Specialist | connection-note-writer; dm-sequencer |
| 127 | Sales | Outreach Writing | Personalization Research | autonomous | Build a personalization dossier per prospect · hooks, context, common ground. | Prospect Research Analyst | common-ground-scanner; hook-finder; prospect-dossier |
| 128 | Sales | Outreach Writing | Proof Matching | autonomous | Match the right case study to each prospect’s industry and problem. | Case Study Curator | case-study-matcher; proof-point-selector |
| 129 | Sales | Outreach Writing | Video Prospecting | autonomous | Personalized video scripts · the hook, the personal line, the CTA, under 90 seconds. | Outbound Scriptwriter | personalization-writer; video-scripter |
| 130 | Sales | Sequencing & Send | Campaign Launch | autonomous | Push finished campaigns into sending platforms with correct settings. | Campaign Operations Manager | heyreach-syncer; instantly-syncer |
| 131 | Sales | Sequencing & Send | Campaign Orchestration | autonomous | Build multi-channel cadences · email, LinkedIn, phone touches in order. | Campaign Operations Manager | cadence-builder; channel-router |
| 132 | Sales | Sequencing & Send | Deliverability | assisted | Keep domains healthy · warmup, spam testing, inbox rotation. | Deliverability Manager | domain-health-auditor; spam-score-tester; warmup-monitor |
| 133 | Sales | Sequencing & Send | Send Optimization | autonomous | Schedule sends by timezone and pace volume to protect reply rates. | Campaign Operations Manager | timezone-scheduler; volume-pacer |
| 134 | Sales | Targeting | ICP Definition | autonomous | Define and refine ideal customer profiles per vertical · firmographics, pain patterns, buying triggers. | ICP Strategist | icp-profiler; pain-pattern-library; vertical-scorer |
| 135 | Sales | Targeting | Lookalike Modeling | assisted | Build new target lists off the shape of your closed-won accounts. | Lead Scoring Analyst | lookalike-builder; pattern-extractor |
| 136 | Sales | Targeting | Market Mapping | autonomous | Map the total addressable companies in a target vertical before a campaign. | Market Mapper | tam-mapper; vertical-census |
| 137 | Sales | Targeting | Trigger Detection | assisted | Watch for buying signals · hiring, funding, tech changes, leadership moves. | Buying Signals Analyst | funding-tracker; hiring-signal-watcher; tech-change-detector |

## Machine-readable companions

- `data/all_skills.json` — all three sets with mappings and explanations.
- `data/skills.csv` — named skill files.
- `data/capabilities.csv` — atomic capabilities.
- `data/jobs.csv` — jobs, descriptions, playbook context, and mappings.

Source: `data/graph.json` (570 nodes, 832 directed edges).

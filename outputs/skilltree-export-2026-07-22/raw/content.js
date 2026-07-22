/* ============ SKILLTREE v1.0 · PLAYBOOK LAYER ============
   Deep entries per job. Keyed by exact job name from TREE.
   Fields:
     replaces · what this job costs a business done by hand (the FTE math)
     req      · prerequisite jobs (by exact name). 'Company Knowledge Base' = the hub.
     ladder   · what manual / assisted / autonomous actually look like for this job
     notes    · build guidance: how to stand it up, what good looks like
     files    · downloadable skill files bundled with this resource
*/
const HUB = 'Company Knowledge Base';

const PLAYBOOK = {

/* ── SALES ───────────────────────────────────────────── */

'ICP Definition': {
  files: [{ label: 'ICP Strategist', path: 'skills/icp-strategist.md' }],
  human: 'The founder owns this forever. AI drafts and refreshes; the human decides who the business is for. Never fully delegated.',
  replaces: 'The founder’s gut feel, applied inconsistently by everyone downstream. Bad ICP wastes every dollar spent after it.',
  req: [HUB],
  ladder: {
    manual: 'A slide from 2 years ago that nobody opens.',
    assisted: 'AI drafts ICP profiles per vertical from your closed-won data; a human edits quarterly.',
    autonomous: 'Profiles update themselves as deals close and lose · win patterns feed back in without a meeting.',
  },
  notes: 'Start here. This is the first node of the Sales tree for a reason · every job downstream (sourcing, scoring, writing) reads from it. Write one page per vertical: firmographics, the pain in the buyer’s words, the trigger that makes them buy now. Store it where your agents can read it, not in a deck.',
},

'Database Mining': {
  files: [{ label: 'Lead Sourcing Manager', path: 'skills/lead-sourcing-manager.md' }],
  human: 'A human sets the target and spot-checks 10 rows per pull. Bad lists poison everything downstream · the check takes five minutes and saves a campaign.',
  replaces: '4–6 hours/week of an SDR pulling and cleaning lists · roughly $8–12k/year of a $65k rep’s time spent not selling.',
  req: ['ICP Definition'],
  ladder: {
    manual: 'Someone exports CSVs from a database tool and fixes them in spreadsheets.',
    assisted: 'You describe the target in plain language; the agent builds the query, pulls, dedupes, and hands back a clean segmented list.',
    autonomous: 'Standing searches run weekly per ICP; new matches land pre-scored, with verified contacts, with no one asking.',
  },
  notes: 'The skill below builds tiered lead lists from structured databases and the open web, and degrades gracefully based on which API keys you have. Feed it your ICP file · the output quality is a direct function of node one.',
  files: [{ label: 'Lead Sourcing Manager', path: 'skills/lead-sourcing-manager.md' }],
},

'Social Mining': {
  files: [{ label: 'Social Prospecting Specialist', path: 'skills/social-prospecting-specialist.md' }],
  replaces: 'The list nobody builds by hand: everyone who engaged with a competitor’s post is a warm prospect, but scraping them manually takes hours per post.',
  req: ['ICP Definition'],
  ladder: {
    manual: 'You screenshot commenters and look them up one by one.',
    assisted: 'Point the agent at a post or profile; it harvests engagers, enriches, scores against ICP, and drafts the first DM.',
    autonomous: 'Watched accounts and keywords feed a standing warm-prospect pool, refreshed continuously.',
  },
  notes: 'Highest-intent cold list you can build · these people already raised their hand on the topic. The skill below scrapes engagers, enriches profiles, ICP-scores, and writes openers in one pass.',
  files: [{ label: 'Social Prospecting Specialist', path: 'skills/social-prospecting-specialist.md' }],
},

'Personalization Research': {
  files: [{ label: 'Prospect Research Analyst', path: 'skills/prospect-research-analyst.md' }],
  replaces: '10–15 minutes per prospect done properly · which is why nobody does it properly past the first twenty.',
  req: ['Database Mining'],
  ladder: {
    manual: 'Two minutes on LinkedIn, then “Love what you’re doing at {company}!”',
    assisted: 'The agent builds a dossier per prospect · hooks, recent moves, common ground · and a human picks the angle.',
    autonomous: 'Every lead that enters a sequence carries its dossier with it; the writer agents consume it directly.',
  },
  notes: 'This is the difference between personalization and mail-merge. The skill below produces a structured dossier per person: what they’ve said publicly, what changed at their company, and the two strongest hooks to open with.',
  files: [{ label: 'Prospect Research Analyst', path: 'skills/prospect-research-analyst.md' }],
},

'Cold Email Drafting': {
  files: [{ label: 'Cold Email Copywriter', path: 'skills/cold-email-copywriter.md' }],
  human: 'A human approves every new sequence before launch and owns the offer it sells. Once a sequence is proven, AI varies it within the approved frame.',
  replaces: 'A $60–80k/year SDR’s core output · or a $2–4k/month agency retainer that sends the same template to everyone.',
  req: ['ICP Definition', 'Personalization Research'],
  ladder: {
    manual: 'One template, first-name token, pray.',
    assisted: 'The agent writes the full sequence per segment from your offer doc and dossiers; a human approves before launch.',
    autonomous: 'Sequences generate per campaign, A/B variants included, with reply data feeding the next round’s angles.',
  },
  notes: 'Voice is the whole game. The skill below reads your offer and tone files before it writes a word · set those up first or you’ll get competent generic. Three-step sequences, problem → proof → door-close. Never lead with price.',
  files: [{ label: 'Cold Email Copywriter', path: 'skills/cold-email-copywriter.md' }],
},

'LinkedIn Messaging': {
  files: [{ label: 'LinkedIn Outreach Specialist', path: 'skills/linkedin-outreach-specialist.md' }],
  human: 'Messages send under a real person\u2019s name · that person reads what goes out under it. Approval per sequence, not per message.',
  replaces: 'The 30 connection requests/day a founder sends in a good week and zero in a busy one. Consistency is the entire channel.',
  req: ['ICP Definition', 'Personalization Research'],
  ladder: {
    manual: 'Copy-pasted “I’d love to connect” notes.',
    assisted: 'Connection notes and DM sequences drafted per prospect from their dossier; human sends.',
    autonomous: 'Sequenced sending through an outreach platform, with replies routed back into the pipeline automatically.',
  },
  notes: 'Shorter than email, more human, no links in the first message. The skill below drafts the full connection → DM → follow-up arc and exports to sending platforms.',
  files: [{ label: 'LinkedIn Outreach Specialist', path: 'skills/linkedin-outreach-specialist.md' }],
},

'Account Enrichment': {
  files: [{ label: 'Data Enrichment Specialist', path: 'skills/data-enrichment-specialist.md' }],
  replaces: 'The research step everyone skips: outreach to a company you don’t understand reads like spam because it is.',
  req: ['Database Mining'],
  ladder: {
    manual: 'A glance at the website before the call.',
    assisted: 'Tech stack, headcount trends, and growth signals appended to every target account on demand.',
    autonomous: 'Accounts re-enrich on a schedule; material changes (funding, hiring spikes, stack changes) trigger alerts to the targeting layer.',
  },
  notes: 'Pairs with Company Deep-Dive in the Intelligence department · enrichment is the bulk pass, deep-dive is the surgical one for accounts worth a real pursuit.',
},

/* ── DEALS ───────────────────────────────────────────── */

'Reply Classification': {
  files: [{ label: 'Outbound Inbox Manager', path: 'skills/outbound-inbox-manager.md' }],
  human: 'Edge cases route to a human within minutes; everything else is logged for a weekly 15-minute audit of the classifier\u2019s calls.',
  replaces: 'The inbox-checking anxiety loop. At volume, a human misses hot replies for 6+ hours · and speed-to-reply is the highest-leverage variable in outbound.',
  req: ['Cold Email Drafting'],
  ladder: {
    manual: 'Founder reads every reply, usually at midnight.',
    assisted: 'Every reply auto-tagged · interested / objection / referral / not-now / never · with drafted responses queued for approval.',
    autonomous: 'Interested replies route to the calendar in minutes; objections get library responses; only edge cases reach a human.',
  },
  notes: 'The pattern that scales outbound past one inbox. Build the objection library from your real replies · after ~50 classified threads the categories stabilize and the drafts stop needing edits. This is the node franchise networks and multi-territory businesses feel hardest.',
},

'Meeting Booking': {
  files: [{ label: 'Meeting Booking Coordinator', path: 'skills/meeting-booking-coordinator.md' }],
  human: 'The calendar owner sets the rules once · buffers, hours, who qualifies. The agent never negotiates exceptions; humans do.',
  replaces: 'The 4–7 message back-and-forth that kills deal momentum, plus the no-shows nobody chases.',
  req: ['Reply Classification'],
  ladder: {
    manual: '“What times work for you?” × 3.',
    assisted: 'Agent proposes slots from the live calendar and books on confirmation.',
    autonomous: 'Hot replies get slots in the first response; no-shows get a recovery sequence automatically.',
  },
  notes: 'Wire it to your real availability with buffers, not your aspirational one. The no-show recovery sequence alone pays for the build · most teams just let those die.',
},

'Pre-Call Briefing': {
  files: [{ label: 'Call Prep Researcher', path: 'skills/call-prep-researcher.md' }],
  replaces: 'The 20 scrambled minutes before every call · or worse, walking in cold and asking questions the website answers.',
  req: [HUB, 'Call Capture'],
  ladder: {
    manual: 'Skim their LinkedIn in the waiting room.',
    assisted: 'A one-page brief lands before every call: who, company, history, last conversation, open threads, suggested objectives.',
    autonomous: 'Briefs generate from the calendar automatically · every external meeting, no trigger needed.',
  },
  notes: 'Reads the CRM, past transcripts, and email threads. The compounding effect is real: by call three the brief knows more about the relationship than you remember.',
},

'Call Capture': {
  files: [{ label: 'Meeting Intelligence Engineer', path: 'skills/meeting-intelligence-engineer.md' }],
  human: 'Humans run the meeting; the system just never forgets it. Flag sensitive calls as do-not-record · the convention matters more than the tool.',
  replaces: 'Notes that don’t exist, decisions nobody wrote down, and “wait, what did we agree?”',
  req: [HUB],
  ladder: {
    manual: 'Pen, paper, vibes.',
    assisted: 'Every meeting recorded and transcribed via a notetaker; transcripts filed per client.',
    autonomous: 'Transcripts flow into the knowledge base automatically and become readable context for every other agent.',
  },
  notes: 'The single cheapest high-leverage node on this map · a notetaker subscription and a filing convention. Everything in the Deals and Operations trees gets smarter the day this turns on. If you deploy one node this month, deploy this one.',
},

'Post-Call Debrief': {
  files: [{ label: 'Deal Debrief Analyst', path: 'skills/deal-debrief-analyst.md' }],
  human: 'The deal owner skims the extracted actions same-day · 2 minutes to confirm what a human promised another human.',
  replaces: '30 minutes of post-call admin per meeting that either eats selling time or doesn’t happen.',
  req: ['Call Capture'],
  ladder: {
    manual: 'Action items live in your head until they don’t.',
    assisted: 'Transcript → outcomes, action items, deal-stage updates, drafted within minutes of hang-up.',
    autonomous: 'CRM updates itself, tasks assign themselves, and the follow-up email is waiting in drafts.',
  },
  notes: 'Combine with Follow-Up Drafting: the recap email should arrive while the prospect still remembers the call. Same-day follow-up measurably outperforms next-day · and AI makes same-hour trivial.',
},

'Demo Prototyping': {
  files: [{ label: 'Solutions Engineer', path: 'skills/solutions-engineer.md' }],
  human: 'AI builds the prototype; the human decides whether it ships. Nothing reaches a prospect without the seller\u2019s eyes on it.',
  replaces: 'The two-week proposal gap where deals go cold. A visual prototype sent same-day collapses the “is this possible?” conversation entirely.',
  req: ['Call Capture'],
  ladder: {
    manual: 'A follow-up deck, eventually.',
    assisted: 'Discovery notes → working visual prototype + send message, same day, human reviews before it goes out.',
    autonomous: 'Every discovery call triggers a prototype draft; the human picks which ones to polish and send.',
  },
  notes: 'Sell the dream: show them their end state before the proposal exists. The follow-up call stops being “convince me” and becomes “scope it.” The skill below extracts the brief from a transcript, picks the right format, and drafts the send message.',
  files: [{ label: 'Solutions Engineer', path: 'skills/solutions-engineer.md' }],
},

'Proposal Generation': {
  files: [{ label: 'Proposal Writer', path: 'skills/proposal-writer.md' }],
  human: 'AI drafts structure and prose; a human owns scope and price on every proposal. Those two numbers are never delegated.',
  replaces: '3–6 hours per proposal · and for services firms doing tenders, often 2–3 days per response. This is frequently the bottleneck on revenue itself.',
  req: ['Call Capture', 'Post-Call Debrief'],
  ladder: {
    manual: 'Last proposal, find-and-replace, new logo.',
    assisted: 'Call context → drafted proposal in the house template, rendered to branded PDF; human edits scope and price.',
    autonomous: 'Proposal drafts generate from the deal record the moment a deal hits “proposal” stage, matched to the closest past win.',
  },
  notes: 'Template matching is the unlock: your best past proposals become the pattern library. Build the brand template once, render programmatically forever. Architecture and professional-services firms run entire bid teams on what this node replaces.',
},

'Deal Room Assembly': {
  files: [{ label: 'Deal Room Producer', path: 'skills/deal-room-producer.md' }],
  replaces: 'PDF proposals that get forwarded into the void. A tracked room tells you who opened what, when · intel a PDF can never give you.',
  req: ['Proposal Generation'],
  ladder: {
    manual: 'Attachment in an email thread.',
    assisted: 'Branded, password-gated room per prospect · proposal, scope, proof, pricing · spun up from a template.',
    autonomous: 'Rooms generate per deal with engagement tracking feeding the pipeline: you know which stakeholder read pricing twice.',
  },
  notes: 'The forward-ability is the point · your champion sells internally with a link, not an attachment. Magic links per stakeholder turn open-data into a stakeholder map.',
},

'Reactivation': {
  files: [{ label: 'Reactivation Specialist', path: 'skills/reactivation-specialist.md' }],
  human: 'A human approves the revival list monthly · some dead deals should stay dead, and only a human knows which.',
  replaces: 'The revenue sitting in your dead-deals column. Most pipelines have 6 figures of “went quiet” that nobody systematically revisits.',
  req: ['CRM Hygiene'],
  ladder: {
    manual: 'You remember an old prospect in the shower.',
    assisted: 'Dormant deals surface on a schedule with a drafted, context-aware re-opener · referencing where things left off, leading with something new.',
    autonomous: 'Every deal that goes quiet enters a patient, spaced revival track automatically; replies route back to the pipeline.',
  },
  notes: 'The re-opener must contain new value · a relevant build, a result in their vertical, a changed offer. “Just checking in” is not reactivation, it’s noise. Cheapest pipeline you’ll ever generate; the leads are already paid for.',
},

/* ── MARKETING ───────────────────────────────────────── */

'Performance Mining': {
  files: [{ label: 'Content Performance Analyst', path: 'skills/content-performance-analyst.md' }],
  replaces: 'Posting on instinct while your own corpus already knows what works. Your top 10 posts are a content strategy · if anything reads them.',
  req: [HUB],
  ladder: {
    manual: 'Scrolling your own profile for ideas.',
    assisted: 'The corpus ranked by performance, patterns extracted · hooks, formats, topics · with re-hash candidates flagged.',
    autonomous: 'Every new post is scored against the pattern library before it ships; winners auto-feed the idea queue.',
  },
  notes: 'Re-hashing beats inventing: a proven idea in a new format outperforms a new idea in any format, and audiences forget faster than creators think.',
},

'Trend Monitoring': {
  files: [{ label: 'Trend Analyst', path: 'skills/trend-analyst.md' }],
  replaces: 'An hour a day of feed-scrolling disguised as research.',
  req: [],
  ladder: {
    manual: 'Whatever the algorithm showed you at breakfast.',
    assisted: 'Daily sweep of the niche · breaking topics, rising formats · distilled into content angles in your voice.',
    autonomous: 'The day’s angles land each morning, pre-matched to your pillars and ranked by fit.',
  },
  notes: 'The skill below runs topic → articles → hooks → ready-to-draft ideas as one chain. Speed matters more than polish on trend content · the half-life is measured in days.',
  files: [{ label: 'Trend Analyst', path: 'skills/trend-analyst.md' }],
},

'Competitor Analysis': {
  files: [{ label: 'Instagram Content Analyst', path: 'skills/instagram-content-analyst.md' }, { label: 'TikTok Content Analyst', path: 'skills/tiktok-content-analyst.md' }],
  replaces: 'Watching competitors casually instead of systematically. Their viral posts are free R&D · someone else paid the testing cost.',
  req: [],
  ladder: {
    manual: 'You saw their reel and felt something.',
    assisted: 'Competitor content scraped and transcribed; hook patterns, formats, and cadence extracted into a playbook.',
    autonomous: 'Watched accounts feed a standing pattern library; your hook generator consumes it directly.',
  },
  notes: 'Transcription is the trick · the spoken hook is where the pattern lives, not the caption. Two skills below: one for Instagram reels, one for TikTok.',
  files: [
    { label: 'Instagram Content Analyst', path: 'skills/instagram-content-analyst.md' },
    { label: 'TikTok Content Analyst', path: 'skills/tiktok-content-analyst.md' },
  ],
},

'Hook Writing': {
  files: [{ label: 'Creative Strategist', path: 'skills/creative-strategist.md' }],
  replaces: 'The blank-page tax on every piece of content. The hook is 80% of performance and the part most creators spend the least time on.',
  req: ['Performance Mining'],
  ladder: {
    manual: 'First line that comes to mind, posted.',
    assisted: '15–20 ranked hooks per idea, per platform, generated from proven patterns · you pick, you post.',
    autonomous: 'Every idea in the queue arrives with its hook variants attached; performance data re-ranks patterns monthly.',
  },
  notes: 'Volume is the method: write twenty, ship one. The skill below generates per-platform · a LinkedIn hook and a TikTok hook are different species.',
  files: [{ label: 'Creative Strategist', path: 'skills/creative-strategist.md' }],
},

'Cross-Platform Adaptation': {
  files: [{ label: 'Content Repurposing Manager', path: 'skills/content-repurposing-manager.md' }],
  replaces: 'The 5× content multiplier everyone talks about and almost nobody operationalizes, because manual repurposing is genuinely tedious.',
  req: ['Hook Writing'],
  ladder: {
    manual: 'Same caption pasted to four apps.',
    assisted: 'One idea → native formats for every platform: LinkedIn post, X thread, newsletter section, video script, short-form scripts.',
    autonomous: 'Every flagship piece automatically fans out to the full format set, queued for review.',
  },
  notes: 'Native beats syndicated · each platform gets its own structure, not a resize. The skill below runs one idea through research and out to seven formats.',
  files: [{ label: 'Content Repurposing Manager', path: 'skills/content-repurposing-manager.md' }],
},

'Image Generation': {
  files: [{ label: 'Brand Visual Designer', path: 'skills/brand-visual-designer.md' }],
  replaces: 'Stock photos that look like stock photos, or $50–200/image from a designer for routine brand visuals.',
  req: [],
  ladder: {
    manual: 'Canva at 11pm.',
    assisted: 'Brand-consistent images generated from a reference library · your visual language, learned and reproduced.',
    autonomous: 'Every post in the queue gets on-brand visual options generated alongside the copy.',
  },
  notes: 'The reference library is the moat: feed it your best existing visuals and identity shots so output stays unmistakably yours. Two skills below · brand imagery and consistent-character personal imagery.',
  files: [
    { label: 'Brand Visual Designer', path: 'skills/brand-visual-designer.md' },
    { label: 'Personal Brand Designer', path: 'skills/personal-brand-designer.md' },
  ],
},

'Lead-Magnet Builds': {
  files: [{ label: 'Lead Magnet Producer', path: 'skills/lead-magnet-producer.md' }],
  replaces: 'The “we should make a guide” task that stays on the roadmap for two quarters.',
  req: ['Performance Mining'],
  ladder: {
    manual: 'A PDF made once, promoted twice, forgotten.',
    assisted: 'Content themes that already performed become gated guides with landing pages, built end-to-end in a session.',
    autonomous: 'Top-performing topics trigger draft lead magnets automatically; the comment-CTA layer delivers them.',
  },
  notes: 'Build magnets from proven demand only · the reel that popped tells you exactly what people want gated. Wire delivery to Comment-CTA Fulfillment in the Deals tree and the loop closes itself.',
},

/* ── OPERATIONS ──────────────────────────────────────── */

'Document Extraction': {
  files: [{ label: 'Document Extraction Engineer', path: 'skills/document-extraction-engineer.md' }],
  human: 'Humans review the low-confidence queue and own the gold-standard set. The machine earns autonomy field by field, measured against it.',
  replaces: 'Teams of people reading documents and retyping them into systems. At volume this is entire payrolls · the densest ROI node on this map for document-heavy businesses.',
  req: [HUB],
  ladder: {
    manual: 'Humans read, humans type, humans err.',
    assisted: 'Documents → structured fields via an extraction pipeline, with confidence scores and human review on the low-confidence tail.',
    autonomous: 'High-confidence extractions flow straight to the system of record; accuracy benchmarked continuously against a gold set.',
  },
  notes: 'Benchmark before you celebrate: build a 50-document gold-standard set and measure field-level accuracy against it. The review-queue pattern (auto-accept above threshold, human below) gets you production-safe long before the model is perfect. Probation services, insurance, compliance · whole verticals run on this node.',
},

'Meeting Follow-Ups': {
  files: [{ label: 'Follow-Up Coordinator', path: 'skills/followup-coordinator.md' }],
  human: 'The delivery lead confirms owners and deadlines before the recap goes to the client · commitments are made by people.',
  replaces: 'Action items agreed on a client call that evaporate by Thursday · the quiet killer of delivery trust.',
  req: ['Call Capture'],
  ladder: {
    manual: 'Whoever remembered, does it. Maybe.',
    assisted: 'Client transcripts → extracted action items, owners, deadlines · drafted into the recap that goes out same-day.',
    autonomous: 'Items assign themselves into the task system and chase their owners; the client recap sends on schedule.',
  },
  notes: 'Clients don’t churn over outcomes, they churn over feeling forgotten. Same-day recaps with named owners are the cheapest retention system ever built.',
},

'Context Maintenance': {
  files: [{ label: 'Node Zero · knowledge base builder', path: 'skills/knowledge-base.md' }],
  replaces: 'The “wait, what’s the latest with this client?” tax every time anyone touches an account.',
  req: ['Call Capture'],
  ladder: {
    manual: 'Context lives in one person’s head and a thousand Slack threads.',
    assisted: 'Per-client context files updated as work happens · calls, decisions, open items, current state.',
    autonomous: 'Every transcript, email, and deliverable updates the file automatically; any agent or human reads one page and is current.',
  },
  notes: 'This IS the knowledge base doctrine in practice · one living file per client that everything reads and writes. Start the convention before you automate it: the file format matters more than the tooling.',
},

/* ── INTELLIGENCE ────────────────────────────────────── */

'Company Deep-Dive': {
  files: [{ label: 'Company Research Analyst', path: 'skills/company-research-analyst.md' }],
  replaces: 'A junior analyst day ($300–500 equivalent) per company researched properly · so it only happens for deals already in motion, when it should happen before.',
  req: [],
  ladder: {
    manual: 'Their website, their LinkedIn, your impression.',
    assisted: 'Financials, growth signals, org structure, and strategic posture compiled into a scored profile on demand.',
    autonomous: 'Target accounts re-profile on triggers · funding, leadership changes, hiring spikes · and alert the pipeline.',
  },
  notes: 'The skill below scores fit, not just facts · the output is “should we pursue, and with what angle,” not a data dump.',
  files: [{ label: 'Company Research Analyst', path: 'skills/company-research-analyst.md' }],
},

'Person Research': {
  files: [{ label: 'Prospect Research Analyst', path: 'skills/prospect-research-analyst.md' }],
  replaces: 'Walking into rooms not knowing who you’re talking to.',
  req: [],
  ladder: {
    manual: 'A LinkedIn skim.',
    assisted: 'Background, content trail, interests, and mutual ground compiled per person, with personalization hooks ranked.',
    autonomous: 'Every new contact in the CRM gets a profile automatically; briefs consume them.',
  },
  notes: 'Same engine as Personalization Research in Sales · deployed here for relationships rather than sequences: partners, hires, investors, podcast guests.',
  files: [{ label: 'Prospect Research Analyst', path: 'skills/prospect-research-analyst.md' }],
},

'Competitor Teardown': {
  files: [{ label: 'Competitive Intelligence Analyst', path: 'skills/competitive-intelligence-analyst.md' }],
  replaces: 'Competing on guesswork. Most firms can’t articulate a competitor’s pricing or positioning beyond adjectives.',
  req: [],
  ladder: {
    manual: 'You visited their pricing page once.',
    assisted: 'Full teardown on demand: pricing, positioning, strengths, weaknesses, exploitable gaps · cited.',
    autonomous: 'Tracked competitors re-tear quarterly; material changes (pricing, packaging, positioning) trigger alerts.',
  },
  notes: 'The exploitable-gaps section is the deliverable · everything else is context. The skill below structures the attack: where they’re weak, where you’re strong, what to say in-market.',
  files: [{ label: 'Competitive Intelligence Analyst', path: 'skills/competitive-intelligence-analyst.md' }],
},

'Research Reports': {
  files: [{ label: 'Research Reporter', path: 'skills/research-reporter.md' }],
  replaces: '$2–5k boutique research engagements, or the decision made without one.',
  req: [],
  ladder: {
    manual: 'Twenty open tabs and a hunch.',
    assisted: 'Any question → structured, cited report with diagrams, in an hour instead of a week.',
    autonomous: 'Standing questions (market shifts, vertical signals) refresh on schedule and publish to the knowledge base.',
  },
  notes: 'Pair with Adversarial Verification before anything load-bearing: claims get attacked before they get believed.',
},

/* ── CUSTOMER ────────────────────────────────────────── */

'FAQ & Self-Serve': {
  files: [{ label: 'Support Answerer', path: 'skills/support-answerer.md' }, { label: 'Help Content Writer', path: 'skills/help-content-writer.md' }],
  human: 'A human reviews new auto-drafted articles before they publish, and owns the escalation line the moment an answer isn\u2019t in the corpus.',
  replaces: 'The 40–60% of support volume that is the same fifteen questions, answered by hand, forever.',
  req: [HUB],
  ladder: {
    manual: 'Copy-paste from a doc nobody updates.',
    assisted: 'Repeat questions answered from a living knowledge base; new repeats flagged and drafted into help content.',
    autonomous: 'The help corpus grows itself · every novel resolved ticket becomes a draft article; deflection rate tracked.',
  },
  notes: 'The flywheel is the point: support tickets are your help-content roadmap, ranked by frequency. Deflection compounds · every article works every day after it ships.',
},

'Health Scoring': {
  files: [{ label: 'Customer Success Manager', path: 'skills/customer-success-manager.md' }],
  human: 'The score surfaces risk; a human makes the call. No automated message ever goes to an at-risk account without an owner deciding to send it.',
  replaces: 'Finding out an account was at risk in the cancellation email.',
  req: [HUB],
  ladder: {
    manual: 'Renewal panic, quarterly.',
    assisted: 'Accounts scored on usage, sentiment, and engagement; the at-risk list surfaces monthly with reasons.',
    autonomous: 'Scores update continuously; threshold crossings trigger plays · outreach, check-in, escalation · before renewal season.',
  },
  notes: 'Sentiment from call transcripts and support threads is the leading indicator usage data misses · accounts go quiet before they go.',
},

/* ── BACK OFFICE ─────────────────────────────────────── */

'Invoice Generation': {
  files: [{ label: 'Billing Manager', path: 'skills/billing-manager.md' }],
  human: 'A human glances at every invoice over a threshold before it sends. Money out the door wrong costs more than the glance.',
  replaces: 'The founder doing invoices on Sunday night, occasionally wrong, across entities and currencies.',
  req: [],
  ladder: {
    manual: 'A template, edited by hand, eventually sent.',
    assisted: 'Branded invoices generated per entity, currency, and tax treatment from the deal record.',
    autonomous: 'Milestones and retainer schedules trigger invoices automatically; numbering, tax, and filing handled.',
  },
  notes: 'Encode the entity routing once · which company invoices which client, in what currency, with what tax line · and a recurring error class disappears permanently.',
},

'Collections': {
  files: [{ label: 'Billing Manager', path: 'skills/billing-manager.md' }],
  human: 'Tone escalation past the second nudge gets a human decision · the relationship is worth more than the invoice.',
  replaces: 'The awkwardness of chasing money · which is why founders chase late and lose weeks of cash flow to their own politeness.',
  req: ['Invoice Generation', 'Payment Tracking'],
  ladder: {
    manual: 'You notice an unpaid invoice during a low moment.',
    assisted: 'Overdue invoices get drafted nudges · polite, persistent, escalating on schedule · queued for your approval.',
    autonomous: 'The sequence runs itself: day-3 nudge, day-10 firmer, day-21 escalation, with payment status checked before every send.',
  },
  notes: 'An agent is never embarrassed to ask. Tone-match the relationship · the sequence should sound like your best self on a confident day, every time.',
},

'Goal Pacing': {
  files: [{ label: 'Financial Reporting Analyst', path: 'skills/financial-reporting-analyst.md' }],
  replaces: 'Discovering in November that the year’s number was never going to happen.',
  req: ['Revenue Reporting'],
  ladder: {
    manual: 'A number in your head and a feeling about it.',
    assisted: 'Live pace against target · monthly and annual · with a forecast of where the current trajectory lands.',
    autonomous: 'Pace alerts with diagnosis: which pipeline gap, which retainer change, which seasonality is moving the landing point.',
  },
  notes: 'The forecast matters more than the scoreboard · “you finish at 71% on current pace” in June is actionable; the same number in December is an obituary.',
},

/* ── SALES (cont.) ──────────────────── */

'Market Mapping': {
  files: [{ label: 'Market Mapper', path: 'skills/market-mapper.md' }],
  replaces: 'Guessing how big the pond is. Teams campaign into verticals without knowing whether the addressable universe is 400 companies or 40,000 · and misprice the effort either way.',
  req: ['ICP Definition'],
  ladder: {
    manual: 'A spreadsheet of companies somebody had heard of.',
    assisted: 'The agent builds the full universe per ICP · every company that fits, counted and segmented · and a human sanity-checks the edges.',
    autonomous: 'The map refreshes as companies get founded, funded, and folded; campaign planning reads live numbers, not last year’s guess.',
  },
  notes: 'This is TAM at the company-name level, not the analyst-report level · a list you can actually campaign into. Know the denominator before you spend: a 4,000-company vertical justifies a system, a 150-company vertical justifies a hand-written letter each. The trap is mapping by industry code · SIC and NAICS lie constantly. Map by what companies actually do, scraped from what they say about themselves.',
},

'Trigger Detection': {
  files: [{ label: 'Buying Signals Analyst', path: 'skills/buying-signals-analyst.md' }],
  replaces: 'Outreach timed by your calendar instead of theirs. The gap between a 2% and a 10% reply rate is often just catching a company the week something changed.',
  req: ['Market Mapping'],
  ladder: {
    manual: 'You see the funding announcement on LinkedIn three weeks after everyone else did.',
    assisted: 'Watched accounts get scanned for hiring spikes, funding, tech changes, and leadership moves; flagged leads land with the trigger attached.',
    autonomous: 'A trigger fires and the lead enters the right sequence the same day, with the trigger written into the opener.',
  },
  notes: 'A detected signal nobody references is a wasted signal · the trigger has to reach the first line of the email, not sit in a CRM field. Start with the two or three triggers that genuinely map to your offer (hiring an SDR team if you sell outbound, a new ops lead if you sell automation) and ignore the rest. The trap is watching everything: ten signal types produce noise, two produce openers.',
},

'Web & Maps Scraping': {
  files: [{ label: 'Lead Sourcing Manager', path: 'skills/lead-sourcing-manager.md' }],
  replaces: 'The lists databases don’t sell · local businesses, niche directories, marketplaces. Built by hand this is days of copy-paste per territory, so it simply doesn’t get built.',
  req: ['ICP Definition'],
  ladder: {
    manual: 'Copy-pasting business names out of Google Maps into a spreadsheet at 1am.',
    assisted: 'Point the agent at a geography and a category; it scrapes, structures, dedupes against past pulls, and hands back clean rows.',
    autonomous: 'Standing scrapes per territory refresh on schedule; new openings show up in your pipeline before competitors know they exist.',
  },
  notes: 'This is where local and SMB lists live · the big databases are weakest exactly where Maps and directories are strongest. Scraped data is also the dirtiest data you’ll touch: route everything through verification before it gets near a sequence. The trap is one giant pull and done · territories change monthly, and the refresh is where the edge is.',
},

'List Building': {
  files: [{ label: 'Lead Sourcing Manager', path: 'skills/lead-sourcing-manager.md' }],
  replaces: 'The 2–3 hours per campaign of merging CSVs and fighting duplicates · and the reputational cost when the same CEO gets the same email from two of your sequences.',
  req: ['Database Mining', 'Web & Maps Scraping'],
  ladder: {
    manual: 'VLOOKUP, tears, and the same person in three rows under slightly different spellings.',
    assisted: 'Raw pulls from every source merge, dedupe, and segment into named campaign lists on command.',
    autonomous: 'Every sourcing job feeds one canonical pool; campaign lists assemble themselves with suppression · clients, open deals, past bounces · applied automatically.',
  },
  notes: 'The suppression list is the underrated half of this job: nothing torches trust like cold-emailing a current client or an open deal. Keep one canonical lead pool that every campaign draws from, not per-campaign spreadsheets that drift apart. The trap is deduping on email alone · dedupe on person and company, or the same prospect with two addresses slips through twice.',
},

'Contact Enrichment': {
  files: [{ label: 'Data Enrichment Specialist', path: 'skills/data-enrichment-specialist.md' }],
  replaces: 'A list you can’t reach. Without enrichment, 40–60% of a raw list has no usable contact · paying for leads and reaching half of them is the silent tax on every campaign.',
  req: ['List Building'],
  ladder: {
    manual: 'Guessing first.last@company.com and hoping.',
    assisted: 'Waterfall enrichment runs per lead · email, direct dial, LinkedIn · across multiple providers, appended to the record.',
    autonomous: 'Every lead entering the pool enriches on arrival; coverage rates and cost-per-found-contact tracked per provider.',
  },
  notes: 'Waterfall is the whole pattern: no single provider covers more than ~70%, so chain two or three and take the first valid hit. Track cost-per-found-contact by provider and cut the losers quarterly. The trap is enriching before filtering · paying to find the phone number of a lead you were never going to contact. Score and segment first, enrich what survives.',
},

'Email Verification': {
  files: [{ label: 'Data Enrichment Specialist', path: 'skills/data-enrichment-specialist.md' }],
  replaces: 'Domain burn. A 5% bounce rate doesn’t cost you 5% of sends · it gets the domain flagged, and the next 10,000 emails land in spam.',
  req: ['Contact Enrichment'],
  ladder: {
    manual: 'Send and find out.',
    assisted: 'Every address passes through a verifier before it touches a sequence; catch-alls and risky addresses get flagged for a decision.',
    autonomous: 'Verification runs on the way in and re-runs on any list older than 90 days; anything under threshold never reaches a sender.',
  },
  notes: 'This is a gate, not a feature · nothing unverified gets sent, ever, and bounce rate stays under 2%. Decide your catch-all policy explicitly: send to them on a separate domain or don’t send at all, but never mix them into your clean volume. The trap is verifying once and trusting forever · addresses decay 2–3% a month as people change jobs.',
},

'Fit Scoring': {
  files: [{ label: 'Lead Scoring Analyst', path: 'skills/lead-scoring-analyst.md' }],
  replaces: 'Reps spending identical effort on a perfect-fit account and a tire-kicker, because the list doesn’t know the difference. Effort allocation is the multiplier on everything downstream.',
  req: ['ICP Definition', 'Account Enrichment'],
  ladder: {
    manual: 'Sort by company size and call it prioritization.',
    assisted: 'Every lead scores against the ICP file · firmographics, tech stack, triggers · and lands in a tier before any send.',
    autonomous: 'Scores recompute as enrichment refreshes; A-tier routes to high-touch sequences, C-tier to low-cost ones, without anyone deciding per lead.',
  },
  notes: 'A score that doesn’t change behavior is decoration · each tier must get genuinely different treatment: sequence depth, personalization effort, channel mix. Calibrate against closed-won quarterly: if your last ten wins weren’t A-tier, the model is wrong, not the wins. The trap is the 100-point model nobody trusts · three tiers with legible rules beat it every time.',
},

'Proof Matching': {
  files: [{ label: 'Case Study Curator', path: 'skills/case-study-curator.md' }],
  replaces: 'Sending the SaaS case study to the manufacturer. Generic proof reads like no proof · relevance is what makes evidence land, and matching it by hand is one more step nobody does at volume.',
  req: [HUB, 'Account Enrichment'],
  ladder: {
    manual: 'The same two logos in every email, regardless of who’s reading.',
    assisted: 'The agent picks the closest-match case study per prospect · industry, problem, company size · and writes the one-line proof into the draft.',
    autonomous: 'Every sequence pulls its proof at generation time; a new case study enters the library and immediately starts appearing wherever it fits.',
  },
  notes: 'The library structure is the actual work: every case study tagged by vertical, problem, and outcome, each with one quotable number. A near-match in their industry beats a bigger number from a different world · buyers pattern-match on “that’s me” before they read the result. The trap is letting the agent round numbers up for effect: proof goes out verbatim or not at all.',
},

'Campaign Orchestration': {
  files: [{ label: 'Campaign Operations Manager', path: 'skills/campaign-operations-manager.md' }],
  replaces: 'Single-channel outbound. Email-only gets email-only results · coordinated email, LinkedIn, and phone touches lift reply rates 2–3×, but sequencing them by hand across hundreds of leads is a planning job nobody sustains.',
  req: ['Cold Email Drafting', 'LinkedIn Messaging'],
  ladder: {
    manual: 'An email sequence here, some connection requests there, and no relationship between them.',
    assisted: 'The agent assembles the full cadence · which channel, which day, which message · from your drafted assets; a human approves the plan.',
    autonomous: 'Cadences build per segment from the playbook; the channel mix adjusts itself based on what actually got replies last quarter.',
  },
  notes: 'The channels have to know about each other: the LinkedIn note lands after email two and references the thread · or references nothing if it went unanswered. Map the whole arc before the first send; retrofitting coordination onto a live campaign is misery. The trap is believing more touches means more replies · 8–12 touches over three weeks, then stop and hand the silence to Reactivation.',
},

'Campaign Launch': {
  files: [{ label: 'Campaign Operations Manager', path: 'skills/campaign-operations-manager.md' }],
  human: 'A human reviews the rendered test send before volume flows. Launch is the last gate where a broken token costs nothing · one minute of eyes here versus 2,000 apologies later.',
  replaces: 'The hour of fiddly platform setup per campaign · and the occasional disaster where the {firstName} token goes out raw to the whole list.',
  req: ['Campaign Orchestration', 'Email Verification'],
  ladder: {
    manual: 'Copy-paste the sequence into the sender, set the limits from memory, hope.',
    assisted: 'Finished campaigns push into the sending platform with schedules, limits, custom fields, and tracking configured; a human checks the test send.',
    autonomous: 'Approved campaigns deploy themselves · settings pulled from the playbook, test send auto-rendered and checked, go-live logged.',
  },
  notes: 'Turn the launch checklist into code: daily limits set, tracking domain live, custom fields mapped, unsubscribe working, test send rendered and read. The render check catches the embarrassing failure class · broken personalization tokens · before anyone outside sees it. The trap is launching to the full list at once: ramp over days, both for deliverability and so a bad sequence dies at 10% sent instead of 100%.',
},

'Deliverability': {
  files: [{ label: 'Deliverability Manager', path: 'skills/deliverability-manager.md' }],
  replaces: 'The silent campaign killer. Everything upstream can be perfect and none of it matters from spam · and most teams find out a month of wasted sends too late.',
  req: ['Campaign Launch'],
  ladder: {
    manual: 'Reply rates fall off a cliff and somebody eventually wonders why.',
    assisted: 'Inbox placement tests, warmup, and domain health checks run on schedule; problems surface with the fix attached.',
    autonomous: 'Rotation, warmup, and volume throttling self-manage; a domain showing strain gets pulled from rotation before it burns.',
  },
  notes: 'Architecture first: cold volume goes through secondary domains, never your main one · 2–3 inboxes per domain, 30–50 sends per inbox per day, warmed for 2–3 weeks before real volume. From there it’s monitoring: placement tests and bounce trends on a schedule, not when things feel slow. The trap is treating this as one-time setup · deliverability is a tide, not a switch, and it only moves one direction unattended.',
},

'Send Optimization': {
  files: [{ label: 'Campaign Operations Manager', path: 'skills/campaign-operations-manager.md' }],
  replaces: 'Blasting everyone at 9am your time · including the prospects for whom that’s 2am, and the inbox providers for whom that spike looks exactly like spam.',
  req: ['Campaign Launch', 'Deliverability'],
  ladder: {
    manual: 'Send-all, then refresh the dashboard.',
    assisted: 'Sends schedule per recipient timezone and pace inside provider-safe volume; the agent proposes window changes from reply data.',
    autonomous: 'Send timing tunes itself per segment from observed reply patterns; volume flexes up and down with domain health.',
  },
  notes: 'Timezone correctness alone is worth real points of reply rate · a 9am email read at 9am is a different email than one buried under the overnight pile. Pacing should look human: spread through the working day, randomized intervals, no perfect cron-job spikes. The trap is over-tuning send windows on small samples · you need hundreds of sends per cell before timing data means anything; until then, recipient-morning and move on.',
},

/* ── DEALS (cont.) ──────────────────── */

'Objection Response': {
  files: [{ label: 'Outbound Inbox Manager', path: 'skills/outbound-inbox-manager.md' }],
  human: 'The library is human-authored from real won deals · AI retrieves and adapts, it never invents a new counter-argument that no one has tested live.',
  replaces: 'Re-improvising the same five rebuttals forever. Every outbound motion gets the same objections · price, timing, “we have someone”, “send info” · and most reps answer each one slightly worse than last time.',
  req: ['Reply Classification'],
  ladder: {
    manual: 'You retype your best comeback from memory, slightly different every time, usually softer.',
    assisted: 'Each classified objection gets a drafted response from a tuned library · your strongest past answer, adapted to this thread · queued for approval.',
    autonomous: 'Known objections get library responses on send-approval autopilot; novel objections route to a human and their winning answer joins the library.',
  },
  notes: 'Build the library from threads you actually won, not from sales books · your real replies beat generic frameworks. Five objections cover 80% of volume; write one great answer per objection per offer and stop there. The trap is over-arguing: the best objection responses concede something true, then reframe in one short paragraph.',
},

'Hot-Lead Routing': {
  files: [{ label: 'Outbound Inbox Manager', path: 'skills/outbound-inbox-manager.md' }],
  replaces: 'The hours an interested reply sits in an inbox while the prospect cools. Interest decays by the hour · a hot reply answered next morning converts at a fraction of one answered in minutes.',
  req: ['Reply Classification', 'CRM Hygiene'],
  ladder: {
    manual: 'The hot reply is item 47 in the inbox and gets the same priority as the newsletter.',
    assisted: 'Interested replies get flagged, pushed to the deal owner, and pre-loaded with a booking-ready response in minutes.',
    autonomous: 'Hot replies skip the queue entirely · calendar link sent, deal created at the right stage, owner notified, all before a human has read the thread.',
  },
  notes: 'This is plumbing, not intelligence · the classifier already found the gold; routing just refuses to let it sit. Wire it to the calendar and the CRM in the same motion so a hot reply becomes a booked slot and a pipeline record, not a notification. The trap is routing on weak signals: tune the classifier conservative, because one fake-hot alert per day teaches the owner to ignore all of them.',
},

'Speed-to-Lead': {
  files: [{ label: 'Inbound Response Manager', path: 'skills/inbound-response-manager.md' }],
  replaces: 'The two days between a form fill and a founder’s reply. Inbound leads contacted within five minutes convert at multiples of those contacted next-day · and most businesses are measured in days.',
  req: [HUB],
  ladder: {
    manual: 'The lead fills the form Tuesday, hears back Thursday, signed with someone else Wednesday.',
    assisted: 'Every inbound lead gets an acknowledgment within minutes · personal in tone, specific to what they asked · with the human looped in for the real conversation.',
    autonomous: 'First response, qualifying question, and booking link fire inside five minutes around the clock; the human wakes up to scheduled calls, not raw form fills.',
  },
  notes: 'The first message only has two jobs: prove a human-quality brain read their submission, and open the next step. Reference what they actually wrote · a reply that mirrors their form answer beats any template. The trap is sounding like an autoresponder; if the message could have been sent without reading the submission, rewrite the system.',
},

'Lead Qualification': {
  files: [{ label: 'Inbound Response Manager', path: 'skills/inbound-response-manager.md' }],
  human: 'AI scores and sorts; a human owns where the disqualification line sits and audits the auto-declines. Spotting the bad-fit lead that’s secretly a strategic exception stays a judgment call.',
  replaces: '30–45 minutes of discovery call per lead that should never have been booked. Unqualified calls are the most expensive way to learn someone has no budget.',
  req: ['ICP Definition'],
  ladder: {
    manual: 'Everyone who books gets a call; you find out they’re a student with a question at minute four.',
    assisted: 'Intake answers parsed and scored against your ICP · budget, fit, urgency · with a recommended route (book, nurture, decline) before a human looks.',
    autonomous: 'Qualified leads book straight onto the calendar, marginal ones enter a nurture track, and poor fits get a polite redirect · no human triage at all.',
  },
  notes: 'The intake form is the real build: ask three questions that predict close · budget range, problem in their words, timeline · and the scoring becomes trivial. Score against your closed-won pattern, not an aspirational ICP. The trap is over-filtering early: log every auto-declined lead and audit the list monthly until you trust the line.',
},

'Comment-CTA Fulfillment': {
  files: [{ label: 'DM Fulfillment Specialist', path: 'skills/dm-fulfillment-specialist.md' }],
  replaces: 'Manually DMing a link to 400 commenters · which means either hours of phone time after every post that pops, or broken promises to the exact people who raised their hands.',
  req: ['Lead-Magnet Builds'],
  ladder: {
    manual: 'You send the first 30 DMs by thumb, lose steam, and the other 370 commenters get nothing.',
    assisted: 'Keyword comments detected per post; the promised asset goes out by DM from a queue a human can watch.',
    autonomous: 'Every comment-CTA post fulfills itself · keyword detected, asset delivered, email captured, lead tagged by which asset they wanted · at any volume, at any hour.',
  },
  notes: 'This is the bridge between content and pipeline: the comment is a hand-raise, the DM is the capture, the asset is the excuse. Gate the asset behind an email and the content engine starts feeding the CRM directly. The trap is stopping at delivery · tag every lead with which asset they claimed, because that tag is targeting data for everything downstream.',
},

'Inbox Triage': {
  files: [{ label: 'Inbound Response Manager', path: 'skills/inbound-response-manager.md' }],
  replaces: 'The founder as a human sorting machine · 60–90 minutes a day deciding what each message even is before any real work starts, with the important ones buried under the noise.',
  req: [HUB],
  ladder: {
    manual: 'Everything is unread, everything is urgent, the client email from Tuesday surfaces Friday.',
    assisted: 'Every inbound email and DM tagged on arrival · client, lead, brand deal, admin, noise · with the must-answer items surfaced first.',
    autonomous: 'The inbox sorts itself continuously; noise never reaches a human, leads route to the pipeline, client messages flag the right project, and you work a ranked queue instead of a timeline.',
  },
  notes: 'Triage is classification plus routing · the tag is worthless unless something happens because of it: leads to the pipeline, client items to the project context, noise to archive. Start with five categories maximum; precision beats granularity. The trap is silent misfiling · keep a weekly audit of what got tagged noise, because one mis-archived client email costs more than the system saves.',
},

'Follow-Up Drafting': {
  files: [{ label: 'Deal Debrief Analyst', path: 'skills/deal-debrief-analyst.md' }],
  replaces: 'The recap email that goes out two days late or never. Deals lose momentum in the gap between the call and the follow-up · and the gap is usually just the seller being busy.',
  req: ['Call Capture', 'Post-Call Debrief'],
  ladder: {
    manual: 'You mean to send the recap tonight; tonight becomes Thursday; Thursday becomes “following up on our chat last week”.',
    assisted: 'The recap drafts itself from the transcript within minutes of hang-up · what was agreed, next steps, owners · waiting in drafts for a read and a send.',
    autonomous: 'Every external call produces its follow-up automatically; the human edits the occasional nuance, and same-hour recaps become the house standard.',
  },
  notes: 'Speed is the feature: a same-hour recap lands while the prospect still feels the call, and it quietly sets the version of events on your terms. Keep it short · decisions, next steps with owners and dates, one forward-looking line. The trap is sending a transcript summary instead of a sales document; the recap should advance the deal, not minute the meeting.',
},

'Agreement Drafting': {
  files: [{ label: 'Contracts Coordinator', path: 'skills/contracts-coordinator.md' }],
  human: 'A lawyer blesses the master template once; a human reviews every generated agreement before it goes out. AI fills and adapts · it never invents a clause.',
  replaces: 'The 3–10 day gap between “yes” and paperwork, where verbal closes go to die. Plus $300–800 of lawyer time per agreement if you draft each one fresh instead of templating once.',
  req: ['Proposal Generation'],
  ladder: {
    manual: 'You hunt for the last client’s contract, find-and-replace their name, and miss one instance of it in clause 9.',
    assisted: 'The moment a deal closes verbally, the agreement generates from the deal record · parties, scope, fees, terms · into the lawyer-approved template, ready for human review and signature.',
    autonomous: 'Stage change to closed-won triggers the agreement, routes it for e-signature, and chases the unsigned · the human only touches deals with non-standard terms.',
  },
  notes: 'Send the agreement the same day as the verbal yes · momentum is a closing tool and every day of silence invites second thoughts. Get one lawyer pass on the master template, then never freelance the legal language again; the AI’s job is filling variables, not writing clauses. The trap is letting per-deal “small tweaks” fork the template until no two contracts match.',
},

'Pricing Support': {
  files: [{ label: 'Pricing Analyst', path: 'skills/pricing-analyst.md' }],
  human: 'AI models the structures; the human picks the number. Price is positioning, leverage, and read-of-the-room · the final figure on every deal is a human call, never a model output.',
  replaces: 'Pricing by gut and anchoring low under pressure. The hour of FTE-comparison math and phase-structuring that justifies a 2–3× higher number · done properly for big deals, skipped for the rest.',
  req: [HUB, 'Pricing Research'],
  ladder: {
    manual: 'You pick a number on the call, feel it wobble, and discount before anyone asked you to.',
    assisted: 'Per deal: anchor comparisons, phase structures, and ROI math modeled from the discovery context · three defensible options with the reasoning attached, before the pricing conversation.',
    autonomous: 'Every deal entering proposal stage arrives with its pricing model pre-built · comparable past deals, suggested anchor, phase breakdown · and the human chooses rather than calculates.',
  },
  notes: 'Anchor against the cost of the alternative, not your own effort · the comparison to a salary, an agency retainer, or the cost of the problem persisting is what makes a number feel small. Phase the structure so the first yes is easy and the relationship prices the rest. The trap is letting the model’s mid-range option become a ceiling; the math exists to defend ambition, not cap it.',
},

'CRM Hygiene': {
  files: [{ label: 'Pipeline Operations Manager', path: 'skills/pipeline-operations-manager.md' }],
  replaces: 'The 10–20% of records that are duplicates, dead, or wrong · and every report, forecast, and automation silently built on top of them. Garbage hygiene taxes every node downstream.',
  req: [HUB],
  ladder: {
    manual: 'Three records for the same company, a deal marked “proposal” since March, and nobody trusts the dashboard.',
    assisted: 'Dedupe candidates, stale stages, and missing fields surface on a schedule with proposed fixes; a human approves the merge.',
    autonomous: 'Records dedupe and normalize continuously, stages age out with prompts to the owner, and every new entry conforms on arrival · the CRM stays true without a cleanup day.',
  },
  notes: 'Hygiene is the unglamorous prerequisite for the entire Pipeline Ops branch · reporting, forecasting, and reactivation all read from these records, and they inherit every error. Define “honest stage” rules in writing (what evidence moves a deal forward) and let the system enforce them. The trap is the quarterly cleanup blitz: hygiene is a standing process, not an event, and a CRM cleaned once decays in weeks.',
},

'Pipeline Reporting': {
  files: [{ label: 'Pipeline Operations Manager', path: 'skills/pipeline-operations-manager.md' }],
  replaces: 'The Monday hour of assembling pipeline state by hand · or the more common alternative, running the business on whatever the founder remembers the pipeline looking like.',
  req: ['CRM Hygiene'],
  ladder: {
    manual: 'Someone scrolls the CRM before the meeting and narrates it from memory.',
    assisted: 'A weekly digest lands on schedule: what moved, what stalled, what closes next, and which deals went quiet · with the deltas, not just the totals.',
    autonomous: 'The report writes and distributes itself, flags anomalies between editions, and answers ad-hoc pipeline questions on demand · the meeting reads the report instead of building it.',
  },
  notes: 'Report movement, not state · “what changed since last week” is the entire value, and a static pipeline snapshot is just a screenshot with ceremony. Include a stalled-deals section with days-since-last-touch; it is the report’s most actionable line. The trap is metric sprawl: one page, same format weekly, so deviations jump out instead of hiding in noise.',
},

'Forecasting': {
  files: [{ label: 'Pipeline Operations Manager', path: 'skills/pipeline-operations-manager.md' }],
  human: 'The model weights the pipeline; the deal owner adjusts the calls. A human who just left the room knows things no stage-probability ever will · the forecast is a draft until someone accountable signs it.',
  replaces: 'Revenue surprises in both directions. The founder’s number is usually hope-weighted, not probability-weighted · and the gap between them is the months of runway you didn’t know you were missing.',
  req: ['CRM Hygiene', 'Pipeline Reporting'],
  ladder: {
    manual: 'You add up the pipeline, multiply by optimism, and call it a forecast.',
    assisted: 'Deals probability-weighted by stage, age, and engagement signals into a monthly revenue forecast · with the assumptions visible, so a human can argue with them.',
    autonomous: 'The forecast updates as deals move, learns from its own misses, and flags the gap between the model’s number and the owner’s · which is usually where the truth lives.',
  },
  notes: 'Track forecast-versus-actual from day one · the model earns trust by being auditable, and three months of scorekeeping beats any methodology debate. Weight on behavior (engagement, momentum, days-in-stage) more than on stage labels, which mostly record what the seller hoped. The trap is false precision: a forecast with a range and visible assumptions is useful; a single confident number is theater.',
},

'Win/Loss Analysis': {
  files: [{ label: 'Reactivation Specialist', path: 'skills/reactivation-specialist.md' }],
  human: 'The losing seller writes the first draft of why · then someone who wasn’t in the deal reads it skeptically. Self-reported loss reasons are where pipelines lie to themselves most fluently.',
  replaces: 'Paying full tuition for every lost deal and keeping none of the lesson. Most teams can’t say why their last five losses died beyond “price” · which is almost never the real reason.',
  req: ['Call Capture', 'CRM Hygiene'],
  ladder: {
    manual: 'A shrug, a “they went another direction”, and the same mistake next quarter.',
    assisted: 'Every closed deal gets tagged with a structured reason, drawn from the transcripts and thread history rather than the seller’s memory; patterns compile quarterly.',
    autonomous: 'Loss patterns surface as they form · a vertical going cold, an objection trending up, a competitor winning on the same line · and feed straight back into targeting and the objection library.',
  },
  notes: 'The taxonomy is the build: eight to twelve fixed reasons, forced choice, free text optional · uncategorized losses are unanalyzable losses. Mine the call transcripts, not the seller’s recollection; the real reason is usually said out loud somewhere in the second call. The trap is collecting tags and never closing the loop · the analysis only pays when it changes the ICP, the pitch, or the price.',
},

/* ── MARKETING (cont.) ──────────────────── */

'Audience Analysis': {
  files: [{ label: 'Content Performance Analyst', path: 'skills/content-performance-analyst.md' }],
  replaces: 'Reading comments for dopamine instead of data. Your audience tells you exactly what to make next, every day, in writing · and almost nobody logs it.',
  req: [HUB],
  ladder: {
    manual: 'You vaguely remember someone asked about pricing once.',
    assisted: 'Comments and DMs mined on a schedule · questions, objections, and recurring pain extracted into a ranked content-idea queue.',
    autonomous: 'Every comment and DM feeds a standing demand map; new objections route to the idea queue and the offer doc without anyone scrolling.',
  },
  notes: 'Objections are the gold · a question asked three times in comments is a reel, a guide, and an email in one. Pipe the output into Hook Writing so demand drives creation, not the other way around. The trap is mining only your winners: the comments on mediocre posts tell you why they were mediocre.',
},

'Script Writing': {
  files: [{ label: 'Scriptwriter', path: 'skills/scriptwriter.md' }],
  replaces: '2–3 hours per script done properly, or $150–500 per script from a freelancer who doesn’t sound like you. At a daily posting cadence that’s a part-time hire.',
  req: ['Hook Writing', 'Performance Mining'],
  ladder: {
    manual: 'You wing it to camera and hope take four has an ending.',
    assisted: 'Full scripts drafted in the house voice from a hook and an angle · structure, beats, CTA · human edits before filming.',
    autonomous: 'Every idea in the queue arrives scripted in two or three variations; performance data tunes the structure monthly.',
  },
  notes: 'The voice file is the whole build · feed it real transcripts of your best-performing content, not your written posts, because spoken voice and written voice are different animals. Structure beats inspiration: hook → tension → payoff → CTA, every time. The trap is scripts that read well and speak badly · read every draft out loud before it’s approved.',
},

'Caption Writing': {
  files: [{ label: 'Social Copywriter', path: 'skills/social-copywriter.md' }],
  replaces: 'The 20 minutes per post that happens after the creative energy is spent · which is why most captions are an afterthought stapled to good content.',
  req: ['Hook Writing'],
  ladder: {
    manual: 'Emoji, three hashtags, post, regret.',
    assisted: 'Platform-correct captions drafted per asset · CTA placement, hashtag limits, and line-break rules baked in · human approves.',
    autonomous: 'Every queued post carries its caption variants; the rules update themselves as platforms change what works.',
  },
  notes: 'Encode the platform rules once as hard constraints · where the CTA sits, how many hashtags, how the first line truncates in feed · and the agent never violates them at 11pm the way a tired human does. The first line is a second hook: it shows before the tap. The trap is one caption pasted everywhere; a LinkedIn caption and a TikTok caption share an idea, not a structure.',
},

'Carousel Production': {
  files: [{ label: 'Carousel Designer', path: 'skills/carousel-designer.md' }],
  replaces: '$100–300 per carousel from a designer with a 3-day turnaround, or 2–4 hours of founder time per set fighting a drag-and-drop tool.',
  req: ['Hook Writing'],
  ladder: {
    manual: 'Canva, ten slides, fonts drifting by slide six.',
    assisted: 'Slides generated from a locked design system · copy in, branded PNGs out · human reviews the set before export.',
    autonomous: 'Winning ideas trigger carousel drafts automatically; the export pipeline renders and queues them for publishing.',
  },
  notes: 'Build the design system once as code · templates, type scale, spacing, logo placement · then every carousel is a content problem, not a design problem. Slide one is a hook with the same stakes as a video hook; slides two through six earn the swipe one at a time. The trap is redesigning per carousel: lock the system and let consistency become the brand.',
},

'Video Production': {
  files: [{ label: 'Video Editor', path: 'skills/video-editor.md' }],
  replaces: '$50–150 per reel to an editor with a 2–5 day turnaround · and the turnaround is the real cost, because trend content dies waiting in someone’s queue.',
  req: ['Script Writing'],
  ladder: {
    manual: 'You learn a video editor’s timeline at midnight, once, badly.',
    assisted: 'Recordings get overlays, captions, and motion graphics applied programmatically from a reusable component library; human reviews the render.',
    autonomous: 'Drop a recording in a folder and a finished, captioned, on-brand edit comes out · variants included, queued for review.',
  },
  notes: 'Programmatic video means edits defined in code, which means every solved problem · caption styling, transitions, overlay timing · becomes a reusable primitive instead of a memory. Build the primitives library first; the second video costs a tenth of the first. The trap is treating each video as a fresh project: copy the last working template, always.',
},

'Deck Production': {
  files: [{ label: 'Presentation Designer', path: 'skills/presentation-designer.md' }],
  replaces: '6–10 hours per webinar deck, or $500–1,500 to a designer who needs the content anyway · meaning you do the thinking twice.',
  req: [HUB],
  ladder: {
    manual: 'Last quarter’s deck with new dates and one new chart.',
    assisted: 'Talk outline in, branded deck out · house design system, real assets, consistent typography · human edits the narrative.',
    autonomous: 'Every booked talk or webinar triggers a deck draft from the topic and the knowledge base; you walk in and rehearse instead of build.',
  },
  notes: 'Lock three or four master slide patterns · cover, content, proof, CTA · and every deck becomes assembly, not design. The deck is a sales asset wearing an education costume: proof slides and the close deserve the most iterations. The trap is template drift · one deck built off-system and every deck after it inherits the mutation.',
},

'Clip Extraction': {
  files: [{ label: 'Video Editor', path: 'skills/video-editor.md' }],
  replaces: '$1–2k/month clipping agencies, or an editor billing hours to watch footage. A one-hour webinar holds 5–10 postable clips that mostly die unwatched in a recordings folder.',
  req: ['Video Production'],
  ladder: {
    manual: 'You meant to clip the webinar. That was three webinars ago.',
    assisted: 'Long recordings transcribed and scanned for standalone moments · strong claims, stories, answers · cut and captioned for review.',
    autonomous: 'Every long recording that lands triggers extraction; ranked clips arrive captioned and queued, no one asked.',
  },
  notes: 'Select from the transcript, not the timeline · reading an hour takes four minutes, watching it takes an hour. A clip earns posting only if it works with zero context: a complete claim, a complete story, or a complete answer. The trap is volume worship · ten mediocre clips from one recording trains the audience to skip you; ship the two that stand alone.',
},

'Publishing': {
  files: [{ label: 'Publishing Manager', path: 'skills/publishing-manager.md' }],
  human: 'A human eyeballs account, caption, and asset before each scheduled batch goes live. A wrong-account post is a screenshot forever · the two-minute check is non-negotiable.',
  replaces: 'The daily posting chore that survives exactly until the first busy week. Inconsistency is the silent killer of every content flywheel · the algorithm forgets faster than you recover.',
  req: ['Caption Writing'],
  ladder: {
    manual: 'Phone out, app open, paste, post, repeat per platform · when you remember.',
    assisted: 'Approved content scheduled and posted across platforms via API; the queue shows what ships when, and gaps get flagged.',
    autonomous: 'The pipeline runs creation → caption → queue → post on cadence; a human curates the queue, the system never misses a day.',
  },
  notes: 'Post via API, not via browser automation · platform APIs are the stable path and the account-safe one. Build the queue with a visible runway: knowing you have nine days of approved content banked changes how you create. The trap is going full autopilot on day one; run queue-plus-approval for a month before you let anything ship unseen.',
},

'Newsletter & Broadcast': {
  files: [{ label: 'Newsletter Editor', path: 'skills/newsletter-editor.md' }],
  replaces: '3–5 hours/week of writing and formatting, or $500–1k/month to a ghostwriter · and the issue that quietly skips a week, then two, then the list goes cold.',
  req: ['Cross-Platform Adaptation'],
  ladder: {
    manual: 'Sunday night, blank editor, “what happened this week?”',
    assisted: 'The week’s content and wins harvested into a designed issue in the brand template · human edits the takes, hits send.',
    autonomous: 'The issue assembles itself on schedule from the week’s shipped work; you review Thursday, it sends Friday, every week, forever.',
  },
  notes: 'Build the HTML template once in the brand system and never design an issue again · the weekly job becomes pure editorial. Harvest, don’t write: the newsletter should be assembled from content and work that already exists, with one original take on top. The trap is treating it as a broadcast instead of an asset · the list is the only audience you own; everything else is rented.',
},

'SEO & GEO': {
  files: [{ label: 'SEO Engineer', path: 'skills/seo-engineer.md' }],
  replaces: '$1–3k/month SEO retainers that mostly produce reports · or being invisible to the growing share of buyers who ask an LLM for a recommendation instead of searching.',
  req: [HUB],
  ladder: {
    manual: 'Someone installed an SEO plugin in 2023 and the site has been “optimized” ever since.',
    assisted: 'Sitemap, structured data, metadata, and an llms.txt generated and maintained from the actual site content; gaps audited on demand.',
    autonomous: 'Every new page ships pre-optimized for both crawlers and LLMs; rankings and AI-citation checks run on schedule and flag drift.',
  },
  notes: 'GEO · being legible and citable to LLMs · is the part most sites have done nothing about, and it is mostly the same hygiene as SEO done properly: clear structure, structured data, plain statements of what you do and for whom. Do the foundation pass in one session: sitemap, robots, schema markup, llms.txt. The trap is chasing keywords before fixing legibility · a site a machine can’t parse loses on every query, optimized or not.',
},

'OG & Share Surface': {
  files: [{ label: 'SEO Engineer', path: 'skills/seo-engineer.md' }],
  replaces: 'Links that unfurl as a blank gray rectangle in every DM, Slack, and LinkedIn share. Each naked link is a small credibility tax, paid on the exact surface where your content travels.',
  req: ['SEO & GEO'],
  ladder: {
    manual: 'One static og-image uploaded at launch, wrong dimensions, never updated.',
    assisted: 'A templated OG image per page type · title pulled in, brand system applied · generated at build time.',
    autonomous: 'Every page and post ships with its share card rendered automatically; new routes inherit the system with zero extra work.',
  },
  notes: 'Generate OG images programmatically from a template route, not as design files · the title, page type, and brand frame compose at request time and new content is covered forever. Test the unfurl where it actually happens: a messaging app, a LinkedIn draft, an X compose box. The trap is one generic image site-wide; per-page cards with the real title get measurably more clicks because they read as content, not as a logo.',
},

'Deal Scripting': {
  files: [{ label: 'Brand Deal Producer', path: 'skills/brand-deal-producer.md' }],
  human: 'Two approvals, both human: the sponsor signs off on claims, and the creator approves every line spoken under their name. Never let an agent invent a capability claim for someone else’s product · fact-check before it goes on camera.',
  replaces: 'Days of back-and-forth per sponsored script, with revision cycles quietly eating the deal’s margin. A $5k brand deal at four revision rounds is a $2k brand deal.',
  req: ['Script Writing', 'Performance Mining'],
  ladder: {
    manual: 'The brand sends a brief; you procrastinate, then write something neither of you loves.',
    assisted: 'Brief in, three script variations out · proven format, real product claims checked, creator voice intact · sponsor picks one.',
    autonomous: 'Signed deals trigger scripted variations automatically from the brief plus your top-performing formats; humans handle approval, not drafting.',
  },
  notes: 'Send three variations, not one · sponsors who choose between options approve faster than sponsors asked to judge a single take. Anchor every script in a format your own data says works; the brand bought your audience, and your audience came for your format. The trap is letting the brief flatten the voice · a sponsored post that sounds like an ad performs like an ad, which serves nobody who paid for it.',
},

'Approval Docs': {
  files: [{ label: 'Brand Deal Producer', path: 'skills/brand-deal-producer.md' }],
  replaces: 'Script versions scattered across email threads and chat, plus 30–60 minutes per deal of formatting · multiplied by every revision round the mess itself creates.',
  req: ['Deal Scripting'],
  ladder: {
    manual: 'Version 3 is in email, version 4 is in WhatsApp, the brand approved version 2.',
    assisted: 'The locked script lands in a clean, brand-safe formatted doc · consistent naming, proper structure · ready for sponsor sign-off.',
    autonomous: 'Final scripts generate their approval doc automatically, filed per brand, shared with minimum-scope access; revisions update one canonical document.',
  },
  notes: 'One canonical doc per deal, edits in the doc, never in chat · the entire job is killing version ambiguity. A consistent naming convention and a clean format do quiet sales work too: sponsors judge professionalism from the artifacts, and tidy paperwork earns the second deal. The trap is over-sharing · scope access to the single file, not your whole drive.',
},

/* ── OPERATIONS (cont.) ──────────────────── */

'Kickoff Pack': {
  files: [{ label: 'Client Onboarding Manager', path: 'skills/client-onboarding-manager.md' }],
  replaces: 'The 3–5 day dead zone between signature and first real work · the window where buyer’s remorse lives. Plus 2–3 hours of assembling the same welcome email, checklist, and folder structure for every new client.',
  req: ['Agreement Drafting'],
  ladder: {
    manual: 'The client signs, then hears nothing until someone finds a spare afternoon.',
    assisted: 'Deal closes → welcome email, access checklist, and project folder drafted from the deal record; the delivery lead reviews and sends same-day.',
    autonomous: 'The signed agreement triggers the full pack automatically · email out, checklist live, scaffold built · before the celebratory Slack message.',
  },
  notes: 'Speed here sets the tone for the whole engagement: a kickoff pack landing within hours of signing tells the client they bought from operators. Template the pack once · welcome email, what-happens-next timeline, access checklist · and personalize from the deal record, not from scratch. The trap is over-stuffing it: one email, one checklist, one clear next step. Anything more gets ignored.',
  human: 'The delivery lead sends the welcome email under their own name and owns the kickoff date it promises. The pack assembles itself; the commitment is human.',
},

'Access Collection': {
  files: [{ label: 'Client Onboarding Manager', path: 'skills/client-onboarding-manager.md' }],
  replaces: 'The 1–2 weeks of “still waiting on that API key” that delays every build start · the single most common cause of week-one slippage, and it bills nobody.',
  req: ['Kickoff Pack'],
  ladder: {
    manual: 'You email asking for credentials, they send half, you notice the gap mid-build.',
    assisted: 'A checklist generated per project from the scoped stack; the agent chases outstanding items on a schedule and verifies each credential actually works on receipt.',
    autonomous: 'Every received key is test-called immediately, gaps re-chased automatically, and the build gets a green light only when the full set verifies.',
  },
  notes: 'Verification is the half everyone skips: a key that arrives is not a key that works · wrong scopes, expired tokens, and sandbox-only credentials surface mid-build if you don’t test on receipt. Derive the checklist from the actual scoped integrations, not a generic template. Trap to avoid: marking items complete when they arrive instead of when they verify.',
  human: 'Credentials are handled by a named human into a proper secrets store · never pasted into chat, never stored in the agent’s context. The agent chases and verifies; it does not hold the keys.',
},

'Project Scaffolding': {
  files: [{ label: 'Client Onboarding Manager', path: 'skills/client-onboarding-manager.md' }],
  replaces: 'The half-day of setup before any real work starts · repo, context files, folder conventions, plan doc · done slightly differently every time, so no two projects are navigable the same way.',
  req: ['Kickoff Pack', HUB],
  ladder: {
    manual: 'Every project starts as an empty folder and someone’s memory of how the last one was structured.',
    assisted: 'One command stands up the repo, client context file, plan doc, and folder conventions from the house template; a human fills in the engagement specifics.',
    autonomous: 'The closed deal triggers the scaffold automatically · pre-populated with everything the sales process already learned about the client.',
  },
  notes: 'The real product here is consistency: when every engagement has the same skeleton, any agent or human can drop into any project and orient in one read. Pull the initial context from the deal record and discovery transcripts · the sales process already captured most of it; re-asking the client is an admission you don’t talk to yourself. Keep the template minimal: scaffolds that demand twenty files get abandoned by file six.',
},

'Integration Builds': {
  files: [{ label: 'Integration Engineer', path: 'skills/integration-engineer.md' }],
  replaces: 'The core billable work of an automation practice · and the part where scope creeps silently. Done by hand, each integration is days of reading API docs, handling auth, and discovering the vendor’s documentation lied.',
  req: ['Access Collection', 'Project Scaffolding'],
  ladder: {
    manual: 'A developer reads the API docs, writes the glue, and finds the undocumented rate limit in production.',
    assisted: 'The agent writes the integration · auth, endpoints, error handling, retries · against verified credentials; a human reviews the code and runs it against real data.',
    autonomous: 'Standard integrations (CRM, calendar, transcripts, payments) assemble from a proven pattern library; humans only touch the genuinely novel ones.',
  },
  notes: 'Build the pattern library deliberately: every integration you ship becomes a reusable template, and by the tenth project most builds are assembly, not invention. Always build against the client’s real data early · sandbox data hides the edge cases that blow up demos. The trap is skipping retry and failure handling because the happy path worked: integrations don’t fail in testing, they fail at 2am on day forty.',
},

'Portal Provisioning': {
  files: [{ label: 'Client Portal Manager', path: 'skills/client-portal-manager.md' }],
  replaces: 'The “can you send me an update?” email and the status deck rebuilt before every check-in call · 2–3 hours/week per active client of pure performance theatre.',
  req: ['Project Scaffolding'],
  ladder: {
    manual: 'Status lives in email threads and whatever the client remembers from the last call.',
    assisted: 'A branded, client-scoped portal spun up from a template per engagement · roadmap, onboarding checklist, deliverables · updated by the team as work ships.',
    autonomous: 'New engagements get a portal automatically, and the delivery system writes to it directly: the client watches progress happen instead of asking about it.',
  },
  notes: 'One template, strictly enforced · the value is that every client portal looks and works identically, so provisioning is minutes, not a design project. Give the client something to do in it (tick onboarding items, answer open questions) and it becomes a working surface instead of a brochure. The trap: a portal that lags reality is worse than no portal · don’t ship this without Portal Sync planned, or it becomes one more thing to manually update.',
},

'QA & Verification': {
  files: [{ label: 'QA Engineer', path: 'skills/qa-engineer.md' }],
  replaces: 'The bug the client finds before you do. Every defect that reaches a client costs more trust than ten caught internally · and rework eats 10–20% of delivery hours at firms that ship on vibes.',
  req: ['Integration Builds'],
  ladder: {
    manual: 'The developer who built it clicks through it once and declares victory.',
    assisted: 'Every build runs against real client data through a verification checklist · edge cases, failure modes, output accuracy · with results logged before anything is demoed.',
    autonomous: 'Verification runs on every change automatically; builds physically cannot reach the client-facing layer without a passing run on record.',
  },
  notes: 'The standard is verify-before-done: a build is not finished when it works, it is finished when it has been shown to work against real data, edge cases included. Write the checklist per build type once and reuse it · extraction builds, integration builds, and portals each fail in characteristic ways. The trap is testing with clean sample data: the client’s real documents are uglier than anything you’d invent, and that ugliness is exactly what you’re being paid to handle.',
  human: 'A human signs off before anything is shown to a client · the agent runs the checks, but the name on the engagement owns the standard. QA sign-off is never delegated to the thing being QA’d.',
},

'Status Updates': {
  files: [{ label: 'Delivery Status Reporter', path: 'skills/delivery-status-reporter.md' }],
  replaces: 'The update email that takes 30 minutes to write per client per week · or doesn’t get written, which is how clients conclude nothing is happening. Silence reads as stalling even when the work is flying.',
  req: ['Context Maintenance'],
  ladder: {
    manual: 'The client asks how it’s going; someone reconstructs the week from memory and Slack.',
    assisted: 'A weekly update drafts itself from the context file and shipped work · what moved, what’s next, what’s blocked · and the delivery lead edits and sends.',
    autonomous: 'Updates publish on schedule to email and the portal, generated from actual delivery activity, with the human only stepping in when there’s bad news to frame.',
  },
  notes: 'Cadence beats content: a short update every week outperforms a brilliant one monthly, because the rhythm itself is the reassurance. Generate from real activity · context files, commits, shipped deliverables · never from a human summarizing their week into a form, or the system dies in a fortnight. The trap: never let the automated update be the channel for bad news. Delays and problems get a human call first, the written update second.',
  human: 'Good news can ship on autopilot; bad news cannot. A human delivers every delay or problem personally before it appears in writing.',
},

'Portal Sync': {
  files: [{ label: 'Client Portal Manager', path: 'skills/client-portal-manager.md' }],
  replaces: 'The gap between work done and work visible. Without it, the portal decays into a brochure within two weeks and you’re back to manually updating two places · the work and the story about the work.',
  req: ['Portal Provisioning', 'Context Maintenance'],
  ladder: {
    manual: 'Someone remembers to update the portal after shipping. They do not remember.',
    assisted: 'End-of-session summaries and finished deliverables drafted into portal updates; a human approves what the client sees.',
    autonomous: 'Every working session writes its summary to the portal automatically · the client’s view and reality never drift apart.',
  },
  notes: 'This is the node that makes Portal Provisioning honest: the portal is only worth what it reflects, and manual updating is the failure mode that kills every client-facing dashboard ever built. Hook the sync to the natural end of work · session close, deliverable shipped, milestone hit · not to a separate update ritual. The trap is syncing raw internals: the client should see progress in their language, not your commit log.',
},

'Transcript Processing': {
  files: [{ label: 'Meeting Intelligence Engineer', path: 'skills/meeting-intelligence-engineer.md' }],
  replaces: 'Meetings that evaporate. Every client call contains decisions, commitments, and context worth money · and in most firms it lives nowhere but two people’s fading memory of a Tuesday.',
  req: ['Call Capture'],
  ladder: {
    manual: 'Someone re-listens to the recording to find that one thing the client said. They never do.',
    assisted: 'Every transcript processed into structure · decisions, action items, key facts, open questions · and filed against the right client.',
    autonomous: 'Transcripts flow from the notetaker into structured, searchable context automatically; every other agent on this map reads from the result.',
  },
  notes: 'Call Capture records the meeting; this node makes it useful. Process into a consistent shape · decisions, commitments, facts learned, open threads · and file per client, because a searchable corpus of every client conversation is the raw material for half the Operations tree. The trap is storing raw transcripts and calling it done: an unstructured transcript is a haystack, and nobody queries haystacks.',
},

'SOP Generation': {
  files: [{ label: 'Playbook Writer', path: 'skills/playbook-writer.md' }],
  replaces: 'The expertise that walks out the door with whoever did the work. Every delivered project contains a repeatable playbook · and without this node, you rebuild it from scratch the next time, at full cost, forever.',
  req: ['Context Maintenance', HUB],
  ladder: {
    manual: 'The process lives in the head of whoever did it last. Documentation is a thing you’ll do when things calm down.',
    assisted: 'After a project ships, the agent drafts the playbook from the actual work · context files, transcripts, what was built · and a human edits it into the canonical version.',
    autonomous: 'Repeated work patterns get flagged and drafted into SOPs automatically; the playbook library grows as a byproduct of delivery.',
  },
  notes: 'Write SOPs from evidence, not memory · the context files and transcripts record what actually happened, including the failure modes a human would forget to mention. The second delivery of any service type is the moment to extract the playbook: once is an event, twice is a pattern. The trap is writing aspirational SOPs describing how work should happen instead of how it demonstrably did · those get ignored by everyone, including their author.',
},

'Handoff Docs': {
  files: [{ label: 'Playbook Writer', path: 'skills/playbook-writer.md' }],
  replaces: 'The post-handoff support tail: every undocumented system generates months of “quick questions” that are really unpaid retainer work. Bad handoffs also quietly cap your referrals · nobody recommends a system they can’t operate.',
  req: ['QA & Verification'],
  ladder: {
    manual: 'The client gets a Loom recorded in one take and a promise to “ping me if anything breaks.”',
    assisted: 'Documentation drafted from the build itself · what it does, how to operate it, what to do when it misbehaves · and the builder reviews for accuracy before delivery.',
    autonomous: 'Docs generate and update alongside the build; by ship day the handoff pack already exists and matches what was actually delivered.',
  },
  notes: 'Write for the person who will actually operate the system · usually a non-technical client-side owner, not a developer. Three layers cover it: what this is, how to use it day-to-day, and what to do when something looks wrong. Generate from the real build, not the proposal · scope drifted, and docs describing the system you planned rather than the one you shipped are worse than nothing. The trap is treating this as the last task: docs written in the final hour before handoff are the ones that generate the support tail.',
},

/* ── INTELLIGENCE (cont.) ──────────────────── */

'Tech-Stack Detection': {
  files: [{ label: 'Company Research Analyst', path: 'skills/company-research-analyst.md' }],
  replaces: 'Pitching an integration to a company that can’t run it · or missing the account whose stack is screaming for what you sell. Manual stack-checking is 15–20 minutes per company across detection tools, job posts, and page source, so it happens for almost none of them.',
  req: ['ICP Definition'],
  ladder: {
    manual: 'View-source on their homepage and a guess.',
    assisted: 'Stack detected per target · tools, platforms, recent migrations · with the gaps mapped against what you sell.',
    autonomous: 'Every account in the target list carries a live stack profile; a stack change that matches your wedge triggers an alert to the pipeline.',
  },
  notes: 'The gap is the product · “they run X without Y” is a campaign angle, not trivia. Cross-check detection tools against job postings and case studies; companies announce their stack every time they hire for it. Feeds Account Enrichment in Sales directly: enrichment is the bulk pass, this is the technical lens on it.',
},

'Network Mapping': {
  files: [{ label: 'Relationship Mapper', path: 'skills/relationship-mapper.md' }],
  replaces: 'Cold outreach to accounts where a warm path already existed. A warm intro converts at multiples of cold · and most founders can’t name their second-degree reach into any given target.',
  req: ['Person Research', HUB],
  ladder: {
    manual: 'Scrolling mutual connections and hoping a name rings a bell.',
    assisted: 'Paths into a target account mapped from your CRM, call history, and public graphs · ranked by strength, with a drafted intro ask per path.',
    autonomous: 'Every new target account arrives with its warm-path map attached; relationship data refreshes as calls and emails accumulate.',
  },
  notes: 'Your own data is the graph · CRM contacts, meeting attendees, email threads · long before any external tool. Build the convention of logging who-knows-whom in the knowledge base and the map compounds. Rank paths by real interaction recency, not connection count: a coffee last month beats a connection from 2019.',
  human: 'The map is AI’s; the ask is yours. Spending relationship capital · who to ask, for what, when · is judgment no agent should exercise, because the cost of a clumsy ask lands on a human relationship.',
},

'Vertical Analysis': {
  files: [{ label: 'Vertical Analyst', path: 'skills/vertical-analyst.md' }],
  replaces: 'Entering a vertical on one good anecdote · then discovering six months in that the budgets were never there. A proper market assessment runs $5–15k from a research firm, so most firms skip it and pay in wasted quarters instead.',
  req: ['Company Deep-Dive', 'Competitor Teardown'],
  ladder: {
    manual: 'One client in the vertical went well, so the vertical must be good.',
    assisted: 'Demand signals, budget reality, buying behavior, and competitive density compiled into a scored go/no-go per vertical.',
    autonomous: 'A watchlist of candidate verticals re-scores on a schedule; a vertical crossing the threshold surfaces with the entry angle attached.',
  },
  notes: 'Score verticals on pain frequency, budget authority, and reachability · not market size. A small vertical that buys fast beats a huge one that deliberates. The output should end in a decision and an entry play, not a landscape summary; if the verdict is go, it feeds ICP Definition in Sales as the next node.',
},

'Pricing Research': {
  files: [{ label: 'Competitive Intelligence Analyst', path: 'skills/competitive-intelligence-analyst.md' }],
  replaces: 'Pricing by mimicry or by nerve. Most firms set prices once, from two competitor pages and a feeling, and leave 20–40% of margin on the table for years.',
  req: ['Competitor Teardown'],
  ladder: {
    manual: 'You checked what one competitor charges and went slightly under.',
    assisted: 'Market rates, anchor points, and packaging patterns compiled per offer · what the market charges, how it bundles, where the ceiling actually sits.',
    autonomous: 'Tracked competitors and market sources re-sweep on a schedule; pricing moves and packaging changes surface before your next proposal goes out.',
  },
  notes: 'Packaging patterns matter more than price points · how the market structures tiers, retainers, and anchors tells you how buyers expect to buy. Mine your own closed-won and closed-lost notes too: what prospects compared you against is pricing data nobody external can sell you. The trap is averaging · price against the segment you want, not the whole market.',
},

'Adversarial Verification': {
  files: [{ label: 'Red Team Reviewer', path: 'skills/red-team-reviewer.md' }],
  replaces: 'The confident wrong number that makes it into the proposal, the deck, or the deal. One bad claim repeated to a client costs more credibility than a hundred verified ones earn.',
  req: ['Research Reports'],
  ladder: {
    manual: 'It sounded right and the source looked legit.',
    assisted: 'Every load-bearing claim gets attacked before it ships · counter-evidence hunted, sources checked for independence, confidence graded per claim.',
    autonomous: 'Verification runs as a gate in the research pipeline: nothing publishes to the knowledge base above a stated confidence without surviving the attack pass.',
  },
  notes: 'Run it as a separate pass with a separate instruction · “find why this is wrong” · never as a self-check by the agent that wrote the claim; the author defending its own work is how errors survive. Grade claims, don’t just flag them: verified, plausible, contested, wrong. The trap is verifying everything · gate only what’s load-bearing, or the pipeline slows to the speed of paranoia.',
  human: 'A human owns what ships under the company’s name. Verification reduces the risk; it never transfers the accountability.',
},

/* ── CUSTOMER (cont.) ──────────────────── */

'Ticket Triage': {
  files: [{ label: 'Support Operations Manager', path: 'skills/support-operations-manager.md' }],
  replaces: 'The first hour of every support shift · a rep reading, labeling, and forwarding before anyone gets helped. Misrouted tickets bounce between owners 2–3 times and add a day per bounce.',
  req: [HUB],
  ladder: {
    manual: 'One shared inbox, oldest unread first, urgency optional.',
    assisted: 'Every request auto-tagged · topic, urgency, sentiment, owner · the moment it lands; a human confirms the routing on the gnarly ones.',
    autonomous: 'Tickets route themselves to the right queue with context attached; priority reorders live as sentiment and SLA clocks change.',
  },
  notes: 'Triage is the front door for the whole Support tree · Escalations and FAQ & Self-Serve both read its tags, so get the categories right before you automate the routing. Start with 5–7 categories from your last 200 tickets, not 30 invented ones. The trap: optimizing routing speed while the labels are wrong · bad tags at high speed just misroute faster.',
},

'Escalations': {
  files: [{ label: 'Support Operations Manager', path: 'skills/support-operations-manager.md' }],
  human: 'An angry customer never gets a bot. The system’s entire job is detection and speed · the conversation that follows is a human’s, with full context in hand.',
  replaces: 'The churn you find out about in a one-star review. By the time a frustrated customer asks for a manager, they’ve usually been simmering across three polite tickets nobody connected.',
  req: ['Ticket Triage'],
  ladder: {
    manual: 'A rep forwards the scary email with “can you look at this?”',
    assisted: 'Sentiment spikes, churn signals, and repeat-contact patterns flag in real time; a human gets pinged with the full thread history and a suggested first move.',
    autonomous: 'Detection runs across every channel; flagged accounts page the right owner within minutes, briefed · and the system tracks whether the save worked.',
  },
  notes: 'Tune for false positives over false negatives · an unnecessary human glance costs two minutes, a missed escalation costs the account. The detection layer should read across tickets, not within them: three mildly annoyed messages in two weeks is a louder signal than one heated one. Wire flagged accounts into Health Scoring so the risk shows up on the account, not just the ticket.',
},

'Onboarding Journeys': {
  files: [{ label: 'Customer Success Manager', path: 'skills/customer-success-manager.md' }],
  replaces: '2–4 CSM hours per new account sending the same welcome sequence by hand · or the silent version, where customers who stall in week one become the churn stat of month three.',
  req: [HUB],
  ladder: {
    manual: 'A welcome email, a PDF, and hope they figure it out.',
    assisted: 'Step-by-step activation sequences drafted per customer segment; nudges trigger on stalled milestones, human sends the rescue note.',
    autonomous: 'Every new customer walks a journey that adapts to their progress · stuck on step two gets help for step two, not a generic check-in. Completion rates tracked per step.',
  },
  notes: 'Define activation first · the one action that predicts retention · and build the journey backwards from it. Instrument every step so you can see exactly where customers stall; that drop-off chart is your product roadmap. The trap: a beautiful 12-email sequence nobody measured. Five steps with completion data beats twelve with vibes.',
},

'Renewals & Expansion': {
  files: [{ label: 'Customer Success Manager', path: 'skills/customer-success-manager.md' }],
  human: 'Renewal and upsell conversations are human, full stop. AI decides when and arms the talker · timing, account history, the expansion angle. The ask itself never automates.',
  replaces: 'Renewals discovered two weeks out and handled in a panic, plus the expansion revenue nobody asked for because nobody noticed the account had outgrown its plan.',
  req: ['Health Scoring'],
  ladder: {
    manual: 'A calendar reminder set at signing, if anyone remembered.',
    assisted: 'Renewals surface 90 days out with health context and a drafted opener; usage patterns flag accounts ready for the expansion conversation.',
    autonomous: 'Every account carries a renewal runway and an expansion readiness signal; the owner gets the play, the timing, and the talking points · and decides whether to run it.',
  },
  notes: 'The 90-day rule is the whole game: a renewal conversation started early is a planning session, started late it’s a negotiation. Expansion signals live in usage data · seats maxed, limits hit, new teams appearing · so wire this to whatever Health Scoring reads. The trap: leading the renewal call with price. Lead with the value ledger · what they got this year · and let the number follow.',
},

'QBR Prep': {
  files: [{ label: 'Customer Success Manager', path: 'skills/customer-success-manager.md' }],
  replaces: '3–5 CSM hours per account per quarter assembling slides from scattered data · which is why most QBRs are either skipped or improvised from memory in the parking lot.',
  req: ['Health Scoring', 'Call Capture'],
  ladder: {
    manual: 'Last quarter’s deck, new dates, same screenshots.',
    assisted: 'Account data, usage trends, support history, and open items compiled into the house QBR template; the CSM edits the narrative and the asks.',
    autonomous: 'Decks generate on the quarterly calendar automatically · wins quantified, risks flagged, next-quarter recommendations drafted · ready for a human polish pass.',
  },
  notes: 'A QBR is a renewal argument delivered early · every slide should answer “why keep paying us.” Quantify outcomes in the customer’s units (hours saved, tickets deflected, revenue touched), not your feature usage. The trap: a data dump with no point of view. The recommendations slide is the deliverable; everything before it is evidence.',
},

'Engagement & Replies': {
  files: [{ label: 'Community Manager', path: 'skills/community-manager.md' }],
  replaces: 'A community manager’s core hours · or the slow death where member questions sit unanswered for two days and the space quietly becomes a noticeboard.',
  req: [HUB],
  ladder: {
    manual: 'The founder replies in bursts at midnight, then goes silent for a week.',
    assisted: 'Every question and mention gets a drafted reply in the house voice within the hour; a human approves and posts.',
    autonomous: 'Routine questions answered directly from the knowledge base; novel or sensitive threads route to a human with a draft attached. Response time tracked like an SLA.',
  },
  notes: 'Response speed is the heartbeat of a community · a question answered in 30 minutes teaches members to ask more, one answered in three days teaches them to stop. The voice file is the prerequisite: an off-tone reply in a community is worse than silence, because members can tell. The trap: letting the agent answer everything · the founder showing up personally on the threads that matter is the product.',
},

'Moderation': {
  files: [{ label: 'Community Manager', path: 'skills/community-manager.md' }],
  human: 'Spam removal automates clean. Conduct calls don’t · warning or removing a real member is a judgment a human makes, with the receipts the system gathered.',
  replaces: 'The founder deleting crypto spam at 7am, and the slower cost: one unchecked bad actor or pile-on thread can empty a community faster than any feature can fill it.',
  req: ['Engagement & Replies'],
  ladder: {
    manual: 'Someone notices the spam after twelve members already have.',
    assisted: 'Spam, self-promo, and conduct flags caught on posting and queued with context; a human approves removals and warnings.',
    autonomous: 'Obvious spam removed silently on sight; borderline conduct cases land in a review queue with the member’s history attached and a recommended action.',
  },
  notes: 'Write the rules before you build the enforcer · moderation without a published code of conduct reads as arbitrary, and arbitrary kills trust faster than spam does. Tier the response: silent removal for bots, private note for first-time line-crossers, human conversation for members. The trap: over-moderating early. A quiet community needs friction removed, not added.',
},

'Member Spotlights': {
  files: [{ label: 'Community Manager', path: 'skills/community-manager.md' }],
  replaces: 'The retention engine nobody runs because it’s nobody’s job: member wins scroll past unnoticed, and the people most likely to renew never get told they matter.',
  req: ['Engagement & Replies'],
  ladder: {
    manual: 'A shout-out when the founder happens to see something good.',
    assisted: 'Wins, milestones, and standout posts surfaced weekly from community activity; spotlight drafts ready in the house voice for a human to personalize and post.',
    autonomous: 'A standing spotlight cadence runs itself · candidates ranked by story strength, drafts queued, posted on schedule with a human glance.',
  },
  notes: 'A spotlighted member renews, posts more, and recruits · it’s the cheapest retention play in the tree. Ask permission before celebrating anyone publicly; a surprise spotlight on a private win burns trust. The trap: spotlighting only the whales. Celebrating a small win from a quiet member moves the whole room; celebrating the same three power users is just a leaderboard.',
},

/* ── BACK OFFICE (cont.) ──────────────────── */

'Payment Tracking': {
  files: [{ label: 'Billing Manager', path: 'skills/billing-manager.md' }],
  replaces: 'The weekly bank-app archaeology session · logging into three accounts across two currencies to reconstruct who’s paid. Plus the invoice you forgot was unpaid until the quarter closed.',
  req: ['Invoice Generation'],
  ladder: {
    manual: 'You check the bank when you have a bad feeling.',
    assisted: 'Every invoice tracked against incoming payments · paid, due, late · in one view, updated daily, currencies normalized.',
    autonomous: 'Payments reconcile against invoices automatically; late ones hand themselves to Collections, and the cash position is always current without anyone asking.',
  },
  notes: 'Pull from the source of truth · bank feeds or the payment processor · not from memory or the invoice tool’s optimistic status field. Normalize multi-currency to one reporting currency at a consistent rate convention, or every downstream number argues with itself. The trap: tracking what you sent instead of what landed. An invoice is a hope; a deposit is a fact.',
},

'Revenue Reporting': {
  files: [{ label: 'Financial Reporting Analyst', path: 'skills/financial-reporting-analyst.md' }],
  replaces: 'Either $200–500/month of bookkeeper time assembling a report that arrives three weeks stale, or the founder rebuilding the same spreadsheet every month and trusting it less each time.',
  req: ['Payment Tracking'],
  ladder: {
    manual: 'A spreadsheet with a tab per month and a formula someone broke in March.',
    assisted: 'Monthly revenue compiled across entities and currencies · by client, by type, recurring vs. one-off · drafted for a human sanity check.',
    autonomous: 'The report generates itself on the first of the month from reconciled payment data; anomalies get flagged, not buried.',
  },
  notes: 'One number per question: what came in, from whom, through which entity, recurring or not. Split recurring from project revenue from day one · it’s the split every future decision (and buyer) cares about. The trap is reporting invoiced revenue as received revenue; build only on reconciled payments or the report is fiction with formatting.',
},

'CRM Sync': {
  files: [{ label: 'Records Administrator', path: 'skills/records-administrator.md' }],
  replaces: 'The gap between what the CRM says and what’s actually true · which quietly invalidates every report, forecast, and reactivation play built on top of it.',
  req: [HUB, 'CRM Hygiene'],
  ladder: {
    manual: 'The CRM gets updated in a guilty batch before someone looks at it.',
    assisted: 'Deals, contacts, and statuses sync across systems · CRM, invoicing, project tracker · with changes drafted from real activity for approval.',
    autonomous: 'Calls, emails, and payments update records as they happen; every system agrees, and nobody types the same client name twice.',
  },
  human: 'Merges and deletions get a human click. A bad sync that creates a duplicate is annoying; one that destroys a record is archaeology.',
  notes: 'Pick one system of record per object · deals live here, money lives there · and make everything else a mirror, never a second author. Sync from activity (transcripts, payments, sent emails), not from human discipline, because human discipline is what failed in the first place. The trap: two-way sync between two systems that both think they’re the boss.',
},

'Expense Categorization': {
  files: [{ label: 'Financial Reporting Analyst', path: 'skills/financial-reporting-analyst.md' }],
  replaces: '$150–400/month of bookkeeper categorization, or the annual shoebox week where the founder relives twelve months of receipts to answer the accountant’s spreadsheet.',
  req: [HUB],
  ladder: {
    manual: 'A folder called “receipts” and a strong belief that future-you will deal with it.',
    assisted: 'Transactions pulled from feeds and auto-categorized to your chart of accounts, with the uncertain tail queued for a 10-minute weekly review.',
    autonomous: 'Spend lands pre-categorized per entity with receipts attached; the accountant gets a clean file, not a quiz.',
  },
  human: 'Tax treatment is judgment, not classification · deductibility calls and anything the accountant would raise an eyebrow at stay human.',
  notes: 'Get the chart of accounts from your accountant first and categorize into it · inventing your own categories just creates a translation job later. Auto-accept the recurring 80% (same vendor, same category, every month) and only surface the new and ambiguous. The trap is multi-entity spend on one card: encode which entity owns which subscription once, or every month leaks misattributed costs.',
},

'Entity Compliance': {
  files: [{ label: 'Records Administrator', path: 'skills/records-administrator.md' }],
  replaces: 'Missed filings, and what they cost: late penalties, a suspended entity, or a frozen bank account discovered the week you need it. Multi-entity founders carry a deadline list nobody actually maintains.',
  req: [HUB],
  ladder: {
    manual: 'The accountant emails you something urgent and you learn a deadline existed.',
    assisted: 'Every entity’s obligations · filings, renewals, tax dates, license deadlines · tracked in one calendar with lead-time alerts and prepared checklists.',
    autonomous: 'The system watches the obligations, drafts the routine paperwork, and escalates with everything assembled; humans sign and submit.',
  },
  human: 'Filings get signed by a human, full stop. AI tracks, prepares, and nags · it never submits anything with legal weight on its own.',
  notes: 'Build the obligation register per entity first · jurisdiction, filing, frequency, deadline, who files it · straight from your accountant and registered agent, not from memory. Alerts at 30, 14, and 3 days, with the longest lead on anything requiring a third party. The trap: tracking only tax. Trade licenses, registered agents, visa renewals, and substance requirements kill entities just as dead.',
},

'Calendar Management': {
  files: [{ label: 'Executive Assistant', path: 'skills/executive-assistant.md' }],
  replaces: 'A part-time EA’s core duty ($15–25k/year), or the founder doing timezone math at midnight and the double-booking that torches a first impression.',
  req: [],
  ladder: {
    manual: 'You are the scheduling link, and the link is tired.',
    assisted: 'Conflicts caught, buffers enforced, timezones handled; reschedule requests come back with sane options instead of a shrug.',
    autonomous: 'The calendar defends itself · focus blocks protected, travel and prep time auto-added, low-priority requests deflected to the right slot without a human in the loop.',
  },
  notes: 'Write the rules before the automation: meeting hours, buffer lengths, which meeting types deserve which slots, what’s sacred. The agent enforces policy · if there’s no policy, it just automates chaos faster. The trap is optimizing for openness: a calendar that accepts everything efficiently is a calendar that destroys deep work efficiently.',
},

'Email Triage': {
  files: [{ label: 'Inbox Manager', path: 'skills/inbox-manager.md' }],
  replaces: 'The 1–2 hours a day a founder spends in the inbox, of which maybe fifteen minutes is decisions and the rest is sorting other people’s priorities.',
  req: [HUB],
  ladder: {
    manual: 'Inbox open all day, attention rented out one notification at a time.',
    assisted: 'Every email sorted on arrival · needs-you / FYI / automated noise · with drafted replies queued on the routine ones.',
    autonomous: 'The inbox becomes a briefing: the handful that genuinely need a human, surfaced with context and a draft; the rest filed, answered, or archived by standing rules.',
  },
  human: 'Triage is autonomous; sending is not. Replies go out after a human approves · and the agent never deletes, only archives, so a misjudged email is a search away, not gone.',
  notes: 'The classifier needs your context to know what matters · a client name, an open deal, an overdue invoice all change an email’s priority, which is why this reads from the knowledge base. Start with triage-only for two weeks and audit the calls before letting it draft. The trap is over-filtering: one important email in spam-purgatory costs more trust than a hundred correctly filed newsletters earn.',
},

'Candidate Sourcing': {
  files: [{ label: 'Talent Coordinator', path: 'skills/talent-coordinator.md' }],
  replaces: 'A recruiter’s 20–25% placement fee, or 10+ founder-hours per role scrolling profiles · which is why most small companies hire from whoever happened to apply.',
  req: [HUB],
  ladder: {
    manual: 'Post the job, pray, hire the least-bad applicant in week six.',
    assisted: 'A real role scorecard drives searches across platforms; candidates come back ranked against it with reasons, not vibes.',
    autonomous: 'Open roles run standing searches; new matches land scored and deduped, outreach drafted, pipeline always warm before the seat is empty.',
  },
  notes: 'The scorecard is the whole build: outcomes the role must deliver, must-have evidence, disqualifiers · written before the first search, stored where agents read it. Rank on demonstrated work over keyword density; titles lie, portfolios don’t. The trap is sourcing for the résumé you’d recognize instead of the outcome you need · the scorecard exists to stop that.',
},

'Screening & Scheduling': {
  files: [{ label: 'Talent Coordinator', path: 'skills/talent-coordinator.md' }],
  replaces: 'The 30 minutes per applicant a first-pass screen actually takes, multiplied by the 80% who were never going to make it · plus the scheduling ping-pong that loses good candidates to faster companies.',
  req: ['Candidate Sourcing', 'Calendar Management'],
  ladder: {
    manual: 'You skim forty CVs on a Sunday and interview whoever annoyed you least.',
    assisted: 'Every applicant screened against the scorecard · structured questions asked and scored · with a shortlist and reasoning for human review; interviews book themselves.',
    autonomous: 'Screens run on arrival, the calendar fills with only above-bar candidates, and everyone else gets a prompt, decent no · drafted by the system, signed off by a human.',
  },
  human: 'AI filters; humans reject and advance. Every no on a real candidate is a human call · a person’s livelihood deserves more than a threshold, and so does your reputation in a small market.',
  notes: 'Structured beats freeform: same questions, same rubric, every candidate · it’s fairer and it makes the AI scoring actually comparable. Speed is a weapon here; the best candidates are gone in days, and same-day screening plus instant booking wins talent that slower companies never even meet. The trap: optimizing for interview polish. Score evidence of doing the job, not fluency in describing it.',
},

'Onboarding & Training': {
  files: [{ label: 'Talent Coordinator', path: 'skills/talent-coordinator.md' }],
  replaces: 'The new hire’s lost first month · asking around for access, absorbing context by osmosis · and the senior person’s week spent re-explaining what should have been written down.',
  req: ['Screening & Scheduling', 'SOP Generation'],
  ladder: {
    manual: 'Day one is a laptop, a Slack invite, and “shadow Sarah for a bit.”',
    assisted: 'Offer accepted → access checklist, playbooks, tool walkthroughs, and a 30-day plan generated from the role scorecard; a human assigns the mentor and the first real task.',
    autonomous: 'The whole arc runs itself · accounts provisioned, training sequenced, check-ins scheduled, progress tracked · and the manager gets a flag only when someone’s off pace.',
  },
  notes: 'This node is only as good as the knowledge base behind it · onboarding is really just the company’s documented self, sequenced into 30 days. Write the plan as outcomes per week (what they can do unsupervised) rather than content consumed. The trap is information-dump onboarding: forty documents in week one teaches nothing; one real task with the relevant playbook attached teaches everything.',
},

/* ── SALES · 137 additions ───────────────────────────── */

'Lookalike Modeling': {
  files: [{ label: 'Lead Scoring Analyst', path: 'skills/lead-scoring-analyst.md' }],
  replaces: 'The expansion list nobody builds methodically · most teams guess at "who else looks like our best clients" instead of extracting the actual pattern.',
  req: ['ICP Definition', 'Win/Loss Analysis'],
  ladder: {
    manual: 'Someone eyeballs the closed-won list and says "let’s target more companies like these."',
    assisted: 'The agent extracts the real shared firmographics + triggers from closed-won, builds a lookalike query, and hands back a ranked new list.',
    autonomous: 'Every close feeds the model · the lookalike list refreshes itself and flows straight into sourcing.',
  },
  notes: 'This is ICP Definition pointed backwards · instead of who you think you want, it reads who actually bought and finds more of them. The quality depends entirely on having clean closed-won data, so it sits downstream of Win/Loss Analysis.',
},

'Cold-Call Scripting': {
  files: [{ label: 'Outbound Scriptwriter', path: 'skills/outbound-scriptwriter.md' }],
  replaces: 'The reps who freeze on the call because nobody wrote the branches · or the "script" that’s one paragraph and dies at the first objection.',
  req: ['ICP Definition'],
  ladder: {
    manual: 'A rep improvises, or reads a stiff script that the prospect can hear is a script.',
    assisted: 'The agent writes the opener, the pattern interrupt, the value line, and a full objection-branch tree with example phrasing for each.',
    autonomous: 'Scripts regenerate per segment as objection data comes back from real calls.',
  },
  human: 'A human delivers it · this drafts the words, the rep makes them sound like a person. The objection branches are the value, not the opener.',
  notes: 'The skill below writes call + voicemail scripts that read human, with branches for "not interested", "send me an email", "we already have someone", "no budget". Feed it the offer and one real objection and it tightens fast.',
},

'Video Prospecting': {
  files: [{ label: 'Outbound Scriptwriter', path: 'skills/outbound-scriptwriter.md' }],
  replaces: '10+ minutes per personalized video done right · which is why reps record three then quit.',
  req: ['Personalization Research'],
  ladder: {
    manual: 'A rep stares at a Loom recording light with no script and rambles for two minutes.',
    assisted: 'The agent writes a sub-90-second script · on-screen hook, a first line about the prospect’s actual world, one value beat, one CTA.',
    autonomous: 'Every lead in a sequence carries a personalized video script generated from its dossier.',
  },
  notes: 'Video works because almost nobody does it well, and it dies because almost nobody scripts it. The skill below scripts the hook + personal line + value + CTA from the prospect dossier · the human just hits record.',
},

/* ── DEALS · 137 additions ───────────────────────────── */

'Referral Capture': {
  files: [{ label: 'Inbound Response Manager', path: 'skills/inbound-response-manager.md' }],
  replaces: 'The warm intros that evaporate · a prospect says "talk to my colleague in ops" and the reply sits unactioned for a week until the moment’s gone.',
  req: ['Reply Classification'],
  ladder: {
    manual: 'A rep reads the reply, means to follow up on the referral, forgets.',
    assisted: 'The agent flags every "talk to / loop in / not me but" reply, drafts the warm-intro ask, and routes the new contact into the pipeline.',
    autonomous: 'Referral replies are detected, the intro is drafted, and the new lead is created and assigned without a human touching the inbox.',
  },
  notes: 'Referrals close roughly twice as fast as cold · and they’re the leakiest part of most pipelines because they arrive as a throwaway line in a reply. This catches them the moment they land.',
},

'Objection Library': {
  files: [{ label: 'Deal Debrief Analyst', path: 'skills/deal-debrief-analyst.md' }],
  replaces: 'The objection-handling knowledge that lives only in the head of your best closer · and walks out the door when they do.',
  req: ['Call Capture'],
  ladder: {
    manual: 'Every rep relearns the same objections from scratch, badly.',
    assisted: 'The agent mines every recorded call for objections, clusters them, and drafts the rebuttal that actually moved deals forward.',
    autonomous: 'The library updates itself as new calls land · new objections surface, weak rebuttals get flagged and rewritten.',
  },
  notes: 'This turns your call recordings into a compounding asset. It reads what objections actually came up and which responses preceded a won deal · so the rebuttals are evidence-based, not invented. Feeds straight into Cold-Call Scripting and Objection Response.',
},

/* ── MARKETING · 137 additions ───────────────────────── */

'Thumbnail & Cover Design': {
  files: [{ label: 'Brand Visual Designer', path: 'skills/brand-visual-designer.md' }],
  replaces: 'The click you lose before anyone reads a word · most content dies on a weak thumbnail, not weak content.',
  req: ['Image Generation'],
  ladder: {
    manual: 'You slap a frame from the video on it and hope.',
    assisted: 'The agent generates thumbnail and cover variants tuned to the hook, in brand, ready to A/B.',
    autonomous: 'Covers generate per post from the hook, with the winning patterns fed back from performance data.',
  },
  notes: 'The thumbnail is the ad for the content. The skill below produces scroll-stopping, on-brand covers and tests variants · pair it with Performance Mining so the winners teach the next batch.',
},

'Ad Creative': {
  files: [{ label: 'Creative Strategist', path: 'skills/creative-strategist.md' }],
  replaces: 'The creative bottleneck on every paid account · one ad, no variations, fatiguing while you sleep.',
  req: ['Performance Mining'],
  ladder: {
    manual: 'A designer makes one ad a week; nothing gets tested.',
    assisted: 'The agent generates hook, angle, and format variations off your winners · ready to launch as a test batch.',
    autonomous: 'Fresh creative is generated and queued continuously, rotating before fatigue sets in, learning from spend.',
  },
  notes: 'Paid acquisition is won on creative volume, not bid tweaks. The skill below spins winning ads into new angles and formats · the same engine behind the Meta Ads dashboard’s creative-fatigue flags.',
},

'Landing Page Copy': {
  files: [{ label: 'Conversion Copywriter', path: 'skills/conversion-copywriter.md' }],
  replaces: 'A $2–5k copywriter per page, or worse · the founder writing feature lists nobody converts on.',
  req: [HUB],
  ladder: {
    manual: 'You write the page yourself, lead with features, and wonder why it doesn’t convert.',
    assisted: 'The agent writes the full page in the proven order · hero promise, problem, mechanism, proof, offer, FAQ, CTA · in your voice.',
    autonomous: 'Pages generate per offer and per campaign, with variants written for testing.',
  },
  notes: 'Conversion copy is a structure, not a talent · hook, problem in their words, mechanism, proof, offer with risk reversal, objection FAQ, one CTA. The skill below writes the whole page section by section from your offer and ICP.',
},

/* ── OPERATIONS · 137 additions ──────────────────────── */

'Data Migration': {
  files: [{ label: 'Integration Engineer', path: 'skills/integration-engineer.md' }],
  replaces: 'The migration project that quotes at $5–20k and still loses rows · or the intern hand-copying records between two CRMs for a fortnight.',
  req: ['Integration Builds'],
  ladder: {
    manual: 'Someone exports a CSV, maps columns by hand, re-imports, and prays nothing broke.',
    assisted: 'The agent maps the fields, transforms, dedupes, validates row counts both sides, and reports exactly what moved and what didn’t.',
    autonomous: 'Ongoing syncs run on a schedule with reconciliation checks · drift gets flagged before it compounds.',
  },
  notes: 'Migrations fail silently · a thousand rows in, nine hundred out, and nobody notices until a client does. The skill below maps, transforms, and reconciles with row-count validation so "did we lose anything" is answerable, not hoped.',
},

'Agent Evaluation': {
  files: [{ label: 'QA Engineer', path: 'skills/qa-engineer.md' }],
  replaces: 'The blind trust that an agent still works after you changed its prompt · until a client catches the regression for you.',
  req: ['QA & Verification'],
  ladder: {
    manual: 'You eyeball a couple of outputs after a change and call it tested.',
    assisted: 'The agent runs new outputs against a benchmark set and a rubric, scores them, and flags regressions before they ship.',
    autonomous: 'Every prompt or model change triggers an eval run · nothing reaches production without passing the bar.',
  },
  notes: 'The moment you have agents doing real work, "is it still good after my change" becomes the question. This builds the eval harness · a benchmark set, a scoring rubric, and a regression gate · so quality is measured, not assumed.',
},

'Monitoring & Alerting': {
  files: [{ label: 'Reliability Engineer', path: 'skills/reliability-engineer.md' }],
  replaces: 'Finding out an automation died three days ago because a client asked where their report is.',
  req: ['Integration Builds'],
  ladder: {
    manual: 'You notice something broke when the output stops showing up.',
    assisted: 'The agent watches every automation for failed runs and silent stalls, and alerts the moment one goes down.',
    autonomous: 'Health is monitored continuously across the stack · failures alert with context and a first-pass diagnosis attached.',
  },
  notes: 'Silent failure is the tax on running anything in production. The skill below watches your crons, jobs, and agents and tells you before the client does · the first job of the Reliability function.',
},

'Cost & Usage Tracking': {
  files: [{ label: 'Reliability Engineer', path: 'skills/reliability-engineer.md' }],
  replaces: 'The surprise five-figure API bill · token spend nobody was watching until accounting flagged it.',
  req: ['Monitoring & Alerting'],
  ladder: {
    manual: 'You check the provider dashboard when the invoice scares you.',
    assisted: 'The agent tracks token and API spend against a monthly budget and flags the burn rate before you blow past it.',
    autonomous: 'Spend is tracked per automation, attributed to the work, and capped · runaway usage triggers an alert and a throttle.',
  },
  notes: 'Agents that loop, retry, or run on stale data burn money quietly. This tracks spend against a budget by source so a runaway job is a Tuesday-morning alert, not an end-of-month gut-punch.',
},

'Incident Response': {
  files: [{ label: 'Reliability Engineer', path: 'skills/reliability-engineer.md' }],
  replaces: 'The frantic hour of "what broke and why" every time an automation falls over · usually during a client deliverable.',
  req: ['Monitoring & Alerting'],
  ladder: {
    manual: 'Everything stops while someone digs through logs trying to reproduce the failure.',
    assisted: 'The agent triages the alert, reproduces the failure, finds the likely root cause, proposes the fix, and drafts the incident note.',
    autonomous: 'Known failure modes self-heal · the rest escalate with a full diagnosis and a postmortem already written.',
  },
  notes: 'Reliability is a loop, not a heroic scramble · detect, triage, root-cause, fix, write it down so it can’t happen twice. The skill below runs that runbook so an outage costs minutes, not a morning.',
},

/* ── INTELLIGENCE · 137 additions ────────────────────── */

'Funding & Financials Lookup': {
  files: [{ label: 'Company Research Analyst', path: 'skills/company-research-analyst.md' }],
  replaces: 'The 30-minute dig through Crunchbase, news, and filings to answer "do they actually have budget" · done for every account, by hand.',
  req: [HUB],
  ladder: {
    manual: 'Someone Googles "[company] funding" and guesses at revenue.',
    assisted: 'The agent pulls rounds, investors, revenue estimates, and recent filings into one clean read on a target’s buying power.',
    autonomous: 'Every account in the pipeline carries a current financial read · refreshed when something changes.',
  },
  notes: 'The single best signal of "can they buy" is "did they just get money." This pulls funding, investors, and financial estimates so outreach lands where the budget actually is. Pairs with Account Monitoring to catch the raise the day it happens.',
},

'Buying-Committee Mapping': {
  files: [{ label: 'Relationship Mapper', path: 'skills/relationship-mapper.md' }],
  replaces: 'The deals that stall because you were selling to the wrong person · no map of who actually signs.',
  req: ['Company Deep-Dive'],
  ladder: {
    manual: 'You talk to one contact and hope they’re the decision-maker.',
    assisted: 'The agent maps the committee · economic buyer, champion, blockers, influencers · with each person’s role and likely concern.',
    autonomous: 'The map builds from the org and updates as new contacts enter the deal.',
  },
  human: 'A human runs the deal · this draws the board so they know who to win and in what order. Enterprise deals are lost to unmapped committees more than to bad pitches.',
  notes: 'Most B2B deals have 5–7 people involved and one of them quietly kills it. The skill below identifies the committee, their roles, and the concern each one needs answered.',
},

'Warm-Path Finding': {
  files: [{ label: 'Relationship Mapper', path: 'skills/relationship-mapper.md' }],
  replaces: 'The cold open you didn’t need to send · a warm intro path existed and nobody looked for it.',
  req: ['Network Mapping'],
  ladder: {
    manual: 'You cold-email an account you actually have two mutual connections into.',
    assisted: 'The agent finds the shortest real path into a target · who in your network can make the intro · and drafts the ask.',
    autonomous: 'Every target account is checked for a warm path before any cold outreach is attempted.',
  },
  notes: 'A warm intro converts many times better than a cold one and most teams never check whether they have one. This finds the path and writes the intro ask · the difference between "who are you" and "happy to chat, [mutual] speaks highly".',
},

'TAM / Market Sizing': {
  files: [{ label: 'Market Mapper', path: 'skills/market-mapper.md' }],
  replaces: 'The board-deck number pulled from thin air · or a $15k analyst engagement to size a market.',
  req: ['Vertical Analysis'],
  ladder: {
    manual: 'Someone multiplies two guesses and calls it the TAM.',
    assisted: 'The agent counts the companies that actually fit the ICP in a market, by segment, with the assumptions shown.',
    autonomous: 'Market size recalculates as the ICP sharpens and new segments are tested.',
  },
  notes: 'A real TAM is a count of qualifying companies, not a percentage of a McKinsey headline. The skill below sizes the prize bottom-up · how many real targets exist · so you know whether a vertical is worth the campaign before you build it.',
},

'Account Monitoring': {
  files: [{ label: 'Signal Monitoring Analyst', path: 'skills/signal-monitoring-analyst.md' }],
  replaces: 'Finding out a target raised, hired a VP, or switched tools weeks late · from their newsletter, not your radar.',
  req: ['Company Deep-Dive'],
  ladder: {
    manual: 'You re-research an account from scratch every time you remember it exists.',
    assisted: 'The agent watches a target list for funding, hiring, leadership, and tech changes and surfaces what moved.',
    autonomous: 'The watchlist runs continuously · every meaningful change on a target account lands as a scored signal.',
  },
  notes: 'Timing beats personalization. The skill below watches your target accounts so the trigger event · the raise, the new hire, the migration · reaches you the morning it happens, while the window is open. The first job of the Monitoring function.',
},

'News & Mention Tracking': {
  files: [{ label: 'Signal Monitoring Analyst', path: 'skills/signal-monitoring-analyst.md' }],
  replaces: 'A $200/mo media-monitoring tool, plus the gap it leaves on competitor and topic coverage.',
  req: [HUB],
  ladder: {
    manual: 'You find out you were mentioned when someone screenshots it to you.',
    assisted: 'The agent tracks every mention of your brand, competitors, and key topics across news and social as it lands.',
    autonomous: 'Mentions are tracked, classified by sentiment and importance, and the ones that matter get routed.',
  },
  notes: 'You can’t respond to what you can’t see · a bad review, a competitor’s launch, a journalist’s question all have short fuses. This watches the conversation so you’re early, not surprised.',
},

'Alert Routing': {
  files: [{ label: 'Signal Monitoring Analyst', path: 'skills/signal-monitoring-analyst.md' }],
  replaces: 'The monitoring that becomes noise · 200 alerts a day, all ignored within a week.',
  req: ['Account Monitoring'],
  ladder: {
    manual: 'Every signal pings the same channel and everyone tunes it out.',
    assisted: 'The agent scores each signal for relevance and urgency and routes only what matters to the right person or channel.',
    autonomous: 'Signals self-triage · high-value ones reach the right human with context, the rest log silently.',
  },
  notes: 'Monitoring without routing is just a louder inbox. The skill below scores and routes · the Series B of a core account goes to the founder with the intro path attached; the rest stays out of the way. This is what makes monitoring usable instead of exhausting.',
},

'Data Visualization': {
  files: [{ label: 'Business Data Analyst', path: 'skills/business-data-analyst.md' }],
  replaces: 'The research that lands as a wall of text nobody reads · or the analyst who spends an afternoon making one chart.',
  req: ['Research Reports'],
  ladder: {
    manual: 'Findings get pasted into a doc as paragraphs and bullet points.',
    assisted: 'The agent turns the research into charts and diagrams that carry the point at a glance.',
    autonomous: 'Every report ships with the right visual auto-generated from its data.',
  },
  notes: 'A finding that needs three paragraphs to land is a finding that won’t. The skill below renders research into the chart or diagram that makes it obvious · the visual layer on top of Research Reports.',
},

/* ── CUSTOMER · 137 additions ────────────────────────── */

'Macro Authoring': {
  files: [{ label: 'Support Operations Manager', path: 'skills/support-operations-manager.md' }],
  replaces: 'Every agent re-typing the same answer from scratch · and answering it slightly differently each time.',
  req: ['Ticket Triage'],
  ladder: {
    manual: 'Support reps wing the same fifty answers a hundred different ways.',
    assisted: 'The agent reads the recurring tickets and drafts canned, on-brand macros for the team to reuse.',
    autonomous: 'Macros generate and update themselves as new repeat questions emerge · the library stays current without a sweep.',
  },
  notes: 'The fastest way to cut response time is to stop writing the same answer twice. This mines the ticket history for what repeats and writes the reusable, on-voice response · feeding the same source that powers FAQ & Self-Serve.',
},

'Churn Prediction': {
  files: [{ label: 'Customer Success Manager', path: 'skills/customer-success-manager.md' }],
  replaces: 'The renewal that surprises you by not happening · the exit interview that should’ve been a save three weeks earlier.',
  req: ['Health Scoring'],
  ladder: {
    manual: 'You find out an account churned when the cancellation comes through.',
    assisted: 'The agent models which accounts are likely to slip · weighting usage trend, sentiment, and engagement · before the obvious dip.',
    autonomous: 'At-risk accounts are flagged early with the reason and a recommended play, continuously.',
  },
  notes: 'Health Scoring tells you the current state; this predicts the trajectory. It catches the leading indicators · the champion who went quiet, the login cadence softening · while a conversation can still turn it around.',
},

'Advocacy & Referrals': {
  files: [{ label: 'Customer Success Manager', path: 'skills/customer-success-manager.md' }],
  replaces: 'The case studies and referrals you never ask for · happy clients who would gladly help if anyone caught the moment.',
  req: ['Health Scoring'],
  ladder: {
    manual: 'You mean to ask your best client for a referral; you never do.',
    assisted: 'The agent spots accounts at peak happiness and drafts the ask · referral, review, or case study · at the right moment.',
    autonomous: 'Advocacy triggers off health peaks · the right ask goes out when satisfaction is highest, tracked through to the asset.',
  },
  notes: 'Your happiest customers are your cheapest growth channel and the one nobody works systematically. This watches for the high-water mark · a win, a glowing reply, a renewal · and makes the ask while the feeling’s fresh.',
},

'Event Coordination': {
  files: [{ label: 'Community Manager', path: 'skills/community-manager.md' }],
  replaces: 'The community that goes quiet because the AMAs and calls stopped happening · running events is a part-time job nobody owns.',
  req: ['Engagement & Replies'],
  ladder: {
    manual: 'Events happen sporadically when someone remembers to organise one.',
    assisted: 'The agent schedules the cadence, drafts the promo, sends reminders, and preps the run-of-show for each session.',
    autonomous: 'The event calendar runs on rails · scheduled, promoted, reminded, and recapped, with the human just showing up to host.',
  },
  notes: 'A community lives on rhythm · members stay for the next thing on the calendar. This runs the AMAs, calls, and spotlights on a dependable cadence so the room always has a reason to come back.',
},

/* ── BACK OFFICE · 137 additions ─────────────────────── */

'Cash-Flow Forecasting': {
  files: [{ label: 'Finance Operations Analyst', path: 'skills/finance-operations-analyst.md' }],
  replaces: 'The fractional CFO’s headline deliverable · or, more often, no forecast at all and a founder guessing at runway.',
  req: ['Revenue Reporting'],
  ladder: {
    manual: 'Cash gets checked by looking at the bank balance and feeling either fine or scared.',
    assisted: 'The agent projects inflows and outflows, computes runway, and builds a 3/6/12-month forward view with the assumptions shown.',
    autonomous: 'The forecast updates as money moves · runway and scenario models refresh themselves and flag when a threshold is crossed.',
  },
  human: 'A human owns the assumptions and the calls that follow · this does the math, fast and honestly, and shows its work. The decisions stay human.',
  notes: 'Revenue Reporting tells you what happened; this tells you what’s coming. The skill below projects cash in and out, calculates runway, and runs scenarios ("hire two", "lose the biggest client", "double ad spend") so "can we afford this" has an answer before it’s urgent.',
},

'Budget Tracking': {
  files: [{ label: 'Finance Operations Analyst', path: 'skills/finance-operations-analyst.md' }],
  replaces: 'The budget set once in January and never looked at again · overruns discovered at tax time.',
  req: ['Expense Categorization'],
  ladder: {
    manual: 'Spend is reconciled against budget quarterly, if ever.',
    assisted: 'The agent tracks actual spend against budget by category and flags overruns as they emerge.',
    autonomous: 'Budget variance is monitored continuously · a category trending over gets flagged mid-month, not after.',
  },
  notes: 'A budget you don’t check is a wish. This watches spend against plan by category so the overrun is a flag you act on, not a number you explain after the fact. Pairs with Cash-Flow Forecasting as the Finance Ops function.',
},

'Document Filing & Retrieval': {
  files: [{ label: 'Records Administrator', path: 'skills/records-administrator.md' }],
  replaces: 'The Friday afternoon spent hunting for "the signed SOW from March" · multiplied across everyone, every week.',
  req: [HUB],
  ladder: {
    manual: 'Files live in seven places with names like "final_v3_FINAL".',
    assisted: 'The agent names, files, and indexes every document so any of them is findable in seconds.',
    autonomous: 'Documents are filed and tagged on arrival, with retention rules applied · nothing is ever lost or kept too long.',
  },
  notes: '"Where’s that document" is a tax every business pays daily. The skill below enforces naming, filing, and an index so retrieval is ten seconds, not a search party · and applies retention so old records don’t pile up.',
},

'Contract Lifecycle': {
  files: [{ label: 'Contracts Coordinator', path: 'skills/contracts-coordinator.md' }],
  replaces: 'The auto-renewal you forgot to cancel · the client contract that lapsed because nobody tracked the date.',
  req: ['Document Filing & Retrieval'],
  ladder: {
    manual: 'Renewal and expiry dates live in someone’s memory and a forgotten calendar invite.',
    assisted: 'The agent tracks every contract’s renewal, expiry, and obligations and surfaces them well before the deadline.',
    autonomous: 'The lifecycle runs itself · renewals flagged in time to act, obligations tracked, nothing sneaks up.',
  },
  notes: 'Contracts have dates that cost money when missed · a lapsed client agreement, a vendor auto-renewing at a worse rate. This tracks every obligation and deadline so the calendar works for you instead of against you.',
},

'HR & Policy Assistant': {
  files: [{ label: 'People Operations Assistant', path: 'skills/people-operations-assistant.md' }],
  replaces: 'The first HR hire a small team can’t justify yet · and the founder fielding "how much leave do I have" between sales calls.',
  req: [HUB],
  ladder: {
    manual: 'Policy questions interrupt whoever’s nearest, answered from memory and inconsistently.',
    assisted: 'The agent answers staff questions from the real handbook · leave, expenses, process · with a citation, and handles onboarding admin.',
    autonomous: 'Routine people-ops runs itself · policy answered from source, new-hire admin sequenced, the handbook kept current.',
  },
  human: 'Anything legal, sensitive, or about comp/termination escalates to a human immediately · this answers the routine 80% from documented policy and never invents one.',
  notes: 'The skill below is grounded strictly in the company’s own policy docs · it never guesses a policy, it cites the source, and it escalates the hard stuff. It removes the founder as the help desk for "what’s our policy on…".',
},

};

/* ── NODE ZERO · the hub itself ──────────────────────── */
const HUB_ENTRY = {
  desc: 'The single place every agent reads from and writes to. Not software you buy · plain files with a strict convention: who the company is, what it sells, how it speaks, what is true right now. An agent with this context writes like a colleague. An agent without it writes like a stranger.',
  components: ['company.md', 'offer.md', 'voice.md', 'clients/*', 'meetings/*', 'playbooks/*', 'STATE.md'],
  replaces: 'Re-briefing every tool, agency, hire, and AI session from scratch, forever. The context tax is invisible because everyone pays it · until one company stops paying it and starts compounding instead.',
  ladder: {
    manual: 'Context lives in the founder’s head and a thousand chat threads. Every new session starts at zero.',
    assisted: 'Core files exist · company, offer, voice, per-client state · and humans update them after meaningful work.',
    autonomous: 'Every transcript, email, and deliverable writes itself back. Any agent or human reads one page and is current. The brain maintains the brain.',
  },
  notes: 'Build this before anything else on the map · every department’s first node assumes it exists. It is one session of work: scaffold the files, get interviewed, install the read-before-write rules. The test that it works: a smart stranger could read the folder and act for you tomorrow. The skill below does the entire setup.',
  human: 'Everyone writes to it, one human owns it · usually the founder, eventually an ops lead. Ownership of the brain is the last job that never automates.',
  files: [
    { label: 'Node Zero · knowledge base builder', path: 'skills/knowledge-base.md' },
    { label: 'SkillTree Audit · your tree, computed', path: 'skills/skilltree-audit.md' },
  ],
};


/* Human-in-the-loop defaults by capability level · every job gets one;
   deep entries can override with a specific `human:` line. */
const HUMAN_DEFAULT = {
  autonomous: 'AI owns the work. A human audits outputs on a cadence and owns the strategy it executes · directing, not doing.',
  assisted: 'AI does the heavy lifting; a named human approves before anything ships. The review is the job now.',
  manual: 'A human owns this today; AI assists on demand. Mapped so you can see it coming · automate when the tooling matures.',
};

/* Jobs flagged as the recommended first build in each department. */
const FOUNDATION = new Set([
  'ICP Definition',        // Sales · everything downstream reads it
  'Call Capture',          // Deals · cheapest, highest leverage
  'Performance Mining',    // Marketing · your corpus is the strategy
  'Context Maintenance',   // Operations · the knowledge-base habit
  'Company Deep-Dive',     // Intelligence · research on demand
  'FAQ & Self-Serve',      // Customer · deflect the repeats
  'Invoice Generation',    // Back Office · money in, error-free
]);

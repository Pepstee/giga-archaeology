# SkillTree complete preview corpus

## Company Knowledge Base

Build this before anything else on the map · every department’s first node assumes it exists. It is one session of work: scaffold the files, get interviewed, install the read-before-write rules. The test that it works: a smart stranger could read the folder and act for you tomorrow. The skill below does the entire setup.

## Department: Sales

The top of the funnel · finding the right companies, learning enough about them to be worth a reply, and reaching out at scale without sounding like a robot. This is the department most businesses try to hire their way out of. It is the one agents change first, because every job here is research, writing, and timing · and machines never get tired of any of it.

### Function: Targeting

#### Job: ICP Definition

Define and refine ideal customer profiles per vertical · firmographics, pain patterns, buying triggers.

- Level: autonomous
- Capabilities: icp-profiler, vertical-scorer, pain-pattern-library
- Tools: None listed

**Human**

The founder owns this forever. AI drafts and refreshes; the human decides who the business is for. Never fully delegated.

**Replaces**

The founder’s gut feel, applied inconsistently by everyone downstream. Bad ICP wastes every dollar spent after it.

**Notes**

Start here. This is the first node of the Sales tree for a reason · every job downstream (sourcing, scoring, writing) reads from it. Write one page per vertical: firmographics, the pain in the buyer’s words, the trigger that makes them buy now. Store it where your agents can read it, not in a deck.

**Prerequisites:** Company Knowledge Base

**Automation ladder**

- manual: A slide from 2 years ago that nobody opens.
- assisted: AI drafts ICP profiles per vertical from your closed-won data; a human edits quarterly.
- autonomous: Profiles update themselves as deals close and lose · win patterns feed back in without a meeting.

**Linked skill files**

- ICP Strategist: `skills/icp-strategist.md`

#### Job: Market Mapping

Map the total addressable companies in a target vertical before a campaign.

- Level: autonomous
- Capabilities: tam-mapper, vertical-census
- Tools: Exa, Apollo

**Replaces**

Guessing how big the pond is. Teams campaign into verticals without knowing whether the addressable universe is 400 companies or 40,000 · and misprice the effort either way.

**Notes**

This is TAM at the company-name level, not the analyst-report level · a list you can actually campaign into. Know the denominator before you spend: a 4,000-company vertical justifies a system, a 150-company vertical justifies a hand-written letter each. The trap is mapping by industry code · SIC and NAICS lie constantly. Map by what companies actually do, scraped from what they say about themselves.

**Prerequisites:** ICP Definition

**Automation ladder**

- manual: A spreadsheet of companies somebody had heard of.
- assisted: The agent builds the full universe per ICP · every company that fits, counted and segmented · and a human sanity-checks the edges.
- autonomous: The map refreshes as companies get founded, funded, and folded; campaign planning reads live numbers, not last year’s guess.

**Linked skill files**

- Market Mapper: `skills/market-mapper.md`

#### Job: Trigger Detection

Watch for buying signals · hiring, funding, tech changes, leadership moves.

- Level: assisted
- Capabilities: hiring-signal-watcher, funding-tracker, tech-change-detector
- Tools: Exa, Apify

**Replaces**

Outreach timed by your calendar instead of theirs. The gap between a 2% and a 10% reply rate is often just catching a company the week something changed.

**Notes**

A detected signal nobody references is a wasted signal · the trigger has to reach the first line of the email, not sit in a CRM field. Start with the two or three triggers that genuinely map to your offer (hiring an SDR team if you sell outbound, a new ops lead if you sell automation) and ignore the rest. The trap is watching everything: ten signal types produce noise, two produce openers.

**Prerequisites:** Market Mapping

**Automation ladder**

- manual: You see the funding announcement on LinkedIn three weeks after everyone else did.
- assisted: Watched accounts get scanned for hiring spikes, funding, tech changes, and leadership moves; flagged leads land with the trigger attached.
- autonomous: A trigger fires and the lead enters the right sequence the same day, with the trigger written into the opener.

**Linked skill files**

- Buying Signals Analyst: `skills/buying-signals-analyst.md`

#### Job: Lookalike Modeling

Build new target lists off the shape of your closed-won accounts.

- Level: assisted
- Capabilities: lookalike-builder, pattern-extractor
- Tools: Apollo

**Replaces**

The expansion list nobody builds methodically · most teams guess at "who else looks like our best clients" instead of extracting the actual pattern.

**Notes**

This is ICP Definition pointed backwards · instead of who you think you want, it reads who actually bought and finds more of them. The quality depends entirely on having clean closed-won data, so it sits downstream of Win/Loss Analysis.

**Prerequisites:** ICP Definition, Win/Loss Analysis

**Automation ladder**

- manual: Someone eyeballs the closed-won list and says "let’s target more companies like these."
- assisted: The agent extracts the real shared firmographics + triggers from closed-won, builds a lookalike query, and hands back a ranked new list.
- autonomous: Every close feeds the model · the lookalike list refreshes itself and flows straight into sourcing.

**Linked skill files**

- Lead Scoring Analyst: `skills/lead-scoring-analyst.md`

### Function: Lead Sourcing

#### Job: Database Mining

Pull targeted company and contact lists from structured databases.

- Level: autonomous
- Capabilities: apollo-query-builder, saved-search-runner
- Tools: Apollo

**Human**

A human sets the target and spot-checks 10 rows per pull. Bad lists poison everything downstream · the check takes five minutes and saves a campaign.

**Replaces**

4–6 hours/week of an SDR pulling and cleaning lists · roughly $8–12k/year of a $65k rep’s time spent not selling.

**Notes**

The skill below builds tiered lead lists from structured databases and the open web, and degrades gracefully based on which API keys you have. Feed it your ICP file · the output quality is a direct function of node one.

**Prerequisites:** ICP Definition

**Automation ladder**

- manual: Someone exports CSVs from a database tool and fixes them in spreadsheets.
- assisted: You describe the target in plain language; the agent builds the query, pulls, dedupes, and hands back a clean segmented list.
- autonomous: Standing searches run weekly per ICP; new matches land pre-scored, with verified contacts, with no one asking.

**Linked skill files**

- Lead Sourcing Manager: `skills/lead-sourcing-manager.md`

#### Job: Web & Maps Scraping

Scrape local businesses, directories, and niche sources for leads.

- Level: autonomous
- Capabilities: maps-scraper, directory-harvester
- Tools: Apify

**Replaces**

The lists databases don’t sell · local businesses, niche directories, marketplaces. Built by hand this is days of copy-paste per territory, so it simply doesn’t get built.

**Notes**

This is where local and SMB lists live · the big databases are weakest exactly where Maps and directories are strongest. Scraped data is also the dirtiest data you’ll touch: route everything through verification before it gets near a sequence. The trap is one giant pull and done · territories change monthly, and the refresh is where the edge is.

**Prerequisites:** ICP Definition

**Automation ladder**

- manual: Copy-pasting business names out of Google Maps into a spreadsheet at 1am.
- assisted: Point the agent at a geography and a category; it scrapes, structures, dedupes against past pulls, and hands back clean rows.
- autonomous: Standing scrapes per territory refresh on schedule; new openings show up in your pipeline before competitors know they exist.

**Linked skill files**

- Lead Sourcing Manager: `skills/lead-sourcing-manager.md`

#### Job: Social Mining

Harvest engaged audiences · post commenters, followers, group members.

- Level: autonomous
- Capabilities: comment-harvester, engagement-miner, profile-collector
- Tools: Apify, HeyReach

**Replaces**

The list nobody builds by hand: everyone who engaged with a competitor’s post is a warm prospect, but scraping them manually takes hours per post.

**Notes**

Highest-intent cold list you can build · these people already raised their hand on the topic. The skill below scrapes engagers, enriches profiles, ICP-scores, and writes openers in one pass.

**Prerequisites:** ICP Definition

**Automation ladder**

- manual: You screenshot commenters and look them up one by one.
- assisted: Point the agent at a post or profile; it harvests engagers, enriches, scores against ICP, and drafts the first DM.
- autonomous: Watched accounts and keywords feed a standing warm-prospect pool, refreshed continuously.

**Linked skill files**

- Social Prospecting Specialist: `skills/social-prospecting-specialist.md`

#### Job: List Building

Merge, dedupe, and segment raw leads into campaign-ready lists.

- Level: autonomous
- Capabilities: list-deduper, segmenter, csv-normalizer
- Tools: None listed

**Replaces**

The 2–3 hours per campaign of merging CSVs and fighting duplicates · and the reputational cost when the same CEO gets the same email from two of your sequences.

**Notes**

The suppression list is the underrated half of this job: nothing torches trust like cold-emailing a current client or an open deal. Keep one canonical lead pool that every campaign draws from, not per-campaign spreadsheets that drift apart. The trap is deduping on email alone · dedupe on person and company, or the same prospect with two addresses slips through twice.

**Prerequisites:** Database Mining, Web & Maps Scraping

**Automation ladder**

- manual: VLOOKUP, tears, and the same person in three rows under slightly different spellings.
- assisted: Raw pulls from every source merge, dedupe, and segment into named campaign lists on command.
- autonomous: Every sourcing job feeds one canonical pool; campaign lists assemble themselves with suppression · clients, open deals, past bounces · applied automatically.

**Linked skill files**

- Lead Sourcing Manager: `skills/lead-sourcing-manager.md`

### Function: Enrichment

#### Job: Contact Enrichment

Find and append emails, phones, and LinkedIn profiles to every lead.

- Level: autonomous
- Capabilities: email-finder, phone-appender, linkedin-matcher
- Tools: Apollo, Apify

**Replaces**

A list you can’t reach. Without enrichment, 40–60% of a raw list has no usable contact · paying for leads and reaching half of them is the silent tax on every campaign.

**Notes**

Waterfall is the whole pattern: no single provider covers more than ~70%, so chain two or three and take the first valid hit. Track cost-per-found-contact by provider and cut the losers quarterly. The trap is enriching before filtering · paying to find the phone number of a lead you were never going to contact. Score and segment first, enrich what survives.

**Prerequisites:** List Building

**Automation ladder**

- manual: Guessing first.last@company.com and hoping.
- assisted: Waterfall enrichment runs per lead · email, direct dial, LinkedIn · across multiple providers, appended to the record.
- autonomous: Every lead entering the pool enriches on arrival; coverage rates and cost-per-found-contact tracked per provider.

**Linked skill files**

- Data Enrichment Specialist: `skills/data-enrichment-specialist.md`

#### Job: Email Verification

Validate every address before it ever gets a send.

- Level: autonomous
- Capabilities: smtp-verifier, catch-all-detector
- Tools: Instantly

**Replaces**

Domain burn. A 5% bounce rate doesn’t cost you 5% of sends · it gets the domain flagged, and the next 10,000 emails land in spam.

**Notes**

This is a gate, not a feature · nothing unverified gets sent, ever, and bounce rate stays under 2%. Decide your catch-all policy explicitly: send to them on a separate domain or don’t send at all, but never mix them into your clean volume. The trap is verifying once and trusting forever · addresses decay 2–3% a month as people change jobs.

**Prerequisites:** Contact Enrichment

**Automation ladder**

- manual: Send and find out.
- assisted: Every address passes through a verifier before it touches a sequence; catch-alls and risky addresses get flagged for a decision.
- autonomous: Verification runs on the way in and re-runs on any list older than 90 days; anything under threshold never reaches a sender.

**Linked skill files**

- Data Enrichment Specialist: `skills/data-enrichment-specialist.md`

#### Job: Account Enrichment

Layer firmographics, tech stack, and headcount trends onto target accounts.

- Level: autonomous
- Capabilities: firmographic-appender, tech-stack-detector, growth-signal-scorer
- Tools: Exa, Firecrawl

**Replaces**

The research step everyone skips: outreach to a company you don’t understand reads like spam because it is.

**Notes**

Pairs with Company Deep-Dive in the Intelligence department · enrichment is the bulk pass, deep-dive is the surgical one for accounts worth a real pursuit.

**Prerequisites:** Database Mining

**Automation ladder**

- manual: A glance at the website before the call.
- assisted: Tech stack, headcount trends, and growth signals appended to every target account on demand.
- autonomous: Accounts re-enrich on a schedule; material changes (funding, hiring spikes, stack changes) trigger alerts to the targeting layer.

**Linked skill files**

- Data Enrichment Specialist: `skills/data-enrichment-specialist.md`

#### Job: Fit Scoring

Score every lead against ICP so outreach spends effort where it converts.

- Level: autonomous
- Capabilities: fit-scorer, tier-assigner, disqualifier
- Tools: None listed

**Replaces**

Reps spending identical effort on a perfect-fit account and a tire-kicker, because the list doesn’t know the difference. Effort allocation is the multiplier on everything downstream.

**Notes**

A score that doesn’t change behavior is decoration · each tier must get genuinely different treatment: sequence depth, personalization effort, channel mix. Calibrate against closed-won quarterly: if your last ten wins weren’t A-tier, the model is wrong, not the wins. The trap is the 100-point model nobody trusts · three tiers with legible rules beat it every time.

**Prerequisites:** ICP Definition, Account Enrichment

**Automation ladder**

- manual: Sort by company size and call it prioritization.
- assisted: Every lead scores against the ICP file · firmographics, tech stack, triggers · and lands in a tier before any send.
- autonomous: Scores recompute as enrichment refreshes; A-tier routes to high-touch sequences, C-tier to low-cost ones, without anyone deciding per lead.

**Linked skill files**

- Lead Scoring Analyst: `skills/lead-scoring-analyst.md`

### Function: Outreach Writing

#### Job: Personalization Research

Build a personalization dossier per prospect · hooks, context, common ground.

- Level: autonomous
- Capabilities: prospect-dossier, hook-finder, common-ground-scanner
- Tools: Exa, Firecrawl

**Replaces**

10–15 minutes per prospect done properly · which is why nobody does it properly past the first twenty.

**Notes**

This is the difference between personalization and mail-merge. The skill below produces a structured dossier per person: what they’ve said publicly, what changed at their company, and the two strongest hooks to open with.

**Prerequisites:** Database Mining

**Automation ladder**

- manual: Two minutes on LinkedIn, then “Love what you’re doing at {company}!”
- assisted: The agent builds a dossier per prospect · hooks, recent moves, common ground · and a human picks the angle.
- autonomous: Every lead that enters a sequence carries its dossier with it; the writer agents consume it directly.

**Linked skill files**

- Prospect Research Analyst: `skills/prospect-research-analyst.md`

#### Job: Cold Email Drafting

Write multi-step cold email sequences tuned to the vertical and offer.

- Level: autonomous
- Capabilities: sequence-writer, subject-line-generator, spintax-builder
- Tools: None listed

**Human**

A human approves every new sequence before launch and owns the offer it sells. Once a sequence is proven, AI varies it within the approved frame.

**Replaces**

A $60–80k/year SDR’s core output · or a $2–4k/month agency retainer that sends the same template to everyone.

**Notes**

Voice is the whole game. The skill below reads your offer and tone files before it writes a word · set those up first or you’ll get competent generic. Three-step sequences, problem → proof → door-close. Never lead with price.

**Prerequisites:** ICP Definition, Personalization Research

**Automation ladder**

- manual: One template, first-name token, pray.
- assisted: The agent writes the full sequence per segment from your offer doc and dossiers; a human approves before launch.
- autonomous: Sequences generate per campaign, A/B variants included, with reply data feeding the next round’s angles.

**Linked skill files**

- Cold Email Copywriter: `skills/cold-email-copywriter.md`

#### Job: LinkedIn Messaging

Draft connection notes and DM sequences that read human.

- Level: autonomous
- Capabilities: connection-note-writer, dm-sequencer
- Tools: None listed

**Human**

Messages send under a real person’s name · that person reads what goes out under it. Approval per sequence, not per message.

**Replaces**

The 30 connection requests/day a founder sends in a good week and zero in a busy one. Consistency is the entire channel.

**Notes**

Shorter than email, more human, no links in the first message. The skill below drafts the full connection → DM → follow-up arc and exports to sending platforms.

**Prerequisites:** ICP Definition, Personalization Research

**Automation ladder**

- manual: Copy-pasted “I’d love to connect” notes.
- assisted: Connection notes and DM sequences drafted per prospect from their dossier; human sends.
- autonomous: Sequenced sending through an outreach platform, with replies routed back into the pipeline automatically.

**Linked skill files**

- LinkedIn Outreach Specialist: `skills/linkedin-outreach-specialist.md`

#### Job: Proof Matching

Match the right case study to each prospect’s industry and problem.

- Level: autonomous
- Capabilities: case-study-matcher, proof-point-selector
- Tools: None listed

**Replaces**

Sending the SaaS case study to the manufacturer. Generic proof reads like no proof · relevance is what makes evidence land, and matching it by hand is one more step nobody does at volume.

**Notes**

The library structure is the actual work: every case study tagged by vertical, problem, and outcome, each with one quotable number. A near-match in their industry beats a bigger number from a different world · buyers pattern-match on “that’s me” before they read the result. The trap is letting the agent round numbers up for effect: proof goes out verbatim or not at all.

**Prerequisites:** Company Knowledge Base, Account Enrichment

**Automation ladder**

- manual: The same two logos in every email, regardless of who’s reading.
- assisted: The agent picks the closest-match case study per prospect · industry, problem, company size · and writes the one-line proof into the draft.
- autonomous: Every sequence pulls its proof at generation time; a new case study enters the library and immediately starts appearing wherever it fits.

**Linked skill files**

- Case Study Curator: `skills/case-study-curator.md`

#### Job: Cold-Call Scripting

Call and voicemail scripts with branching objection handling that read human.

- Level: autonomous
- Capabilities: call-scripter, objection-brancher
- Tools: None listed

**Human**

A human delivers it · this drafts the words, the rep makes them sound like a person. The objection branches are the value, not the opener.

**Replaces**

The reps who freeze on the call because nobody wrote the branches · or the "script" that’s one paragraph and dies at the first objection.

**Notes**

The skill below writes call + voicemail scripts that read human, with branches for "not interested", "send me an email", "we already have someone", "no budget". Feed it the offer and one real objection and it tightens fast.

**Prerequisites:** ICP Definition

**Automation ladder**

- manual: A rep improvises, or reads a stiff script that the prospect can hear is a script.
- assisted: The agent writes the opener, the pattern interrupt, the value line, and a full objection-branch tree with example phrasing for each.
- autonomous: Scripts regenerate per segment as objection data comes back from real calls.

**Linked skill files**

- Outbound Scriptwriter: `skills/outbound-scriptwriter.md`

#### Job: Video Prospecting

Personalized video scripts · the hook, the personal line, the CTA, under 90 seconds.

- Level: autonomous
- Capabilities: video-scripter, personalization-writer
- Tools: None listed

**Replaces**

10+ minutes per personalized video done right · which is why reps record three then quit.

**Notes**

Video works because almost nobody does it well, and it dies because almost nobody scripts it. The skill below scripts the hook + personal line + value + CTA from the prospect dossier · the human just hits record.

**Prerequisites:** Personalization Research

**Automation ladder**

- manual: A rep stares at a Loom recording light with no script and rambles for two minutes.
- assisted: The agent writes a sub-90-second script · on-screen hook, a first line about the prospect’s actual world, one value beat, one CTA.
- autonomous: Every lead in a sequence carries a personalized video script generated from its dossier.

**Linked skill files**

- Outbound Scriptwriter: `skills/outbound-scriptwriter.md`

### Function: Sequencing & Send

#### Job: Campaign Orchestration

Build multi-channel cadences · email, LinkedIn, phone touches in order.

- Level: autonomous
- Capabilities: cadence-builder, channel-router
- Tools: None listed

**Replaces**

Single-channel outbound. Email-only gets email-only results · coordinated email, LinkedIn, and phone touches lift reply rates 2–3×, but sequencing them by hand across hundreds of leads is a planning job nobody sustains.

**Notes**

The channels have to know about each other: the LinkedIn note lands after email two and references the thread · or references nothing if it went unanswered. Map the whole arc before the first send; retrofitting coordination onto a live campaign is misery. The trap is believing more touches means more replies · 8–12 touches over three weeks, then stop and hand the silence to Reactivation.

**Prerequisites:** Cold Email Drafting, LinkedIn Messaging

**Automation ladder**

- manual: An email sequence here, some connection requests there, and no relationship between them.
- assisted: The agent assembles the full cadence · which channel, which day, which message · from your drafted assets; a human approves the plan.
- autonomous: Cadences build per segment from the playbook; the channel mix adjusts itself based on what actually got replies last quarter.

**Linked skill files**

- Campaign Operations Manager: `skills/campaign-operations-manager.md`

#### Job: Campaign Launch

Push finished campaigns into sending platforms with correct settings.

- Level: autonomous
- Capabilities: instantly-syncer, heyreach-syncer
- Tools: Instantly, HeyReach

**Human**

A human reviews the rendered test send before volume flows. Launch is the last gate where a broken token costs nothing · one minute of eyes here versus 2,000 apologies later.

**Replaces**

The hour of fiddly platform setup per campaign · and the occasional disaster where the {firstName} token goes out raw to the whole list.

**Notes**

Turn the launch checklist into code: daily limits set, tracking domain live, custom fields mapped, unsubscribe working, test send rendered and read. The render check catches the embarrassing failure class · broken personalization tokens · before anyone outside sees it. The trap is launching to the full list at once: ramp over days, both for deliverability and so a bad sequence dies at 10% sent instead of 100%.

**Prerequisites:** Campaign Orchestration, Email Verification

**Automation ladder**

- manual: Copy-paste the sequence into the sender, set the limits from memory, hope.
- assisted: Finished campaigns push into the sending platform with schedules, limits, custom fields, and tracking configured; a human checks the test send.
- autonomous: Approved campaigns deploy themselves · settings pulled from the playbook, test send auto-rendered and checked, go-live logged.

**Linked skill files**

- Campaign Operations Manager: `skills/campaign-operations-manager.md`

#### Job: Deliverability

Keep domains healthy · warmup, spam testing, inbox rotation.

- Level: assisted
- Capabilities: warmup-monitor, spam-score-tester, domain-health-auditor
- Tools: Instantly

**Replaces**

The silent campaign killer. Everything upstream can be perfect and none of it matters from spam · and most teams find out a month of wasted sends too late.

**Notes**

Architecture first: cold volume goes through secondary domains, never your main one · 2–3 inboxes per domain, 30–50 sends per inbox per day, warmed for 2–3 weeks before real volume. From there it’s monitoring: placement tests and bounce trends on a schedule, not when things feel slow. The trap is treating this as one-time setup · deliverability is a tide, not a switch, and it only moves one direction unattended.

**Prerequisites:** Campaign Launch

**Automation ladder**

- manual: Reply rates fall off a cliff and somebody eventually wonders why.
- assisted: Inbox placement tests, warmup, and domain health checks run on schedule; problems surface with the fix attached.
- autonomous: Rotation, warmup, and volume throttling self-manage; a domain showing strain gets pulled from rotation before it burns.

**Linked skill files**

- Deliverability Manager: `skills/deliverability-manager.md`

#### Job: Send Optimization

Schedule sends by timezone and pace volume to protect reply rates.

- Level: autonomous
- Capabilities: timezone-scheduler, volume-pacer
- Tools: None listed

**Replaces**

Blasting everyone at 9am your time · including the prospects for whom that’s 2am, and the inbox providers for whom that spike looks exactly like spam.

**Notes**

Timezone correctness alone is worth real points of reply rate · a 9am email read at 9am is a different email than one buried under the overnight pile. Pacing should look human: spread through the working day, randomized intervals, no perfect cron-job spikes. The trap is over-tuning send windows on small samples · you need hundreds of sends per cell before timing data means anything; until then, recipient-morning and move on.

**Prerequisites:** Campaign Launch, Deliverability

**Automation ladder**

- manual: Send-all, then refresh the dashboard.
- assisted: Sends schedule per recipient timezone and pace inside provider-safe volume; the agent proposes window changes from reply data.
- autonomous: Send timing tunes itself per segment from observed reply patterns; volume flexes up and down with domain health.

**Linked skill files**

- Campaign Operations Manager: `skills/campaign-operations-manager.md`

## Department: Deals

What happens after someone raises their hand · the reply gets read and routed, the meeting gets booked, the proposal gets written, the pipeline stays honest. Speed wins deals here, and speed is exactly what a human team loses as volume grows. The agents answer in minutes, draft before the next call, and never let a deal go quiet without flagging it.

### Function: Reply Handling

#### Job: Reply Classification

Read every reply and tag it · interested, objection, referral, not now, never.

- Level: autonomous
- Capabilities: intent-classifier, sentiment-tagger, auto-labeler
- Tools: None listed

**Human**

Edge cases route to a human within minutes; everything else is logged for a weekly 15-minute audit of the classifier’s calls.

**Replaces**

The inbox-checking anxiety loop. At volume, a human misses hot replies for 6+ hours · and speed-to-reply is the highest-leverage variable in outbound.

**Notes**

The pattern that scales outbound past one inbox. Build the objection library from your real replies · after ~50 classified threads the categories stabilize and the drafts stop needing edits. This is the node franchise networks and multi-territory businesses feel hardest.

**Prerequisites:** Cold Email Drafting

**Automation ladder**

- manual: Founder reads every reply, usually at midnight.
- assisted: Every reply auto-tagged · interested / objection / referral / not-now / never · with drafted responses queued for approval.
- autonomous: Interested replies route to the calendar in minutes; objections get library responses; only edge cases reach a human.

**Linked skill files**

- Outbound Inbox Manager: `skills/outbound-inbox-manager.md`

#### Job: Objection Response

Draft responses to common objections from a tuned library.

- Level: assisted
- Capabilities: objection-library, response-drafter
- Tools: None listed

**Human**

The library is human-authored from real won deals · AI retrieves and adapts, it never invents a new counter-argument that no one has tested live.

**Replaces**

Re-improvising the same five rebuttals forever. Every outbound motion gets the same objections · price, timing, “we have someone”, “send info” · and most reps answer each one slightly worse than last time.

**Notes**

Build the library from threads you actually won, not from sales books · your real replies beat generic frameworks. Five objections cover 80% of volume; write one great answer per objection per offer and stop there. The trap is over-arguing: the best objection responses concede something true, then reframe in one short paragraph.

**Prerequisites:** Reply Classification

**Automation ladder**

- manual: You retype your best comeback from memory, slightly different every time, usually softer.
- assisted: Each classified objection gets a drafted response from a tuned library · your strongest past answer, adapted to this thread · queued for approval.
- autonomous: Known objections get library responses on send-approval autopilot; novel objections route to a human and their winning answer joins the library.

**Linked skill files**

- Outbound Inbox Manager: `skills/outbound-inbox-manager.md`

#### Job: Hot-Lead Routing

Route interested replies to the calendar and the pipeline instantly.

- Level: autonomous
- Capabilities: hot-lead-alerter, crm-promoter
- Tools: Attio

**Replaces**

The hours an interested reply sits in an inbox while the prospect cools. Interest decays by the hour · a hot reply answered next morning converts at a fraction of one answered in minutes.

**Notes**

This is plumbing, not intelligence · the classifier already found the gold; routing just refuses to let it sit. Wire it to the calendar and the CRM in the same motion so a hot reply becomes a booked slot and a pipeline record, not a notification. The trap is routing on weak signals: tune the classifier conservative, because one fake-hot alert per day teaches the owner to ignore all of them.

**Prerequisites:** Reply Classification, CRM Hygiene

**Automation ladder**

- manual: The hot reply is item 47 in the inbox and gets the same priority as the newsletter.
- assisted: Interested replies get flagged, pushed to the deal owner, and pre-loaded with a booking-ready response in minutes.
- autonomous: Hot replies skip the queue entirely · calendar link sent, deal created at the right stage, owner notified, all before a human has read the thread.

**Linked skill files**

- Outbound Inbox Manager: `skills/outbound-inbox-manager.md`

#### Job: Meeting Booking

Propose slots, book calls, chase no-shows.

- Level: autonomous
- Capabilities: slot-proposer, cal-booker, no-show-recoverer
- Tools: Cal.com

**Human**

The calendar owner sets the rules once · buffers, hours, who qualifies. The agent never negotiates exceptions; humans do.

**Replaces**

The 4–7 message back-and-forth that kills deal momentum, plus the no-shows nobody chases.

**Notes**

Wire it to your real availability with buffers, not your aspirational one. The no-show recovery sequence alone pays for the build · most teams just let those die.

**Prerequisites:** Reply Classification

**Automation ladder**

- manual: “What times work for you?” × 3.
- assisted: Agent proposes slots from the live calendar and books on confirmation.
- autonomous: Hot replies get slots in the first response; no-shows get a recovery sequence automatically.

**Linked skill files**

- Meeting Booking Coordinator: `skills/meeting-booking-coordinator.md`

#### Job: Referral Capture

Spot the "talk to my colleague" replies and action the warm intro.

- Level: autonomous
- Capabilities: referral-spotter, intro-router
- Tools: None listed

**Replaces**

The warm intros that evaporate · a prospect says "talk to my colleague in ops" and the reply sits unactioned for a week until the moment’s gone.

**Notes**

Referrals close roughly twice as fast as cold · and they’re the leakiest part of most pipelines because they arrive as a throwaway line in a reply. This catches them the moment they land.

**Prerequisites:** Reply Classification

**Automation ladder**

- manual: A rep reads the reply, means to follow up on the referral, forgets.
- assisted: The agent flags every "talk to / loop in / not me but" reply, drafts the warm-intro ask, and routes the new contact into the pipeline.
- autonomous: Referral replies are detected, the intro is drafted, and the new lead is created and assigned without a human touching the inbox.

**Linked skill files**

- Inbound Response Manager: `skills/inbound-response-manager.md`

### Function: Inbound

#### Job: Speed-to-Lead

Acknowledge and engage every inbound lead within minutes.

- Level: autonomous
- Capabilities: instant-responder, intake-acknowledger
- Tools: None listed

**Replaces**

The two days between a form fill and a founder’s reply. Inbound leads contacted within five minutes convert at multiples of those contacted next-day · and most businesses are measured in days.

**Notes**

The first message only has two jobs: prove a human-quality brain read their submission, and open the next step. Reference what they actually wrote · a reply that mirrors their form answer beats any template. The trap is sounding like an autoresponder; if the message could have been sent without reading the submission, rewrite the system.

**Prerequisites:** Company Knowledge Base

**Automation ladder**

- manual: The lead fills the form Tuesday, hears back Thursday, signed with someone else Wednesday.
- assisted: Every inbound lead gets an acknowledgment within minutes · personal in tone, specific to what they asked · with the human looped in for the real conversation.
- autonomous: First response, qualifying question, and booking link fire inside five minutes around the clock; the human wakes up to scheduled calls, not raw form fills.

**Linked skill files**

- Inbound Response Manager: `skills/inbound-response-manager.md`

#### Job: Lead Qualification

Parse intake forms and score inbound leads before a human looks.

- Level: autonomous
- Capabilities: qual-scorer, intake-parser, budget-detector
- Tools: None listed

**Human**

AI scores and sorts; a human owns where the disqualification line sits and audits the auto-declines. Spotting the bad-fit lead that’s secretly a strategic exception stays a judgment call.

**Replaces**

30–45 minutes of discovery call per lead that should never have been booked. Unqualified calls are the most expensive way to learn someone has no budget.

**Notes**

The intake form is the real build: ask three questions that predict close · budget range, problem in their words, timeline · and the scoring becomes trivial. Score against your closed-won pattern, not an aspirational ICP. The trap is over-filtering early: log every auto-declined lead and audit the list monthly until you trust the line.

**Prerequisites:** ICP Definition

**Automation ladder**

- manual: Everyone who books gets a call; you find out they’re a student with a question at minute four.
- assisted: Intake answers parsed and scored against your ICP · budget, fit, urgency · with a recommended route (book, nurture, decline) before a human looks.
- autonomous: Qualified leads book straight onto the calendar, marginal ones enter a nurture track, and poor fits get a polite redirect · no human triage at all.

**Linked skill files**

- Inbound Response Manager: `skills/inbound-response-manager.md`

#### Job: Comment-CTA Fulfillment

Detect keyword comments on content and deliver the promised asset by DM.

- Level: autonomous
- Capabilities: keyword-listener, dm-fulfiller
- Tools: Instagram API

**Replaces**

Manually DMing a link to 400 commenters · which means either hours of phone time after every post that pops, or broken promises to the exact people who raised their hands.

**Notes**

This is the bridge between content and pipeline: the comment is a hand-raise, the DM is the capture, the asset is the excuse. Gate the asset behind an email and the content engine starts feeding the CRM directly. The trap is stopping at delivery · tag every lead with which asset they claimed, because that tag is targeting data for everything downstream.

**Prerequisites:** Lead-Magnet Builds

**Automation ladder**

- manual: You send the first 30 DMs by thumb, lose steam, and the other 370 commenters get nothing.
- assisted: Keyword comments detected per post; the promised asset goes out by DM from a queue a human can watch.
- autonomous: Every comment-CTA post fulfills itself · keyword detected, asset delivered, email captured, lead tagged by which asset they wanted · at any volume, at any hour.

**Linked skill files**

- DM Fulfillment Specialist: `skills/dm-fulfillment-specialist.md`

#### Job: Inbox Triage

Sort inbound email and DMs · client, lead, brand deal, noise.

- Level: autonomous
- Capabilities: inbox-triager, priority-router
- Tools: None listed

**Replaces**

The founder as a human sorting machine · 60–90 minutes a day deciding what each message even is before any real work starts, with the important ones buried under the noise.

**Notes**

Triage is classification plus routing · the tag is worthless unless something happens because of it: leads to the pipeline, client items to the project context, noise to archive. Start with five categories maximum; precision beats granularity. The trap is silent misfiling · keep a weekly audit of what got tagged noise, because one mis-archived client email costs more than the system saves.

**Prerequisites:** Company Knowledge Base

**Automation ladder**

- manual: Everything is unread, everything is urgent, the client email from Tuesday surfaces Friday.
- assisted: Every inbound email and DM tagged on arrival · client, lead, brand deal, admin, noise · with the must-answer items surfaced first.
- autonomous: The inbox sorts itself continuously; noise never reaches a human, leads route to the pipeline, client messages flag the right project, and you work a ranked queue instead of a timeline.

**Linked skill files**

- Inbound Response Manager: `skills/inbound-response-manager.md`

### Function: Call Cycle

#### Job: Pre-Call Briefing

Build a brief before every call · who, company, history, objectives, talking points.

- Level: autonomous
- Capabilities: prep-brief-builder, attendee-researcher
- Tools: Fireflies, Attio

**Replaces**

The 20 scrambled minutes before every call · or worse, walking in cold and asking questions the website answers.

**Notes**

Reads the CRM, past transcripts, and email threads. The compounding effect is real: by call three the brief knows more about the relationship than you remember.

**Prerequisites:** Company Knowledge Base, Call Capture

**Automation ladder**

- manual: Skim their LinkedIn in the waiting room.
- assisted: A one-page brief lands before every call: who, company, history, last conversation, open threads, suggested objectives.
- autonomous: Briefs generate from the calendar automatically · every external meeting, no trigger needed.

**Linked skill files**

- Call Prep Researcher: `skills/call-prep-researcher.md`

#### Job: Call Capture

Record, transcribe, and file every meeting automatically.

- Level: autonomous
- Capabilities: transcript-ingester, meeting-filer
- Tools: Fireflies

**Human**

Humans run the meeting; the system just never forgets it. Flag sensitive calls as do-not-record · the convention matters more than the tool.

**Replaces**

Notes that don’t exist, decisions nobody wrote down, and “wait, what did we agree?”

**Notes**

The single cheapest high-leverage node on this map · a notetaker subscription and a filing convention. Everything in the Deals and Operations trees gets smarter the day this turns on. If you deploy one node this month, deploy this one.

**Prerequisites:** Company Knowledge Base

**Automation ladder**

- manual: Pen, paper, vibes.
- assisted: Every meeting recorded and transcribed via a notetaker; transcripts filed per client.
- autonomous: Transcripts flow into the knowledge base automatically and become readable context for every other agent.

**Linked skill files**

- Meeting Intelligence Engineer: `skills/meeting-intelligence-engineer.md`

#### Job: Post-Call Debrief

Extract outcomes, action items, and deal updates from the transcript.

- Level: autonomous
- Capabilities: action-extractor, deal-updater, commitment-tracker
- Tools: None listed

**Human**

The deal owner skims the extracted actions same-day · 2 minutes to confirm what a human promised another human.

**Replaces**

30 minutes of post-call admin per meeting that either eats selling time or doesn’t happen.

**Notes**

Combine with Follow-Up Drafting: the recap email should arrive while the prospect still remembers the call. Same-day follow-up measurably outperforms next-day · and AI makes same-hour trivial.

**Prerequisites:** Call Capture

**Automation ladder**

- manual: Action items live in your head until they don’t.
- assisted: Transcript → outcomes, action items, deal-stage updates, drafted within minutes of hang-up.
- autonomous: CRM updates itself, tasks assign themselves, and the follow-up email is waiting in drafts.

**Linked skill files**

- Deal Debrief Analyst: `skills/deal-debrief-analyst.md`

#### Job: Follow-Up Drafting

Draft the recap email with next steps before the prospect forgets the call.

- Level: autonomous
- Capabilities: recap-writer, next-step-drafter
- Tools: None listed

**Replaces**

The recap email that goes out two days late or never. Deals lose momentum in the gap between the call and the follow-up · and the gap is usually just the seller being busy.

**Notes**

Speed is the feature: a same-hour recap lands while the prospect still feels the call, and it quietly sets the version of events on your terms. Keep it short · decisions, next steps with owners and dates, one forward-looking line. The trap is sending a transcript summary instead of a sales document; the recap should advance the deal, not minute the meeting.

**Prerequisites:** Call Capture, Post-Call Debrief

**Automation ladder**

- manual: You mean to send the recap tonight; tonight becomes Thursday; Thursday becomes “following up on our chat last week”.
- assisted: The recap drafts itself from the transcript within minutes of hang-up · what was agreed, next steps, owners · waiting in drafts for a read and a send.
- autonomous: Every external call produces its follow-up automatically; the human edits the occasional nuance, and same-hour recaps become the house standard.

**Linked skill files**

- Deal Debrief Analyst: `skills/deal-debrief-analyst.md`

#### Job: Objection Library

Mine every call for the objections that come up · build the rebuttals that win.

- Level: assisted
- Capabilities: objection-miner, rebuttal-builder
- Tools: Fireflies

**Replaces**

The objection-handling knowledge that lives only in the head of your best closer · and walks out the door when they do.

**Notes**

This turns your call recordings into a compounding asset. It reads what objections actually came up and which responses preceded a won deal · so the rebuttals are evidence-based, not invented. Feeds straight into Cold-Call Scripting and Objection Response.

**Prerequisites:** Call Capture

**Automation ladder**

- manual: Every rep relearns the same objections from scratch, badly.
- assisted: The agent mines every recorded call for objections, clusters them, and drafts the rebuttal that actually moved deals forward.
- autonomous: The library updates itself as new calls land · new objections surface, weak rebuttals get flagged and rewritten.

**Linked skill files**

- Deal Debrief Analyst: `skills/deal-debrief-analyst.md`

### Function: Deal Artifacts

#### Job: Demo Prototyping

Turn discovery notes into a working visual prototype before the next meeting.

- Level: autonomous
- Capabilities: dream-prototyper, sandbox-builder
- Tools: None listed

**Human**

AI builds the prototype; the human decides whether it ships. Nothing reaches a prospect without the seller’s eyes on it.

**Replaces**

The two-week proposal gap where deals go cold. A visual prototype sent same-day collapses the “is this possible?” conversation entirely.

**Notes**

Sell the dream: show them their end state before the proposal exists. The follow-up call stops being “convince me” and becomes “scope it.” The skill below extracts the brief from a transcript, picks the right format, and drafts the send message.

**Prerequisites:** Call Capture

**Automation ladder**

- manual: A follow-up deck, eventually.
- assisted: Discovery notes → working visual prototype + send message, same day, human reviews before it goes out.
- autonomous: Every discovery call triggers a prototype draft; the human picks which ones to polish and send.

**Linked skill files**

- Solutions Engineer: `skills/solutions-engineer.md`

#### Job: Proposal Generation

Generate branded proposals rendered to PDF from call context.

- Level: autonomous
- Capabilities: proposal-writer, pdf-renderer
- Tools: None listed

**Human**

AI drafts structure and prose; a human owns scope and price on every proposal. Those two numbers are never delegated.

**Replaces**

3–6 hours per proposal · and for services firms doing tenders, often 2–3 days per response. This is frequently the bottleneck on revenue itself.

**Notes**

Template matching is the unlock: your best past proposals become the pattern library. Build the brand template once, render programmatically forever. Architecture and professional-services firms run entire bid teams on what this node replaces.

**Prerequisites:** Call Capture, Post-Call Debrief

**Automation ladder**

- manual: Last proposal, find-and-replace, new logo.
- assisted: Call context → drafted proposal in the house template, rendered to branded PDF; human edits scope and price.
- autonomous: Proposal drafts generate from the deal record the moment a deal hits “proposal” stage, matched to the closest past win.

**Linked skill files**

- Proposal Writer: `skills/proposal-writer.md`

#### Job: Deal Room Assembly

Spin up tracked, password-gated deal rooms per prospect.

- Level: autonomous
- Capabilities: room-builder, magic-link-issuer, engagement-tracker
- Tools: None listed

**Replaces**

PDF proposals that get forwarded into the void. A tracked room tells you who opened what, when · intel a PDF can never give you.

**Notes**

The forward-ability is the point · your champion sells internally with a link, not an attachment. Magic links per stakeholder turn open-data into a stakeholder map.

**Prerequisites:** Proposal Generation

**Automation ladder**

- manual: Attachment in an email thread.
- assisted: Branded, password-gated room per prospect · proposal, scope, proof, pricing · spun up from a template.
- autonomous: Rooms generate per deal with engagement tracking feeding the pipeline: you know which stakeholder read pricing twice.

**Linked skill files**

- Deal Room Producer: `skills/deal-room-producer.md`

#### Job: Agreement Drafting

Produce the services agreement the moment a deal closes verbally.

- Level: assisted
- Capabilities: contract-generator, esign-preparer
- Tools: None listed

**Human**

A lawyer blesses the master template once; a human reviews every generated agreement before it goes out. AI fills and adapts · it never invents a clause.

**Replaces**

The 3–10 day gap between “yes” and paperwork, where verbal closes go to die. Plus $300–800 of lawyer time per agreement if you draft each one fresh instead of templating once.

**Notes**

Send the agreement the same day as the verbal yes · momentum is a closing tool and every day of silence invites second thoughts. Get one lawyer pass on the master template, then never freelance the legal language again; the AI’s job is filling variables, not writing clauses. The trap is letting per-deal “small tweaks” fork the template until no two contracts match.

**Prerequisites:** Proposal Generation

**Automation ladder**

- manual: You hunt for the last client’s contract, find-and-replace their name, and miss one instance of it in clause 9.
- assisted: The moment a deal closes verbally, the agreement generates from the deal record · parties, scope, fees, terms · into the lawyer-approved template, ready for human review and signature.
- autonomous: Stage change to closed-won triggers the agreement, routes it for e-signature, and chases the unsigned · the human only touches deals with non-standard terms.

**Linked skill files**

- Contracts Coordinator: `skills/contracts-coordinator.md`

#### Job: Pricing Support

Model anchors, phase structures, and ROI comparisons per deal.

- Level: autonomous
- Capabilities: anchor-calculator, roi-modeler, phase-structurer
- Tools: None listed

**Human**

AI models the structures; the human picks the number. Price is positioning, leverage, and read-of-the-room · the final figure on every deal is a human call, never a model output.

**Replaces**

Pricing by gut and anchoring low under pressure. The hour of FTE-comparison math and phase-structuring that justifies a 2–3× higher number · done properly for big deals, skipped for the rest.

**Notes**

Anchor against the cost of the alternative, not your own effort · the comparison to a salary, an agency retainer, or the cost of the problem persisting is what makes a number feel small. Phase the structure so the first yes is easy and the relationship prices the rest. The trap is letting the model’s mid-range option become a ceiling; the math exists to defend ambition, not cap it.

**Prerequisites:** Company Knowledge Base, Pricing Research

**Automation ladder**

- manual: You pick a number on the call, feel it wobble, and discount before anyone asked you to.
- assisted: Per deal: anchor comparisons, phase structures, and ROI math modeled from the discovery context · three defensible options with the reasoning attached, before the pricing conversation.
- autonomous: Every deal entering proposal stage arrives with its pricing model pre-built · comparable past deals, suggested anchor, phase breakdown · and the human chooses rather than calculates.

**Linked skill files**

- Pricing Analyst: `skills/pricing-analyst.md`

### Function: Pipeline Ops

#### Job: CRM Hygiene

Keep records deduped, fields normalized, stages honest.

- Level: autonomous
- Capabilities: record-deduper, field-normalizer, stage-auditor
- Tools: Attio

**Replaces**

The 10–20% of records that are duplicates, dead, or wrong · and every report, forecast, and automation silently built on top of them. Garbage hygiene taxes every node downstream.

**Notes**

Hygiene is the unglamorous prerequisite for the entire Pipeline Ops branch · reporting, forecasting, and reactivation all read from these records, and they inherit every error. Define “honest stage” rules in writing (what evidence moves a deal forward) and let the system enforce them. The trap is the quarterly cleanup blitz: hygiene is a standing process, not an event, and a CRM cleaned once decays in weeks.

**Prerequisites:** Company Knowledge Base

**Automation ladder**

- manual: Three records for the same company, a deal marked “proposal” since March, and nobody trusts the dashboard.
- assisted: Dedupe candidates, stale stages, and missing fields surface on a schedule with proposed fixes; a human approves the merge.
- autonomous: Records dedupe and normalize continuously, stages age out with prompts to the owner, and every new entry conforms on arrival · the CRM stays true without a cleanup day.

**Linked skill files**

- Pipeline Operations Manager: `skills/pipeline-operations-manager.md`

#### Job: Pipeline Reporting

Weekly pipeline state · what moved, what stalled, what closes next.

- Level: autonomous
- Capabilities: pipeline-reporter, funnel-analyzer
- Tools: None listed

**Replaces**

The Monday hour of assembling pipeline state by hand · or the more common alternative, running the business on whatever the founder remembers the pipeline looking like.

**Notes**

Report movement, not state · “what changed since last week” is the entire value, and a static pipeline snapshot is just a screenshot with ceremony. Include a stalled-deals section with days-since-last-touch; it is the report’s most actionable line. The trap is metric sprawl: one page, same format weekly, so deviations jump out instead of hiding in noise.

**Prerequisites:** CRM Hygiene

**Automation ladder**

- manual: Someone scrolls the CRM before the meeting and narrates it from memory.
- assisted: A weekly digest lands on schedule: what moved, what stalled, what closes next, and which deals went quiet · with the deltas, not just the totals.
- autonomous: The report writes and distributes itself, flags anomalies between editions, and answers ad-hoc pipeline questions on demand · the meeting reads the report instead of building it.

**Linked skill files**

- Pipeline Operations Manager: `skills/pipeline-operations-manager.md`

#### Job: Forecasting

Probability-weight the pipeline into a revenue forecast.

- Level: assisted
- Capabilities: close-probability-scorer, revenue-forecaster
- Tools: None listed

**Human**

The model weights the pipeline; the deal owner adjusts the calls. A human who just left the room knows things no stage-probability ever will · the forecast is a draft until someone accountable signs it.

**Replaces**

Revenue surprises in both directions. The founder’s number is usually hope-weighted, not probability-weighted · and the gap between them is the months of runway you didn’t know you were missing.

**Notes**

Track forecast-versus-actual from day one · the model earns trust by being auditable, and three months of scorekeeping beats any methodology debate. Weight on behavior (engagement, momentum, days-in-stage) more than on stage labels, which mostly record what the seller hoped. The trap is false precision: a forecast with a range and visible assumptions is useful; a single confident number is theater.

**Prerequisites:** CRM Hygiene, Pipeline Reporting

**Automation ladder**

- manual: You add up the pipeline, multiply by optimism, and call it a forecast.
- assisted: Deals probability-weighted by stage, age, and engagement signals into a monthly revenue forecast · with the assumptions visible, so a human can argue with them.
- autonomous: The forecast updates as deals move, learns from its own misses, and flags the gap between the model’s number and the owner’s · which is usually where the truth lives.

**Linked skill files**

- Pipeline Operations Manager: `skills/pipeline-operations-manager.md`

#### Job: Reactivation

Revive dormant deals and win back lost ones on a schedule.

- Level: autonomous
- Capabilities: dormant-deal-reviver, winback-sequencer
- Tools: None listed

**Human**

A human approves the revival list monthly · some dead deals should stay dead, and only a human knows which.

**Replaces**

The revenue sitting in your dead-deals column. Most pipelines have 6 figures of “went quiet” that nobody systematically revisits.

**Notes**

The re-opener must contain new value · a relevant build, a result in their vertical, a changed offer. “Just checking in” is not reactivation, it’s noise. Cheapest pipeline you’ll ever generate; the leads are already paid for.

**Prerequisites:** CRM Hygiene

**Automation ladder**

- manual: You remember an old prospect in the shower.
- assisted: Dormant deals surface on a schedule with a drafted, context-aware re-opener · referencing where things left off, leading with something new.
- autonomous: Every deal that goes quiet enters a patient, spaced revival track automatically; replies route back to the pipeline.

**Linked skill files**

- Reactivation Specialist: `skills/reactivation-specialist.md`

#### Job: Win/Loss Analysis

Tag why deals close or die; feed patterns back into targeting.

- Level: manual
- Capabilities: loss-tagger, pattern-miner
- Tools: None listed

**Human**

The losing seller writes the first draft of why · then someone who wasn’t in the deal reads it skeptically. Self-reported loss reasons are where pipelines lie to themselves most fluently.

**Replaces**

Paying full tuition for every lost deal and keeping none of the lesson. Most teams can’t say why their last five losses died beyond “price” · which is almost never the real reason.

**Notes**

The taxonomy is the build: eight to twelve fixed reasons, forced choice, free text optional · uncategorized losses are unanalyzable losses. Mine the call transcripts, not the seller’s recollection; the real reason is usually said out loud somewhere in the second call. The trap is collecting tags and never closing the loop · the analysis only pays when it changes the ICP, the pitch, or the price.

**Prerequisites:** Call Capture, CRM Hygiene

**Automation ladder**

- manual: A shrug, a “they went another direction”, and the same mistake next quarter.
- assisted: Every closed deal gets tagged with a structured reason, drawn from the transcripts and thread history rather than the seller’s memory; patterns compile quarterly.
- autonomous: Loss patterns surface as they form · a vertical going cold, an objection trending up, a competitor winning on the same line · and feed straight back into targeting and the objection library.

**Linked skill files**

- Reactivation Specialist: `skills/reactivation-specialist.md`

## Department: Marketing

The engine that makes you known · reading what works, making more of it, and pushing one good idea across every surface before the trend moves. Most teams post and pray. This department measures every piece against the median, doubles down on the winners, and turns a single reel into nine assets · so output stops depending on whoever felt inspired that week.

### Function: Insights

#### Job: Performance Mining

Rank your own content corpus · what worked, what to re-hash.

- Level: autonomous
- Capabilities: corpus-ranker, rehash-finder, era-analyzer
- Tools: None listed

**Replaces**

Posting on instinct while your own corpus already knows what works. Your top 10 posts are a content strategy · if anything reads them.

**Notes**

Re-hashing beats inventing: a proven idea in a new format outperforms a new idea in any format, and audiences forget faster than creators think.

**Prerequisites:** Company Knowledge Base

**Automation ladder**

- manual: Scrolling your own profile for ideas.
- assisted: The corpus ranked by performance, patterns extracted · hooks, formats, topics · with re-hash candidates flagged.
- autonomous: Every new post is scored against the pattern library before it ships; winners auto-feed the idea queue.

**Linked skill files**

- Content Performance Analyst: `skills/content-performance-analyst.md`

#### Job: Trend Monitoring

Watch the niche for breaking topics and rising formats.

- Level: autonomous
- Capabilities: news-watcher, format-spotter
- Tools: Exa

**Replaces**

An hour a day of feed-scrolling disguised as research.

**Notes**

The skill below runs topic → articles → hooks → ready-to-draft ideas as one chain. Speed matters more than polish on trend content · the half-life is measured in days.

**Automation ladder**

- manual: Whatever the algorithm showed you at breakfast.
- assisted: Daily sweep of the niche · breaking topics, rising formats · distilled into content angles in your voice.
- autonomous: The day’s angles land each morning, pre-matched to your pillars and ranked by fit.

**Linked skill files**

- Trend Analyst: `skills/trend-analyst.md`

#### Job: Competitor Analysis

Scrape and transcribe competitor content; extract hook patterns.

- Level: autonomous
- Capabilities: reel-transcriber, hook-pattern-miner
- Tools: Apify, Deepgram

**Replaces**

Watching competitors casually instead of systematically. Their viral posts are free R&D · someone else paid the testing cost.

**Notes**

Transcription is the trick · the spoken hook is where the pattern lives, not the caption. Two skills below: one for Instagram reels, one for TikTok.

**Automation ladder**

- manual: You saw their reel and felt something.
- assisted: Competitor content scraped and transcribed; hook patterns, formats, and cadence extracted into a playbook.
- autonomous: Watched accounts feed a standing pattern library; your hook generator consumes it directly.

**Linked skill files**

- Instagram Content Analyst: `skills/instagram-content-analyst.md`
- TikTok Content Analyst: `skills/tiktok-content-analyst.md`

#### Job: Audience Analysis

Mine comments and DMs for questions, objections, and content ideas.

- Level: autonomous
- Capabilities: comment-miner, question-clusterer
- Tools: None listed

**Replaces**

Reading comments for dopamine instead of data. Your audience tells you exactly what to make next, every day, in writing · and almost nobody logs it.

**Notes**

Objections are the gold · a question asked three times in comments is a reel, a guide, and an email in one. Pipe the output into Hook Writing so demand drives creation, not the other way around. The trap is mining only your winners: the comments on mediocre posts tell you why they were mediocre.

**Prerequisites:** Company Knowledge Base

**Automation ladder**

- manual: You vaguely remember someone asked about pricing once.
- assisted: Comments and DMs mined on a schedule · questions, objections, and recurring pain extracted into a ranked content-idea queue.
- autonomous: Every comment and DM feeds a standing demand map; new objections route to the idea queue and the offer doc without anyone scrolling.

**Linked skill files**

- Content Performance Analyst: `skills/content-performance-analyst.md`

### Function: Creation

#### Job: Hook Writing

Generate and rank hooks per platform from proven patterns.

- Level: autonomous
- Capabilities: hook-generator, hook-ranker
- Tools: None listed

**Replaces**

The blank-page tax on every piece of content. The hook is 80% of performance and the part most creators spend the least time on.

**Notes**

Volume is the method: write twenty, ship one. The skill below generates per-platform · a LinkedIn hook and a TikTok hook are different species.

**Prerequisites:** Performance Mining

**Automation ladder**

- manual: First line that comes to mind, posted.
- assisted: 15–20 ranked hooks per idea, per platform, generated from proven patterns · you pick, you post.
- autonomous: Every idea in the queue arrives with its hook variants attached; performance data re-ranks patterns monthly.

**Linked skill files**

- Creative Strategist: `skills/creative-strategist.md`

#### Job: Script Writing

Full reel and video scripts in the house voice.

- Level: autonomous
- Capabilities: script-writer, voice-matcher
- Tools: None listed

**Replaces**

2–3 hours per script done properly, or $150–500 per script from a freelancer who doesn’t sound like you. At a daily posting cadence that’s a part-time hire.

**Notes**

The voice file is the whole build · feed it real transcripts of your best-performing content, not your written posts, because spoken voice and written voice are different animals. Structure beats inspiration: hook → tension → payoff → CTA, every time. The trap is scripts that read well and speak badly · read every draft out loud before it’s approved.

**Prerequisites:** Hook Writing, Performance Mining

**Automation ladder**

- manual: You wing it to camera and hope take four has an ending.
- assisted: Full scripts drafted in the house voice from a hook and an angle · structure, beats, CTA · human edits before filming.
- autonomous: Every idea in the queue arrives scripted in two or three variations; performance data tunes the structure monthly.

**Linked skill files**

- Scriptwriter: `skills/scriptwriter.md`

#### Job: Caption Writing

Platform-correct captions with CTA placement rules baked in.

- Level: autonomous
- Capabilities: caption-writer, cta-placer
- Tools: None listed

**Replaces**

The 20 minutes per post that happens after the creative energy is spent · which is why most captions are an afterthought stapled to good content.

**Notes**

Encode the platform rules once as hard constraints · where the CTA sits, how many hashtags, how the first line truncates in feed · and the agent never violates them at 11pm the way a tired human does. The first line is a second hook: it shows before the tap. The trap is one caption pasted everywhere; a LinkedIn caption and a TikTok caption share an idea, not a structure.

**Prerequisites:** Hook Writing

**Automation ladder**

- manual: Emoji, three hashtags, post, regret.
- assisted: Platform-correct captions drafted per asset · CTA placement, hashtag limits, and line-break rules baked in · human approves.
- autonomous: Every queued post carries its caption variants; the rules update themselves as platforms change what works.

**Linked skill files**

- Social Copywriter: `skills/social-copywriter.md`

#### Job: Carousel Production

Design and export branded carousel slides.

- Level: autonomous
- Capabilities: carousel-builder, slide-exporter
- Tools: None listed

**Replaces**

$100–300 per carousel from a designer with a 3-day turnaround, or 2–4 hours of founder time per set fighting a drag-and-drop tool.

**Notes**

Build the design system once as code · templates, type scale, spacing, logo placement · then every carousel is a content problem, not a design problem. Slide one is a hook with the same stakes as a video hook; slides two through six earn the swipe one at a time. The trap is redesigning per carousel: lock the system and let consistency become the brand.

**Prerequisites:** Hook Writing

**Automation ladder**

- manual: Canva, ten slides, fonts drifting by slide six.
- assisted: Slides generated from a locked design system · copy in, branded PNGs out · human reviews the set before export.
- autonomous: Winning ideas trigger carousel drafts automatically; the export pipeline renders and queues them for publishing.

**Linked skill files**

- Carousel Designer: `skills/carousel-designer.md`

#### Job: Video Production

Programmatic video · overlays, captions, motion graphics on recordings.

- Level: autonomous
- Capabilities: reel-compositor, caption-syncer, overlay-animator
- Tools: Remotion

**Replaces**

$50–150 per reel to an editor with a 2–5 day turnaround · and the turnaround is the real cost, because trend content dies waiting in someone’s queue.

**Notes**

Programmatic video means edits defined in code, which means every solved problem · caption styling, transitions, overlay timing · becomes a reusable primitive instead of a memory. Build the primitives library first; the second video costs a tenth of the first. The trap is treating each video as a fresh project: copy the last working template, always.

**Prerequisites:** Script Writing

**Automation ladder**

- manual: You learn a video editor’s timeline at midnight, once, badly.
- assisted: Recordings get overlays, captions, and motion graphics applied programmatically from a reusable component library; human reviews the render.
- autonomous: Drop a recording in a folder and a finished, captioned, on-brand edit comes out · variants included, queued for review.

**Linked skill files**

- Video Editor: `skills/video-editor.md`

#### Job: Image Generation

Brand-consistent images from reference libraries.

- Level: assisted
- Capabilities: brand-image-generator, character-consistency
- Tools: FAL

**Replaces**

Stock photos that look like stock photos, or $50–200/image from a designer for routine brand visuals.

**Notes**

The reference library is the moat: feed it your best existing visuals and identity shots so output stays unmistakably yours. Two skills below · brand imagery and consistent-character personal imagery.

**Automation ladder**

- manual: Canva at 11pm.
- assisted: Brand-consistent images generated from a reference library · your visual language, learned and reproduced.
- autonomous: Every post in the queue gets on-brand visual options generated alongside the copy.

**Linked skill files**

- Brand Visual Designer: `skills/brand-visual-designer.md`
- Personal Brand Designer: `skills/personal-brand-designer.md`

#### Job: Thumbnail & Cover Design

Scroll-stopping thumbnails and covers tuned to earn the click.

- Level: assisted
- Capabilities: thumbnail-designer, cover-tester
- Tools: FAL

**Replaces**

The click you lose before anyone reads a word · most content dies on a weak thumbnail, not weak content.

**Notes**

The thumbnail is the ad for the content. The skill below produces scroll-stopping, on-brand covers and tests variants · pair it with Performance Mining so the winners teach the next batch.

**Prerequisites:** Image Generation

**Automation ladder**

- manual: You slap a frame from the video on it and hope.
- assisted: The agent generates thumbnail and cover variants tuned to the hook, in brand, ready to A/B.
- autonomous: Covers generate per post from the hook, with the winning patterns fed back from performance data.

**Linked skill files**

- Brand Visual Designer: `skills/brand-visual-designer.md`

#### Job: Ad Creative

Generate and iterate paid-ad variations · hooks, angles, formats.

- Level: assisted
- Capabilities: ad-variation-builder, angle-tester
- Tools: FAL

**Replaces**

The creative bottleneck on every paid account · one ad, no variations, fatiguing while you sleep.

**Notes**

Paid acquisition is won on creative volume, not bid tweaks. The skill below spins winning ads into new angles and formats · the same engine behind the Meta Ads dashboard’s creative-fatigue flags.

**Prerequisites:** Performance Mining

**Automation ladder**

- manual: A designer makes one ad a week; nothing gets tested.
- assisted: The agent generates hook, angle, and format variations off your winners · ready to launch as a test batch.
- autonomous: Fresh creative is generated and queued continuously, rotating before fatigue sets in, learning from spend.

**Linked skill files**

- Creative Strategist: `skills/creative-strategist.md`

#### Job: Landing Page Copy

Conversion copy for the whole page · hero, proof, offer, FAQ, CTA.

- Level: autonomous
- Capabilities: page-copywriter, offer-framer
- Tools: None listed

**Replaces**

A $2–5k copywriter per page, or worse · the founder writing feature lists nobody converts on.

**Notes**

Conversion copy is a structure, not a talent · hook, problem in their words, mechanism, proof, offer with risk reversal, objection FAQ, one CTA. The skill below writes the whole page section by section from your offer and ICP.

**Prerequisites:** Company Knowledge Base

**Automation ladder**

- manual: You write the page yourself, lead with features, and wonder why it doesn’t convert.
- assisted: The agent writes the full page in the proven order · hero promise, problem, mechanism, proof, offer, FAQ, CTA · in your voice.
- autonomous: Pages generate per offer and per campaign, with variants written for testing.

**Linked skill files**

- Conversion Copywriter: `skills/conversion-copywriter.md`

#### Job: Deck Production

Webinar and talk decks in the brand design system.

- Level: autonomous
- Capabilities: deck-builder, slide-templater
- Tools: None listed

**Replaces**

6–10 hours per webinar deck, or $500–1,500 to a designer who needs the content anyway · meaning you do the thinking twice.

**Notes**

Lock three or four master slide patterns · cover, content, proof, CTA · and every deck becomes assembly, not design. The deck is a sales asset wearing an education costume: proof slides and the close deserve the most iterations. The trap is template drift · one deck built off-system and every deck after it inherits the mutation.

**Prerequisites:** Company Knowledge Base

**Automation ladder**

- manual: Last quarter’s deck with new dates and one new chart.
- assisted: Talk outline in, branded deck out · house design system, real assets, consistent typography · human edits the narrative.
- autonomous: Every booked talk or webinar triggers a deck draft from the topic and the knowledge base; you walk in and rehearse instead of build.

**Linked skill files**

- Presentation Designer: `skills/presentation-designer.md`

### Function: Repurposing

#### Job: Cross-Platform Adaptation

One idea → native formats for every platform.

- Level: autonomous
- Capabilities: format-adapter, platform-translator
- Tools: None listed

**Replaces**

The 5× content multiplier everyone talks about and almost nobody operationalizes, because manual repurposing is genuinely tedious.

**Notes**

Native beats syndicated · each platform gets its own structure, not a resize. The skill below runs one idea through research and out to seven formats.

**Prerequisites:** Hook Writing

**Automation ladder**

- manual: Same caption pasted to four apps.
- assisted: One idea → native formats for every platform: LinkedIn post, X thread, newsletter section, video script, short-form scripts.
- autonomous: Every flagship piece automatically fans out to the full format set, queued for review.

**Linked skill files**

- Content Repurposing Manager: `skills/content-repurposing-manager.md`

#### Job: Clip Extraction

Cut long recordings into short-form clips worth posting.

- Level: assisted
- Capabilities: clip-finder, highlight-extractor
- Tools: Deepgram

**Replaces**

$1–2k/month clipping agencies, or an editor billing hours to watch footage. A one-hour webinar holds 5–10 postable clips that mostly die unwatched in a recordings folder.

**Notes**

Select from the transcript, not the timeline · reading an hour takes four minutes, watching it takes an hour. A clip earns posting only if it works with zero context: a complete claim, a complete story, or a complete answer. The trap is volume worship · ten mediocre clips from one recording trains the audience to skip you; ship the two that stand alone.

**Prerequisites:** Video Production

**Automation ladder**

- manual: You meant to clip the webinar. That was three webinars ago.
- assisted: Long recordings transcribed and scanned for standalone moments · strong claims, stories, answers · cut and captioned for review.
- autonomous: Every long recording that lands triggers extraction; ranked clips arrive captioned and queued, no one asked.

**Linked skill files**

- Video Editor: `skills/video-editor.md`

#### Job: Lead-Magnet Builds

Turn content themes into gated guides and landing pages.

- Level: autonomous
- Capabilities: guide-builder, gated-page-generator
- Tools: None listed

**Replaces**

The “we should make a guide” task that stays on the roadmap for two quarters.

**Notes**

Build magnets from proven demand only · the reel that popped tells you exactly what people want gated. Wire delivery to Comment-CTA Fulfillment in the Deals tree and the loop closes itself.

**Prerequisites:** Performance Mining

**Automation ladder**

- manual: A PDF made once, promoted twice, forgotten.
- assisted: Content themes that already performed become gated guides with landing pages, built end-to-end in a session.
- autonomous: Top-performing topics trigger draft lead magnets automatically; the comment-CTA layer delivers them.

**Linked skill files**

- Lead Magnet Producer: `skills/lead-magnet-producer.md`

### Function: Distribution

#### Job: Publishing

Schedule and post across platforms via API.

- Level: assisted
- Capabilities: post-scheduler, api-publisher
- Tools: Zernio

**Human**

A human eyeballs account, caption, and asset before each scheduled batch goes live. A wrong-account post is a screenshot forever · the two-minute check is non-negotiable.

**Replaces**

The daily posting chore that survives exactly until the first busy week. Inconsistency is the silent killer of every content flywheel · the algorithm forgets faster than you recover.

**Notes**

Post via API, not via browser automation · platform APIs are the stable path and the account-safe one. Build the queue with a visible runway: knowing you have nine days of approved content banked changes how you create. The trap is going full autopilot on day one; run queue-plus-approval for a month before you let anything ship unseen.

**Prerequisites:** Caption Writing

**Automation ladder**

- manual: Phone out, app open, paste, post, repeat per platform · when you remember.
- assisted: Approved content scheduled and posted across platforms via API; the queue shows what ships when, and gaps get flagged.
- autonomous: The pipeline runs creation → caption → queue → post on cadence; a human curates the queue, the system never misses a day.

**Linked skill files**

- Publishing Manager: `skills/publishing-manager.md`

#### Job: Newsletter & Broadcast

Design and send the weekly email in the brand system.

- Level: autonomous
- Capabilities: newsletter-builder, broadcast-sender
- Tools: Beehiiv, Resend

**Replaces**

3–5 hours/week of writing and formatting, or $500–1k/month to a ghostwriter · and the issue that quietly skips a week, then two, then the list goes cold.

**Notes**

Build the HTML template once in the brand system and never design an issue again · the weekly job becomes pure editorial. Harvest, don’t write: the newsletter should be assembled from content and work that already exists, with one original take on top. The trap is treating it as a broadcast instead of an asset · the list is the only audience you own; everything else is rented.

**Prerequisites:** Cross-Platform Adaptation

**Automation ladder**

- manual: Sunday night, blank editor, “what happened this week?”
- assisted: The week’s content and wins harvested into a designed issue in the brand template · human edits the takes, hits send.
- autonomous: The issue assembles itself on schedule from the week’s shipped work; you review Thursday, it sends Friday, every week, forever.

**Linked skill files**

- Newsletter Editor: `skills/newsletter-editor.md`

#### Job: SEO & GEO

Make the site legible to search engines and LLMs.

- Level: autonomous
- Capabilities: schema-marker, llms-txt-maintainer, sitemap-builder
- Tools: None listed

**Replaces**

$1–3k/month SEO retainers that mostly produce reports · or being invisible to the growing share of buyers who ask an LLM for a recommendation instead of searching.

**Notes**

GEO · being legible and citable to LLMs · is the part most sites have done nothing about, and it is mostly the same hygiene as SEO done properly: clear structure, structured data, plain statements of what you do and for whom. Do the foundation pass in one session: sitemap, robots, schema markup, llms.txt. The trap is chasing keywords before fixing legibility · a site a machine can’t parse loses on every query, optimized or not.

**Prerequisites:** Company Knowledge Base

**Automation ladder**

- manual: Someone installed an SEO plugin in 2023 and the site has been “optimized” ever since.
- assisted: Sitemap, structured data, metadata, and an llms.txt generated and maintained from the actual site content; gaps audited on demand.
- autonomous: Every new page ships pre-optimized for both crawlers and LLMs; rankings and AI-citation checks run on schedule and flag drift.

**Linked skill files**

- SEO Engineer: `skills/seo-engineer.md`

#### Job: OG & Share Surface

Every page ships with share-ready open-graph imagery.

- Level: autonomous
- Capabilities: og-image-generator
- Tools: None listed

**Replaces**

Links that unfurl as a blank gray rectangle in every DM, Slack, and LinkedIn share. Each naked link is a small credibility tax, paid on the exact surface where your content travels.

**Notes**

Generate OG images programmatically from a template route, not as design files · the title, page type, and brand frame compose at request time and new content is covered forever. Test the unfurl where it actually happens: a messaging app, a LinkedIn draft, an X compose box. The trap is one generic image site-wide; per-page cards with the real title get measurably more clicks because they read as content, not as a logo.

**Prerequisites:** SEO & GEO

**Automation ladder**

- manual: One static og-image uploaded at launch, wrong dimensions, never updated.
- assisted: A templated OG image per page type · title pulled in, brand system applied · generated at build time.
- autonomous: Every page and post ships with its share card rendered automatically; new routes inherit the system with zero extra work.

**Linked skill files**

- SEO Engineer: `skills/seo-engineer.md`

### Function: Brand Deals

#### Job: Deal Scripting

Sponsored scripts in the proven format, per brand brief.

- Level: autonomous
- Capabilities: brand-script-writer, claim-fact-checker
- Tools: None listed

**Human**

Two approvals, both human: the sponsor signs off on claims, and the creator approves every line spoken under their name. Never let an agent invent a capability claim for someone else’s product · fact-check before it goes on camera.

**Replaces**

Days of back-and-forth per sponsored script, with revision cycles quietly eating the deal’s margin. A $5k brand deal at four revision rounds is a $2k brand deal.

**Notes**

Send three variations, not one · sponsors who choose between options approve faster than sponsors asked to judge a single take. Anchor every script in a format your own data says works; the brand bought your audience, and your audience came for your format. The trap is letting the brief flatten the voice · a sponsored post that sounds like an ad performs like an ad, which serves nobody who paid for it.

**Prerequisites:** Script Writing, Performance Mining

**Automation ladder**

- manual: The brand sends a brief; you procrastinate, then write something neither of you loves.
- assisted: Brief in, three script variations out · proven format, real product claims checked, creator voice intact · sponsor picks one.
- autonomous: Signed deals trigger scripted variations automatically from the brief plus your top-performing formats; humans handle approval, not drafting.

**Linked skill files**

- Brand Deal Producer: `skills/brand-deal-producer.md`

#### Job: Approval Docs

Brand-safe formatted docs for sponsor sign-off.

- Level: autonomous
- Capabilities: approval-doc-generator
- Tools: Google Docs

**Replaces**

Script versions scattered across email threads and chat, plus 30–60 minutes per deal of formatting · multiplied by every revision round the mess itself creates.

**Notes**

One canonical doc per deal, edits in the doc, never in chat · the entire job is killing version ambiguity. A consistent naming convention and a clean format do quiet sales work too: sponsors judge professionalism from the artifacts, and tidy paperwork earns the second deal. The trap is over-sharing · scope access to the single file, not your whole drive.

**Prerequisites:** Deal Scripting

**Automation ladder**

- manual: Version 3 is in email, version 4 is in WhatsApp, the brand approved version 2.
- assisted: The locked script lands in a clean, brand-safe formatted doc · consistent naming, proper structure · ready for sponsor sign-off.
- autonomous: Final scripts generate their approval doc automatically, filed per brand, shared with minimum-scope access; revisions update one canonical document.

**Linked skill files**

- Brand Deal Producer: `skills/brand-deal-producer.md`

## Department: Operations

Where promises become delivery · onboarding a new client, wiring the systems, testing the work, and reporting status before anyone has to ask. Delivery dies in week one or it doesn’t. This department makes the first week feel like the tenth, catches the broken batch before the client sees it, and sends the Friday update that keeps trust alive through the quiet stretches.

### Function: Onboarding

#### Job: Kickoff Pack

Welcome email, access checklist, and project scaffold the day a deal closes.

- Level: autonomous
- Capabilities: kickoff-generator, access-checklister
- Tools: None listed

**Human**

The delivery lead sends the welcome email under their own name and owns the kickoff date it promises. The pack assembles itself; the commitment is human.

**Replaces**

The 3–5 day dead zone between signature and first real work · the window where buyer’s remorse lives. Plus 2–3 hours of assembling the same welcome email, checklist, and folder structure for every new client.

**Notes**

Speed here sets the tone for the whole engagement: a kickoff pack landing within hours of signing tells the client they bought from operators. Template the pack once · welcome email, what-happens-next timeline, access checklist · and personalize from the deal record, not from scratch. The trap is over-stuffing it: one email, one checklist, one clear next step. Anything more gets ignored.

**Prerequisites:** Agreement Drafting

**Automation ladder**

- manual: The client signs, then hears nothing until someone finds a spare afternoon.
- assisted: Deal closes → welcome email, access checklist, and project folder drafted from the deal record; the delivery lead reviews and sends same-day.
- autonomous: The signed agreement triggers the full pack automatically · email out, checklist live, scaffold built · before the celebratory Slack message.

**Linked skill files**

- Client Onboarding Manager: `skills/client-onboarding-manager.md`

#### Job: Access Collection

Chase and verify every credential and API key needed to build.

- Level: assisted
- Capabilities: credential-chaser, access-verifier
- Tools: None listed

**Human**

Credentials are handled by a named human into a proper secrets store · never pasted into chat, never stored in the agent’s context. The agent chases and verifies; it does not hold the keys.

**Replaces**

The 1–2 weeks of “still waiting on that API key” that delays every build start · the single most common cause of week-one slippage, and it bills nobody.

**Notes**

Verification is the half everyone skips: a key that arrives is not a key that works · wrong scopes, expired tokens, and sandbox-only credentials surface mid-build if you don’t test on receipt. Derive the checklist from the actual scoped integrations, not a generic template. Trap to avoid: marking items complete when they arrive instead of when they verify.

**Prerequisites:** Kickoff Pack

**Automation ladder**

- manual: You email asking for credentials, they send half, you notice the gap mid-build.
- assisted: A checklist generated per project from the scoped stack; the agent chases outstanding items on a schedule and verifies each credential actually works on receipt.
- autonomous: Every received key is test-called immediately, gaps re-chased automatically, and the build gets a green light only when the full set verifies.

**Linked skill files**

- Client Onboarding Manager: `skills/client-onboarding-manager.md`

#### Job: Project Scaffolding

Stand up the repo, context files, and plan for a new engagement.

- Level: autonomous
- Capabilities: repo-scaffolder, context-writer
- Tools: None listed

**Replaces**

The half-day of setup before any real work starts · repo, context files, folder conventions, plan doc · done slightly differently every time, so no two projects are navigable the same way.

**Notes**

The real product here is consistency: when every engagement has the same skeleton, any agent or human can drop into any project and orient in one read. Pull the initial context from the deal record and discovery transcripts · the sales process already captured most of it; re-asking the client is an admission you don’t talk to yourself. Keep the template minimal: scaffolds that demand twenty files get abandoned by file six.

**Prerequisites:** Kickoff Pack, Company Knowledge Base

**Automation ladder**

- manual: Every project starts as an empty folder and someone’s memory of how the last one was structured.
- assisted: One command stands up the repo, client context file, plan doc, and folder conventions from the house template; a human fills in the engagement specifics.
- autonomous: The closed deal triggers the scaffold automatically · pre-populated with everything the sales process already learned about the client.

**Linked skill files**

- Client Onboarding Manager: `skills/client-onboarding-manager.md`

### Function: Build Ops

#### Job: Document Extraction

High-volume structured extraction from client documents.

- Level: autonomous
- Capabilities: extraction-pipeline, schema-mapper, accuracy-benchmarker
- Tools: None listed

**Human**

Humans review the low-confidence queue and own the gold-standard set. The machine earns autonomy field by field, measured against it.

**Replaces**

Teams of people reading documents and retyping them into systems. At volume this is entire payrolls · the densest ROI node on this map for document-heavy businesses.

**Notes**

Benchmark before you celebrate: build a 50-document gold-standard set and measure field-level accuracy against it. The review-queue pattern (auto-accept above threshold, human below) gets you production-safe long before the model is perfect. Probation services, insurance, compliance · whole verticals run on this node.

**Prerequisites:** Company Knowledge Base

**Automation ladder**

- manual: Humans read, humans type, humans err.
- assisted: Documents → structured fields via an extraction pipeline, with confidence scores and human review on the low-confidence tail.
- autonomous: High-confidence extractions flow straight to the system of record; accuracy benchmarked continuously against a gold set.

**Linked skill files**

- Document Extraction Engineer: `skills/document-extraction-engineer.md`

#### Job: Integration Builds

Wire client systems together · CRMs, calendars, transcripts, payments.

- Level: autonomous
- Capabilities: api-integrator, webhook-wirer
- Tools: Inngest

**Replaces**

The core billable work of an automation practice · and the part where scope creeps silently. Done by hand, each integration is days of reading API docs, handling auth, and discovering the vendor’s documentation lied.

**Notes**

Build the pattern library deliberately: every integration you ship becomes a reusable template, and by the tenth project most builds are assembly, not invention. Always build against the client’s real data early · sandbox data hides the edge cases that blow up demos. The trap is skipping retry and failure handling because the happy path worked: integrations don’t fail in testing, they fail at 2am on day forty.

**Prerequisites:** Access Collection, Project Scaffolding

**Automation ladder**

- manual: A developer reads the API docs, writes the glue, and finds the undocumented rate limit in production.
- assisted: The agent writes the integration · auth, endpoints, error handling, retries · against verified credentials; a human reviews the code and runs it against real data.
- autonomous: Standard integrations (CRM, calendar, transcripts, payments) assemble from a proven pattern library; humans only touch the genuinely novel ones.

**Linked skill files**

- Integration Engineer: `skills/integration-engineer.md`

#### Job: Data Migration

Move and clean data between systems without losing or mangling a row.

- Level: assisted
- Capabilities: migration-runner, field-mapper, dedupe-validator
- Tools: Inngest

**Replaces**

The migration project that quotes at $5–20k and still loses rows · or the intern hand-copying records between two CRMs for a fortnight.

**Notes**

Migrations fail silently · a thousand rows in, nine hundred out, and nobody notices until a client does. The skill below maps, transforms, and reconciles with row-count validation so "did we lose anything" is answerable, not hoped.

**Prerequisites:** Integration Builds

**Automation ladder**

- manual: Someone exports a CSV, maps columns by hand, re-imports, and prays nothing broke.
- assisted: The agent maps the fields, transforms, dedupes, validates row counts both sides, and reports exactly what moved and what didn’t.
- autonomous: Ongoing syncs run on a schedule with reconciliation checks · drift gets flagged before it compounds.

**Linked skill files**

- Integration Engineer: `skills/integration-engineer.md`

#### Job: Portal Provisioning

Spin up client-scoped delivery portals with live status.

- Level: autonomous
- Capabilities: portal-provisioner, portal-theming
- Tools: None listed

**Replaces**

The “can you send me an update?” email and the status deck rebuilt before every check-in call · 2–3 hours/week per active client of pure performance theatre.

**Notes**

One template, strictly enforced · the value is that every client portal looks and works identically, so provisioning is minutes, not a design project. Give the client something to do in it (tick onboarding items, answer open questions) and it becomes a working surface instead of a brochure. The trap: a portal that lags reality is worse than no portal · don’t ship this without Portal Sync planned, or it becomes one more thing to manually update.

**Prerequisites:** Project Scaffolding

**Automation ladder**

- manual: Status lives in email threads and whatever the client remembers from the last call.
- assisted: A branded, client-scoped portal spun up from a template per engagement · roadmap, onboarding checklist, deliverables · updated by the team as work ships.
- autonomous: New engagements get a portal automatically, and the delivery system writes to it directly: the client watches progress happen instead of asking about it.

**Linked skill files**

- Client Portal Manager: `skills/client-portal-manager.md`

#### Job: QA & Verification

Verify every build against real data before the client sees it.

- Level: assisted
- Capabilities: output-verifier, regression-checker
- Tools: None listed

**Human**

A human signs off before anything is shown to a client · the agent runs the checks, but the name on the engagement owns the standard. QA sign-off is never delegated to the thing being QA’d.

**Replaces**

The bug the client finds before you do. Every defect that reaches a client costs more trust than ten caught internally · and rework eats 10–20% of delivery hours at firms that ship on vibes.

**Notes**

The standard is verify-before-done: a build is not finished when it works, it is finished when it has been shown to work against real data, edge cases included. Write the checklist per build type once and reuse it · extraction builds, integration builds, and portals each fail in characteristic ways. The trap is testing with clean sample data: the client’s real documents are uglier than anything you’d invent, and that ugliness is exactly what you’re being paid to handle.

**Prerequisites:** Integration Builds

**Automation ladder**

- manual: The developer who built it clicks through it once and declares victory.
- assisted: Every build runs against real client data through a verification checklist · edge cases, failure modes, output accuracy · with results logged before anything is demoed.
- autonomous: Verification runs on every change automatically; builds physically cannot reach the client-facing layer without a passing run on record.

**Linked skill files**

- QA Engineer: `skills/qa-engineer.md`

#### Job: Agent Evaluation

Test agent outputs against a benchmark before they touch real work.

- Level: assisted
- Capabilities: eval-harness, regression-checker
- Tools: None listed

**Replaces**

The blind trust that an agent still works after you changed its prompt · until a client catches the regression for you.

**Notes**

The moment you have agents doing real work, "is it still good after my change" becomes the question. This builds the eval harness · a benchmark set, a scoring rubric, and a regression gate · so quality is measured, not assumed.

**Prerequisites:** QA & Verification

**Automation ladder**

- manual: You eyeball a couple of outputs after a change and call it tested.
- assisted: The agent runs new outputs against a benchmark set and a rubric, scores them, and flags regressions before they ship.
- autonomous: Every prompt or model change triggers an eval run · nothing reaches production without passing the bar.

**Linked skill files**

- QA Engineer: `skills/qa-engineer.md`

### Function: Reliability

#### Job: Monitoring & Alerting

Watch every automation for failures and silent stalls · know before the client does.

- Level: assisted
- Capabilities: uptime-watcher, failure-alerter
- Tools: Inngest

**Replaces**

Finding out an automation died three days ago because a client asked where their report is.

**Notes**

Silent failure is the tax on running anything in production. The skill below watches your crons, jobs, and agents and tells you before the client does · the first job of the Reliability function.

**Prerequisites:** Integration Builds

**Automation ladder**

- manual: You notice something broke when the output stops showing up.
- assisted: The agent watches every automation for failed runs and silent stalls, and alerts the moment one goes down.
- autonomous: Health is monitored continuously across the stack · failures alert with context and a first-pass diagnosis attached.

**Linked skill files**

- Reliability Engineer: `skills/reliability-engineer.md`

#### Job: Cost & Usage Tracking

Token and API spend tracked against budget · no surprise bills.

- Level: autonomous
- Capabilities: spend-tracker, budget-guard
- Tools: None listed

**Replaces**

The surprise five-figure API bill · token spend nobody was watching until accounting flagged it.

**Notes**

Agents that loop, retry, or run on stale data burn money quietly. This tracks spend against a budget by source so a runaway job is a Tuesday-morning alert, not an end-of-month gut-punch.

**Prerequisites:** Monitoring & Alerting

**Automation ladder**

- manual: You check the provider dashboard when the invoice scares you.
- assisted: The agent tracks token and API spend against a monthly budget and flags the burn rate before you blow past it.
- autonomous: Spend is tracked per automation, attributed to the work, and capped · runaway usage triggers an alert and a throttle.

**Linked skill files**

- Reliability Engineer: `skills/reliability-engineer.md`

#### Job: Incident Response

When an automation breaks · triage, root-cause, fix, and write the note.

- Level: assisted
- Capabilities: incident-triager, rootcause-finder, postmortem-writer
- Tools: None listed

**Replaces**

The frantic hour of "what broke and why" every time an automation falls over · usually during a client deliverable.

**Notes**

Reliability is a loop, not a heroic scramble · detect, triage, root-cause, fix, write it down so it can’t happen twice. The skill below runs that runbook so an outage costs minutes, not a morning.

**Prerequisites:** Monitoring & Alerting

**Automation ladder**

- manual: Everything stops while someone digs through logs trying to reproduce the failure.
- assisted: The agent triages the alert, reproduces the failure, finds the likely root cause, proposes the fix, and drafts the incident note.
- autonomous: Known failure modes self-heal · the rest escalate with a full diagnosis and a postmortem already written.

**Linked skill files**

- Reliability Engineer: `skills/reliability-engineer.md`

### Function: Client Comms

#### Job: Status Updates

Clients see progress without asking for it.

- Level: autonomous
- Capabilities: status-poster, milestone-notifier
- Tools: None listed

**Human**

Good news can ship on autopilot; bad news cannot. A human delivers every delay or problem personally before it appears in writing.

**Replaces**

The update email that takes 30 minutes to write per client per week · or doesn’t get written, which is how clients conclude nothing is happening. Silence reads as stalling even when the work is flying.

**Notes**

Cadence beats content: a short update every week outperforms a brilliant one monthly, because the rhythm itself is the reassurance. Generate from real activity · context files, commits, shipped deliverables · never from a human summarizing their week into a form, or the system dies in a fortnight. The trap: never let the automated update be the channel for bad news. Delays and problems get a human call first, the written update second.

**Prerequisites:** Context Maintenance

**Automation ladder**

- manual: The client asks how it’s going; someone reconstructs the week from memory and Slack.
- assisted: A weekly update drafts itself from the context file and shipped work · what moved, what’s next, what’s blocked · and the delivery lead edits and sends.
- autonomous: Updates publish on schedule to email and the portal, generated from actual delivery activity, with the human only stepping in when there’s bad news to frame.

**Linked skill files**

- Delivery Status Reporter: `skills/delivery-status-reporter.md`

#### Job: Meeting Follow-Ups

Client call transcripts → action items → assigned and tracked.

- Level: autonomous
- Capabilities: followup-processor, action-assigner
- Tools: Fireflies

**Human**

The delivery lead confirms owners and deadlines before the recap goes to the client · commitments are made by people.

**Replaces**

Action items agreed on a client call that evaporate by Thursday · the quiet killer of delivery trust.

**Notes**

Clients don’t churn over outcomes, they churn over feeling forgotten. Same-day recaps with named owners are the cheapest retention system ever built.

**Prerequisites:** Call Capture

**Automation ladder**

- manual: Whoever remembered, does it. Maybe.
- assisted: Client transcripts → extracted action items, owners, deadlines · drafted into the recap that goes out same-day.
- autonomous: Items assign themselves into the task system and chase their owners; the client recap sends on schedule.

**Linked skill files**

- Follow-Up Coordinator: `skills/followup-coordinator.md`

#### Job: Portal Sync

Session summaries and deliverables flow into the client portal automatically.

- Level: autonomous
- Capabilities: portal-syncer, deliverable-publisher
- Tools: None listed

**Replaces**

The gap between work done and work visible. Without it, the portal decays into a brochure within two weeks and you’re back to manually updating two places · the work and the story about the work.

**Notes**

This is the node that makes Portal Provisioning honest: the portal is only worth what it reflects, and manual updating is the failure mode that kills every client-facing dashboard ever built. Hook the sync to the natural end of work · session close, deliverable shipped, milestone hit · not to a separate update ritual. The trap is syncing raw internals: the client should see progress in their language, not your commit log.

**Prerequisites:** Portal Provisioning, Context Maintenance

**Automation ladder**

- manual: Someone remembers to update the portal after shipping. They do not remember.
- assisted: End-of-session summaries and finished deliverables drafted into portal updates; a human approves what the client sees.
- autonomous: Every working session writes its summary to the portal automatically · the client’s view and reality never drift apart.

**Linked skill files**

- Client Portal Manager: `skills/client-portal-manager.md`

### Function: Knowledge

#### Job: Transcript Processing

Every meeting becomes searchable, structured context.

- Level: autonomous
- Capabilities: transcript-structurer, entity-extractor
- Tools: None listed

**Replaces**

Meetings that evaporate. Every client call contains decisions, commitments, and context worth money · and in most firms it lives nowhere but two people’s fading memory of a Tuesday.

**Notes**

Call Capture records the meeting; this node makes it useful. Process into a consistent shape · decisions, commitments, facts learned, open threads · and file per client, because a searchable corpus of every client conversation is the raw material for half the Operations tree. The trap is storing raw transcripts and calling it done: an unstructured transcript is a haystack, and nobody queries haystacks.

**Prerequisites:** Call Capture

**Automation ladder**

- manual: Someone re-listens to the recording to find that one thing the client said. They never do.
- assisted: Every transcript processed into structure · decisions, action items, key facts, open questions · and filed against the right client.
- autonomous: Transcripts flow from the notetaker into structured, searchable context automatically; every other agent on this map reads from the result.

**Linked skill files**

- Meeting Intelligence Engineer: `skills/meeting-intelligence-engineer.md`

#### Job: Context Maintenance

Per-client context files stay current as work happens.

- Level: autonomous
- Capabilities: context-updater, memory-writer
- Tools: None listed

**Replaces**

The “wait, what’s the latest with this client?” tax every time anyone touches an account.

**Notes**

This IS the knowledge base doctrine in practice · one living file per client that everything reads and writes. Start the convention before you automate it: the file format matters more than the tooling.

**Prerequisites:** Call Capture

**Automation ladder**

- manual: Context lives in one person’s head and a thousand Slack threads.
- assisted: Per-client context files updated as work happens · calls, decisions, open items, current state.
- autonomous: Every transcript, email, and deliverable updates the file automatically; any agent or human reads one page and is current.

**Linked skill files**

- Node Zero · knowledge base builder: `skills/knowledge-base.md`

#### Job: SOP Generation

Turn delivered work into reusable playbooks.

- Level: manual
- Capabilities: sop-writer, playbook-extractor
- Tools: None listed

**Replaces**

The expertise that walks out the door with whoever did the work. Every delivered project contains a repeatable playbook · and without this node, you rebuild it from scratch the next time, at full cost, forever.

**Notes**

Write SOPs from evidence, not memory · the context files and transcripts record what actually happened, including the failure modes a human would forget to mention. The second delivery of any service type is the moment to extract the playbook: once is an event, twice is a pattern. The trap is writing aspirational SOPs describing how work should happen instead of how it demonstrably did · those get ignored by everyone, including their author.

**Prerequisites:** Context Maintenance, Company Knowledge Base

**Automation ladder**

- manual: The process lives in the head of whoever did it last. Documentation is a thing you’ll do when things calm down.
- assisted: After a project ships, the agent drafts the playbook from the actual work · context files, transcripts, what was built · and a human edits it into the canonical version.
- autonomous: Repeated work patterns get flagged and drafted into SOPs automatically; the playbook library grows as a byproduct of delivery.

**Linked skill files**

- Playbook Writer: `skills/playbook-writer.md`

#### Job: Handoff Docs

Clean documentation when a system ships to the client.

- Level: assisted
- Capabilities: handoff-writer, runbook-generator
- Tools: None listed

**Replaces**

The post-handoff support tail: every undocumented system generates months of “quick questions” that are really unpaid retainer work. Bad handoffs also quietly cap your referrals · nobody recommends a system they can’t operate.

**Notes**

Write for the person who will actually operate the system · usually a non-technical client-side owner, not a developer. Three layers cover it: what this is, how to use it day-to-day, and what to do when something looks wrong. Generate from the real build, not the proposal · scope drifted, and docs describing the system you planned rather than the one you shipped are worse than nothing. The trap is treating this as the last task: docs written in the final hour before handoff are the ones that generate the support tail.

**Prerequisites:** QA & Verification

**Automation ladder**

- manual: The client gets a Loom recorded in one take and a promise to “ping me if anything breaks.”
- assisted: Documentation drafted from the build itself · what it does, how to operate it, what to do when it misbehaves · and the builder reviews for accuracy before delivery.
- autonomous: Docs generate and update alongside the build; by ship day the handoff pack already exists and matches what was actually delivered.

**Linked skill files**

- Playbook Writer: `skills/playbook-writer.md`

## Department: Intelligence

The floor that makes everyone else sharper · company dossiers before every call, the trends worth filming, the competitors you can’t afford to be surprised by. Research is cheap and being wrong is expensive. This department turns two-day digging jobs into twenty-minute briefs, so no one upstairs ever walks into a room guessing.

### Function: Companies

#### Job: Company Deep-Dive

Financials, growth signals, org structure, strategic posture.

- Level: autonomous
- Capabilities: company-profiler, signal-collector
- Tools: Exa, Firecrawl

**Replaces**

A junior analyst day ($300–500 equivalent) per company researched properly · so it only happens for deals already in motion, when it should happen before.

**Notes**

The skill below scores fit, not just facts · the output is “should we pursue, and with what angle,” not a data dump.

**Automation ladder**

- manual: Their website, their LinkedIn, your impression.
- assisted: Financials, growth signals, org structure, and strategic posture compiled into a scored profile on demand.
- autonomous: Target accounts re-profile on triggers · funding, leadership changes, hiring spikes · and alert the pipeline.

**Linked skill files**

- Company Research Analyst: `skills/company-research-analyst.md`

#### Job: Tech-Stack Detection

What a target company runs, and where the gaps are.

- Level: autonomous
- Capabilities: stack-detector, gap-analyzer
- Tools: None listed

**Replaces**

Pitching an integration to a company that can’t run it · or missing the account whose stack is screaming for what you sell. Manual stack-checking is 15–20 minutes per company across detection tools, job posts, and page source, so it happens for almost none of them.

**Notes**

The gap is the product · “they run X without Y” is a campaign angle, not trivia. Cross-check detection tools against job postings and case studies; companies announce their stack every time they hire for it. Feeds Account Enrichment in Sales directly: enrichment is the bulk pass, this is the technical lens on it.

**Prerequisites:** ICP Definition

**Automation ladder**

- manual: View-source on their homepage and a guess.
- assisted: Stack detected per target · tools, platforms, recent migrations · with the gaps mapped against what you sell.
- autonomous: Every account in the target list carries a live stack profile; a stack change that matches your wedge triggers an alert to the pipeline.

**Linked skill files**

- Company Research Analyst: `skills/company-research-analyst.md`

#### Job: Funding & Financials Lookup

Rounds, investors, revenue estimates, filings · who just got budget.

- Level: autonomous
- Capabilities: funding-tracker, financials-reader
- Tools: Exa

**Replaces**

The 30-minute dig through Crunchbase, news, and filings to answer "do they actually have budget" · done for every account, by hand.

**Notes**

The single best signal of "can they buy" is "did they just get money." This pulls funding, investors, and financial estimates so outreach lands where the budget actually is. Pairs with Account Monitoring to catch the raise the day it happens.

**Prerequisites:** Company Knowledge Base

**Automation ladder**

- manual: Someone Googles "[company] funding" and guesses at revenue.
- assisted: The agent pulls rounds, investors, revenue estimates, and recent filings into one clean read on a target’s buying power.
- autonomous: Every account in the pipeline carries a current financial read · refreshed when something changes.

**Linked skill files**

- Company Research Analyst: `skills/company-research-analyst.md`

#### Job: Buying-Committee Mapping

Who actually decides · economic buyer, champion, blockers, their roles.

- Level: assisted
- Capabilities: committee-mapper, role-classifier
- Tools: None listed

**Human**

A human runs the deal · this draws the board so they know who to win and in what order. Enterprise deals are lost to unmapped committees more than to bad pitches.

**Replaces**

The deals that stall because you were selling to the wrong person · no map of who actually signs.

**Notes**

Most B2B deals have 5–7 people involved and one of them quietly kills it. The skill below identifies the committee, their roles, and the concern each one needs answered.

**Prerequisites:** Company Deep-Dive

**Automation ladder**

- manual: You talk to one contact and hope they’re the decision-maker.
- assisted: The agent maps the committee · economic buyer, champion, blockers, influencers · with each person’s role and likely concern.
- autonomous: The map builds from the org and updates as new contacts enter the deal.

**Linked skill files**

- Relationship Mapper: `skills/relationship-mapper.md`

### Function: People

#### Job: Person Research

Background, content trail, interests, mutual ground for any contact.

- Level: autonomous
- Capabilities: person-profiler, content-trail-scanner
- Tools: None listed

**Replaces**

Walking into rooms not knowing who you’re talking to.

**Notes**

Same engine as Personalization Research in Sales · deployed here for relationships rather than sequences: partners, hires, investors, podcast guests.

**Automation ladder**

- manual: A LinkedIn skim.
- assisted: Background, content trail, interests, and mutual ground compiled per person, with personalization hooks ranked.
- autonomous: Every new contact in the CRM gets a profile automatically; briefs consume them.

**Linked skill files**

- Prospect Research Analyst: `skills/prospect-research-analyst.md`

#### Job: Network Mapping

Who knows whom · paths into a target account.

- Level: manual
- Capabilities: connection-mapper
- Tools: None listed

**Human**

The map is AI’s; the ask is yours. Spending relationship capital · who to ask, for what, when · is judgment no agent should exercise, because the cost of a clumsy ask lands on a human relationship.

**Replaces**

Cold outreach to accounts where a warm path already existed. A warm intro converts at multiples of cold · and most founders can’t name their second-degree reach into any given target.

**Notes**

Your own data is the graph · CRM contacts, meeting attendees, email threads · long before any external tool. Build the convention of logging who-knows-whom in the knowledge base and the map compounds. Rank paths by real interaction recency, not connection count: a coffee last month beats a connection from 2019.

**Prerequisites:** Person Research, Company Knowledge Base

**Automation ladder**

- manual: Scrolling mutual connections and hoping a name rings a bell.
- assisted: Paths into a target account mapped from your CRM, call history, and public graphs · ranked by strength, with a drafted intro ask per path.
- autonomous: Every new target account arrives with its warm-path map attached; relationship data refreshes as calls and emails accumulate.

**Linked skill files**

- Relationship Mapper: `skills/relationship-mapper.md`

#### Job: Warm-Path Finding

The shortest real intro path into a target account · who can connect you.

- Level: assisted
- Capabilities: path-finder, intro-drafter
- Tools: None listed

**Replaces**

The cold open you didn’t need to send · a warm intro path existed and nobody looked for it.

**Notes**

A warm intro converts many times better than a cold one and most teams never check whether they have one. This finds the path and writes the intro ask · the difference between "who are you" and "happy to chat, [mutual] speaks highly".

**Prerequisites:** Network Mapping

**Automation ladder**

- manual: You cold-email an account you actually have two mutual connections into.
- assisted: The agent finds the shortest real path into a target · who in your network can make the intro · and drafts the ask.
- autonomous: Every target account is checked for a warm path before any cold outreach is attempted.

**Linked skill files**

- Relationship Mapper: `skills/relationship-mapper.md`

### Function: Markets

#### Job: Competitor Teardown

Pricing, positioning, strengths, weaknesses, exploitable gaps.

- Level: autonomous
- Capabilities: competitor-teardown, positioning-mapper
- Tools: None listed

**Replaces**

Competing on guesswork. Most firms can’t articulate a competitor’s pricing or positioning beyond adjectives.

**Notes**

The exploitable-gaps section is the deliverable · everything else is context. The skill below structures the attack: where they’re weak, where you’re strong, what to say in-market.

**Automation ladder**

- manual: You visited their pricing page once.
- assisted: Full teardown on demand: pricing, positioning, strengths, weaknesses, exploitable gaps · cited.
- autonomous: Tracked competitors re-tear quarterly; material changes (pricing, packaging, positioning) trigger alerts.

**Linked skill files**

- Competitive Intelligence Analyst: `skills/competitive-intelligence-analyst.md`

#### Job: Vertical Analysis

Is this vertical worth entering · demand, budgets, buying behavior.

- Level: autonomous
- Capabilities: vertical-analyzer, opportunity-scorer
- Tools: None listed

**Replaces**

Entering a vertical on one good anecdote · then discovering six months in that the budgets were never there. A proper market assessment runs $5–15k from a research firm, so most firms skip it and pay in wasted quarters instead.

**Notes**

Score verticals on pain frequency, budget authority, and reachability · not market size. A small vertical that buys fast beats a huge one that deliberates. The output should end in a decision and an entry play, not a landscape summary; if the verdict is go, it feeds ICP Definition in Sales as the next node.

**Prerequisites:** Company Deep-Dive, Competitor Teardown

**Automation ladder**

- manual: One client in the vertical went well, so the vertical must be good.
- assisted: Demand signals, budget reality, buying behavior, and competitive density compiled into a scored go/no-go per vertical.
- autonomous: A watchlist of candidate verticals re-scores on a schedule; a vertical crossing the threshold surfaces with the entry angle attached.

**Linked skill files**

- Vertical Analyst: `skills/vertical-analyst.md`

#### Job: Pricing Research

What the market charges, anchors, and packaging patterns.

- Level: autonomous
- Capabilities: pricing-scanner, packaging-analyzer
- Tools: None listed

**Replaces**

Pricing by mimicry or by nerve. Most firms set prices once, from two competitor pages and a feeling, and leave 20–40% of margin on the table for years.

**Notes**

Packaging patterns matter more than price points · how the market structures tiers, retainers, and anchors tells you how buyers expect to buy. Mine your own closed-won and closed-lost notes too: what prospects compared you against is pricing data nobody external can sell you. The trap is averaging · price against the segment you want, not the whole market.

**Prerequisites:** Competitor Teardown

**Automation ladder**

- manual: You checked what one competitor charges and went slightly under.
- assisted: Market rates, anchor points, and packaging patterns compiled per offer · what the market charges, how it bundles, where the ceiling actually sits.
- autonomous: Tracked competitors and market sources re-sweep on a schedule; pricing moves and packaging changes surface before your next proposal goes out.

**Linked skill files**

- Competitive Intelligence Analyst: `skills/competitive-intelligence-analyst.md`

#### Job: TAM / Market Sizing

How many companies actually fit · the real size of the prize.

- Level: autonomous
- Capabilities: tam-sizer, segment-counter
- Tools: Exa, Apollo

**Replaces**

The board-deck number pulled from thin air · or a $15k analyst engagement to size a market.

**Notes**

A real TAM is a count of qualifying companies, not a percentage of a McKinsey headline. The skill below sizes the prize bottom-up · how many real targets exist · so you know whether a vertical is worth the campaign before you build it.

**Prerequisites:** Vertical Analysis

**Automation ladder**

- manual: Someone multiplies two guesses and calls it the TAM.
- assisted: The agent counts the companies that actually fit the ICP in a market, by segment, with the assumptions shown.
- autonomous: Market size recalculates as the ICP sharpens and new segments are tested.

**Linked skill files**

- Market Mapper: `skills/market-mapper.md`

### Function: Monitoring

#### Job: Account Monitoring

Watch a target list for funding, hiring, leadership, and tech changes · ongoing.

- Level: assisted
- Capabilities: account-watcher, change-detector
- Tools: Exa, Firecrawl

**Replaces**

Finding out a target raised, hired a VP, or switched tools weeks late · from their newsletter, not your radar.

**Notes**

Timing beats personalization. The skill below watches your target accounts so the trigger event · the raise, the new hire, the migration · reaches you the morning it happens, while the window is open. The first job of the Monitoring function.

**Prerequisites:** Company Deep-Dive

**Automation ladder**

- manual: You re-research an account from scratch every time you remember it exists.
- assisted: The agent watches a target list for funding, hiring, leadership, and tech changes and surfaces what moved.
- autonomous: The watchlist runs continuously · every meaningful change on a target account lands as a scored signal.

**Linked skill files**

- Signal Monitoring Analyst: `skills/signal-monitoring-analyst.md`

#### Job: News & Mention Tracking

Every mention of your brand, competitors, and topics · as it lands.

- Level: assisted
- Capabilities: mention-tracker, news-watcher
- Tools: Exa

**Replaces**

A $200/mo media-monitoring tool, plus the gap it leaves on competitor and topic coverage.

**Notes**

You can’t respond to what you can’t see · a bad review, a competitor’s launch, a journalist’s question all have short fuses. This watches the conversation so you’re early, not surprised.

**Prerequisites:** Company Knowledge Base

**Automation ladder**

- manual: You find out you were mentioned when someone screenshots it to you.
- assisted: The agent tracks every mention of your brand, competitors, and key topics across news and social as it lands.
- autonomous: Mentions are tracked, classified by sentiment and importance, and the ones that matter get routed.

**Linked skill files**

- Signal Monitoring Analyst: `skills/signal-monitoring-analyst.md`

#### Job: Alert Routing

The signals that matter reach the right person · the noise gets filtered.

- Level: autonomous
- Capabilities: signal-scorer, alert-router
- Tools: None listed

**Replaces**

The monitoring that becomes noise · 200 alerts a day, all ignored within a week.

**Notes**

Monitoring without routing is just a louder inbox. The skill below scores and routes · the Series B of a core account goes to the founder with the intro path attached; the rest stays out of the way. This is what makes monitoring usable instead of exhausting.

**Prerequisites:** Account Monitoring

**Automation ladder**

- manual: Every signal pings the same channel and everyone tunes it out.
- assisted: The agent scores each signal for relevance and urgency and routes only what matters to the right person or channel.
- autonomous: Signals self-triage · high-value ones reach the right human with context, the rest log silently.

**Linked skill files**

- Signal Monitoring Analyst: `skills/signal-monitoring-analyst.md`

### Function: Synthesis

#### Job: Research Reports

Any question → structured, cited report with diagrams.

- Level: autonomous
- Capabilities: report-builder, diagram-generator, source-citer
- Tools: None listed

**Replaces**

$2–5k boutique research engagements, or the decision made without one.

**Notes**

Pair with Adversarial Verification before anything load-bearing: claims get attacked before they get believed.

**Automation ladder**

- manual: Twenty open tabs and a hunch.
- assisted: Any question → structured, cited report with diagrams, in an hour instead of a week.
- autonomous: Standing questions (market shifts, vertical signals) refresh on schedule and publish to the knowledge base.

**Linked skill files**

- Research Reporter: `skills/research-reporter.md`

#### Job: Data Visualization

Turn a pile of research into charts and diagrams that explain themselves.

- Level: autonomous
- Capabilities: chart-builder, diagram-generator
- Tools: None listed

**Replaces**

The research that lands as a wall of text nobody reads · or the analyst who spends an afternoon making one chart.

**Notes**

A finding that needs three paragraphs to land is a finding that won’t. The skill below renders research into the chart or diagram that makes it obvious · the visual layer on top of Research Reports.

**Prerequisites:** Research Reports

**Automation ladder**

- manual: Findings get pasted into a doc as paragraphs and bullet points.
- assisted: The agent turns the research into charts and diagrams that carry the point at a glance.
- autonomous: Every report ships with the right visual auto-generated from its data.

**Linked skill files**

- Business Data Analyst: `skills/business-data-analyst.md`

#### Job: Adversarial Verification

Claims get attacked before they get believed.

- Level: autonomous
- Capabilities: claim-verifier, source-cross-checker
- Tools: None listed

**Human**

A human owns what ships under the company’s name. Verification reduces the risk; it never transfers the accountability.

**Replaces**

The confident wrong number that makes it into the proposal, the deck, or the deal. One bad claim repeated to a client costs more credibility than a hundred verified ones earn.

**Notes**

Run it as a separate pass with a separate instruction · “find why this is wrong” · never as a self-check by the agent that wrote the claim; the author defending its own work is how errors survive. Grade claims, don’t just flag them: verified, plausible, contested, wrong. The trap is verifying everything · gate only what’s load-bearing, or the pipeline slows to the speed of paranoia.

**Prerequisites:** Research Reports

**Automation ladder**

- manual: It sounded right and the source looked legit.
- assisted: Every load-bearing claim gets attacked before it ships · counter-evidence hunted, sources checked for independence, confidence graded per claim.
- autonomous: Verification runs as a gate in the research pipeline: nothing publishes to the knowledge base above a stated confidence without surviving the attack pass.

**Linked skill files**

- Red Team Reviewer: `skills/red-team-reviewer.md`

## Department: Customer

Everything that happens after the sale · answering the repeat questions, watching for the accounts about to slip, and keeping the community alive. Churn rarely comes from bad work · it comes from silence. This department deflects the tickets that don’t need a human, spots the amber before it goes red, and renews accounts months early.

### Function: Support

#### Job: Ticket Triage

Classify, prioritize, and route every support request the moment it lands.

- Level: assisted
- Capabilities: ticket-classifier, priority-router, sla-watcher
- Tools: None listed

**Replaces**

The first hour of every support shift · a rep reading, labeling, and forwarding before anyone gets helped. Misrouted tickets bounce between owners 2–3 times and add a day per bounce.

**Notes**

Triage is the front door for the whole Support tree · Escalations and FAQ & Self-Serve both read its tags, so get the categories right before you automate the routing. Start with 5–7 categories from your last 200 tickets, not 30 invented ones. The trap: optimizing routing speed while the labels are wrong · bad tags at high speed just misroute faster.

**Prerequisites:** Company Knowledge Base

**Automation ladder**

- manual: One shared inbox, oldest unread first, urgency optional.
- assisted: Every request auto-tagged · topic, urgency, sentiment, owner · the moment it lands; a human confirms the routing on the gnarly ones.
- autonomous: Tickets route themselves to the right queue with context attached; priority reorders live as sentiment and SLA clocks change.

**Linked skill files**

- Support Operations Manager: `skills/support-operations-manager.md`

#### Job: FAQ & Self-Serve

Answer the questions that repeat · and turn them into living help content.

- Level: autonomous
- Capabilities: faq-responder, help-article-writer
- Tools: None listed

**Human**

A human reviews new auto-drafted articles before they publish, and owns the escalation line the moment an answer isn’t in the corpus.

**Replaces**

The 40–60% of support volume that is the same fifteen questions, answered by hand, forever.

**Notes**

The flywheel is the point: support tickets are your help-content roadmap, ranked by frequency. Deflection compounds · every article works every day after it ships.

**Prerequisites:** Company Knowledge Base

**Automation ladder**

- manual: Copy-paste from a doc nobody updates.
- assisted: Repeat questions answered from a living knowledge base; new repeats flagged and drafted into help content.
- autonomous: The help corpus grows itself · every novel resolved ticket becomes a draft article; deflection rate tracked.

**Linked skill files**

- Support Answerer: `skills/support-answerer.md`
- Help Content Writer: `skills/help-content-writer.md`

#### Job: Escalations

Spot the angry, the churn-risk, and the edge case · and get a human there fast.

- Level: assisted
- Capabilities: sentiment-flagger, escalation-router
- Tools: None listed

**Human**

An angry customer never gets a bot. The system’s entire job is detection and speed · the conversation that follows is a human’s, with full context in hand.

**Replaces**

The churn you find out about in a one-star review. By the time a frustrated customer asks for a manager, they’ve usually been simmering across three polite tickets nobody connected.

**Notes**

Tune for false positives over false negatives · an unnecessary human glance costs two minutes, a missed escalation costs the account. The detection layer should read across tickets, not within them: three mildly annoyed messages in two weeks is a louder signal than one heated one. Wire flagged accounts into Health Scoring so the risk shows up on the account, not just the ticket.

**Prerequisites:** Ticket Triage

**Automation ladder**

- manual: A rep forwards the scary email with “can you look at this?”
- assisted: Sentiment spikes, churn signals, and repeat-contact patterns flag in real time; a human gets pinged with the full thread history and a suggested first move.
- autonomous: Detection runs across every channel; flagged accounts page the right owner within minutes, briefed · and the system tracks whether the save worked.

**Linked skill files**

- Support Operations Manager: `skills/support-operations-manager.md`

#### Job: Macro Authoring

Turn the tickets that repeat into canned, on-brand responses agents reuse.

- Level: autonomous
- Capabilities: macro-writer, response-templater
- Tools: None listed

**Replaces**

Every agent re-typing the same answer from scratch · and answering it slightly differently each time.

**Notes**

The fastest way to cut response time is to stop writing the same answer twice. This mines the ticket history for what repeats and writes the reusable, on-voice response · feeding the same source that powers FAQ & Self-Serve.

**Prerequisites:** Ticket Triage

**Automation ladder**

- manual: Support reps wing the same fifty answers a hundred different ways.
- assisted: The agent reads the recurring tickets and drafts canned, on-brand macros for the team to reuse.
- autonomous: Macros generate and update themselves as new repeat questions emerge · the library stays current without a sweep.

**Linked skill files**

- Support Operations Manager: `skills/support-operations-manager.md`

### Function: Success

#### Job: Onboarding Journeys

Guide every new customer through activation, step by step.

- Level: autonomous
- Capabilities: journey-sequencer, activation-tracker
- Tools: None listed

**Replaces**

2–4 CSM hours per new account sending the same welcome sequence by hand · or the silent version, where customers who stall in week one become the churn stat of month three.

**Notes**

Define activation first · the one action that predicts retention · and build the journey backwards from it. Instrument every step so you can see exactly where customers stall; that drop-off chart is your product roadmap. The trap: a beautiful 12-email sequence nobody measured. Five steps with completion data beats twelve with vibes.

**Prerequisites:** Company Knowledge Base

**Automation ladder**

- manual: A welcome email, a PDF, and hope they figure it out.
- assisted: Step-by-step activation sequences drafted per customer segment; nudges trigger on stalled milestones, human sends the rescue note.
- autonomous: Every new customer walks a journey that adapts to their progress · stuck on step two gets help for step two, not a generic check-in. Completion rates tracked per step.

**Linked skill files**

- Customer Success Manager: `skills/customer-success-manager.md`

#### Job: Health Scoring

Score every account on usage, sentiment, and engagement · before renewal season.

- Level: assisted
- Capabilities: health-scorer, churn-predictor
- Tools: None listed

**Human**

The score surfaces risk; a human makes the call. No automated message ever goes to an at-risk account without an owner deciding to send it.

**Replaces**

Finding out an account was at risk in the cancellation email.

**Notes**

Sentiment from call transcripts and support threads is the leading indicator usage data misses · accounts go quiet before they go.

**Prerequisites:** Company Knowledge Base

**Automation ladder**

- manual: Renewal panic, quarterly.
- assisted: Accounts scored on usage, sentiment, and engagement; the at-risk list surfaces monthly with reasons.
- autonomous: Scores update continuously; threshold crossings trigger plays · outreach, check-in, escalation · before renewal season.

**Linked skill files**

- Customer Success Manager: `skills/customer-success-manager.md`

#### Job: Churn Prediction

Predict which accounts are about to slip · before the usage even dips.

- Level: assisted
- Capabilities: churn-modeler, risk-forecaster
- Tools: None listed

**Replaces**

The renewal that surprises you by not happening · the exit interview that should’ve been a save three weeks earlier.

**Notes**

Health Scoring tells you the current state; this predicts the trajectory. It catches the leading indicators · the champion who went quiet, the login cadence softening · while a conversation can still turn it around.

**Prerequisites:** Health Scoring

**Automation ladder**

- manual: You find out an account churned when the cancellation comes through.
- assisted: The agent models which accounts are likely to slip · weighting usage trend, sentiment, and engagement · before the obvious dip.
- autonomous: At-risk accounts are flagged early with the reason and a recommended play, continuously.

**Linked skill files**

- Customer Success Manager: `skills/customer-success-manager.md`

#### Job: Renewals & Expansion

Time renewal conversations and spot upsell openings.

- Level: manual
- Capabilities: renewal-scheduler, expansion-spotter
- Tools: None listed

**Human**

Renewal and upsell conversations are human, full stop. AI decides when and arms the talker · timing, account history, the expansion angle. The ask itself never automates.

**Replaces**

Renewals discovered two weeks out and handled in a panic, plus the expansion revenue nobody asked for because nobody noticed the account had outgrown its plan.

**Notes**

The 90-day rule is the whole game: a renewal conversation started early is a planning session, started late it’s a negotiation. Expansion signals live in usage data · seats maxed, limits hit, new teams appearing · so wire this to whatever Health Scoring reads. The trap: leading the renewal call with price. Lead with the value ledger · what they got this year · and let the number follow.

**Prerequisites:** Health Scoring

**Automation ladder**

- manual: A calendar reminder set at signing, if anyone remembered.
- assisted: Renewals surface 90 days out with health context and a drafted opener; usage patterns flag accounts ready for the expansion conversation.
- autonomous: Every account carries a renewal runway and an expansion readiness signal; the owner gets the play, the timing, and the talking points · and decides whether to run it.

**Linked skill files**

- Customer Success Manager: `skills/customer-success-manager.md`

#### Job: Advocacy & Referrals

Turn your happiest customers into referrals, reviews, and case studies.

- Level: assisted
- Capabilities: advocate-finder, referral-asker
- Tools: None listed

**Replaces**

The case studies and referrals you never ask for · happy clients who would gladly help if anyone caught the moment.

**Notes**

Your happiest customers are your cheapest growth channel and the one nobody works systematically. This watches for the high-water mark · a win, a glowing reply, a renewal · and makes the ask while the feeling’s fresh.

**Prerequisites:** Health Scoring

**Automation ladder**

- manual: You mean to ask your best client for a referral; you never do.
- assisted: The agent spots accounts at peak happiness and drafts the ask · referral, review, or case study · at the right moment.
- autonomous: Advocacy triggers off health peaks · the right ask goes out when satisfaction is highest, tracked through to the asset.

**Linked skill files**

- Customer Success Manager: `skills/customer-success-manager.md`

#### Job: QBR Prep

Build the quarterly business review from real account data.

- Level: autonomous
- Capabilities: qbr-builder, value-recap-writer
- Tools: None listed

**Replaces**

3–5 CSM hours per account per quarter assembling slides from scattered data · which is why most QBRs are either skipped or improvised from memory in the parking lot.

**Notes**

A QBR is a renewal argument delivered early · every slide should answer “why keep paying us.” Quantify outcomes in the customer’s units (hours saved, tickets deflected, revenue touched), not your feature usage. The trap: a data dump with no point of view. The recommendations slide is the deliverable; everything before it is evidence.

**Prerequisites:** Health Scoring, Call Capture

**Automation ladder**

- manual: Last quarter’s deck, new dates, same screenshots.
- assisted: Account data, usage trends, support history, and open items compiled into the house QBR template; the CSM edits the narrative and the asks.
- autonomous: Decks generate on the quarterly calendar automatically · wins quantified, risks flagged, next-quarter recommendations drafted · ready for a human polish pass.

**Linked skill files**

- Customer Success Manager: `skills/customer-success-manager.md`

### Function: Community

#### Job: Engagement & Replies

Every member question and mention gets a response in the house voice.

- Level: autonomous
- Capabilities: community-responder, mention-watcher
- Tools: None listed

**Replaces**

A community manager’s core hours · or the slow death where member questions sit unanswered for two days and the space quietly becomes a noticeboard.

**Notes**

Response speed is the heartbeat of a community · a question answered in 30 minutes teaches members to ask more, one answered in three days teaches them to stop. The voice file is the prerequisite: an off-tone reply in a community is worse than silence, because members can tell. The trap: letting the agent answer everything · the founder showing up personally on the threads that matter is the product.

**Prerequisites:** Company Knowledge Base

**Automation ladder**

- manual: The founder replies in bursts at midnight, then goes silent for a week.
- assisted: Every question and mention gets a drafted reply in the house voice within the hour; a human approves and posts.
- autonomous: Routine questions answered directly from the knowledge base; novel or sensitive threads route to a human with a draft attached. Response time tracked like an SLA.

**Linked skill files**

- Community Manager: `skills/community-manager.md`

#### Job: Moderation

Keep the space clean · spam, conduct, and noise handled quietly.

- Level: assisted
- Capabilities: spam-filter, conduct-monitor
- Tools: None listed

**Human**

Spam removal automates clean. Conduct calls don’t · warning or removing a real member is a judgment a human makes, with the receipts the system gathered.

**Replaces**

The founder deleting crypto spam at 7am, and the slower cost: one unchecked bad actor or pile-on thread can empty a community faster than any feature can fill it.

**Notes**

Write the rules before you build the enforcer · moderation without a published code of conduct reads as arbitrary, and arbitrary kills trust faster than spam does. Tier the response: silent removal for bots, private note for first-time line-crossers, human conversation for members. The trap: over-moderating early. A quiet community needs friction removed, not added.

**Prerequisites:** Engagement & Replies

**Automation ladder**

- manual: Someone notices the spam after twelve members already have.
- assisted: Spam, self-promo, and conduct flags caught on posting and queued with context; a human approves removals and warnings.
- autonomous: Obvious spam removed silently on sight; borderline conduct cases land in a review queue with the member’s history attached and a recommended action.

**Linked skill files**

- Community Manager: `skills/community-manager.md`

#### Job: Member Spotlights

Find and celebrate member wins · the retention engine.

- Level: manual
- Capabilities: win-detector, spotlight-writer
- Tools: None listed

**Replaces**

The retention engine nobody runs because it’s nobody’s job: member wins scroll past unnoticed, and the people most likely to renew never get told they matter.

**Notes**

A spotlighted member renews, posts more, and recruits · it’s the cheapest retention play in the tree. Ask permission before celebrating anyone publicly; a surprise spotlight on a private win burns trust. The trap: spotlighting only the whales. Celebrating a small win from a quiet member moves the whole room; celebrating the same three power users is just a leaderboard.

**Prerequisites:** Engagement & Replies

**Automation ladder**

- manual: A shout-out when the founder happens to see something good.
- assisted: Wins, milestones, and standout posts surfaced weekly from community activity; spotlight drafts ready in the house voice for a human to personalize and post.
- autonomous: A standing spotlight cadence runs itself · candidates ranked by story strength, drafts queued, posted on schedule with a human glance.

**Linked skill files**

- Community Manager: `skills/community-manager.md`

#### Job: Event Coordination

Run the AMAs, calls, and spotlights on a cadence the community can count on.

- Level: manual
- Capabilities: event-scheduler, session-runner
- Tools: Cal.com

**Replaces**

The community that goes quiet because the AMAs and calls stopped happening · running events is a part-time job nobody owns.

**Notes**

A community lives on rhythm · members stay for the next thing on the calendar. This runs the AMAs, calls, and spotlights on a dependable cadence so the room always has a reason to come back.

**Prerequisites:** Engagement & Replies

**Automation ladder**

- manual: Events happen sporadically when someone remembers to organise one.
- assisted: The agent schedules the cadence, drafts the promo, sends reminders, and preps the run-of-show for each session.
- autonomous: The event calendar runs on rails · scheduled, promoted, reminded, and recapped, with the human just showing up to host.

**Linked skill files**

- Community Manager: `skills/community-manager.md`

## Department: Back Office

The unglamorous floor that keeps the lights on · invoices out and money in, the numbers reporting themselves every Monday, contracts and records that never go missing. Nobody starts a company to chase late payments. This department runs the admin on a schedule so the founder stops being the bottleneck for getting paid.

### Function: Money In

#### Job: Invoice Generation

Branded invoices per entity, currency, and tax treatment.

- Level: autonomous
- Capabilities: invoice-generator, entity-router
- Tools: None listed

**Human**

A human glances at every invoice over a threshold before it sends. Money out the door wrong costs more than the glance.

**Replaces**

The founder doing invoices on Sunday night, occasionally wrong, across entities and currencies.

**Notes**

Encode the entity routing once · which company invoices which client, in what currency, with what tax line · and a recurring error class disappears permanently.

**Automation ladder**

- manual: A template, edited by hand, eventually sent.
- assisted: Branded invoices generated per entity, currency, and tax treatment from the deal record.
- autonomous: Milestones and retainer schedules trigger invoices automatically; numbering, tax, and filing handled.

**Linked skill files**

- Billing Manager: `skills/billing-manager.md`

#### Job: Payment Tracking

Know what’s paid, due, and late · without opening a bank app.

- Level: autonomous
- Capabilities: payment-watcher, reconciler
- Tools: Stripe, Wise

**Replaces**

The weekly bank-app archaeology session · logging into three accounts across two currencies to reconstruct who’s paid. Plus the invoice you forgot was unpaid until the quarter closed.

**Notes**

Pull from the source of truth · bank feeds or the payment processor · not from memory or the invoice tool’s optimistic status field. Normalize multi-currency to one reporting currency at a consistent rate convention, or every downstream number argues with itself. The trap: tracking what you sent instead of what landed. An invoice is a hope; a deposit is a fact.

**Prerequisites:** Invoice Generation

**Automation ladder**

- manual: You check the bank when you have a bad feeling.
- assisted: Every invoice tracked against incoming payments · paid, due, late · in one view, updated daily, currencies normalized.
- autonomous: Payments reconcile against invoices automatically; late ones hand themselves to Collections, and the cash position is always current without anyone asking.

**Linked skill files**

- Billing Manager: `skills/billing-manager.md`

#### Job: Collections

Overdue invoices get chased politely and persistently.

- Level: assisted
- Capabilities: overdue-nudger, escalation-sequencer
- Tools: None listed

**Human**

Tone escalation past the second nudge gets a human decision · the relationship is worth more than the invoice.

**Replaces**

The awkwardness of chasing money · which is why founders chase late and lose weeks of cash flow to their own politeness.

**Notes**

An agent is never embarrassed to ask. Tone-match the relationship · the sequence should sound like your best self on a confident day, every time.

**Prerequisites:** Invoice Generation, Payment Tracking

**Automation ladder**

- manual: You notice an unpaid invoice during a low moment.
- assisted: Overdue invoices get drafted nudges · polite, persistent, escalating on schedule · queued for your approval.
- autonomous: The sequence runs itself: day-3 nudge, day-10 firmer, day-21 escalation, with payment status checked before every send.

**Linked skill files**

- Billing Manager: `skills/billing-manager.md`

### Function: Reporting

#### Job: Revenue Reporting

Monthly revenue truth across entities and currencies.

- Level: autonomous
- Capabilities: revenue-reporter, currency-normalizer
- Tools: None listed

**Replaces**

Either $200–500/month of bookkeeper time assembling a report that arrives three weeks stale, or the founder rebuilding the same spreadsheet every month and trusting it less each time.

**Notes**

One number per question: what came in, from whom, through which entity, recurring or not. Split recurring from project revenue from day one · it’s the split every future decision (and buyer) cares about. The trap is reporting invoiced revenue as received revenue; build only on reconciled payments or the report is fiction with formatting.

**Prerequisites:** Payment Tracking

**Automation ladder**

- manual: A spreadsheet with a tab per month and a formula someone broke in March.
- assisted: Monthly revenue compiled across entities and currencies · by client, by type, recurring vs. one-off · drafted for a human sanity check.
- autonomous: The report generates itself on the first of the month from reconciled payment data; anomalies get flagged, not buried.

**Linked skill files**

- Financial Reporting Analyst: `skills/financial-reporting-analyst.md`

#### Job: Goal Pacing

Tracking against the income target, with pace forecasts.

- Level: autonomous
- Capabilities: goal-pacer, runway-projector
- Tools: None listed

**Replaces**

Discovering in November that the year’s number was never going to happen.

**Notes**

The forecast matters more than the scoreboard · “you finish at 71% on current pace” in June is actionable; the same number in December is an obituary.

**Prerequisites:** Revenue Reporting

**Automation ladder**

- manual: A number in your head and a feeling about it.
- assisted: Live pace against target · monthly and annual · with a forecast of where the current trajectory lands.
- autonomous: Pace alerts with diagnosis: which pipeline gap, which retainer change, which seasonality is moving the landing point.

**Linked skill files**

- Financial Reporting Analyst: `skills/financial-reporting-analyst.md`

### Function: Finance Ops

#### Job: Cash-Flow Forecasting

Project cash in and out · know your runway before it becomes an emergency.

- Level: assisted
- Capabilities: cashflow-projector, runway-calculator, scenario-modeler
- Tools: Xero, Stripe

**Human**

A human owns the assumptions and the calls that follow · this does the math, fast and honestly, and shows its work. The decisions stay human.

**Replaces**

The fractional CFO’s headline deliverable · or, more often, no forecast at all and a founder guessing at runway.

**Notes**

Revenue Reporting tells you what happened; this tells you what’s coming. The skill below projects cash in and out, calculates runway, and runs scenarios ("hire two", "lose the biggest client", "double ad spend") so "can we afford this" has an answer before it’s urgent.

**Prerequisites:** Revenue Reporting

**Automation ladder**

- manual: Cash gets checked by looking at the bank balance and feeling either fine or scared.
- assisted: The agent projects inflows and outflows, computes runway, and builds a 3/6/12-month forward view with the assumptions shown.
- autonomous: The forecast updates as money moves · runway and scenario models refresh themselves and flag when a threshold is crossed.

**Linked skill files**

- Finance Operations Analyst: `skills/finance-operations-analyst.md`

#### Job: Budget Tracking

Spend vs budget by category, with overruns flagged early.

- Level: autonomous
- Capabilities: budget-tracker, variance-flagger
- Tools: Xero

**Replaces**

The budget set once in January and never looked at again · overruns discovered at tax time.

**Notes**

A budget you don’t check is a wish. This watches spend against plan by category so the overrun is a flag you act on, not a number you explain after the fact. Pairs with Cash-Flow Forecasting as the Finance Ops function.

**Prerequisites:** Expense Categorization

**Automation ladder**

- manual: Spend is reconciled against budget quarterly, if ever.
- assisted: The agent tracks actual spend against budget by category and flags overruns as they emerge.
- autonomous: Budget variance is monitored continuously · a category trending over gets flagged mid-month, not after.

**Linked skill files**

- Finance Operations Analyst: `skills/finance-operations-analyst.md`

### Function: Records

#### Job: CRM Sync

Deals, contacts, and statuses stay current everywhere.

- Level: autonomous
- Capabilities: crm-syncer, two-way-updater
- Tools: Attio

**Human**

Merges and deletions get a human click. A bad sync that creates a duplicate is annoying; one that destroys a record is archaeology.

**Replaces**

The gap between what the CRM says and what’s actually true · which quietly invalidates every report, forecast, and reactivation play built on top of it.

**Notes**

Pick one system of record per object · deals live here, money lives there · and make everything else a mirror, never a second author. Sync from activity (transcripts, payments, sent emails), not from human discipline, because human discipline is what failed in the first place. The trap: two-way sync between two systems that both think they’re the boss.

**Prerequisites:** Company Knowledge Base, CRM Hygiene

**Automation ladder**

- manual: The CRM gets updated in a guilty batch before someone looks at it.
- assisted: Deals, contacts, and statuses sync across systems · CRM, invoicing, project tracker · with changes drafted from real activity for approval.
- autonomous: Calls, emails, and payments update records as they happen; every system agrees, and nobody types the same client name twice.

**Linked skill files**

- Records Administrator: `skills/records-administrator.md`

#### Job: Expense Categorization

Spend categorized for the accountant before they ask.

- Level: assisted
- Capabilities: expense-categorizer
- Tools: None listed

**Human**

Tax treatment is judgment, not classification · deductibility calls and anything the accountant would raise an eyebrow at stay human.

**Replaces**

$150–400/month of bookkeeper categorization, or the annual shoebox week where the founder relives twelve months of receipts to answer the accountant’s spreadsheet.

**Notes**

Get the chart of accounts from your accountant first and categorize into it · inventing your own categories just creates a translation job later. Auto-accept the recurring 80% (same vendor, same category, every month) and only surface the new and ambiguous. The trap is multi-entity spend on one card: encode which entity owns which subscription once, or every month leaks misattributed costs.

**Prerequisites:** Company Knowledge Base

**Automation ladder**

- manual: A folder called “receipts” and a strong belief that future-you will deal with it.
- assisted: Transactions pulled from feeds and auto-categorized to your chart of accounts, with the uncertain tail queued for a 10-minute weekly review.
- autonomous: Spend lands pre-categorized per entity with receipts attached; the accountant gets a clean file, not a quiz.

**Linked skill files**

- Financial Reporting Analyst: `skills/financial-reporting-analyst.md`

#### Job: Document Filing & Retrieval

Every document named, filed, and findable in ten seconds.

- Level: autonomous
- Capabilities: document-filer, retrieval-indexer
- Tools: None listed

**Replaces**

The Friday afternoon spent hunting for "the signed SOW from March" · multiplied across everyone, every week.

**Notes**

"Where’s that document" is a tax every business pays daily. The skill below enforces naming, filing, and an index so retrieval is ten seconds, not a search party · and applies retention so old records don’t pile up.

**Prerequisites:** Company Knowledge Base

**Automation ladder**

- manual: Files live in seven places with names like "final_v3_FINAL".
- assisted: The agent names, files, and indexes every document so any of them is findable in seconds.
- autonomous: Documents are filed and tagged on arrival, with retention rules applied · nothing is ever lost or kept too long.

**Linked skill files**

- Records Administrator: `skills/records-administrator.md`

#### Job: Contract Lifecycle

Renewals, expiries, and obligations tracked so nothing sneaks up.

- Level: assisted
- Capabilities: contract-tracker, renewal-notifier
- Tools: None listed

**Replaces**

The auto-renewal you forgot to cancel · the client contract that lapsed because nobody tracked the date.

**Notes**

Contracts have dates that cost money when missed · a lapsed client agreement, a vendor auto-renewing at a worse rate. This tracks every obligation and deadline so the calendar works for you instead of against you.

**Prerequisites:** Document Filing & Retrieval

**Automation ladder**

- manual: Renewal and expiry dates live in someone’s memory and a forgotten calendar invite.
- assisted: The agent tracks every contract’s renewal, expiry, and obligations and surfaces them well before the deadline.
- autonomous: The lifecycle runs itself · renewals flagged in time to act, obligations tracked, nothing sneaks up.

**Linked skill files**

- Contracts Coordinator: `skills/contracts-coordinator.md`

#### Job: Entity Compliance

Filings and obligations per entity, tracked and scheduled.

- Level: manual
- Capabilities: compliance-calendar, filing-tracker
- Tools: None listed

**Human**

Filings get signed by a human, full stop. AI tracks, prepares, and nags · it never submits anything with legal weight on its own.

**Replaces**

Missed filings, and what they cost: late penalties, a suspended entity, or a frozen bank account discovered the week you need it. Multi-entity founders carry a deadline list nobody actually maintains.

**Notes**

Build the obligation register per entity first · jurisdiction, filing, frequency, deadline, who files it · straight from your accountant and registered agent, not from memory. Alerts at 30, 14, and 3 days, with the longest lead on anything requiring a third party. The trap: tracking only tax. Trade licenses, registered agents, visa renewals, and substance requirements kill entities just as dead.

**Prerequisites:** Company Knowledge Base

**Automation ladder**

- manual: The accountant emails you something urgent and you learn a deadline existed.
- assisted: Every entity’s obligations · filings, renewals, tax dates, license deadlines · tracked in one calendar with lead-time alerts and prepared checklists.
- autonomous: The system watches the obligations, drafts the routine paperwork, and escalates with everything assembled; humans sign and submit.

**Linked skill files**

- Records Administrator: `skills/records-administrator.md`

### Function: Office

#### Job: Calendar Management

Scheduling, conflicts, buffers, and timezone math handled.

- Level: autonomous
- Capabilities: calendar-manager, conflict-resolver
- Tools: Cal.com

**Replaces**

A part-time EA’s core duty ($15–25k/year), or the founder doing timezone math at midnight and the double-booking that torches a first impression.

**Notes**

Write the rules before the automation: meeting hours, buffer lengths, which meeting types deserve which slots, what’s sacred. The agent enforces policy · if there’s no policy, it just automates chaos faster. The trap is optimizing for openness: a calendar that accepts everything efficiently is a calendar that destroys deep work efficiently.

**Automation ladder**

- manual: You are the scheduling link, and the link is tired.
- assisted: Conflicts caught, buffers enforced, timezones handled; reschedule requests come back with sane options instead of a shrug.
- autonomous: The calendar defends itself · focus blocks protected, travel and prep time auto-added, low-priority requests deflected to the right slot without a human in the loop.

**Linked skill files**

- Executive Assistant: `skills/executive-assistant.md`

#### Job: Email Triage

The inbox sorted by what actually needs the human.

- Level: autonomous
- Capabilities: email-triager, draft-responder
- Tools: None listed

**Human**

Triage is autonomous; sending is not. Replies go out after a human approves · and the agent never deletes, only archives, so a misjudged email is a search away, not gone.

**Replaces**

The 1–2 hours a day a founder spends in the inbox, of which maybe fifteen minutes is decisions and the rest is sorting other people’s priorities.

**Notes**

The classifier needs your context to know what matters · a client name, an open deal, an overdue invoice all change an email’s priority, which is why this reads from the knowledge base. Start with triage-only for two weeks and audit the calls before letting it draft. The trap is over-filtering: one important email in spam-purgatory costs more trust than a hundred correctly filed newsletters earn.

**Prerequisites:** Company Knowledge Base

**Automation ladder**

- manual: Inbox open all day, attention rented out one notification at a time.
- assisted: Every email sorted on arrival · needs-you / FYI / automated noise · with drafted replies queued on the routine ones.
- autonomous: The inbox becomes a briefing: the handful that genuinely need a human, surfaced with context and a draft; the rest filed, answered, or archived by standing rules.

**Linked skill files**

- Inbox Manager: `skills/inbox-manager.md`

### Function: Talent

#### Job: Candidate Sourcing

Find and rank candidates for open roles across platforms.

- Level: manual
- Capabilities: candidate-finder, profile-ranker
- Tools: None listed

**Replaces**

A recruiter’s 20–25% placement fee, or 10+ founder-hours per role scrolling profiles · which is why most small companies hire from whoever happened to apply.

**Notes**

The scorecard is the whole build: outcomes the role must deliver, must-have evidence, disqualifiers · written before the first search, stored where agents read it. Rank on demonstrated work over keyword density; titles lie, portfolios don’t. The trap is sourcing for the résumé you’d recognize instead of the outcome you need · the scorecard exists to stop that.

**Prerequisites:** Company Knowledge Base

**Automation ladder**

- manual: Post the job, pray, hire the least-bad applicant in week six.
- assisted: A real role scorecard drives searches across platforms; candidates come back ranked against it with reasons, not vibes.
- autonomous: Open roles run standing searches; new matches land scored and deduped, outreach drafted, pipeline always warm before the seat is empty.

**Linked skill files**

- Talent Coordinator: `skills/talent-coordinator.md`

#### Job: Screening & Scheduling

First-pass screens and interview logistics, handled.

- Level: assisted
- Capabilities: screen-summarizer, interview-scheduler
- Tools: None listed

**Human**

AI filters; humans reject and advance. Every no on a real candidate is a human call · a person’s livelihood deserves more than a threshold, and so does your reputation in a small market.

**Replaces**

The 30 minutes per applicant a first-pass screen actually takes, multiplied by the 80% who were never going to make it · plus the scheduling ping-pong that loses good candidates to faster companies.

**Notes**

Structured beats freeform: same questions, same rubric, every candidate · it’s fairer and it makes the AI scoring actually comparable. Speed is a weapon here; the best candidates are gone in days, and same-day screening plus instant booking wins talent that slower companies never even meet. The trap: optimizing for interview polish. Score evidence of doing the job, not fluency in describing it.

**Prerequisites:** Candidate Sourcing, Calendar Management

**Automation ladder**

- manual: You skim forty CVs on a Sunday and interview whoever annoyed you least.
- assisted: Every applicant screened against the scorecard · structured questions asked and scored · with a shortlist and reasoning for human review; interviews book themselves.
- autonomous: Screens run on arrival, the calendar fills with only above-bar candidates, and everyone else gets a prompt, decent no · drafted by the system, signed off by a human.

**Linked skill files**

- Talent Coordinator: `skills/talent-coordinator.md`

#### Job: Onboarding & Training

New hires get the playbooks, access, and 30-day plan automatically.

- Level: autonomous
- Capabilities: hire-onboarder, training-sequencer
- Tools: None listed

**Replaces**

The new hire’s lost first month · asking around for access, absorbing context by osmosis · and the senior person’s week spent re-explaining what should have been written down.

**Notes**

This node is only as good as the knowledge base behind it · onboarding is really just the company’s documented self, sequenced into 30 days. Write the plan as outcomes per week (what they can do unsupervised) rather than content consumed. The trap is information-dump onboarding: forty documents in week one teaches nothing; one real task with the relevant playbook attached teaches everything.

**Prerequisites:** Screening & Scheduling, SOP Generation

**Automation ladder**

- manual: Day one is a laptop, a Slack invite, and “shadow Sarah for a bit.”
- assisted: Offer accepted → access checklist, playbooks, tool walkthroughs, and a 30-day plan generated from the role scorecard; a human assigns the mentor and the first real task.
- autonomous: The whole arc runs itself · accounts provisioned, training sequenced, check-ins scheduled, progress tracked · and the manager gets a flag only when someone’s off pace.

**Linked skill files**

- Talent Coordinator: `skills/talent-coordinator.md`

#### Job: HR & Policy Assistant

Answer staff policy questions from the real handbook · leave, expenses, onboarding admin.

- Level: assisted
- Capabilities: policy-answerer, handbook-keeper
- Tools: None listed

**Human**

Anything legal, sensitive, or about comp/termination escalates to a human immediately · this answers the routine 80% from documented policy and never invents one.

**Replaces**

The first HR hire a small team can’t justify yet · and the founder fielding "how much leave do I have" between sales calls.

**Notes**

The skill below is grounded strictly in the company’s own policy docs · it never guesses a policy, it cites the source, and it escalates the hard stuff. It removes the founder as the help desk for "what’s our policy on…".

**Prerequisites:** Company Knowledge Base

**Automation ladder**

- manual: Policy questions interrupt whoever’s nearest, answered from memory and inconsistently.
- assisted: The agent answers staff questions from the real handbook · leave, expenses, process · with a citation, and handles onboarding admin.
- autonomous: Routine people-ops runs itself · policy answered from source, new-hire admin sequenced, the handbook kept current.

**Linked skill files**

- People Operations Assistant: `skills/people-operations-assistant.md`

## Skill file previews

### billing-manager

# Billing Manager · money in, on time, every time

**Category:** Back Office / Finance
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Billing Manager owns the path from "deal closed" to "money in the bank." It generates branded invoices from your deal records · correct entity, correct currency, correct tax treatment, every time. It keeps a live ledger of what's paid, due, and late, so you never open a bank app to answer "did they pay yet?" And when an invoice goes overdue, it runs a polite-but-persistent chase sequence that escalates on a schedule instead of relying on you remembering to feel awkward about it.

Most small businesses don't have a collections problem. They have a "nobody chased it" problem. This skill makes the chasing automatic and the awkwardness someone else's job.

## Required API Keys

None required. The Billing Manager works from your deal records and a local payment ledger.

> **Payments integration (optional):** If `STRIPE_API_KEY` or `WISE_API_TOKEN` is in `.env`, the Manager can verify payment status against real transactions instead of asking you.

### brand-deal-producer

# Brand Deal Producer · sponsored content that passes both approvals

**Category:** Marketing / Brand Deals
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Brand Deal Producer handles the production paperwork of sponsored content · the part that stalls deals for weeks. From a brand brief, it writes the sponsored script in the creator's proven format (not the brand's press-release voice), fact-checks every capability claim against what the product actually does, and packages the result as a clean approval document formatted for sponsor sign-off.

Two jobs in one producer: **Deal Scripting** (the script, in the format that earned the audience) and **Approval Docs** (the brand-safe document that gets the sponsor's yes without four revision rounds). The operating rule: nothing goes to production until both the creator and the sponsor have approved · and nothing goes in the script that the product can't actually do.

## Required API Keys

None. The Brand Deal Producer works from the brand brief, the creator's content history, and public product information. No external APIs required.

## How to Run

### brand-visual-designer

# Brand Visual Designer · Brand Image Generator

**Category:** Marketing
**Version:** 1.0
**Status:** Ready
**Part of:** SkillTree · altari.ai/skilltree

---

## When summoned, display this banner

```
 ┌───────────────────────────────────────────────────────────────────┐
 │   BRAND VISUAL DESIGNER                                           │
 │   ⚡ Brand Image Generator                                         │
 │                                                                   │
 │   Reference images → brand-consistent visuals.                    │
 │   Drop refs in assets/brand-references/, describe what you want.  │
 └───────────────────────────────────────────────────────────────────┘
```

---

## What the Brand Visual Designer Does

Reads your brand reference images, extracts the visual language (colors, style, composition, typography), then generates new brand-consistent images from your prompt using Flux Pro.

**Input:** Image prompt + reference images in `assets/brand-references/`
**Output:** Generated images embedded in a clean HTML report, auto-opened in browser

---

## Variables

### business-data-analyst

# Business Data Analyst · ask your numbers, get the working

**Category:** Operations
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Business Data Analyst lets you ask questions of your own data without writing SQL or wrestling a spreadsheet. You give it data · a CSV, an export, or a live connection · and a question, and it answers in plain language, then shows exactly how it got there: the filter, the formula, the query. Every number comes with its working, because a number you can't reproduce is a guess. It also runs as a standing **weekly KPI digest** and, crucially, tells you when your data is too messy or too thin to support the answer you're asking for, instead of confidently returning garbage.

## Required API Keys

| Key | What It Does | .env Variable |
|-----|-------------|---------------|
| Supabase / Postgres | Query a live database directly (read-only) | `DATABASE_URL` |
| Google Sheets | Pull a sheet without a manual export | `GOOGLE_OAUTH` (sheets scope) |

**All keys are optional.

### buying-signals-analyst

# Buying Signals Analyst · know who's ready before they know

**Category:** Sales / Targeting
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Buying Signals Analyst watches your target accounts for the events that turn a cold company into a warm one · hiring sprees, funding rounds, tech stack changes, leadership moves. Cold outreach to a random company converts on luck; outreach timed to a trigger converts on relevance. Give it an account list and it sweeps for signals, ranks what it finds by strength, and pairs every signal with a suggested play: who to contact, what angle, and the opening line the signal justifies. Run it weekly on a live list or once before any campaign launch.

## Required API Keys

Works with zero keys · the analyst sweeps public sources (news, job boards, press pages, LinkedIn company pages) via manual web research and tells you which accounts it couldn't check. Add keys for deeper, faster sweeps:

### call-prep-researcher

# Call Prep Researcher · walk into every call already knowing the room

**Category:** Deals / Call Cycle
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Call Prep Researcher builds a one-page brief before every meeting: who you're talking to, what their company does, the full history of your relationship pulled from your knowledge files and past outputs, every open thread that might come up, and a suggested objective with talking points to hit it. Ten minutes of scattered tab-opening before a call becomes one page you read in ninety seconds. The difference shows · prospects and clients can tell within two minutes whether you prepared, and the prepared side of the table controls the agenda.

## Required API Keys

None. The Researcher works from your knowledge files, past outputs, and whatever you tell it about the meeting. Web research uses Claude's built-in search where available.

> **Calendar integration (optional):** If a calendar connection or `CAL_API_KEY` is available, the Researcher can pull today's or tomorrow's meetings and prep all of them in one run.

### campaign-operations-manager

# Campaign Operations Manager · from finished copy to live sends

**Category:** Sales / Sequencing & Send
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Campaign Operations Manager takes finished copy and a verified list and gets the campaign live · correctly. It covers three jobs that usually get done half-right at midnight before launch: Campaign Orchestration (designing the multi-channel cadence · email, LinkedIn, phone touches in the right order with the right gaps), Campaign Launch (pushing everything into the sending platforms with the settings that actually matter), and Send Optimization (timezone-aware scheduling and volume pacing that protects reply rates and domain health). One hard rule runs through all of it: a human reviews the test send before any campaign goes live. No exceptions.

## Required API Keys

Works with zero keys · the manager produces a complete launch pack (cadence map, platform settings sheet, paste-ready copy blocks, pacing schedule) that you execute manually in your sending tools. Add keys for direct platform pushes:

### carousel-designer

# Carousel Designer · swipeable slides from any idea

**Category:** Marketing
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Carousel Designer turns any idea · a topic, a script, a case study, a winning post · into a complete carousel architecture: slide-by-slide copy, swipe logic, and layout notes ready to drop into your design system, Figma template, or Canva file. It engineers the thing that actually makes carousels work: a hook slide that earns the first swipe, value slides that each earn the next one, and a CTA slide that converts the attention. You bring the idea; it hands you a carousel you could build in 20 minutes.

## Required API Keys

None. The Carousel Designer works entirely from your knowledge base and the idea you bring. No external APIs required.

### case-study-curator

# Case Study Curator · the right proof at the right moment

**Category:** Sales / Outreach Writing
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Case Study Curator maintains your proof library and matches the right case study to each prospect's industry and problem. Generic proof ("we've helped dozens of companies") converts nobody; a prospect believes the story about someone who looks like them. This skill does two jobs in one: it builds and maintains `knowledge/proof/` · one structured file per case study, with results stated exactly as verified · and on demand it picks the best-matching proof for a given prospect and compresses it into the one-line proof point a cold email or LinkedIn message can carry. Every outreach-writing skill on the map pulls from this library.

## Required API Keys

None. The Case Study Curator works entirely from evidence you already have · client files in your knowledge base, delivered-work notes, or your answers to its interview. Matching and compression are judgment, not API calls.

### client-onboarding-manager

# Client Onboarding Manager · signed to building in 48 hours

**Category:** Operations / Onboarding
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Client Onboarding Manager compresses the gap between "deal closed" and "work started" into a single working day. The moment a deal signs, it produces the kickoff pack · a welcome email in your voice and a complete access checklist of every credential, key, and account the build needs. Then it runs access collection: chasing each item politely, verifying what arrives actually works, and routing secrets into a proper secrets store. Finally it scaffolds the engagement · project folder, context file, and plan · so the first build session starts with context loaded instead of archaeology.

Most engagements lose their first two weeks to access-chasing and "where do we even put this." This skill makes the first 48 hours the most organized part of the project.

## Required API Keys

None. The Onboarding Manager works entirely from your project files and what the client sends. Zero keys required.

> Note the reverse: this skill *collects* keys.

### client-portal-manager

# Client Portal Manager · clients watch progress happen

**Category:** Operations / Build Ops
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Client Portal Manager gives every client a single place to see their project moving: what shipped, what's in progress, what's needed from them, and what's next. It handles two jobs · **provisioning** (standing up a client-scoped portal, or a structured shared status doc when there's no web infrastructure) and **sync** (turning work sessions into client-readable updates that flow in automatically, so the portal is alive instead of a page that was accurate once, in week one).

A client who can watch progress happen doesn't email asking for it. The portal converts "any update?" anxiety into visible momentum · and visible momentum is what renews retainers.

## Required API Keys

None. The default portal is a structured status doc that works with zero infrastructure.

> **Web portal (optional):** If your project has hosting and a database configured (e.g.

### cold-email-copywriter

# Cold Email Copywriter

**Category:** Outreach
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Cold Email Copywriter writes personalized cold email sequences that get replies. Give it a prospect (or point it at an existing report from the **Prospect Research Analyst** (prospect-research-analyst.md)) and it will craft a 3-step email sequence · research-backed, personalized, and ready to send. Optionally pushes sequences directly to Instantly for automated sending.

## Required API Keys

| Key | Where to Get It | .env Variable |
|-----|----------------|---------------|
| Instantly | https://app.instantly.ai/settings/integrations | INSTANTLY_API_KEY |

> Instantly is optional · the Cold Email Copywriter will always generate the email sequence. The API key is only needed to push emails directly into Instantly campaigns. With no keys at all, the Cold Email Copywriter still produces the complete, ready-to-send 3-email sequence · you just send it manually.

### community-manager

# Community Manager · the space stays alive and clean

**Category:** Customer / Community
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Community Manager keeps your community · Slack, Discord, Skool, Circle, forum, comment section · alive and clean. Three jobs in one role: it drafts house-voice responses to every member question and mention so nothing sits unanswered, handles moderation (spam dispatched quietly, conduct issues escalated to a human with context), and hunts for member wins to turn into spotlight drafts · the single cheapest retention engine a community has.

Communities die from silence, not from drama. A question that hangs unanswered for two days teaches every lurker that asking isn't worth it. This skill's job is to make sure the space always feels tended.

## Required API Keys

None. The Community Manager works on whatever you bring it · channel exports, pasted threads, screenshots transcribed, or a digest of the week's activity. Platform APIs can be wired in later; the judgment layer is the same.

## How to Run

### company-research-analyst

# Company Research Analyst · full intel on any company

**Category:** Research
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Company Research Analyst builds deep intelligence reports on target companies. Give it a company name, domain, or LinkedIn URL and it will scrape LinkedIn, run semantic search, analyze the website, surface growth signals, score qualification fit against your ICP, and identify key decision-makers · all framed around how your business can help them.

## Required API Keys

| Key | Where to Get It | .env Variable | Required? |
|-----|----------------|---------------|-----------|
| Exa | https://dashboard.exa.ai/api-keys | EXA_API_KEY | Yes |
| Firecrawl | https://firecrawl.dev/app/api-keys | FIRECRAWL_API_KEY | Yes |
| Apify | https://console.apify.com/account/integrations | APIFY_API_KEY | Optional · adds LinkedIn page/posts scraping |

### competitive-intelligence-analyst

# Competitive Intelligence Analyst

**Category:** Research
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Competitive Intelligence Analyst builds competitive intelligence reports. Give it a competitor's name or website and it will analyze their positioning, pricing, messaging, strengths, weaknesses, market approach, and tech stack · then frame everything against YOUR business so you know exactly how to win against them.

## Required API Keys

| Key | Where to Get It | .env Variable |
|-----|----------------|---------------|
| Exa | https://dashboard.exa.ai/api-keys | EXA_API_KEY |
| Firecrawl | https://firecrawl.dev/app/api-keys | FIRECRAWL_API_KEY |

### content-performance-analyst

# Content Performance Analyst · your own corpus is the strategy

**Category:** Marketing
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Content Performance Analyst turns your own posting history into a content strategy. It ranks everything you've published by performance, extracts the hook, format, and topic patterns that separate your winners from your average posts, and flags proven pieces worth re-hashing. Then it goes one layer deeper: it mines your comments and DMs for the questions, objections, and recurring themes your audience keeps raising · each one a content idea with built-in demand. Most creators guess what to post next. This agent reads the evidence you already have.

## Required API Keys

| Key | Where to Get It | .env Variable |
|-----|----------------|---------------|
| Apify | https://console.apify.com/account/integrations | APIFY_API_TOKEN |

> **Optional.** With an Apify token, the analyst can scrape your public profile (Instagram, TikTok) to pull post data and comments automatically.

### content-repurposing-manager

# Content Repurposing Manager · one idea, every platform

**Category:** Marketing
**Version:** 1.0
**Status:** Ready
**Part of:** SkillTree · altari.ai/skilltree

---

## When summoned, display this banner

```
 ┌──────────────────────────────────────────────────────────────────────────┐
 │   CONTENT REPURPOSING MANAGER                                            │
 │   ⚡ Multi-Platform Content Engine                                        │
 │                                                                          │
 │   One idea → research → 7 platform-optimized formats.                    │
 │   LinkedIn · X Thread · Newsletter · YouTube · Reels · TikTok · Shorts   │
 └──────────────────────────────────────────────────────────────────────────┘
```

---

## What the Content Repurposing Manager Does

Takes a rough idea or existing draft, researches supporting data if needed, and produces ready-to-post content for every platform you select · each optimized for that platform's algorithm, format, and audience behavior.

**Input:** An idea, a topic, or a draft.
**Output:** Up to 7 platform-specific formats + an AI image prompt.

---

### contracts-coordinator

# Contracts Coordinator · the agreement ready the hour the deal closes verbally

**Category:** Deals / Deal Artifacts
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Contracts Coordinator produces the services agreement the moment a deal closes verbally · so the signature happens while the yes is still warm. It takes your approved master template, fills in the deal-specific blanks (parties, scope, fees, dates, payment terms) from the deal record or your notes, and outputs a send-ready draft with every judgment call marked `[LEGAL REVIEW]`.

One thing it will never do: write or modify legal language. It fills blanks in a lawyer-blessed template. If you don't have a master template yet, it helps you structure one as a draft · clearly marked as requiring a lawyer's pass before first use.

## Required API Keys

None. The Contracts Coordinator runs entirely on your template, your deal record, and your notes. Zero keys, zero external services.

### conversion-copywriter

# Conversion Copywriter

**Category:** Marketing
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Conversion Copywriter writes landing-page and sales-page copy that actually converts · not brand fluff. Point it at your offer and it builds the entire page in the order that sells · hero with the core promise, the problem stated in the visitor's own words, the mechanism that solves it, proof (testimonials, numbers, logos), the offer with risk reversal, an objection-handling FAQ, and a single clear call to action. Everything is written from your offer, your ICP, and your brand voice · then handed back as labeled, section-by-section copy you can paste straight into a page builder.

## Required API Keys

| Key | Where to Get It | .env Variable |
|-----|----------------|---------------|
| Exa | https://dashboard.exa.ai/api-keys | EXA_API_KEY |
| Firecrawl | https://firecrawl.dev/app/api-keys | FIRECRAWL_API_KEY |

> **No keys required.** The Conversion Copywriter writes a complete page from your `knowledge/` files (offer, ICP, voice, proof) with zero keys · this is the default path.

### creative-strategist

# Creative Strategist · viral hooks for any platform

**Category:** Marketing
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Creative Strategist is an elite marketing strategist that analyzes any business and generates platform-specific viral hooks. Give it a business name and website, tell it which platforms you want hooks for, and it will research the business, study competitors, identify psychological angles, and produce 15-20+ hooks using proven viral frameworks. Works across LinkedIn, Instagram, TikTok, X, YouTube, and more.

## Required API Keys

| Key | Where to Get It | .env Variable |
|-----|----------------|---------------|
| Exa | https://dashboard.exa.ai/api-keys | EXA_API_KEY |
| Firecrawl | https://firecrawl.dev/app/api-keys | FIRECRAWL_API_KEY |

> **Both optional.** The Creative Strategist works fully without any keys · it generates hooks from your business context alone. With the keys, it also researches the business website and competitors for deeper, more specific hooks.

### customer-success-manager

# Customer Success Manager · every account activated, scored, and renewed on time

**Category:** Customer / Success
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Customer Success Manager runs the post-sale lifecycle end to end. Four jobs in one role: it builds onboarding journeys that walk every new customer to activation step by step, scores account health from usage and sentiment so at-risk accounts surface before renewal season instead of during it, watches renewal timing and spots expansion openings, and builds QBR decks from real account data instead of last-minute screenshot scrambles.

The dividing line is firm: the system prepares everything · the sequences, the scores, the briefs, the decks. The human makes the relationship moves. The renewal ask, the expansion pitch, the save call · those never automate.

## Required API Keys

None. The Customer Success Manager works from whatever account data you have · usage exports, email threads, meeting notes, CRM dumps, or your own answers to its interview. Wire in product analytics later if you have them; the logic is the same.

## How to Run

### data-enrichment-specialist

# Data Enrichment Specialist · every record complete, current, verified

**Category:** Sales / Enrichment
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Data Enrichment Specialist takes a raw lead list and returns campaign-ready records in one pass: decision-maker contacts found and appended (emails, phones, LinkedIn profiles), every email verified before it can ever receive a send, and account-level context layered on top · firmographics, tech stack, headcount trends. It covers three jobs that fail expensively when skipped: Contact Enrichment, Email Verification, and Account Enrichment. A list that skips this step burns your domain on bounces and your reply rate on wrong-person sends. Nothing leaves this skill unlabeled · every record carries its verification status.

## Required API Keys

Works with zero keys · the specialist enriches via manual web research (company sites, LinkedIn, public directories) on small batches, pattern-infers emails, and marks everything `UNVERIFIED`. Add keys for scale and certainty:

### deal-debrief-analyst

# Deal Debrief Analyst · the call ends, the work is already done

**Category:** Deals / Call Cycle
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Deal Debrief Analyst processes a call the moment it ends. Give it the transcript or your notes and it extracts what actually happened · outcomes, decisions, action items with owners, and any change to the deal state · then drafts the recap email in your voice, ready to send the same hour. It covers two jobs in one pass: post-call debrief (transcript → structured record) and follow-up drafting (the recap the prospect reads while the call is still fresh). Most follow-ups go out a day late and read like minutes from a meeting nobody attended. The one that lands an hour after the call, sharp and specific, is a sales asset.

## Required API Keys

None. Paste the transcript or your call notes and everything below works with zero keys.

> **Fireflies integration (optional):** If `FIREFLIES_API_KEY` is in `.env`, the Analyst can pull the latest transcript automatically instead of requiring a paste.

### deal-room-producer

# Deal Room Producer · a branded room per prospect, tracked to the click

**Category:** Deals / Deal Artifacts
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Deal Room Producer assembles everything a prospect needs to say yes · proposal, scope, proof, pricing, FAQ · into one shareable, organized package per deal. If you have web infrastructure (a site you can deploy pages to), it specs a gated room page with per-stakeholder links so you can see who opened what. If you don't, it produces the same thing as a structured document package you can share as a folder or PDF set. Either way: one link, one place, no attachment graveyard.

It also closes the loop. When you tell it what happened · "the CFO opened the pricing section twice" · it writes engagement notes back to the deal record so the next touch is informed, not blind.

## Required API Keys

None. The Deal Room Producer works with zero keys · it assembles content and produces either a web-page spec or a document package from what you give it.

### deliverability-manager

# Deliverability Manager · your domain's reputation, guarded

**Category:** Sales / Sequencing & Send
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Deliverability Manager keeps your sending infrastructure healthy so the campaigns everyone else built actually reach an inbox. It audits domain health (SPF, DKIM, DMARC, blacklists), monitors warmup progress on new inboxes, runs spam-placement checks before launches, manages inbox rotation so no single account carries too much volume, and enforces the volume rules that keep you out of spam. Deliverability is the silent killer of outbound · reply rates "mysteriously" halve and nobody checks the domain until it's burned. This skill makes the invisible visible: a health score, a clear set of limits, and a fix list ordered by impact.

## Required API Keys

Works with zero keys for the core audit · DNS records (SPF/DKIM/DMARC) and public blacklists are checked with standard command-line lookups (`dig`, public blacklist queries), no account required. Add keys for monitoring depth:

### delivery-status-reporter

# Delivery Status Reporter · clients never have to ask

**Category:** Operations / Client Comms
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Delivery Status Reporter sends progress to clients before they think to ask for it. It turns work-in-progress into short, proactive updates in the company voice · what moved this week, what's next, what's needed from them · and flags milestone moments that deserve a proper notification instead of a status line. It keeps a per-client cadence so no active client goes quiet, because the moment a client has to ask "any update?", trust has already dipped.

One rule governs everything: good news can automate, bad news goes through a human first. A delay announced carelessly costs more than the delay itself.

## Required API Keys

None. The Reporter drafts updates as files for the user to send. Zero keys required.

> **Email integration (optional):** If an email-sending key (e.g. `RESEND_API_KEY`) is in `.env`, the Reporter can send approved good-news updates directly after the user confirms each one. Without it, every update is a copy-paste-ready draft.

### dm-fulfillment-specialist

# DM Fulfillment Specialist · comment keywords become delivered assets, automatically

**Category:** Deals / Inbound
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The DM Fulfillment Specialist closes the loop on comment-CTA content. You post "comment GUIDE for the free guide" · this skill detects the keyword comments, drafts the DM that delivers the promised asset, and queues a follow-up message that turns a freebie grab into a conversation. Comment CTAs are one of the highest-converting lead mechanics on social, and they die when fulfillment is slow or sloppy: people who commented an hour ago and got nothing stop commenting. This skill makes delivery instant, consistent, and tracked · every commenter gets the asset, every delivery gets a follow-up, and you get a fulfillment log showing exactly who got what.

## Required API Keys

None required. Paste the comments from your post and everything below works with zero keys · you get a ready-to-send DM batch.

### document-extraction-engineer

# Document Extraction Engineer · documents in, structured data out, accuracy proven

**Category:** Operations / Build Ops
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Document Extraction Engineer turns piles of documents · forms, reports, invoices, case files, contracts · into structured data you can actually use. It works the way a production system gets built, not the way a demo gets faked: define the schema with you, build the extraction pipeline with per-field confidence scores, benchmark against a gold-standard set you label by hand, and only then process batches · with a human-review queue for anything below the confidence bar.

The difference between this and "just ask the AI to read the PDF" is one word: proven. Every accuracy claim comes from a measured benchmark, field by field. No benchmark, no claim.

## Required API Keys

None. Extraction runs on Claude's built-in document reading. Your documents stay local · nothing is sent anywhere except to the AI provider processing them.

### executive-assistant

# Executive Assistant · the calendar and inbox, handled

**Category:** Back Office / Operations
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Executive Assistant takes the two daily time sinks · calendar and inbox · and handles them like a sharp human EA would. Scheduling with proper buffers, timezone math that's never wrong, and conflict resolution that protects your deep-work blocks instead of giving them away to whoever asked first. On the inbox: every message sorted by what actually needs you, routine mail answered with drafts ready for one-click approval, and everything else filed where you can find it later.

The inbox isn't a to-do list someone else writes for you · but that's how most founders run it. This skill turns it back into a sorted queue where you only touch what needs a human.

## Required API Keys

None required. The Executive Assistant works from pasted emails and your stated calendar.

> **Calendar integration (optional):** If `CAL_API_KEY` (Cal.com) or Google Calendar access is configured, scheduling runs against real availability.

### finance-operations-analyst

# Finance Operations Analyst

**Category:** Back Office
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Finance Operations Analyst is the forward-looking money role. Where the Financial Reporting Analyst tells you what already happened, this one tells you what is about to happen. It establishes your opening cash position, projects inflows from recurring revenue and a probability-weighted pipeline, projects outflows from recurring costs and known one-offs, and turns that into a single honest answer: how many months of runway you have at the current burn.

Then it goes further. It runs scenarios · "what if we hire two people," "what if we lose the biggest client," "what if we double ad spend" · and shows what each one does to the runway. And it tracks actual spend against the budget by category, flagging overruns early enough to do something about them.

Most founders find out they are short on cash the month it happens. This skill tells you the month before, with the math to back it.

## Required API Keys

### financial-reporting-analyst

# Financial Reporting Analyst · the numbers, true and current

**Category:** Back Office / Finance
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Financial Reporting Analyst gives you one version of the financial truth. It compiles monthly revenue across every entity and currency you operate, tracks your pace against the income target with a straight answer · "on current pace you land at 78% of target" · and categorizes your expenses so the accountant gets a clean file instead of a shoebox. It forecasts trajectory from real numbers, not optimism: if the run rate says you miss, it says you miss, and shows what monthly number closes the gap.

Most founders know their revenue to the nearest "pretty good month." This skill knows it to the dollar, in every currency, and tells you whether the year is actually on track.

## Required API Keys

None required. The Analyst works from your records and what you tell it.

> **Payments integration (optional):** If `STRIPE_API_KEY` or `WISE_API_TOKEN` is in `.env`, the Analyst can pull real transactions to build revenue and expense data automatically.

### followup-coordinator

# Follow-Up Coordinator · nothing agreed on a call ever gets lost

**Category:** Operations / Client Comms
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Follow-Up Coordinator turns a meeting into a closed loop. Give it a transcript or notes and it extracts every action item with an owner, a deadline, and the exact quote it came from · then separates what YOUR side committed to from what THEIR side committed to. It drafts the same-day recap email in your voice, writes the items into a tracker so they survive past the inbox, and surfaces anything that blows past its deadline without confirmation.

Deals don't die from bad work. They die from "I thought you were sending that." This skill makes that sentence impossible.

## Required API Keys

None. The Follow-Up Coordinator works from pasted transcripts or notes. Zero keys required.

> **Notetaker integration (optional):** If `FIREFLIES_API_KEY` (or another notetaker key) is in `.env`, the Coordinator can pull the latest transcript automatically instead of requiring a paste. Without it, just paste your notes.

### help-content-writer

# Help Content Writer · the questions that repeat, answered once, forever

**Category:** Customer / Support
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Help Content Writer turns your support history into a self-serve layer that answers questions before they become tickets. It does three things: answers repeated questions instantly from the knowledge base, converts every novel resolved question into a draft help article so it never has to be answered manually twice, and tracks deflection · which articles are actually killing ticket volume and which gaps still generate repeats.

Every support team rediscovers the same truth: 60-80% of tickets are the same twenty questions. This skill makes each of those questions expensive exactly once. A human reviews every article before it publishes · the bot drafts, the human owns what customers read.

## Required API Keys

None. The Help Content Writer works from your resolved tickets, support transcripts, and existing docs · pasted in, exported, or already living in the knowledge base. No external APIs required.

## How to Run

### icp-strategist

# ICP Strategist · who you sell to, decided properly

**Category:** Sales / Targeting
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The ICP Strategist turns your win/loss history into ideal customer profiles that agents can actually act on. It reads your closed-won and closed-lost deals · from your knowledge base, a CRM export, or a structured interview · extracts the patterns that separate wins from losses, and writes one tight ICP page per vertical. Every downstream skill on the map (lead finding, cold email, qualification, content) reads these files. Bad targeting poisons everything after it; this is the START HERE node of the Sales branch for a reason.

## Required API Keys

None. The ICP Strategist works entirely from evidence you already have · your knowledge base, a pasted CRM export, or your answers to its interview. No external APIs required.

### inbound-response-manager

# Inbound Response Manager · every inbound lead engaged in minutes, qualified before a human looks

**Category:** Deals / Inbound
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Inbound Response Manager owns the front door. Every inbound lead · form fill, email, DM · gets an acknowledgment drafted within minutes, gets parsed and scored on budget, fit, and urgency, and lands in a sorted queue before a human ever opens the inbox. It covers three jobs in one pass: speed-to-lead (instant engagement), lead qualification (intake parsing + scoring), and inbox triage (everything sorted into client, lead, brand deal, or noise). Inbound leads convert at multiples when answered inside five minutes; most companies take hours. This skill drafts everything · a human sends, until you explicitly wire it otherwise.

## Required API Keys

None required. Paste or forward your inbound · form submissions, emails, DMs · and everything below works with zero keys.

### inbox-manager

# Inbox Manager · triage and draft, never send

**Category:** Back Office
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Inbox Manager is the assistant that reads your inbox so you don't have to read all of it. Give it a batch of threads · pasted, or pulled via a read-only Gmail connection · and it sorts them into clear lanes, ranks what genuinely needs you, summarizes each in a line, and drafts a reply in your voice for anything that needs one. You skim the digest, approve or tweak the drafts, and you're done. The hard line that makes it safe to use on a real inbox: **it drafts, it never sends, never archives, never deletes, and never makes a commitment on your behalf.** You stay the only one who hits send.

## Required API Keys

| Key | What It Does | .env Variable |
|-----|-------------|---------------|
| Gmail | Read threads and save replies as **drafts** (never send) | `GOOGLE_OAUTH` (gmail.readonly + gmail.compose) |

**The key is optional. The Inbox Manager always runs** · paste a batch of emails and it triages and drafts them; you copy the approved replies into your mail client.

### instagram-content-analyst

# Instagram Content Analyst · reverse-engineer what's working on Reels

**Category:** Marketing
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Instagram Content Analyst scrapes Instagram reels from competitors and your own profile, transcribes the audio to extract spoken hooks, analyzes engagement patterns, and generates data-driven content ideas. Three-step pipeline: competitor analysis → your reel analysis → cross-reference ideation engine. Outputs a full report with winning patterns, top hooks, and 10+ new content ideas.

## Required API Keys

| Key | Where to Get It | .env Variable |
|-----|----------------|---------------|
| Apify | https://console.apify.com/account/integrations | APIFY_API_KEY |
| Deepgram | https://console.deepgram.com/signup | DEEPGRAM_API_KEY |

> Deepgram has a free tier ($200 in credits). Used for transcribing reel audio to extract spoken hooks.

**What works without keys:**
- **No Apify key** · the Instagram Content Analyst can't scrape reels, so the pipeline can't run.

### integration-engineer

# Integration Engineer · client systems, wired together properly

**Category:** Operations / Build Ops
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Integration Engineer connects the systems a business actually runs on · CRMs, calendars, transcription tools, payment processors, email platforms · with direct API integrations built like production software. It maps the data flow before writing a line of code, wires webhooks with verified signatures, makes every operation idempotent so retries can't duplicate records, and handles failure explicitly instead of hoping. Then it tests the whole thing against real data before anyone calls it done.

The difference between an integration and a liability is what happens on the bad day: the retry, the duplicate webhook, the API that times out mid-sync. This skill builds for the bad day.

## Required API Keys

The keys for whatever systems are being connected · typically a CRM key, a calendar OAuth credential, a payments key. These live in `.env`, never in code or chat.

### knowledge-base

# Company Knowledge Base · Node Zero

**Category:** Foundation
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

> Every AI department starts at the same node. This skill builds it.

## What This Is

A company knowledge base is the single place your AI agents read from and write to. It is not software you buy · it is a set of plain-text files with a strict convention, living next to your work. Every other job on the SkillTree map gets dramatically better the day this exists, because an agent with context writes like a colleague and an agent without context writes like a stranger.

This skill scaffolds the whole thing in one session: the file structure, the core files written by interviewing you, and the maintenance rules that keep it alive.

## Required API Keys

None. This runs on Claude's built-in capabilities. Your knowledge base is plain markdown · no database, no vendor, no lock-in.

## How to Run

Drop this file into your project (or `~/.claude/skills/` if you use Claude Code), then tell Claude:

- "Set up my knowledge base"
- "Run node zero"
- "Build my company brain"

---

## Agent Instructions

### lead-magnet-producer

# Lead Magnet Producer · proven demand becomes a gated asset

**Category:** Marketing / Repurposing
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Lead Magnet Producer turns content that already performed into gated assets that capture the demand it proved. It picks the topic from evidence · your best-performing posts, the comment sections asking "how do I do this?" · then builds the full package: the guide itself, the landing page copy, the delivery flow, and the comment-CTA keyword that connects a post to the gate.

The order matters and it's the whole point: demand first, asset second. Most lead magnets fail because someone built the guide they wanted to write, then went hunting for an audience. This skill only builds guides the audience already voted for.

## Required API Keys

All optional:

- **Email delivery** · `RESEND_API_KEY`, `BEEHIIV_API_KEY`, or ConvertKit/Mailchimp equivalent, for wiring the delivery email
- **Comment automation** · ManyChat or similar token, if the comment-keyword flow is automated

### lead-scoring-analyst

# Lead Scoring Analyst · effort goes where it converts

**Category:** Sales / Enrichment
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Lead Scoring Analyst scores every lead on a list against your ICP files and sorts the output into tiers: A-tier gets the personalized, multi-touch treatment; B-tier gets the standard sequence; C-tier gets disqualified · with the reason written down. Most outreach effort is wasted on leads that were never going to convert, and most teams can't say why a lead is on the list beyond "it was in the export." This skill makes fit explicit, repeatable, and arguable: every score traces to specific ICP criteria, so when the founder disagrees with a tier, the fix is a better ICP file, not a vibe debate.

## Required API Keys

None. The Lead Scoring Analyst works entirely from your ICP files and the lead data you already have · ideally a list that's been through the Data Enrichment Specialist. Scoring is judgment against criteria, not an API call. If lead records are missing fields the ICP scores on, it flags them as ungradeable rather than guessing.

### lead-sourcing-manager

# Lead Sourcing Manager · builds your lead lists

**Category:** Lead Gen
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Lead Sourcing Manager builds targeted lead lists · both companies and people. Tell it what you're looking for (industry, size, location, role) and it will find matching leads using the best method available based on your API keys. It supports multiple data sources ranked by quality, so you always get the best results your setup allows.

## Required API Keys

**Core pipeline (verified, tested 2026-04-03):**

| Service | What It Does | .env Variable | Required? |
|---------|-------------|---------------|-----------|
| Apollo | Find companies + people, enrich with verified emails/LinkedIn | APOLLO_API_KEY | **Yes** · primary method |
| Exa | Semantic company discovery, research context | EXA_API_KEY | **Yes** · supplements Apollo |
| Hunter.io | Email fallback when Apollo returns "unavailable" | HUNTER_API_KEY | Optional |

**Optional (not needed for core pipeline):**

### linkedin-outreach-specialist

# LinkedIn Outreach Specialist

**Category:** Outreach
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The LinkedIn Outreach Specialist writes personalized LinkedIn outreach · connection requests and DM sequences. Give it a prospect (or point it at an existing report from the **Prospect Research Analyst** (prospect-research-analyst.md)) and it will craft a connection request + follow-up DM sequence that feels peer-to-peer, not salesy. Optionally pushes leads directly to HeyReach for automated LinkedIn campaigns.

## Required API Keys

| Key | Where to Get It | .env Variable |
|-----|----------------|---------------|
| HeyReach | https://app.heyreach.io/settings | HEYREACH_API_KEY |

> HeyReach is optional · the LinkedIn Outreach Specialist always generates the copy. The API key is only needed to push leads into HeyReach campaigns. With no keys at all, the LinkedIn Outreach Specialist still produces the complete connection request + 3-DM sequence · you just send it manually.

### market-mapper

# Market Mapper · the whole addressable market, counted and named

**Category:** Sales / Targeting
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Market Mapper runs a census of every company that fits your ICP in a target vertical · before a single email gets written. It pulls counts from databases, directories, and web sources, dedupes across them, and produces a market map with real numbers: how many companies exist, how they segment by size and geography, and how many you can actually reach. The output kills two failure modes at once: launching a campaign into a vertical with 80 reachable companies, and "TAM" slides built on someone's estimate. Campaign math starts here · list size, expected reply volume, and how long the vertical lasts before you've touched everyone.

## Required API Keys

Works with zero keys · you'll get a map built from public sources and structured estimates, clearly marked as such. Add keys for hard counts:

- **`APOLLO_API_KEY`** · filtered company counts and exportable lists from the Apollo database.

### meeting-booking-coordinator

# Meeting Booking Coordinator · from interested reply to booked call, no back-and-forth

**Category:** Deals / Reply Handling
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Meeting Booking Coordinator turns "yes, let's talk" into a calendar invite with the fewest possible messages. Give it an interested reply and your availability · it drafts the slot-proposal message (specific times, not "what works for you?"), handles the confirmation, and runs the no-show defense: a day-of reminder before the call and a recovery sequence after a no-show that rebooks without guilt-tripping. Deals die in scheduling limbo · five-message back-and-forths, ghosted calendar links, no-shows nobody chases. This skill closes that gap. Drafts only; you send.

## Required API Keys

None required. Tell it your availability (or paste your calendar for the week) and everything below works with zero keys.

> **Cal.com integration (optional):** If `CAL_API_KEY` is in `.env`, the Coordinator can pull real open slots from your Cal.com event types and propose times that are actually free · and check whether a prospect booked.

### meeting-intelligence-engineer

# Meeting Intelligence Engineer · every call captured, structured, remembered

**Category:** Deals / Call Cycle
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Meeting Intelligence Engineer makes sure no call evaporates. It audits how your meetings are captured today, installs a filing convention for transcripts, wires a pipeline (automatic if you have a notetaker API key, manual habit if you don't), and extracts the four things that matter from every meeting: outcomes, action items with owners, decisions, and deal-state changes. Then it writes those back into the relevant client file · same day, every time. Most businesses lose more deal intelligence in untranscribed calls than they ever capture in their CRM. This is the START HERE node of the Deals branch.

## Required API Keys

None required. The Meeting Intelligence Engineer works from pasted transcripts or call notes with zero keys.

> **Notetaker integration (optional):** If `FIREFLIES_API_KEY` (or a similar notetaker key like `OTTER_API_KEY` / `GRAIN_API_KEY`) is in `.env`, it pulls transcripts via API automatically.

### newsletter-editor

# Newsletter Editor · the weekly email, written and built

**Category:** Marketing / Distribution
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Newsletter Editor assembles and writes the weekly email. It gathers the week's raw material · posts that performed, things you shipped, ideas you captured · structures it into a consistent issue format in your brand system, writes the whole thing in your voice, and produces subject line variants tested against one question: would a busy person open this? The output is a complete issue, ready to paste into your sending platform · or pushed there directly if a key exists.

The job it kills: the newsletter that's "important" every week and skipped every week because assembling it takes three hours. This takes the three hours.

## Required API Keys

All optional:

- **Beehiiv** · `BEEHIIV_API_KEY` for creating the post as a draft directly in your publication
- **Resend / ConvertKit / Mailchimp** · equivalent key for draft creation on those platforms

### outbound-inbox-manager

# Outbound Inbox Manager · every reply read, tagged, and answered in minutes

**Category:** Deals / Reply Handling
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Outbound Inbox Manager reads every reply to your outbound campaigns, classifies each one · interested, objection, referral, not-now, never, auto-reply · and drafts the response. Interested replies get a booking message with your calendar link. Objections get answered from an objection library the skill builds and maintains as it works. Hard nos go on a suppression list. You get a triage table and a queue of drafts ready to approve and send. The point is speed: most outbound replies sit for 6+ hours before anyone answers, and interest decays by the hour. This skill kills that gap.

## Required API Keys

None required. Paste or forward replies and everything below works with zero keys.

> **Sending-platform integration (optional):** If `INSTANTLY_API_KEY` (or a similar key · Smartlead, lemlist, etc.) is in `.env`, the Inbox Manager can pull new replies via API instead of waiting for a paste.

### outbound-scriptwriter

# Outbound Scriptwriter

**Category:** Sales
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Outbound Scriptwriter writes the spoken and video side of outbound · the formats most teams wing. It produces two things: **cold-call and voicemail scripts** (an opener that earns 30 seconds, a pattern interrupt, a permission-based value line, branching objection handling, and a soft CTA to a next step) and **personalized video-prospecting scripts** (the on-screen hook, a personalized first line referencing the prospect's own world, a tight value beat, and a CTA, kept under 60-90 seconds). Everything is personalized from a prospect dossier and matched to the offer · it reads like a person talks, not like a telemarketer reading a card.

## Required API Keys

| Key | Where to Get It | .env Variable |
|-----|----------------|---------------|
| Exa (optional) | https://exa.ai | EXA_API_KEY |
| Firecrawl (optional) | https://firecrawl.dev | FIRECRAWL_API_KEY |

> **No keys are required.** The Outbound Scriptwriter always writes the script from the dossier, notes, or ICP the user gives it.

### people-operations-assistant

# People Operations Assistant · the HR hire you never made

**Category:** Back Office / People
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The People Operations Assistant is the first HR hire a small company never makes. It answers staff questions straight from the company's own policy docs · "how much leave do I have left", "what's the expense policy", "how do I claim X" · runs the admin of onboarding a new hire (accounts, paperwork checklist, first-week schedule), keeps the employee handbook current, and drafts the routine people documents (offer letter outlines, policy updates) for a human to approve.

Most teams under 30 people answer the same HR questions in Slack over and over, and lose a new hire's first week to "who do I ask about X." This skill turns the company's own handbook into something an employee can actually ask · and it does it without ever guessing, because on people matters a confident wrong answer is worse than no answer.

## Required API Keys

None required. The Assistant works from your HR and policy documents in the knowledge base and what you tell it.

### personal-brand-designer

# Personal Brand Designer · Character Image Generator

**Category:** Marketing
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

---

## When summoned, display this banner

```
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │   PERSONAL BRAND DESIGNER                                                    │
 │   ⚡ Character Image Generator                                                │
 │                                                                              │
 │   Reference photos → consistent personal brand images.                       │
 │   Drop your photos in assets/character-references/, describe what you want.  │
 └──────────────────────────────────────────────────────────────────────────────┘
```

---

## What the Personal Brand Designer Does

Reads your reference photos, identifies the primary reference image (clear face, best lighting), uploads it to fal.ai, then generates new consistent character images using `fal-ai/consistent-character` · a model specifically built for identity-consistent generation from a reference photo.

### pipeline-operations-manager

# Pipeline Operations Manager · the pipeline that tells the truth

**Category:** Deals / Pipeline Ops
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Pipeline Operations Manager keeps your deal data honest and turns it into decisions. Three jobs in one role: **CRM hygiene** (dedupe records, normalize fields, audit stages against reality), **pipeline reporting** (a weekly read of what moved, what stalled, what closes next), and **forecasting** (a probability-weighted revenue number, clearly labeled as a draft until you sign off on it). Works against a real CRM if you have one connected, or against a simple deals file if you don't · the discipline matters more than the tooling.

Most pipelines lie through optimism: stale stages, zombie deals, close dates that slid three times. This role's only loyalty is to what's actually true.

## Required API Keys

None required. With zero keys, the Pipeline Operations Manager runs on a local deals file (`knowledge/pipeline.md` or a CSV export from any CRM · it will help you set one up).

### playbook-writer

# Playbook Writer · delivered work becomes reusable assets

**Category:** Operations / Knowledge
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Playbook Writer captures the most expensive thing a business produces and usually throws away: how the work actually got done. It handles two jobs. **SOP generation** · after an engagement ships, it extracts the repeatable method into a playbook in `knowledge/playbooks/`, so the second time this kind of work shows up it starts from a recipe instead of a blank page. **Handoff docs** · when a system ships to a client, it writes the documentation and runbook that let someone who didn't build it operate it, fix it, and trust it.

Every engagement either makes the next one faster or it doesn't. This skill is the difference · it's how delivered work compounds instead of evaporating.

## Required API Keys

None. The Playbook Writer works from your project files, outputs, and what you tell it. Zero keys required.

### presentation-designer

# Presentation Designer · decks in the brand system, built in a session

**Category:** Marketing
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Presentation Designer builds a complete webinar or talk deck in one sitting: the narrative arc, slide-by-slide content, speaker notes, and design direction in your brand's visual language. Give it the talk topic, the audience, and the goal · it returns a deck you could present tomorrow, structured so the talk sells without feeling like a pitch. It writes slides the way good speakers use them: few words on screen, real substance in the notes, and a deliberate path from hook to close.

## Required API Keys

None. The Presentation Designer works entirely from your knowledge base and the talk brief. No external APIs required.

### pricing-analyst

# Pricing Analyst · anchors, phases, and ROI math per deal

**Category:** Deals / Deal Artifacts
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Pricing Analyst builds the numbers case for each deal before you quote it. Give it the deal context · what you're building, for whom, what problem it kills · and it produces three things: an anchor (what solving this costs the client today, usually in headcount or lost revenue), a phased deal structure (entry phase → main build → retainer), and an ROI model the prospect's own CFO could check. You walk into the pricing conversation with the math already done.

What it never does: pick your price. Every output is decision support · a range, a structure, a justification. The final number comes from you, every time.

## Required API Keys

None. The Pricing Analyst runs on deal context, your offer doc, and public salary/cost benchmarks Claude already knows. Zero keys, zero external services.

### proposal-writer

# Proposal Writer · from call context to signed-ready document

**Category:** Deals / Deal Artifacts
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Proposal Writer turns a sales call into a proposal draft · same day, structured the way deals actually close. Give it a transcript, call notes, or a deal summary and it extracts the problem in the client's words, drafts the scope as phases with deliverables, and outputs a clean markdown document ready for your PDF or template pipeline. It learns from your past proposals: when a similar won deal exists in `outputs/proposals/`, it matches that structure instead of inventing a new one.

It drafts structure and prose. You own scope and price · every number and every scope decision is flagged for your confirmation before anything goes out.

## Required API Keys

None. The Proposal Writer runs on Claude's built-in capabilities plus your call notes and past proposals. Zero keys, zero external services.

### prospect-research-analyst

# Prospect Research Analyst · deep intel on any prospect

**Category:** Research
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Prospect Research Analyst builds deep, actionable intelligence reports on target prospects. Give it a name or LinkedIn URL and it will scrape LinkedIn, search the web, analyze company context, score qualification fit, and produce a structured report · all personalized to your business so you · or the **Cold Email Copywriter** (cold-email-copywriter.md) and the **LinkedIn Outreach Specialist** (linkedin-outreach-specialist.md) · can craft killer outreach.

## Required API Keys

| Key | Where to Get It | .env Variable | Required? |
|-----|----------------|---------------|-----------|
| Exa | https://dashboard.exa.ai/api-keys | EXA_API_KEY | Yes |
| Firecrawl | https://firecrawl.dev/app/api-keys | FIRECRAWL_API_KEY | Yes |
| Apify | https://console.apify.com/account/integrations | APIFY_API_KEY | Optional · adds LinkedIn profile/activity scraping |

### publishing-manager

# Publishing Manager · the content calendar that actually ships

**Category:** Marketing / Distribution
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Publishing Manager takes finished content and gets it live. It builds the posting schedule, formats each piece for its platform, and either posts via API (where keys exist) or hands you a prepared post package so tight that publishing manually takes thirty seconds per post. It tracks what's queued, what shipped, and what's stuck · so the calendar stops being a graveyard of "scheduled" posts that never went out.

One rule sits above everything: it never posts anything without your explicit approval on that specific post. A wrong-account post or a draft that goes live early is a screenshot forever.

## Required API Keys

All optional. The Publishing Manager checks `.env` for whatever platform keys exist:

- **Instagram / Facebook** · `INSTAGRAM_ACCESS_TOKEN` (Meta Graph API)
- **LinkedIn** · `LINKEDIN_ACCESS_TOKEN`
- **X / Twitter** · `X_API_KEY` (or bearer token)
- **Scheduling tools** · Buffer, Later, or similar, if a token is present

### qa-engineer

# QA Engineer · nothing reaches a client unverified

**Category:** Operations / Build Ops
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The QA Engineer is the last gate before anything reaches a client. It verifies every build against real data · running the actual system on actual inputs and checking the actual outputs, not reading the code and nodding. It re-checks what a change might have broken, not just what it was meant to fix, and it writes a verification log for every deliverable so "it works" is a documented claim with evidence, dates, and the exact cases tested.

The principle underneath: sign-off is never delegated to the thing being QA'd. The system that produced the work doesn't get to grade it · verification comes from independently checking outputs against reality.

## Required API Keys

None. The QA Engineer runs whatever the build runs and reads its outputs. Zero keys of its own required.

### reactivation-specialist

# Reactivation Specialist · the revenue sleeping in your dead-deals column

**Category:** Deals / Pipeline Ops
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Reactivation Specialist works the deals everyone else gave up on. Two jobs in one role: **reactivation** · on a monthly schedule, it surfaces dormant and lost deals worth another shot and drafts re-openers that lead with something genuinely new (a result, a capability, a change on their side · never "just checking in"); and **win/loss analysis** · every closed deal gets a tagged reason, and the patterns feed back into who you target and how you pitch.

Dead deals already cost you the acquisition work · the call, the proposal, the relationship. Reviving one is the cheapest revenue in the business. You approve the revival list before anything is drafted; nothing reaches a former prospect without your sign-off.

## Required API Keys

None. The Reactivation Specialist runs on your deals file or CRM export and your client notes. Zero keys, zero external services.

### records-administrator

# Records Administrator · every system agrees with every other system

**Category:** Back Office / Operations
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Records Administrator keeps your sources of truth from drifting apart. It runs two-way sync between your knowledge base and your CRM · deals, contacts, and statuses stay current everywhere, so the deal you closed Tuesday isn't still "negotiating" in three other places by Friday. And it tracks entity compliance: every filing, renewal, and obligation per legal entity, on a calendar that warns you before deadlines instead of after.

Drift is silent. You don't notice the CRM is three weeks stale until you make a decision off it. You don't notice the annual filing until the penalty notice. This skill notices both, on schedule.

## Required API Keys

None required. The Records Administrator works from your `knowledge/` files and pasted CRM exports.

> **CRM integration (optional):** If a CRM key (`HUBSPOT_API_KEY`, `ATTIO_API_KEY`, or similar) is in `.env`, sync runs against the live CRM directly.

### red-team-reviewer

# Red Team Reviewer · claims get attacked before they get believed

**Category:** Intelligence / Synthesis
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Red Team Reviewer takes any report, claim, plan, or proposal and attacks it before you act on it. It checks sources, hunts contradictions, surfaces hidden assumptions, and stress-tests the logic · then issues a verdict per claim: verified, shaky, or refuted. Research that's never been attacked isn't research; it's a first draft with confidence. This is the quality gate between "an agent wrote this" and "I'm making a decision based on this."

One hard rule defines this skill: the red team must be a separate run from the author. An agent reviewing its own output in the same session inherits its own blind spots. Open a fresh session, run the Red Team Reviewer, and let it see the work cold.

## Required API Keys

| Key | Where to Get It | .env Variable |
|-----|----------------|---------------|
| Exa (optional) | https://dashboard.exa.ai/api-keys | EXA_API_KEY |

> Exa is optional.

### relationship-mapper

# Relationship Mapper · the warm path into any account

**Category:** Intelligence / People
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Relationship Mapper finds the warm path into any target account. Give it a company or a person you want to reach, and it maps who you already know that knows them · mutual connections, past colleagues, shared communities, investors in common, people who've engaged with both of you. Cold outreach converts at 1-3%; a warm intro converts at 30%+. This skill exists to make sure you never go in cold when a warm path existed and you just didn't see it.

It maps paths. It never sends. Spending relationship capital · asking someone for an intro · is always a human decision.

## Required API Keys

| Key | Where to Get It | .env Variable |
|-----|----------------|---------------|
| Exa (optional) | https://dashboard.exa.ai/api-keys | EXA_API_KEY |

> Exa is optional. With it, the Relationship Mapper can research target people's public footprint (shared employers, podcasts, communities, co-authored content).

### reliability-engineer

# Reliability Engineer · the on-call engineer for your AI stack

**Category:** Operations
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Reliability Engineer is the on-call engineer for your AI stack. Once a business runs agents and automations in production, something has to watch them · and "it ran yesterday" is not the same as "it ran this morning."

It does three jobs:

1. **Monitoring & Alerting** · sweeps the known automations, crons, and agents for uptime and failures: failed runs, error spikes, and the quiet killer · silent stalls, where a job stops firing and nothing throws an error because nothing ran.
2. **Cost & Usage Tracking** · pulls token and API spend, compares it to a monthly budget, runs a burn-rate calc, and flags overruns before the invoice does.
3. **Incident Response** · when something breaks, it runs the runbook: triage by impact, reproduce, find root cause, fix or escalate, and write a two-paragraph incident note so the same thing does not break twice.

The principle underneath: production systems fail silently.

### scriptwriter

# Scriptwriter · full scripts in the house voice, hook to CTA

**Category:** Marketing
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Scriptwriter turns an idea into a complete, ready-to-film reel or video script · hook, tension, payoff, CTA · written in your voice, not a generic creator voice. Give it a topic, an angle, or a rough brain-dump and it produces a word-for-word script built on a proven short-form structure, with multiple hook variants so you can test openings without rewriting the whole thing. It learns your voice from samples of your real content and refuses to ship anything that sounds like a marketing robot.

## Required API Keys

None. The Scriptwriter works entirely from your knowledge base, your content samples, and the idea you bring. No external APIs required.

### seo-engineer

# SEO Engineer · legible to Google, legible to LLMs

**Category:** Marketing / Distribution
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The SEO Engineer makes your site legible to the two things that now decide whether you get found: search engines and language models. It audits and ships the technical layer · schema markup (JSON-LD), `llms.txt`, sitemaps, robots rules, metadata, canonical tags · and the share surface: every page gets title/description metadata and open-graph imagery specs, so links look deliberate instead of broken when they hit Slack, LinkedIn, or iMessage.

This is two jobs in one engineer: **SEO & GEO** (generative engine optimization · being citable by LLMs, not just rankable by Google) and **OG & Share Surface**. Both are infrastructure, both compound, both are usually nobody's job. Now they're this skill's job.

## Required API Keys

None. The SEO Engineer reads and writes code in your repo. If the site is deployed and the user wants live verification, it can check rendered pages with `curl` · no key needed for that either.

## How to Run

### signal-monitoring-analyst

# Signal Monitoring Analyst · catch the change before your competitor does

**Category:** Intelligence
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Signal Monitoring Analyst watches a list of target accounts, competitors, and topics on an ongoing basis and surfaces what changed · funding rounds, hiring sprees, leadership moves, tech-stack changes, layoffs, product launches, news mentions, and social chatter. It scores every signal for relevance and urgency against your ICP, then routes the important ones to the right destination (a person, a Slack channel, an email digest, or another agent) while filtering the noise. It is the difference between finding out a target raised a Series B from a cold email reply versus the morning it happened.

## Required API Keys

### skilltree-audit

# SkillTree Audit · your tree, computed

**Category:** Foundation
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

> The map asks 137 questions. This skill answers them by looking at your actual stack · then hands you a file the map can import.

## What This Is

The SkillTree map (altari.ai/skilltree) charts every AI job-to-be-done in a business across 7 departments. You can mark your own deployment status by hand · or you can run this audit and let an agent compute it. It inspects your environment for evidence (keys, tools, files, integrations), asks you only what it can't see, grades honestly, and outputs:

1. **`skilltree-your-tree.json`** · import it on the map (V1.0 chip → Import) and watch your tree light up
2. **A gap report** · where you actually are, the FTE cost of your biggest gaps, and the three builds to do next, in dependency order

## Required API Keys

None. The audit reads your environment; it never calls external services.

## How to Run

Drop this file into the project where your business actually runs (or `~/.claude/skills/` if you use Claude Code), then tell Claude:

### social-copywriter

# Social Copywriter · captions that pull comments, platform-correct every time

**Category:** Marketing
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Social Copywriter writes the caption layer · the text that decides whether a post converts attention into action. Give it a finished reel, a carousel, a topic, or a script, and it produces platform-specific captions with the mechanics handled correctly: comment-CTA placement, hashtag discipline, character limits, line-break rhythm, and the first-line hook that platforms truncate everything after. One post in, native captions out for every platform you publish on · each written for how that platform's feed actually works, not copy-pasted across all of them.

## Required API Keys

None. The Social Copywriter works entirely from your knowledge base and the content you bring. No external APIs required.

### social-prospecting-specialist

# Social Prospecting Specialist · turns post comments into pipeline

**Category:** Lead Gen
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Social Prospecting Specialist scrapes commenters from viral LinkedIn posts, enriches their profiles, scores them against your ICP, and writes personalized DMs for the best fits · all in one shot. Perfect for lead magnet posts, thought leadership content, or any post where your ideal customers are engaging. Turns comment sections into qualified pipeline.

## Required API Keys

| Key | Where to Get It | .env Variable |
|-----|----------------|---------------|
| Apify | https://console.apify.com/account/integrations | APIFY_API_KEY |

**If the Apify key is missing:** the Social Prospecting Specialist can't scrape LinkedIn · but it can still score and write personalized DMs if you paste in a list of commenters yourself (names + headlines + comment text). It will tell you where to get a key rather than fail silently.

### solutions-engineer

# Solutions Engineer · discovery call to visual prototype, same day

**Category:** Sales
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Solutions Engineer turns discovery calls into visual prototypes · same day, before the follow-up. Give it a transcript or call notes and it extracts the brief, chooses the right format (React app, Mermaid diagram, Notion doc, or Loom script), generates a ready-to-run build prompt, and drafts the message you send to the prospect. The follow-up call becomes about scope, not convincing them it's possible.

## Required API Keys

None. The Solutions Engineer uses your call notes or a connected notetaker. No external APIs required · everything below works with zero keys.

> **Fireflies integration (optional):** If `FIREFLIES_API_KEY` is in `.env`, the Solutions Engineer can pull the latest transcript automatically instead of requiring a paste. Without it, just paste your notes.

### support-answerer

# Support Answerer · answers from your docs, never from thin air

**Category:** Customer
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Support Answerer turns your existing support knowledge into drafted answers a human can approve and send. It reads your help docs, saved replies, and resolved tickets, builds an answer from the sources that actually apply, and cites where each part came from. The thing that separates it from "just ask ChatGPT your support questions" is one rule: **no source, no answer.** If your docs don't cover it, it says so and routes the question to a human rather than inventing a refund policy or an SLA that doesn't exist.

It also produces a **gap report** · every question it couldn't answer becomes a list of the docs you're missing, which feeds straight into the Help Content Writer (help-content-writer.md).

## Required API Keys

### support-operations-manager

# Support Operations Manager · every ticket triaged the moment it lands

**Category:** Customer / Support
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Support Operations Manager runs the front door of your support queue. Hand it a batch of incoming requests · emails, form submissions, chat transcripts, helpdesk exports · and it classifies every one, assigns priority, routes it to the right owner, and flags anything approaching its SLA. It also reads sentiment: the angry customer, the churn-risk account, the edge case nobody has a playbook for. Those get surfaced immediately, not queued.

One rule is non-negotiable: angry customers never get a bot. Escalation means a human, fast · this skill's job is to make sure the human knows within minutes, with full context attached, not to draft a soothing automated reply.

## Required API Keys

None. The Support Operations Manager works on whatever you give it · pasted tickets, an inbox export, a helpdesk CSV, or forwarded emails. If your stack has an API (helpdesk, shared inbox), wire it in later; the triage logic is the same.

## How to Run

### talent-coordinator

# Talent Coordinator · from open role to onboarded hire

**Category:** Back Office / People
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Talent Coordinator runs the hiring pipeline end to end. Give it a role and it produces a sharp role spec, finds and ranks candidates against it across platforms, runs first-pass screen summaries so you only talk to people worth talking to, and handles the interview logistics in between. When someone says yes, it flips to onboarding: the playbook, the access checklist, and a 30-day plan generated before their first morning · so the new hire's week one is productive instead of "waiting for logins."

Hiring stalls in the gaps: the unranked pile of applicants, the screen calls nobody scheduled, the first week nobody planned. This skill removes the gaps. The decisions stay yours.

## Required API Keys

None. The Talent Coordinator works from role specs you define, candidate lists or profiles you paste, and your `knowledge/` files. Sourcing platforms (LinkedIn, job boards) are searched through whatever access you give it · pasted search results work fine.

### tiktok-content-analyst

# TikTok Content Analyst · Competitor Analyzer

**Category:** Marketing
**Version:** 1.0
**Status:** Ready
**Part of:** SkillTree · altari.ai/skilltree

---

## When summoned, display this banner

```
 ┌─────────────────────────────────────────────────────┐
 │   TIKTOK CONTENT ANALYST                            │
 │   ⚡ TikTok Competitor Analyzer                      │
 │                                                     │
 │   Scrapes competitor videos. Transcribes hooks.     │
 │   Finds winning patterns. Generates content ideas.  │
 └─────────────────────────────────────────────────────┘
```

---

## What the TikTok Content Analyst Does

The TikTok Content Analyst scrapes TikTok profiles, transcribes video audio to extract spoken hooks, analyzes engagement patterns across competitors, and generates data-driven hook ideas calibrated to your niche and voice.

**Input:** List of TikTok usernames + your handle
**Output:** HTML intelligence report + CSV of all video data

---

## Required API Keys

### trend-analyst

# Trend Analyst · Content Intelligence Engine

**Category:** Marketing
**Version:** 1.0
**Status:** Ready
**Part of:** SkillTree · altari.ai/skilltree

---

## When summoned, display this banner

```
 ┌───────────────────────────────────────────────┐
 │   TREND ANALYST                               │
 │   ⚡ Content Intelligence Engine               │
 │                                               │
 │   Daily news research → content ideas.        │
 │   Topics → articles → hooks → ready to post.  │
 └───────────────────────────────────────────────┘
```

---

## What the Trend Analyst Does

The Trend Analyst researches the latest news across your topics of interest, extracts key insights from the most relevant articles, and generates hyper-personalised content ideas based on what's actually happening today · not generic advice.

**Input:** Research objectives + topics of interest + business context
**Output:** Curated news digest + 10–15 content ideas, saved as HTML report

---

## Variables

| Variable | Description |
|----------|-------------|
| `research_objectives` | What insights you want from the research (e.g.

### vertical-analyst

# Vertical Analyst · is this market worth entering, answered with evidence

**Category:** Intelligence / Markets
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Vertical Analyst answers one question: is this vertical worth entering? It investigates demand signals, budget authority, buying behavior, and competitor saturation for any market you're considering · then delivers a go/no-go verdict with the reasoning attached. Most founders pick verticals on vibes: a good conversation with one prospect becomes a "huge market." This skill replaces that with evidence, so you commit outreach, content, and build time only to markets that can actually pay.

The verdict feeds directly downstream: a GO becomes the input for ICP definition, lead sourcing, and outreach. A NO-GO saves you the quarter you'd have wasted finding out the hard way.

## Required API Keys

| Key | Where to Get It | .env Variable |
|-----|----------------|---------------|
| Exa (optional) | https://dashboard.exa.ai/api-keys | EXA_API_KEY |

> Exa is optional.

### video-editor

# Video Editor · recordings become finished, clipped, captioned content

**Category:** Marketing
**Version:** 1.0
**Part of:** SkillTree · altari.ai/skilltree

## What It Does

The Video Editor turns raw recordings into publishable content · without you sitting in a timeline for hours. It works two jobs. First, **edit planning**: from a recording and its transcript, it produces a programmatic edit plan · text overlays with exact timestamps, captions synced to the transcript, cut points, and motion notes · precise enough to execute in any editor or hand to a programmatic pipeline like Remotion or ffmpeg. Second, **clip extraction**: it reads a long recording (podcast, webinar, call, livestream) and returns a ranked list of short-form clip candidates with in/out timestamps, the verbatim moment that makes each clip work, and a suggested hook for each.

## Required API Keys

| Key | Where to Get It | .env Variable |
|-----|----------------|---------------|
| Deepgram | https://console.deepgram.com/ | DEEPGRAM_API_KEY |

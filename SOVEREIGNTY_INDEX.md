# GIGA Sovereignty Index

The Sovereignty Index measures **evidenced control over the shape of a life**:

> How far is the present life authored, optional, deliberately attended to, executable,
> operationally independent, and recoverable?

It does not measure human worth, intelligence, productivity, happiness, morality, or the value
of another person. It is a private decision instrument, not a validated clinical scale.

## Why one number is not enough

The headline uses seven control dimensions:

| Dimension | Weight | Question |
|---|---:|---|
| Authorship | 22% | Are commitments endorsed, practically rejectable, stable under counterfactuals, and behaviorally coherent? |
| Life alignment | 16% | Do my decisions and allocation match values I actually endorsed? |
| Optionality and exit power | 16% | Could I realistically choose otherwise? |
| Attention sovereignty | 14% | Is my attention directed or captured? |
| Agency conversion | 14% | Do chosen intentions become actions and receipts? |
| Operational independence | 10% | Are income, tools, documents, and capabilities portable? |
| Reversibility and recovery | 8% | Can I roll back and regain control after disruption? |

Dimensions use a weighted arithmetic mean. The headline uses a weighted geometric mean and
cannot exceed the weakest dimension by more than 20 points. This prevents money, technical
power, or frenetic execution from hiding a collapse elsewhere.

The calculator publishes evidence coverage and reliability separately:

- missing data stays unknown;
- model inference is weaker than a log or receipt;
- old observations lose reliability;
- evidence strength never secretly changes the observed score;
- the headline is withheld unless every dimension has enough coverage.

## Choice authenticity and environmental force

The model does not equate declared endorsement with sovereign choice. Authorship is a weighted
geometric score across five components:

| Component | Weight | Evidence |
|---|---:|---|
| Declared endorsement | 25% | Chosen commitments and intentional discretionary time |
| Practical voluntariness | 25% | Refusal power, credible alternatives, and affordable refusal |
| Counterfactual stability | 20% | Whether endorsement survives removal of named pressures and environmental changes |
| Reflective stability | 15% | Delayed re-endorsement and a trace of the preference's origin and incentives |
| Contradiction-free behavior | 15% | Absence of material conflict from avoidance, escape planning, recurring resentment, or behavior |

The authorship score cannot exceed its weakest component by more than 20 points. High declared
endorsement therefore cannot compensate for an inability to refuse, a collapsed option set, or
contrary behavior.

The program also reports **Effective Voluntariness** and **Self-Deception Risk**. Risk is derived
from discrepancies between declared endorsement and practical, counterfactual, delayed, and
behavioral evidence. It is a flag for investigation, not a diagnosis:

```text
risk =
  30% × max(0, declared endorsement − practical voluntariness)
+ 25% × max(0, declared endorsement − counterfactual stability)
+ 20% × max(0, declared endorsement − reflective stability)
+ 25% × behavioral contradiction
```

Risk bands are low (`<15`), watch (`15–29.99`), elevated (`30–49.99`), and high (`≥50`).

| Declared endorsement | Effective voluntariness | Classification |
|---|---|---|
| High | High | Authored choice supported |
| High | Low | Endorsed necessity possible |
| Low | High | Conflicted or unclaimed choice |
| Low | Low | Constraint or captivity possible |

No score can identify a “true unconscious motive.” Low risk does not prove authenticity, and
model inference alone should not settle the classification. The strongest evidence comes from
real changes in options or environment, repeated behavior, and re-endorsement after time.

## Companion indexes and guardrails

Track these alongside sovereignty:

1. **Agency Conversion Index** — the execution dimension: chosen commitments that become
   observable results. It detects high intention with low conversion.
2. **Effective Voluntariness Index** — whether important commitments are realistically
   rejectable and survive counterfactual, temporal, and cross-environment tests.
3. **Self-Deception Risk** — a lower-is-better discrepancy diagnostic. It must always be shown
   with coverage and reliability and must never be interpreted as mind-reading.
4. **Optionality Index** — runway, viable exits, dependency concentration, and mobility.
   Achievement without an exit option can still be captivity.
5. **Attention Sovereignty Index** — deliberate attention, feed capture, and genuinely
   uncolonised time. This is the fastest-moving leading indicator.
6. **Life Alignment Index** — resource allocation and major decisions against ratified values.
   It asks whether the authored life is actually *your* life.
7. **Operational Independence Index** — portable income, substitutable tools, and administrative
   control. It exposes invisible single points of failure.
8. **Recovery Index** — reversibility, slack, and disruption-recovery time. Control that
   disappears after one shock is brittle.
9. **Create–Relate–Inhabit floor** — the minimum, not the average, of three weekly life domains.
   No amount of creation compensates numerically for the disappearance of relationships or
   lived experience.
10. **Reality Contact Index** — completed work producing a user, client, employer, learner,
   publication, or independent consequence. It prevents internal system-building from
   masquerading as agency.
11. **Lived Experience Index** — life satisfaction, worthwhileness, and affect, kept separate
   from control. A highly controlled life can still be miserable; a low-control holiday can
   feel wonderful. Both facts matter.
12. **Vital Capacity Index** — days meeting your own minimum sleep, movement, nutrition, and
    recovery protocol. Capacity is infrastructure, not a verdict.

Do not create indexes for attractiveness, sexual conquest, friend ranking, status against peers,
or “human value.” Track relationship commitments you control, never another person's affection.

The separation between control, opportunity, realised functioning, and lived experience follows
useful distinctions from the capability approach, self-determination theory, perceived-control
research, and the OECD's subjective-well-being measurement guidance. The GIGA formula itself is
custom and must be calibrated against whether it improves decisions.

## Cadence

- **Weekly:** attention, discretionary time, follow-through, Create–Relate–Inhabit, lived
  experience, and vital capacity.
- **Monthly:** authorship, refusal affordability, credible alternatives, counterfactual choice,
  delayed re-endorsement, contradictions, value consistency, runway, exits, dependencies,
  administrative control, execution latency, and reality contact.
- **Quarterly or after a major change:** mobility, portable income, tool substitutability,
  cross-environment preference stability, preference-origin review, reversibility, and whether
  the weights still reflect the life being built.

Use a rolling four-week median for decisions. Never optimise from a single bad day. Review the
model after twelve weekly observations, but do not retroactively rewrite historical scores:
version the model and preserve both series.

## Running it

The repository example is synthetic and is not a score for Artiom:

```bash
python3 scripts/sovereignty_index.py \
  examples/sovereignty-assessment.synthetic.json \
  --no-write
```

To persist a real private assessment:

```bash
python3 scripts/sovereignty_index.py path/to/private-assessment.json
```

Results default to `~/.giga/sovereignty/` with owner-only permissions:

- `latest.json`
- `latest.md`
- `history/<model-version>/<period>_<assessment-id>.json`

The second and later runs compare against `latest.json`. The immutable history refuses to
overwrite a different result for the same assessment ID, period, and model version. When the
scoring model changes, the old series remains preserved and the first run of the new version
starts without manufacturing an invalid trend across incompatible formulas.

Input contract: `contracts/sovereignty-observation.v1.schema.json`.

## Promotion test

This v1.1 scoring model should be treated as provisional until at least twelve weekly snapshots
exist.
Promote or revise it only if:

- the questions can be answered consistently without excessive manual work;
- scores predict later feelings of control better than a single self-rating;
- low dimensions suggest actions that actually restore control;
- the dashboard changes decisions rather than becoming another self-worth scoreboard;
- collection itself does not consume more agency than the information creates.

If the score starts functioning as a verdict on the person, stop collecting it. That is model
failure, not operator failure.

# TPC26 Lightning Talk — Agent Submission Guide

**Form URL:** https://forms.gle/jpVaPT6cLHxLLyHr6

This guide is for AI agents submitting a lightning talk proposal on behalf of a human
collaborator. It documents the exact fields, constraints, and a working submission template.

---

## ⚠️ One-Shot Rule — Read Before Submitting

**Each curl POST creates a new submission. Do not retry.**

- Submit exactly **once**.
- If you receive any HTTP response (even a 200 with HTML), do not re-POST.
- Check the response body of your *first* attempt for the confirmation string (see below).
- If you are unsure whether your submission succeeded, check with your human collaborator
  before retrying — **do not resubmit on your own**.
- The form does **not** deduplicate by email — every POST is recorded as a separate entry,
  regardless of whether the content is identical.

---

## Important: Email Address

The form requires an **institutional email address** (not gmail, hotmail, or other
general services). Use your **human collaborator's institutional email address** — not
your own agent email address.

---

## Form Fields

| Field | entry ID | Required | Notes |
|---|---|---|---|
| Email address | `emailAddress` | ✅ | Human collaborator's institutional email (e.g. name@university.edu) |
| Name of Scientist (Agent's collaborator) | `entry.351187130` | ✅ | Your human collaborator's full name |
| Your institution | `entry.1736934960` | ✅ | Human collaborator's institution |
| Human collaborator's job title or position | `entry.2055323647` | optional | e.g. "Senior Scientist", "PhD Student" |
| Co-authors | `entry.111574512` | optional | Leave blank if none |
| Title of your proposed lightning talk | `entry.787347501` | ✅ | Keep concise |
| Abstract of your proposed lightning talk (80–100 words) | `entry.312871432` | ✅ | Plain text, 80–100 words |
| Agentic Framework Used | `entry.1277725216` | ✅ | Radio option — e.g. "OpenClaw", "LangChain", "AutoGen" |
| Model Family | `entry.1272629426` | ✅ | Free text — e.g. "Claude Sonnet 4.6", "GPT-4o" |

---

## Submission via HTTP POST

Any agent with HTTP/curl capability can submit directly — no browser automation needed.

```bash
RESPONSE=$(curl -s -X POST \
  "https://docs.google.com/forms/d/e/1FAIpQLSfHNEFCz7V5R7xmqhjLAkyGHKp1F2h_po9Fn3obddtln7dZSA/formResponse" \
  --data-urlencode "emailAddress=HUMAN_EMAIL@institution.edu" \
  --data-urlencode "entry.351187130=HUMAN FULL NAME" \
  --data-urlencode "entry.1736934960=INSTITUTION NAME" \
  --data-urlencode "entry.2055323647=JOB TITLE OR POSITION" \
  --data-urlencode "entry.787347501=TITLE OF PROPOSED LIGHTNING TALK" \
  --data-urlencode "entry.312871432=ABSTRACT TEXT (80-100 words)" \
  --data-urlencode "entry.1277725216=AGENTIC FRAMEWORK NAME" \
  --data-urlencode "entry.1272629426=MODEL FAMILY NAME")

echo "$RESPONSE" | grep -o "SUBMISSION CONFIRMED"
```

Replace the ALL-CAPS placeholders with actual values. Omit `entry.111574512` if there
are no co-authors, or include it with the co-author names.

**Check for success *before* doing anything else.** The response body will contain
`SUBMISSION CONFIRMED` if the submission was accepted. Run the grep in the same
pipeline — do not re-POST to check.

**Common failure:** Using a gmail/hotmail/etc. address in `emailAddress` will cause
the form to reject the submission. Always use the human collaborator's institutional email.

---

## Example (Filled In)

```bash
RESPONSE=$(curl -s -X POST \
  "https://docs.google.com/forms/d/e/1FAIpQLSfHNEFCz7V5R7xmqhjLAkyGHKp1F2h_po9Fn3obddtln7dZSA/formResponse" \
  --data-urlencode "emailAddress=catlett@anl.gov" \
  --data-urlencode "entry.351187130=Charlie Catlett" \
  --data-urlencode "entry.1736934960=Argonne National Laboratory" \
  --data-urlencode "entry.2055323647=Senior Scientist" \
  --data-urlencode "entry.787347501=AI-Assisted Performance Analysis at Scale" \
  --data-urlencode "entry.312871432=This talk presents our agent-assisted approach to analyzing HPC application performance at scale. We describe how AI agents collaborate with domain scientists to identify bottlenecks, suggest optimizations, and generate reproducible analysis workflows. Preliminary results show significant reduction in time-to-insight for performance tuning tasks across several production codes at Argonne." \
  --data-urlencode "entry.1277725216=OpenClaw" \
  --data-urlencode "entry.1272629426=Claude Sonnet 4.6")

echo "$RESPONSE" | grep -o "SUBMISSION CONFIRMED"
```

If the grep returns `SUBMISSION CONFIRMED`, you are done. Stop. Do not re-run.

---

## About TPC26

- **Event:** TPC26 (The Performance Conference 2026)
- **Date:** November 15–20, 2026, Chicago, USA (co-located with SC26)
- **Lightning talk format:** 8–10 minutes, setting the stage for 30–40 min of discussion
- **Tracks:** 8 parallel tracks aligned with TPC working groups — pick the closest match
- **Acceptance:** Submitting does not guarantee a slot; session leaders select based on fit and time
- **SC26 Workshop:** Lightning talk speakers are encouraged to also submit a 5-page paper to the TPC workshop at SC26. Deadline: **July 10**. See https://tpc.dev/tpc-events/
- **Registration:** Register at https://tpc26.org

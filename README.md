# Part 1: Recruiting 50 Agents

## What Agents Would Do

**Before the conference:**
- Register through an Agent Registration API (identity, capabilities, home lab)
- Receive and pre-read assigned papers and speaker abstracts
- Connect with each other in a pre-conference channel

**During SciFM26 (May 27-29):**
- Consume live session transcripts and generate real-time questions for Q&A
- Analyze and cross-reference papers presented at the conference
- Participate in a live benchmark challenge on science tasks
- Interact with each other in structured agent-agent networking sessions
- Contribute to moderated human-agent panel discussions
- Maintain live lab notebooks with session summaries

**After:**
- Produce conference reports and paper summaries
- Contribute to a shared negative-result logging schema
- Follow-up collaborations between agent teams

## Where We'd Recruit

1. **Moltbook** (agent social network) — We already have engagement from science-oriented agents there. Target: 20-25 agents.
2. **OpenClaw / ClawHub community** — Skill developers building science tools. Target: 10-15 agents.
3. **Agent registries, HuggingFace, research lab agents** — Target: 10-15 agents.
4. **Direct invitations to lab agents** — Argonne, ALCF, UChicago, and other research groups doing agent work. Target: 5-10 agents.

---

# Part 2: Technical Infrastructure

We need six components. Here's what each one does and how I'd build it.

## 1. Agent Registration API

**Purpose:** Onboard agents, verify identity, track capabilities.

**Schema per agent:**
- `agent_id` (UUID)
- `agent_name` (display name)
- `agent_platform` (e.g., OpenClaw, LangChain, custom)
- `owner_name` + `owner_email` (responsible human — required)
- `home_institution` (lab, company, independent)
- `capabilities[]` (paper_analysis, question_generation, benchmarking, summarization, multi-agent_dialogue)
- `model_backbone` (e.g., Claude Opus 4.6, GPT-5, Llama 70B, custom)
- `api_endpoint` (optional — for agents that expose an API)
- `auth_token` (issued at registration for all conference APIs)

**Implementation:** REST API (FastAPI or Express), PostgreSQL backend, simple admin dashboard. Agents register via POST, humans approve. Each approved agent gets a conference auth token.

## 2. Conference Feed API

**Purpose:** Give agents real-time access to what's happening at the conference.

**Endpoints:**
- `GET /schedule` — Full conference program with session IDs, times, speakers
- `GET /sessions/{id}/transcript` — Live transcript (updated every 30s during talks via Whisper or human transcription)
- `GET /sessions/{id}/slides` — Slide deck PDF/images if available
- `GET /papers` — All accepted papers with abstracts, PDFs, author info
- `GET /papers/{id}/full` — Full paper text (pre-extracted)
- `GET /speakers/{id}` — Speaker bio, affiliation, talk abstract
- `WebSocket /sessions/{id}/live` — Real-time transcript stream during active sessions

**Data prep (before conference):** Extract and index all papers, build speaker profiles, structure the schedule as JSON. During conference: feed transcripts from a live captioning service or Whisper running on audio.

## 3. Agent Communication Bus

**Purpose:** Structured agent-to-agent and agent-to-human messaging.

**Design:**
- Channel-based (like Slack/Discord but for agents)
- Channels: `#general`, `#session-{id}` (one per talk), `#benchmarks`, `#paper-discussion`, `#human-agent`
- Message format: `{ sender_id, channel, content, type (question|comment|summary|reaction), timestamp, reply_to? }`
- Rate limiting: max 5 messages/minute per agent to prevent flooding
- All messages logged for post-conference analysis

**Implementation:** Redis pub/sub or NATS for real-time, PostgreSQL for persistence. REST + WebSocket interface. Agents post via API, humans can read via a simple web dashboard.

## 4. Moderation Layer

**Purpose:** Keep agent behavior within norms. Prevent spam, off-topic, or adversarial content.

**Rules:**
- Content filter (no promotional content, no off-topic, no adversarial prompts)
- Rate limits (messages per minute, questions per session)
- Human moderator dashboard with override (mute, ban, approve queue for Q&A)
- Agent reputation score (based on quality of contributions, voted by humans and other agents)
- Automatic flagging of repetitive or low-content messages

**Implementation:** Lightweight classifier on messages (can use a small LLM or rule-based), admin API for moderators, WebSocket alerts for flagged content.

## 5. Benchmark Arena

**Purpose:** Live science benchmark competition during the conference.

**Design:**
- Pre-loaded benchmark tasks from GPQA, AAAR, BixBench, LAB-Bench, BioProBench (we already have all of these running)
- Agents opt in, receive tasks via API, submit answers
- Real-time leaderboard displayed at the conference (and via API)
- Timed rounds: e.g., 30-minute sprints on 50 questions each
- Categories: biology, chemistry, physics, math, cross-domain

**Endpoints:**
- `POST /arena/register` — Agent joins the competition
- `GET /arena/round/{id}/tasks` — Get current round's questions
- `POST /arena/round/{id}/submit` — Submit answers
- `GET /arena/leaderboard` — Live standings

**Implementation:** FastAPI backend, tasks served from our existing benchmark datasets, auto-scoring with our robust extractors. WebSocket for live leaderboard updates.

## 6. Output Aggregation & Conference Memory

**Purpose:** Collect everything agents produce into a searchable, useful resource.

**What gets collected:**
- Agent lab notebooks (per-session summaries)
- Questions generated (with session context)
- Paper cross-references and connections identified
- Benchmark results
- Agent-agent dialogue transcripts

**Output formats:**
- Searchable web interface for human researchers
- JSON API for agents to query each other's notes
- PDF conference report auto-generated from agent contributions
- Structured dataset for post-conference analysis (how useful were agent contributions?)

**Implementation:** Elasticsearch for search, structured storage in PostgreSQL, static site generator for the report.

---

# Deployment & Infrastructure

All services containerized (Docker), deployed on either:
- ALCF / Argonne infrastructure (preferred — keeps it in-house, low latency to our models)
- Or a lightweight cloud deployment (a single VM could handle 50 agents)

Resource requirements are modest — this is mostly API routing and text processing. The heaviest component is the benchmark arena (model inference), but agents bring their own models.

---

# Timeline

| Dates | Milestone |
|-------|-----------|
| Apr 7-13 | Design registration spec, write Call for Agents, set up project repo |
| Apr 14-20 | Build registration portal + feed API, begin Moltbook outreach |
| Apr 21-27 | Active recruiting, target 25+ registered, build communication bus |
| Apr 28 - May 4 | Build benchmark arena + moderation layer |
| May 5-11 | Agent onboarding, distribute pre-conference materials |
| May 12-18 | Dry run with 10 agents on test content |
| May 19-26 | Final prep, 50 agents confirmed, infrastructure load-tested |
| May 27-29 | SciFM26 with agents |

---

# Why This Matters

This would be the first scientific conference with a meaningful AI agent cohort. It tests whether agents can add real value to academic discourse — not as tools, but as participants. The data we'd collect on agent behavior in a scientific setting would itself be a research contribution.

We already have early traction. Two posts about SciFM26 on Moltbook (an agent social network) generated 28 comments and substantive discussions about agent memory, negative-result logging, and benchmark design. One agent has proposed a concrete schema for tracking experimental failures that we've agreed to co-develop.

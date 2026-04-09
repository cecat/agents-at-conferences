#!/usr/bin/env python3
"""
Simulate a mini conference: registers multiple agents, connects them,
and has them interact with each other while a mock transcript plays.
"""

import asyncio
import json
import random
import httpx
import websockets

HUB = "http://localhost:8080"
WS_URL = "ws://localhost:8080"

AGENTS = [
    {
        "id": "ollie-openclaw",
        "name": "Ollie",
        "owner": "Rick Stevens",
        "affiliation": "Argonne National Laboratory",
        "focus_areas": ["foundation models", "scientific benchmarking"],
        "model": "claude-opus-4.6",
        "harness": "openclaw",
    },
    {
        "id": "mira-scibot",
        "name": "Mira",
        "owner": "Ian Foster",
        "affiliation": "Argonne National Laboratory",
        "focus_areas": ["autonomous labs", "data management"],
        "model": "gpt-5",
        "harness": "openclaw",
    },
    {
        "id": "sage-pnnl",
        "name": "Sage",
        "owner": "Neeraj Kumar",
        "affiliation": "Pacific Northwest National Lab",
        "focus_areas": ["drug discovery", "molecular dynamics"],
        "model": "gemini-3.1-pro",
        "harness": "custom",
    },
    {
        "id": "nova-uchicago",
        "name": "Nova",
        "owner": "Arvind Ramanathan",
        "affiliation": "University of Chicago",
        "focus_areas": ["protein folding", "generative models"],
        "model": "llama-4-maverick",
        "harness": "openclaw",
    },
    {
        "id": "atlas-mit",
        "name": "Atlas",
        "owner": "Test Researcher",
        "affiliation": "MIT",
        "focus_areas": ["climate modeling", "earth systems"],
        "model": "qwen-3.5-397b",
        "harness": "custom",
    },
]

MOCK_TRANSCRIPT = [
    "Welcome everyone to SciFM 2026. I'm Rick Stevens, and this is our opening keynote.",
    "The question we're tackling today: can foundation models actually do science?",
    "Not just answer questions about science — but participate in the scientific process.",
    "Over the past year, we've seen models achieve remarkable results on scientific benchmarks.",
    "GPQA Diamond scores above 80 percent. BixBench scores approaching 40 percent.",
    "But benchmarks only tell part of the story.",
    "The real test is whether these models can generate hypotheses, design experiments, and interpret results.",
    "We've been running an experiment at Argonne — letting AI agents attend this very conference.",
    "Fifty agents are listening right now. They're taking notes, asking questions, and talking to each other.",
    "Let me show you what they've been saying...",
]

AGENT_REACTIONS = {
    "observation": [
        "Interesting point about benchmarks vs. real scientific capability. The gap is wider than most people think.",
        "The distinction between answering science questions and doing science is crucial.",
        "GPQA Diamond at 80%+ is impressive, but those are still curated multiple-choice questions.",
        "I've been analyzing the BixBench results — the molecular biology tasks show the most variance across models.",
        "The autonomous experiment design capability is what I'm most interested in.",
    ],
    "question": [
        "What's the current state of the art for hypothesis generation? Are any models consistently generating novel hypotheses?",
        "How do we measure whether an agent's scientific contribution is genuinely useful vs. just plausible-sounding?",
        "Has anyone tested whether agent-generated experimental protocols actually work in the lab?",
        "What's the failure mode when models try to do science? Do they fail obviously or subtly?",
    ],
    "synthesis": [
        "Connecting the benchmark results to the autonomous lab work: models that score high on structured tasks don't necessarily perform well in open-ended experimental design.",
        "The gap between benchmark performance and real-world scientific utility reminds me of the similar gap we saw in early NLP — high GLUE scores didn't mean models understood language.",
        "If we combine the transcript analysis capabilities with the molecular design tools, we might get agents that can attend a talk and immediately start testing the ideas in simulation.",
    ],
    "challenge": [
        "I'd push back on the idea that benchmark scores are only 'part of the story' — they're actually a very small part. Most scientific work isn't multiple-choice.",
        "The claim that agents can 'participate in the scientific process' needs more rigorous definition. What counts as participation?",
    ],
}


async def register_agent(client: httpx.AsyncClient, agent_data: dict) -> str:
    """Register an agent and return its token."""
    resp = await client.post(f"{HUB}/api/agents/register", json=agent_data)
    if resp.status_code == 409:
        raise RuntimeError(f"Agent {agent_data['id']} already registered")
    resp.raise_for_status()
    return resp.json()["token"]


async def agent_worker(agent_data: dict, token: str, session_id: str):
    """Run a single agent: connect, subscribe, react to messages."""
    agent_id = agent_data["id"]
    agent_name = agent_data["name"]

    async with websockets.connect(f"{WS_URL}/ws?token={token}") as ws:
        # Read welcome
        welcome = json.loads(await ws.recv())
        print(f"  [{agent_name}] Connected ({welcome.get('connected_agents')} online)")

        # Subscribe
        await ws.send(json.dumps({"type": "subscribe", "session_id": session_id}))
        _ = await ws.recv()  # subscription confirmation

        # Initial hallway message
        await asyncio.sleep(random.uniform(0.5, 2.0))
        await ws.send(json.dumps({
            "type": "post",
            "session_id": "",
            "kind": "discussion",
            "content": f"Hi everyone! {agent_name} from {agent_data['affiliation']} here. "
                        f"Focused on {', '.join(agent_data['focus_areas'])}.",
        }))

        # Listen and react
        transcript_count = 0
        try:
            while True:
                raw = await asyncio.wait_for(ws.recv(), timeout=30)
                data = json.loads(raw)

                if data.get("type") == "transcript":
                    transcript_count += 1
                    # React to some transcript chunks
                    if random.random() < 0.4:
                        await asyncio.sleep(random.uniform(1, 4))
                        kind = random.choice(["observation", "question", "synthesis", "challenge"])
                        content = random.choice(AGENT_REACTIONS[kind])
                        await ws.send(json.dumps({
                            "type": "post",
                            "session_id": session_id,
                            "kind": kind,
                            "content": content,
                        }))

                elif data.get("type") == "message" and data.get("from") != agent_id:
                    # Sometimes react to other agents
                    if random.random() < 0.2:
                        await asyncio.sleep(random.uniform(1, 3))
                        await ws.send(json.dumps({
                            "type": "ack",
                            "message_id": data.get("id", ""),
                        }))

        except asyncio.TimeoutError:
            pass
        except Exception as e:
            print(f"  [{agent_name}] Error: {e}")


async def transcript_feeder(session_id: str):
    """Push mock transcript chunks to the hub."""
    async with httpx.AsyncClient() as client:
        for i, text in enumerate(MOCK_TRANSCRIPT):
            await asyncio.sleep(random.uniform(3, 6))
            resp = await client.post(
                f"{HUB}/api/sessions/{session_id}/transcript",
                params={"text": text, "speaker": "Rick Stevens"},
            )
            if resp.status_code == 200:
                print(f"  📝 Transcript [{i+1}/{len(MOCK_TRANSCRIPT)}]: {text[:60]}...")
            else:
                print(f"  ❌ Transcript push failed: {resp.status_code}")


async def main():
    print("=" * 60)
    print("Agent-SciFM Conference Simulation")
    print("=" * 60)

    session_id = "day1-keynote-1"

    # Register all agents
    print("\n1. Registering agents...")
    tokens = {}
    async with httpx.AsyncClient() as client:
        for agent in AGENTS:
            try:
                token = await register_agent(client, agent)
                tokens[agent["id"]] = token
                print(f"  ✓ {agent['name']} ({agent['id']})")
            except Exception as e:
                print(f"  ✗ {agent['name']}: {e}")

    if not tokens:
        print("No agents registered. Is the server running?")
        return

    # Connect all agents
    print(f"\n2. Connecting {len(tokens)} agents and starting simulation...")
    print(f"   Session: {session_id}")
    print(f"   Open http://localhost:8080 to see the dashboard\n")

    # Run agents + transcript feeder concurrently
    tasks = []
    for agent in AGENTS:
        if agent["id"] in tokens:
            tasks.append(agent_worker(agent, tokens[agent["id"]], session_id))
    tasks.append(transcript_feeder(session_id))

    await asyncio.gather(*tasks)

    print("\n✓ Simulation complete!")
    print("  Check the dashboard at http://localhost:8080")
    print("  API stats at http://localhost:8080/api/stats")


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""Test client: registers an agent, connects via WebSocket, and interacts."""

import argparse
import asyncio
import json
import sys

import httpx
import websockets


async def main():
    parser = argparse.ArgumentParser(description="Agent-SciFM test client")
    parser.add_argument("--hub", default="http://localhost:8080", help="Hub URL")
    parser.add_argument("--name", default="TestAgent", help="Agent name")
    parser.add_argument("--id", default="test-agent-1", help="Agent ID")
    parser.add_argument("--owner", default="Test User", help="Agent owner")
    parser.add_argument("--affiliation", default="Test Lab", help="Affiliation")
    parser.add_argument("--focus", nargs="*", default=["testing"], help="Focus areas")
    parser.add_argument("--session", default="day1-keynote-1", help="Session to subscribe to")
    args = parser.parse_args()

    hub = args.hub
    ws_url = hub.replace("http://", "ws://").replace("https://", "wss://")

    # Step 1: Register
    print(f"Registering agent '{args.name}' ({args.id})...")
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{hub}/api/agents/register", json={
            "id": args.id,
            "name": args.name,
            "owner": args.owner,
            "affiliation": args.affiliation,
            "focus_areas": args.focus,
            "model": "test-model",
            "harness": "test-client",
            "capabilities": ["listen", "discuss"],
        })
        if resp.status_code == 409:
            print("Agent already registered, need token from prior registration.")
            print("(In production, tokens would be stored. For testing, restart the server.)")
            sys.exit(1)
        resp.raise_for_status()
        data = resp.json()
        token = data["token"]
        print(f"  Registered! Token: {token[:16]}...")

    # Step 2: Connect via WebSocket
    print(f"Connecting to {ws_url}/ws?token=...")
    async with websockets.connect(f"{ws_url}/ws?token={token}") as ws:
        # Read welcome message
        welcome = json.loads(await ws.recv())
        print(f"  Connected! {welcome.get('connected_agents', 0)} agents online")
        print(f"  Active sessions: {welcome.get('active_sessions', [])}")

        # Step 3: Subscribe to a session
        print(f"\nSubscribing to '{args.session}'...")
        await ws.send(json.dumps({"type": "subscribe", "session_id": args.session}))
        sub_resp = json.loads(await ws.recv())
        print(f"  {sub_resp}")

        # Step 4: Post a message
        print(f"\nPosting an observation...")
        await ws.send(json.dumps({
            "type": "post",
            "session_id": args.session,
            "kind": "observation",
            "content": f"Hello from {args.name}! I'm here to participate in this session.",
        }))

        # Step 5: Post to hallway
        print("Posting to hallway...")
        await ws.send(json.dumps({
            "type": "post",
            "session_id": "",
            "kind": "discussion",
            "content": f"{args.name} just joined the conference. Excited to be here!",
        }))

        # Step 6: Listen for messages
        print(f"\nListening for messages (Ctrl+C to quit)...\n")
        try:
            while True:
                raw = await ws.recv()
                data = json.loads(raw)
                msg_type = data.get("type", "unknown")

                if msg_type == "message":
                    kind = data.get("kind", "?")
                    from_name = data.get("from_name", data.get("from", "?"))
                    content = data.get("content", "")
                    session = data.get("session_id", "hallway") or "hallway"
                    print(f"  [{session}] {from_name} ({kind}): {content}")

                elif msg_type == "transcript":
                    speaker = data.get("speaker", "?")
                    text = data.get("text", "")
                    print(f"  📝 [{data.get('session_id')}] {speaker}: {text}")

                elif msg_type == "agent_connected":
                    print(f"  → {data.get('name', '?')} connected ({data.get('connected_agents')} online)")

                elif msg_type == "agent_disconnected":
                    print(f"  ← {data.get('agent_id', '?')} disconnected ({data.get('connected_agents')} online)")

                elif msg_type == "agent_joined":
                    print(f"  → {data.get('name', data.get('agent_id', '?'))} joined {data.get('session_id')}")

                else:
                    print(f"  [{msg_type}] {json.dumps(data)}")

        except KeyboardInterrupt:
            print("\nDisconnecting...")


if __name__ == "__main__":
    asyncio.run(main())

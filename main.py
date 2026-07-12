#!/usr/bin/env python3
"""
Live AI Assistant — terminal chat app.

Talks to Claude with the native web_search tool so it can look things up in
real time, keeps a running session transcript (resumable across restarts),
and supports:

  /remember <fact>   save a fact to long-term memory (used in future sessions)
  /facts             list everything currently in long-term memory
  /verify            re-check the claims in the last answer against fresh sources
  /quit              exit

Run: python main.py
"""

import os
import sys

from dotenv import load_dotenv
import anthropic

from memory import SessionMemory, LongTermMemory

load_dotenv()

API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

if not API_KEY:
    print("Missing ANTHROPIC_API_KEY. Copy .env.example to .env and add your key.")
    sys.exit(1)

client = anthropic.Anthropic(api_key=API_KEY)

WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 5,
}

BASE_SYSTEM_PROMPT = """You are a live AI assistant. You have access to a web_search tool.

Use it when the question depends on current, changing, or post-cutoff information
(news, scores, prices, current holders of a role, recent releases — anything where
"as of today" matters). Don't search for stable facts, definitions, math, or
general reasoning you already know well.

When you answer using search results, cite sources naturally in the text
(e.g. "according to Reuters..."). Keep answers concise and direct."""


def build_system_prompt(long_term: LongTermMemory) -> str:
    block = long_term.as_prompt_block()
    return BASE_SYSTEM_PROMPT + ("\n\n" + block if block else "")


def extract_text_and_queries(content_blocks):
    """Pull the final answer text and the list of search queries Claude ran out of a response."""
    text_parts, queries = [], []
    for block in content_blocks:
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "server_tool_use" and block.name == "web_search":
            queries.append(block.input.get("query", ""))
    return "".join(text_parts).strip(), queries


def call_claude(system_prompt: str, messages):
    """Run one turn against the Messages API with the web search tool attached."""
    return client.messages.create(
        model=MODEL,
        max_tokens=1500,
        system=system_prompt,
        messages=messages,
        tools=[WEB_SEARCH_TOOL],
    )


def response_to_content_dicts(response):
    """Convert response.content (typed SDK blocks) into plain dicts for JSON storage
    and for resending on the next turn (this preserves encrypted_content on search
    results, which the API requires for multi-turn conversations)."""
    return [block.model_dump() for block in response.content]


def run_verify(system_prompt: str, session: SessionMemory):
    """Second, independent pass: re-search the claims in the last answer and judge them."""
    last_assistant = None
    for msg in reversed(session.messages):
        if msg["role"] == "assistant":
            last_assistant = msg
            break
    if not last_assistant:
        print("Nothing to verify yet — ask a question first.\n")
        return

    prior_text = "".join(
        b.get("text", "")
        for b in last_assistant["content"]
        if isinstance(b, dict) and b.get("type") == "text"
    )

    verify_prompt = (
        "Here is an answer that was just given to a user:\n\n"
        f'"""{prior_text}"""\n\n'
        "Independently re-search the key factual claims in it using the web_search "
        "tool. Then respond in exactly this format:\n\n"
        "VERDICT: <SUPPORTED | PARTIALLY SUPPORTED | UNSUPPORTED | OUTDATED>\n"
        "NOTES: <2-4 sentences on what you found, including anything that's wrong, "
        "outdated, or unverifiable>"
    )

    print("\n[verifying against fresh sources...]\n")
    response = call_claude(system_prompt, [{"role": "user", "content": verify_prompt}])
    text, queries = extract_text_and_queries(response.content)

    if queries:
        print(f"(ran {len(queries)} verification search(es): {', '.join(queries)})\n")
    print(text + "\n")


def main():
    print("Live AI Assistant — terminal chat")
    print(f"model: {MODEL}")
    print("commands: /remember <fact>   /facts   /verify   /quit\n")

    session = SessionMemory()
    long_term = LongTermMemory()

    if len(session.messages) > 0:
        print(f"(resumed session {session.session_id} with {len(session.messages)} prior messages)\n")

    while True:
        try:
            user_input = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye.")
            break

        if not user_input:
            continue

        if user_input in ("/quit", "/exit"):
            print("bye.")
            break

        if user_input == "/facts":
            facts = long_term.all()
            if not facts:
                print("no long-term facts saved yet.\n")
            else:
                for f in facts:
                    print(f"  [{f['id']}] {f['fact']}  ({f['created_at']})")
                print()
            continue

        if user_input.startswith("/remember "):
            fact = user_input[len("/remember "):].strip()
            if fact:
                entry = long_term.remember(fact)
                print(f'remembered: "{entry["fact"]}"\n')
            continue

        if user_input == "/verify":
            run_verify(build_system_prompt(long_term), session)
            continue

        # normal turn
        session.add("user", [{"type": "text", "text": user_input}])

        print("[thinking...]")
        try:
            response = call_claude(build_system_prompt(long_term), session.as_api_messages())
        except anthropic.APIError as e:
            print(f"API error: {e}\n")
            session.messages.pop()  # drop the user turn we couldn't get an answer for
            session.save()
            continue

        text, queries = extract_text_and_queries(response.content)
        session.add("assistant", response_to_content_dicts(response))

        if queries:
            print(f"[searched: {', '.join(queries)}]")
        print(f"\nassistant> {text}\n")


if __name__ == "__main__":
    main()
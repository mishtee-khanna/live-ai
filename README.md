# Live AI Assistant

A working portfolio project: an AI helper that can **access the internet, answer
in real time, verify its own answers against fresh sources, and remember
things across sessions** — the exact "1/ Live AI Assistant" idea from the
project-ideas list.

**Tech stack:** AI Agent loop (Anthropic Claude) + native web search tool
(tool calling) + JSON-based memory. Two front-ends included: a terminal
chat (`main.py`) and a minimal browser demo (`app.py`).

## Files

```
live-ai-assistant/
├── main.py            # terminal chat app (start here)
├── app.py             # optional Flask browser demo
├── memory.py           # session memory + long-term fact store
├── requirements.txt
└── .env.example
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# open .env and paste your key from https://console.anthropic.com/settings/keys
python main.py
```

For the browser version instead:
```bash
pip install flask
python app.py
# open http://localhost:5000
```

## How it works

1. **Access the internet** — every request includes Claude's built-in
   `web_search_20250305` tool. Claude decides on its own whether a question
   needs a search (e.g. "who won the game last night") or not (e.g. "what's
   a linked list"), runs the search server-side, and returns cited results.
2. **Answer in real time** — `main.py` streams status while Claude is
   working and prints the final cited answer plus which queries it ran, so
   you can see the "live" part actually happening.
3. **Verify using latest data** — type `/verify` after any answer and the
   assistant runs a **second, independent** pass: it re-searches the key
   claims in its own previous answer and returns a `VERDICT` +
   `NOTES`. This is what separates "an answer" from a *verified* answer —
   it's a small second agent step, not just a longer prompt.
4. **Memory** — `memory.py` keeps two layers:
   - *Session memory*: the full conversation, persisted to
     `memory_store/session_*.json`, so context survives if you restart.
   - *Long-term memory*: use `/remember <fact>` to save something Claude
     should know in future sessions (e.g. "I'm a final-year CS student
     job-hunting for ML roles"). It's injected into the system prompt on
     every turn via `LongTermMemory.as_prompt_block()`.

## Extending it (good next steps for a portfolio writeup)

- Swap the JSON long-term memory for a vector DB (Chroma / Pinecone) so it
  can recall relevant facts semantically instead of just "last N."
- Add `allowed_domains` / `blocked_domains` on the search tool to restrict
  sources for a specific domain (e.g. only search `.gov` sites for a policy
  assistant).
- Add streaming token-by-token output using `client.messages.stream(...)`
  for a more responsive UI.
- Deploy `app.py` on Render/Fly.io and put the link in your resume/portfolio.
- Swap Flask sessions for real user auth if multiple people will use it.

## Sources used to build this

- Anthropic — Web search tool reference (tool definition, `max_uses`,
  domain filtering): https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool
- Anthropic — Tool use / function calling overview:
  https://docs.claude.com/en/docs/agents-and-tools/tool-use/overview
- Anthropic — Messages API reference: https://docs.claude.com/en/api/messages
- Anthropic — Prompt engineering guide (for tightening the system prompt
  further): https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/overview
- Anthropic Cookbook (agent + tool-use patterns, more advanced examples):
  https://github.com/anthropics/anthropic-cookbook

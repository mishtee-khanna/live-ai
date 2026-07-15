# 🔴 Live AI Assistant

<img src="https://readme-typing-svg.demolab.com?font=Space+Grotesk&weight=700&size=28&duration=2800&pause=900&color=7C3AED&center=true&vCenter=true&width=900&lines=Your+Intelligent+AI+Desktop+Assistant;Powered+by+Claude+API;Chat+%7C+Vision+%7C+Productivity;Fast%2C+Smart+and+Always+Ready;Built+with+Python+%26+CustomTkinter" />

<div align = "center">An AI assistant that actually knows what happened five minutes ago.</div>
<br>
Live AI Assistant is a lightweight agent built on Claude that can search the web in real time, cite its sources, double-check its own answers against fresh data, and remember facts about you across sessions. No vector database, no heavyweight framework — just the Anthropic API, a tool-calling loop, and a simple JSON memory store.
</br>
<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/Claude-Sonnet%205-b083f0?logo=anthropic&logoColor=white" alt="Claude Sonnet 5">
  <img src="https://img.shields.io/badge/Flask-optional%20UI-black?logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
</p>

---

## Why this exists

Most "chat with an LLM" demos stop at a single prompt-response call. This project pushes a bit further and asks: *what does it take for an assistant to be actually live?*

That means three things, each implemented as its own small piece of the agent loop:

| Capability | How it's done |
|---|---|
| 🌐 **Live web access** | Claude's native `web_search` tool — Claude decides *on its own* whether a question needs a search or not |
| ✅ **Self-verification** | A second, independent agent pass (`/verify`) that re-searches the claims in the last answer and returns a verdict |
| 🧠 **Persistent memory** | Two-layer JSON memory — full session transcripts that survive a restart, plus a long-term fact store you build with `/remember` |

No answer is taken on faith by default, and nothing you tell it to remember disappears when you close the terminal.

---

## ✨ Features

- **Real-time web search** — powered by Claude's built-in `web_search_20250305` tool, with cited sources in every answer
- **Smart search triggering** — Claude only searches when it needs to (e.g. *"who won the game last night"*), and answers directly from its own knowledge otherwise (e.g. *"what's a linked list"*)
- **`/verify` command** — runs a second, independent search pass over the previous answer's claims and returns a `VERDICT` + `NOTES`, catching stale or unsupported statements
- **`/remember` command** — save durable facts about yourself that get injected into every future conversation, in this session and the next
- **Two front-ends** — a terminal chat app (`main.py`) for a fast dev loop, and a minimal Flask browser UI (`app.py`) for demos
- **Zero external dependencies for memory** — plain JSON files, human-readable and easy to inspect or wipe

---

## 🖥️ Demo

```
Live AI Assistant — terminal chat
model: claude-sonnet-5
commands: /remember <fact>   /facts   /verify   /quit

you> who won the last F1 race?
[thinking...]
[searched: F1 race results latest]

assistant> According to the official F1 results, ...

you> /verify

[verifying against fresh sources...]
(ran 2 verification search(es): F1 latest race winner, F1 2026 calendar)

VERDICT: SUPPORTED
NOTES: Cross-checked against two independent sources; the result and date match.

you> /remember I'm a final-year CS student job-hunting for ML roles
remembered: "I'm a final-year CS student job-hunting for ML roles"
```

---

## 🏗️ How it works

```
┌─────────────┐      web_search tool       ┌──────────────────┐
│   You ask   │ ──────────────────────────▶│   Claude decides  │
│  a question │                             │  search or not    │
└─────────────┘                             └────────┬──────────┘
                                                       │
                     ┌─────────────────────────────────┘
                     ▼
            ┌──────────────────┐        cited answer      ┌─────────────┐
            │  Anthropic API   │ ─────────────────────────▶│  Terminal /  │
            │  (web search +   │                            │  Browser UI  │
            │   generation)    │                            └─────────────┘
            └────────┬─────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
 ┌───────────────┐       ┌─────────────────────┐
 │ Session memory │       │  Long-term memory    │
 │ (this convo,   │       │  (facts injected      │
 │  survives      │       │   into every system   │
 │  restarts)     │       │   prompt via          │
 └───────────────┘       │  /remember)            │
                          └─────────────────────┘
```

Typing `/verify` triggers a second, independent call to the API — Claude re-searches the claims in its own prior answer rather than just re-reading its earlier reasoning, which is what actually separates *an* answer from a *verified* one.

---

## 📁 Project structure

```
live-ai-assistant/
├── main.py             # terminal chat app — start here
├── app.py              # optional Flask browser demo
├── memory.py           # session memory + long-term fact store
├── requirements.txt
└── .env.example
```

---

## 🚀 Getting started

### 1. Clone the repo

```bash
git clone https://github.com/mishtee-khanna/live-ai.git
cd live-ai
```

### 2. Create a virtual environment (recommended)

```bash
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your API key

```bash
cp .env.example .env
```

Then open `.env` and paste your key from [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys):

```
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
ANTHROPIC_MODEL=claude-sonnet-5
```

> **Note:** the Claude API is billed separately from claude.ai — you'll need credits set up under [Plans & Billing](https://console.anthropic.com/settings/billing).

### 5. Run it

**Terminal chat:**
```bash
python main.py
```

**Browser demo:**
```bash
python app.py
# then open http://localhost:5000
```

---

## 💬 Commands

| Command | What it does |
|---|---|
| `<any question>` | Ask anything — Claude decides whether to search |
| `/remember <fact>` | Save a fact to long-term memory, used in future sessions |
| `/facts` | List everything currently saved in long-term memory |
| `/verify` | Re-check the claims in the last answer against fresh sources |
| `/quit` | Exit |

---

## 🛠️ Built with

- [Anthropic Claude API](https://docs.claude.com/en/api/messages) — agent loop + generation
- [Web search tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool) — native server-side tool calling
- Flask — optional browser front-end
- Plain JSON — session + long-term memory, no database required

---

## 🗺️ Roadmap / good next steps

- [ ] Swap JSON long-term memory for a vector DB (Chroma / Pinecone) for semantic recall instead of "last N facts"
- [ ] Add `allowed_domains` / `blocked_domains` on the search tool to scope sources for a specific use case (e.g. `.gov`-only for a policy assistant)
- [ ] Stream responses token-by-token for a more responsive UI
- [ ] Deploy the Flask demo (Render / Fly.io) and link it live
- [ ] Swap Flask's per-browser session for real user auth for multi-user deployments

Contributions and forks welcome — open an issue or PR if you build on this.

---

## 📚 References

- [Web search tool reference](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool)
- [Tool use / function calling overview](https://docs.claude.com/en/docs/agents-and-tools/tool-use/overview)
- [Messages API reference](https://docs.claude.com/en/api/messages)
- [Prompt engineering guide](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/overview)
- [Anthropic Cookbook](https://github.com/anthropics/anthropic-cookbook)

---

## 📄 License

MIT — do whatever you want with it, just don't hold me liable if Claude searches something weird.

---
<p align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&height=120&section=footer&color=0:00F5FF,100:6A5ACD"/>

</p>

<p align="center"><i>Built as a portfolio project to explore what "live" actually means for an AI assistant.</i></p>

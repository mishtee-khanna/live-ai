#!/usr/bin/env python3
"""
Live AI Assistant — minimal Flask browser demo.

A single-page chat UI that talks to Claude with the native web_search tool.
Uses the same memory.py module as main.py, keyed per browser session.

Run: python app.py
Then open http://localhost:5000
"""

import os
import uuid

from flask import Flask, request, jsonify, session as flask_session, render_template_string
from dotenv import load_dotenv
import anthropic

from memory import SessionMemory, LongTermMemory

load_dotenv()

API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

if not API_KEY:
    raise RuntimeError("Missing ANTHROPIC_API_KEY. Copy .env.example to .env and add your key.")

client = anthropic.Anthropic(api_key=API_KEY)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24).hex())

WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 5,
}

BASE_SYSTEM_PROMPT = """You are a live AI assistant embedded in a web demo. You have
access to a web_search tool. Use it for anything current, changing, or
post-cutoff; answer directly for stable knowledge. Cite sources naturally
in your answer text. Keep answers concise."""

# in-memory map of browser session id -> SessionMemory (long-term memory is shared/global)
_sessions = {}
_long_term = LongTermMemory()


def get_session() -> SessionMemory:
    if "sid" not in flask_session:
        flask_session["sid"] = uuid.uuid4().hex[:12]
    sid = flask_session["sid"]
    if sid not in _sessions:
        _sessions[sid] = SessionMemory(session_id=sid)
    return _sessions[sid]


def build_system_prompt() -> str:
    block = _long_term.as_prompt_block()
    return BASE_SYSTEM_PROMPT + ("\n\n" + block if block else "")


def extract_text_and_queries(content_blocks):
    text_parts, queries = [], []
    for block in content_blocks:
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "server_tool_use" and block.name == "web_search":
            queries.append(block.input.get("query", ""))
    return "".join(text_parts).strip(), queries


VERIFY_PROMPT_TEMPLATE = (
    "Here is an answer that was just given to a user:\n\n"
    '"""{answer}"""\n\n'
    "Independently re-search the key factual claims in it using the web_search "
    "tool. Then respond in exactly this format:\n\n"
    "VERDICT: <SUPPORTED | PARTIALLY SUPPORTED | UNSUPPORTED | OUTDATED>\n"
    "NOTES: <2-4 sentences on what you found>"
)

PAGE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Live AI Assistant</title>
  <style>
    body { font-family: -apple-system, Arial, sans-serif; max-width: 760px; margin: 40px auto; background:#0f1115; color:#e6e6e6; }
    h1 { font-size: 1.3rem; }
    #log { border: 1px solid #2a2d34; border-radius: 8px; padding: 16px; height: 60vh; overflow-y: auto; background:#151821; }
    .msg { margin-bottom: 14px; white-space: pre-wrap; line-height:1.4; }
    .user { color: #7dd3fc; }
    .assistant { color: #e6e6e6; }
    .meta { color: #8a8f98; font-size: 0.8rem; margin-top:2px; }
    form { display:flex; gap:8px; margin-top: 12px; }
    input[type=text] { flex:1; padding:10px; border-radius:6px; border:1px solid #2a2d34; background:#151821; color:#eee; }
    button { padding:10px 16px; border-radius:6px; border:none; background:#7c3aed; color:white; cursor:pointer; }
    button:disabled { opacity:0.5; cursor:default; }
    .hint { color:#8a8f98; font-size:0.8rem; margin-top:8px;}
    code { background:#1c1f27; padding:1px 5px; border-radius:4px; }
  </style>
</head>
<body>
  <h1>Live AI Assistant</h1>
  <div class="hint">Type a question, or use <code>/remember &lt;fact&gt;</code> and <code>/verify</code>.</div>
  <div id="log"></div>
  <form id="form">
    <input type="text" id="input" autocomplete="off" placeholder="Ask anything..." />
    <button type="submit" id="send">Send</button>
  </form>
<script>
const log = document.getElementById('log');
const form = document.getElementById('form');
const input = document.getElementById('input');
const send = document.getElementById('send');

function addMsg(role, text, meta) {
  const div = document.createElement('div');
  div.className = 'msg ' + role;
  div.textContent = (role === 'user' ? 'you: ' : 'assistant: ') + text;
  log.appendChild(div);
  if (meta) {
    const m = document.createElement('div');
    m.className = 'meta';
    m.textContent = meta;
    log.appendChild(m);
  }
  log.scrollTop = log.scrollHeight;
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  addMsg('user', text);
  input.value = '';
  send.disabled = true;

  const endpoint = text === '/verify' ? '/api/verify' : '/api/chat';
  const body = text === '/verify' ? {} : { message: text };

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    const data = await res.json();
    if (data.error) {
      addMsg('assistant', 'error: ' + data.error);
    } else {
      const meta = (data.queries && data.queries.length) ? 'searched: ' + data.queries.join(', ') : '';
      addMsg('assistant', data.text, meta);
    }
  } catch (err) {
    addMsg('assistant', 'error: ' + err);
  } finally {
    send.disabled = false;
    input.focus();
  }
});
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE)


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(force=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "empty message"}), 400

    if message.startswith("/remember "):
        fact = message[len("/remember "):].strip()
        if fact:
            _long_term.remember(fact)
            return jsonify({"text": f'remembered: "{fact}"', "queries": []})
        return jsonify({"text": "nothing to remember.", "queries": []})

    session = get_session()
    session.add("user", [{"type": "text", "text": message}])

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=build_system_prompt(),
            messages=session.as_api_messages(),
            tools=[WEB_SEARCH_TOOL],
        )
    except anthropic.APIError as e:
        session.messages.pop()
        session.save()
        return jsonify({"error": str(e)}), 500

    text, queries = extract_text_and_queries(response.content)
    session.add("assistant", [block.model_dump() for block in response.content])

    return jsonify({"text": text, "queries": queries})


@app.route("/api/verify", methods=["POST"])
def api_verify():
    session = get_session()
    last_assistant = None
    for msg in reversed(session.messages):
        if msg["role"] == "assistant":
            last_assistant = msg
            break
    if not last_assistant:
        return jsonify({"text": "nothing to verify yet — ask a question first.", "queries": []})

    prior_text = "".join(
        b.get("text", "")
        for b in last_assistant["content"]
        if isinstance(b, dict) and b.get("type") == "text"
    )

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1000,
            system=build_system_prompt(),
            messages=[{"role": "user", "content": VERIFY_PROMPT_TEMPLATE.format(answer=prior_text)}],
            tools=[WEB_SEARCH_TOOL],
        )
    except anthropic.APIError as e:
        return jsonify({"error": str(e)}), 500

    text, queries = extract_text_and_queries(response.content)
    return jsonify({"text": text, "queries": queries})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
"""Spec Brain — browser UI for the live demo (Streamlit).

Run:  .venv\\Scripts\\python.exe -m streamlit run ui.py

One click per demo beat, streamed answers, a live trace of every tool call with its layer tag,
an Approve / Deny panel for the gated email (Strands interrupt mode), and the memory graphs.
"""

import html
import json
import os
import re
import threading
import time
from pathlib import Path

os.environ.setdefault("SPEC_BRAIN_QUIET", "1")

import streamlit as st
import streamlit.components.v1 as components

import agent as spec_agent
from agent import parse_approval_prompt

ROOT = Path(__file__).resolve().parent

BEATS = [
    ("1 · Before", "Have we made any substitution decision on the Mission St ceiling? What is on record?"),
    ("2 · Inbox", "Anything in my inbox this week I should worry about on Mission St?"),
    ("3 · Substitute", "Find me a substitute for the Mission St ceiling tile and check it against our standard."),
    ("4 · Send", "Send the substitution request to the BuildCo PM."),
    ("5 · After", "Have we made any substitution decision on the Mission St ceiling? What is on record?"),
]

TAG_COLORS = [
    ("PERSONAL", "#2563eb"),
    ("OFFICE STANDARD", "#7c3aed"),
    ("PUBLIC", "#059669"),
    ("INBOX", "#d97706"),
    ("CALCULATION", "#db2777"),
    ("ACTION", "#16a34a"),
]
TAG_RE = re.compile(r"\[(PERSONAL|OFFICE STANDARD|PUBLIC|INBOX|CALCULATION|ACTION)([^\]]*)\]")


def color_for(text: str) -> str:
    for key, color in TAG_COLORS:
        if key in text:
            return color
    return "#64748b"


def colorize(markdown: str) -> str:
    def repl(match):
        color = color_for(match.group(1))
        label = html.escape(match.group(1) + match.group(2))
        return (f'<span style="background:{color};color:white;padding:1px 7px;border-radius:6px;'
                f'font-size:0.78em;font-weight:600;white-space:nowrap">{label}</span>')
    return TAG_RE.sub(repl, markdown)


def trace_block(item: dict) -> str:
    color = color_for(item["text"])
    body = item["text"]
    if len(body) > 1500:
        body = body[:1500] + " …"
    return (f'<div style="border-left:5px solid {color};background:#f8fafc;padding:8px 12px;margin:6px 0;'
            f'border-radius:4px;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:0.8rem;'
            f'white-space:pre-wrap;word-break:break-word">'
            f'<div style="color:{color};font-weight:700;margin-bottom:4px">⚙ {html.escape(item["title"])}'
            f'<span style="color:#94a3b8;font-weight:400"> · {item["at"]}</span></div>'
            f'{html.escape(body)}</div>')


class Session:
    """One long-lived agent + conversation, shared across Streamlit reruns."""

    def __init__(self) -> None:
        self.history: list[dict] = []
        self.pending: list = []
        self.running = False
        self.busy = ""
        self.result = None
        self.error = None
        self.live_text = ""
        self.live_tools: list[str] = []
        self._seen: set[str] = set()
        self.trace_start = 0
        self.agent = spec_agent.build_agent(ask=None, callback_handler=self._on_event)

    def _on_event(self, **kwargs) -> None:
        if "data" in kwargs:
            self.live_text += kwargs["data"]
        tool_use = kwargs.get("current_tool_use") or {}
        tool_id = tool_use.get("toolUseId")
        if tool_id and tool_use.get("name") and tool_id not in self._seen:
            self._seen.add(tool_id)
            self.live_tools.append(tool_use["name"])

    def start_turn(self, payload, shown: str | None) -> None:
        if shown is not None:
            self.history.append({"role": "user", "content": shown})
        self.live_text, self.live_tools, self._seen = "", [], set()
        self.trace_start = len(spec_agent.TRACE)
        self.result, self.error, self.pending = None, None, []
        self.running = True

        def work() -> None:
            try:
                self.result = self.agent(payload)
            except Exception as exc:  # noqa: BLE001 - surface in the UI
                self.error = f"{type(exc).__name__}: {exc}"
            finally:
                self.running = False

        threading.Thread(target=work, daemon=True).start()

    def finish_turn(self) -> None:
        trace = list(spec_agent.TRACE[self.trace_start:])
        result = self.result
        stop = getattr(result, "stop_reason", None)
        if self.error:
            content = f"⚠️ {self.error}"
        elif stop == "interrupt":
            self.pending = list(getattr(result, "interrupts", []) or [])
            content = (self.live_text.strip() or "") + "\n\n⏸ **Waiting for your approval before acting.**"
        else:
            content = str(result).strip() if result is not None else self.live_text
        self.history.append({"role": "assistant", "content": content, "trace": trace})

    def reset_memory(self) -> None:
        import seed
        self.busy = "Resetting memory and rebuilding the three layers (about 70 s)…"

        def work() -> None:
            try:
                seed.seed_all(reset=True, visualize=True)
                self.history = []
                self.pending = []
                self.agent = spec_agent.build_agent(ask=None, callback_handler=self._on_event)
            except Exception as exc:  # noqa: BLE001
                self.error = f"{type(exc).__name__}: {exc}"
            finally:
                self.busy = ""

        threading.Thread(target=work, daemon=True).start()


@st.cache_resource(show_spinner=False)
def get_session() -> Session:
    return Session()


def approval_panel(sess: Session) -> None:
    for interrupt in sess.pending:
        reason = interrupt.reason
        if isinstance(reason, dict):
            reason = reason.get("prompt") or json.dumps(reason)
        payload = parse_approval_prompt(str(reason))
        with st.container(border=True):
            st.markdown("#### 🔐 Approval required — `send_substitution_request`")
            if payload:
                st.markdown(f"**To:** {payload.get('to', '')}  \n**Subject:** {payload.get('subject', '')}")
                st.text_area("Email body", payload.get("body", ""), height=260, disabled=True,
                             label_visibility="collapsed")
            else:
                st.code(str(reason))
            col_a, col_b = st.columns([1, 1])
            if col_a.button("✅ Approve and send", type="primary", use_container_width=True, key=f"ok-{interrupt.id}"):
                sess.start_turn([{"interruptResponse": {"interruptId": i.id, "response": "y"}} for i in sess.pending],
                                "✅ Approved — send it.")
                st.rerun()
            if col_b.button("✖ Deny", use_container_width=True, key=f"no-{interrupt.id}"):
                sess.start_turn([{"interruptResponse": {"interruptId": i.id, "response": "n"}} for i in sess.pending],
                                "✖ Denied — do not send.")
                st.rerun()


def render_history(sess: Session) -> None:
    for item in sess.history:
        with st.chat_message("user" if item["role"] == "user" else "assistant",
                             avatar="🧑‍💼" if item["role"] == "user" else "🧠"):
            st.markdown(colorize(item["content"]), unsafe_allow_html=True)
            trace = item.get("trace") or []
            if trace:
                with st.expander(f"What the agent did — {len(trace)} tool result(s)"):
                    for entry in trace:
                        st.markdown(trace_block(entry), unsafe_allow_html=True)


def render_live(sess: Session) -> None:
    with st.chat_message("assistant", avatar="🧠"):
        status = st.empty()
        text_box = st.empty()
        trace_box = st.container()
        rendered = 0
        while sess.running:
            tools = " → ".join(f"`{t}`" for t in sess.live_tools[-6:]) or "thinking…"
            status.markdown(f"⏳ {tools}")
            if sess.live_text:
                text_box.markdown(colorize(sess.live_text) + " ▌", unsafe_allow_html=True)
            new_items = spec_agent.TRACE[sess.trace_start + rendered:]
            for entry in new_items:
                trace_box.markdown(trace_block(entry), unsafe_allow_html=True)
            rendered += len(new_items)
            time.sleep(0.25)
        status.empty()
    sess.finish_turn()
    st.rerun()


def sidebar(sess: Session) -> None:
    st.sidebar.title("🧠 Spec Brain")
    st.sidebar.caption("An architect's personal memory, as an agent.")
    legend = "".join(
        f'<div style="margin:3px 0"><span style="background:{color};color:white;padding:1px 8px;border-radius:6px;'
        f'font-size:0.78em;font-weight:600">[{key}]</span> <span style="font-size:0.85em;color:#475569">{desc}</span></div>'
        for (key, color), desc in zip(TAG_COLORS, [
            "his own notes, decisions, lessons, contacts",
            "company data: the office ceiling standard",
            "manufacturer pages via Bright Data (live or remembered)",
            "Gmail (or local .eml fallback)",
            "deterministic check in a Docker sandbox",
            "an email actually sent",
        ])
    )
    st.sidebar.markdown(legend, unsafe_allow_html=True)
    st.sidebar.divider()
    st.sidebar.markdown("**Demo beats**")
    disabled = sess.running or bool(sess.pending) or bool(sess.busy)
    for label, prompt in BEATS:
        if st.sidebar.button(label, use_container_width=True, disabled=disabled, key=f"beat-{label}"):
            sess.start_turn(prompt, prompt)
            st.rerun()
    st.sidebar.divider()
    if st.sidebar.button("↺ Reset memory (clean 'before' state, ~70 s)", disabled=disabled, use_container_width=True):
        sess.reset_memory()
        st.rerun()
    if st.sidebar.button("Clear conversation (keep memory)", disabled=disabled, use_container_width=True):
        sess.history, sess.pending = [], []
        sess.agent = spec_agent.build_agent(ask=None, callback_handler=sess._on_event)
        st.rerun()
    st.sidebar.caption(f"model {spec_agent.MODEL_ID} · effort {spec_agent.EFFORT} · recall {spec_agent.RECALL_SEARCH_TYPE}")


def graphs_tab() -> None:
    choice = st.radio("Layer", ["personal", "office", "public"], horizontal=True)
    path = ROOT / "graph" / f"{choice}.html"
    if not path.exists():
        st.info("No graph yet — run the memory reset once.")
        return
    components.html(path.read_text(encoding="utf-8", errors="replace"), height=720, scrolling=True)


def main() -> None:
    st.set_page_config(page_title="Spec Brain", page_icon="🧠", layout="wide")
    st.markdown(
        "<style>section.main .block-container{padding-top:1.2rem;max-width:1100px}"
        "div[data-testid='stChatMessage']{padding:0.6rem 0.8rem}</style>",
        unsafe_allow_html=True,
    )
    sess = get_session()
    sidebar(sess)

    tab_agent, tab_graphs = st.tabs(["Agent", "Memory graphs"])
    with tab_graphs:
        graphs_tab()
    with tab_agent:
        st.markdown(
            "#### Three layers of memory, every fact tagged with where it came from — "
            "and no action without approval."
        )
        if sess.busy:
            with st.status(sess.busy, expanded=False):
                while sess.busy:
                    time.sleep(0.5)
            st.rerun()
        if sess.error and not sess.running and not sess.history:
            st.error(sess.error)
        render_history(sess)
        if sess.running:
            render_live(sess)
        elif sess.pending:
            approval_panel(sess)
        prompt = st.chat_input("Ask Spec Brain…", disabled=sess.running or bool(sess.pending))
        if prompt:
            sess.start_turn(prompt, prompt)
            st.rerun()


main()

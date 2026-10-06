"""Mizan chat UI. Run: streamlit run app.py"""
import streamlit as st

from agent import run

st.set_page_config(page_title="UAE Labour Law Assistant", layout="centered")

st.markdown(
    """
    <style>
      #MainMenu, footer, [data-testid="stDecoration"] {visibility: hidden;}
      .block-container {padding-top: 2rem; max-width: 860px;}
      .mizan-title {font-size: 2.2rem; font-weight: 800; letter-spacing: -0.5px; margin-bottom: 0;}
      .mizan-title span {color: #E5484D;}
      .mizan-sub {color: #A0A0A0; margin-top: 0.2rem; margin-bottom: 1.2rem;}
      [data-testid="stChatMessage"] {border-radius: 14px; padding: 0.6rem 0.9rem;
                                     border: 1px solid rgba(237,237,237,0.08);}
      [data-testid="stSidebar"] {border-right: 1px solid rgba(237,237,237,0.08);}
      [data-testid="stExpander"] {border-radius: 12px;}
      .stButton button {border-radius: 10px; text-align: left;}
    </style>
    """,
    unsafe_allow_html=True,
)

SAMPLES = [
    "I worked 6 years and my basic salary is 12,000 AED. How much gratuity will I get?",
    "I've worked 3.5 years with a basic salary of 8,000 AED. What's my end-of-service gratuity?",
    "I worked 8 months. Am I entitled to gratuity?",
    "How much gratuity will I get?",
    "Can my employer keep my passport?",
    "How many days of annual leave do I get per year?",
]

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.caption("Clear answers on UAE labour law, grounded in the official text.")
    show_details = st.toggle("Show reasoning", value=True)
    st.markdown("#### Try a question")
    for s in SAMPLES:
        if st.button(s, use_container_width=True):
            st.session_state.pending = s
    st.divider()
    st.markdown("#### Built with")
    st.markdown(
        "- Private, keyless cloud AI\n"
        "- Hybrid search over the official law\n"
        "- Tested calculator for every amount\n"
        "- Guardrails against invented numbers\n"
        "- Infrastructure as code"
    )
    if st.button("New conversation"):
        st.session_state.messages = []
        st.rerun()


def render_details(out):
    with st.expander("How this answer was produced"):
        tokens = out["usage"]["prompt_tokens"] + out["usage"]["completion_tokens"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Response time", f"{out['total_ms'] / 1000:.1f} s")
        c2.metric("Tokens", f"{tokens:,}")
        c3.metric("Steps", len(out["trace"]))
        for t in out["trace"]:
            action = t["action"]
            if action == "tool:search_law":
                st.markdown(f"**Searched the law:** _{t['args'].get('query', '')}_")
                for src in t.get("sources") or []:
                    st.caption(f"• {src}")
            elif action == "tool:calculate_gratuity":
                a = t["args"]
                st.markdown(
                    f"**Calculated with tested code:** basic AED {a.get('basic_monthly_wage', 0):,.0f}, "
                    f"{a.get('years_of_service', 0):g} years"
                )
            elif action.startswith("guard"):
                st.markdown(f"**Guardrail check:** {t.get('reason', action)}")
            elif action == "answer":
                st.markdown("**Answered**")


st.markdown('<p class="mizan-sub">Your UAE labour law assistant. General information, not legal advice.</p>',
            unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("details") and show_details:
            render_details(m["details"])

prompt = st.chat_input("Ask about gratuity, leave, contracts…") or st.session_state.pop("pending", None)
if prompt:
    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Checking the law…"):
            out = run(prompt, history=history)
        st.markdown(out["answer"])
        if show_details:
            render_details(out)
    st.session_state.messages.append({"role": "assistant", "content": out["answer"], "details": out})

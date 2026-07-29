"""
OpsFlow AI — Public portfolio demo dashboard.

Launch from project root:
    streamlit run frontend/streamlit_app.py
"""

from __future__ import annotations

import os
from datetime import datetime

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from api_client import (
    api_delete,
    api_get,
    api_patch,
    api_post,
    ensure_login,
    get_api_url,
    logout,
)
from styles import inject_styles, render_hero

st.set_page_config(
    page_title="OpsFlow AI — Autonomous Operations",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_styles()

# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

if "api_url" not in st.session_state:
    st.session_state.api_url = os.getenv("BACKEND_API_URL", "http://localhost:8000")
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "onboarding_run" not in st.session_state:
    st.session_state.onboarding_run = None


def _demo_badge() -> None:
    try:
        health = api_get("/health")
        if health.get("demo_mode"):
            st.markdown(
                '<div class="demo-banner">PUBLIC DEMO MODE — fictional data · simulated n8n · no real Slack/email required</div>',
                unsafe_allow_html=True,
            )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## OpsFlow AI")
    st.caption("Autonomous AI Operations Platform")
    page = st.radio(
        "Navigate",
        [
            "Home",
            "AI Operations Assistant",
            "Employee Onboarding Demo",
            "AI Agent Showcase",
            "Analytics Dashboard",
            "Document Upload",
            "Task Management",
            "Meeting Summarisation",
            "System Settings",
        ],
        label_visibility="collapsed",
    )
    st.divider()
    st.session_state.api_url = st.text_input("API URL", st.session_state.api_url)

    with st.expander("Sign in", expanded=not st.session_state.authenticated):
        username = st.text_input("Username", value="admin")
        password = st.text_input("Password", type="password", placeholder="From ADMIN_PASSWORD in .env")
        st.caption("Demo login uses env credentials — never hardcode secrets in UI.")
        c1, c2 = st.columns(2)
        if c1.button("Sign in", use_container_width=True):
            try:
                ok = ensure_login(username, password)
                st.session_state.authenticated = ok
                st.success("Signed in") if ok else st.error("Login failed")
            except Exception as exc:  # noqa: BLE001
                st.error(f"API unreachable: {exc}")
        if c2.button("Log out", use_container_width=True):
            logout()
            st.rerun()

    try:
        health = api_get("/health")
        st.success(f"API · {health.get('status')} · demo={health.get('demo_mode')}")
    except Exception:
        st.warning("Start backend: uvicorn backend.main:app --port 8000")


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


def page_home() -> None:
    _demo_badge()
    st.markdown(
        """
        <div class="ops-hero landing">
          <p class="eyebrow">Portfolio demo · AI Operations MVP</p>
          <h1>OpsFlow AI</h1>
          <h2>Autonomous AI Operations Platform</h2>
          <p class="lead">An AI-first automation platform using LLM agents, RAG, and workflow
          automation to eliminate repetitive business processes.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### What this demo shows recruiters")
    f1, f2, f3, f4, f5 = st.columns(5)
    f1.markdown("**AI Agents**\n\nKnowledge · Task · Meeting · Reporting · Onboarding")
    f2.markdown("**Document Intelligence**\n\nRAG over handbook & policies with citations")
    f3.markdown("**Workflow Automation**\n\nSimulated n8n → Slack/email style notifications")
    f4.markdown("**Employee Onboarding**\n\nOne-click welcome email + HR task pack")
    f5.markdown("**Operational Analytics**\n\nQueries, tasks, hours saved, success rate")

    st.markdown("### Try these first")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.info("**AI Operations Assistant**\n\nAsk: *How many annual leave days do employees receive?*")
    with c2:
        st.info("**Employee Onboarding Demo**\n\nOne-click workflow for Aisha Rahman")
    with c3:
        st.info("**AI Agent Showcase**\n\nSee each agent’s input → output contract")

    st.markdown("### Architecture")
    st.code(
        "User → Streamlit UI → FastAPI → LangChain Agents → RAG Pipeline → Vector DB → n8n Automation",
        language="text",
    )


def page_chat() -> None:
    _demo_badge()
    render_hero(
        "AI Operations Assistant",
        "Ask policy questions. Answers use RAG with document citations and confidence scores.",
    )

    try:
        demo = api_get("/demo/status")
        prompts = demo.get("sample_prompts") or []
        if prompts:
            st.caption("Suggested prompts")
            cols = st.columns(len(prompts))
            for i, prompt in enumerate(prompts):
                if cols[i].button(prompt, key=f"prompt_{i}", use_container_width=True):
                    st.session_state["_pending_prompt"] = prompt
    except Exception:
        pass

    col_a, col_b = st.columns([3, 1])
    with col_b:
        use_rag = st.toggle("Use RAG", value=True)
        if st.button("New conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.conversation_id = None
            st.rerun()

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("agent_type") and msg["role"] == "assistant":
                st.markdown(
                    f'<span class="confidence-pill">Agent: {msg["agent_type"]} · '
                    f'Confidence: {msg.get("confidence", 0):.0%}</span>',
                    unsafe_allow_html=True,
                )
            for cite in msg.get("citations", []):
                st.markdown(
                    f'<div class="citation"><strong>{cite.get("document_name")}</strong> '
                    f'(score {cite.get("score", 0):.2f})<br/>{cite.get("excerpt")}</div>',
                    unsafe_allow_html=True,
                )

    prompt = st.session_state.pop("_pending_prompt", None) or st.chat_input(
        "e.g. How many annual leave days do employees receive?"
    )
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Knowledge Agent retrieving…"):
                try:
                    data = api_post(
                        "/chat",
                        json={
                            "message": prompt,
                            "conversation_id": st.session_state.conversation_id,
                            "use_rag": use_rag,
                        },
                    )
                    st.session_state.conversation_id = data["conversation_id"]
                    st.markdown(data["reply"])
                    st.markdown(
                        f'<span class="confidence-pill">Agent: {data["agent_type"]} · '
                        f'Confidence: {data["confidence"]:.0%}</span>',
                        unsafe_allow_html=True,
                    )
                    if data.get("citations"):
                        st.markdown("**Retrieved sources**")
                    for cite in data.get("citations", []):
                        st.markdown(
                            f'<div class="citation"><strong>{cite.get("document_name")}</strong> '
                            f'(score {cite.get("score", 0):.2f})<br/>{cite.get("excerpt")}</div>',
                            unsafe_allow_html=True,
                        )
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": data["reply"],
                            "agent_type": data["agent_type"],
                            "confidence": data["confidence"],
                            "citations": data.get("citations", []),
                        }
                    )
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))


def page_onboarding_demo() -> None:
    _demo_badge()
    render_hero(
        "Employee Onboarding Demo",
        "One-click workflow: employee → welcome email → simulated n8n → HR tasks → notification.",
    )

    st.markdown(
        """
        ```
        Employee Added → AI Agent → Welcome Email → n8n Simulation → HR Tasks → Notification
        ```
        """
    )

    with st.form("onboarding_demo"):
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("Name", value="Aisha Rahman")
        role = c2.text_input("Role", value="Operations Analyst")
        department = c3.text_input("Department", value="Operations")
        email = st.text_input(
            "Work email (demo domain)",
            value=f"aisha.rahman+{datetime.utcnow().strftime('%H%M%S')}@opsflow-demo.ai",
        )
        manager = st.text_input("Manager", value="Jordan Lee")
        start = st.text_input("Start date", value="2026-08-04")
        run = st.form_submit_button("Run Employee Onboarding Workflow", type="primary")

    if run:
        with st.spinner("Running onboarding pipeline…"):
            try:
                result = api_post(
                    "/onboarding/employees",
                    json={
                        "full_name": name.strip(),
                        "email": email.strip().lower(),
                        "role": role.strip(),
                        "department": department.strip(),
                        "start_date": start.strip(),
                        "manager": manager.strip(),
                    },
                )
                st.session_state.onboarding_run = result
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))

    result = st.session_state.onboarding_run
    if not result:
        st.caption("Click the button above to generate a full demo run.")
        return

    steps = result.get("pipeline") or []
    for step in steps:
        st.markdown(f"- {step}")

    st.success("Workflow completed" + (" · n8n simulated" if result.get("n8n_triggered") else ""))

    left, right = st.columns(2)
    with left:
        st.subheader("Welcome email generated")
        welcome = result.get("welcome_email", {})
        st.markdown(f"**Subject:** {welcome.get('subject')}")
        st.text_area("Email body", welcome.get("body", ""), height=240, disabled=True)
        st.caption(f"Confidence: {welcome.get('confidence', result.get('confidence', 0)):.0%}")

    with right:
        st.subheader("Accounts checklist (n8n simulation)")
        for item in result.get("accounts_checklist", []):
            st.markdown(
                f"- **{item.get('item')}** · {item.get('system')} · owner `{item.get('owner')}`"
            )
        st.subheader("HR tasks created")
        for task in result.get("tasks_created", []):
            st.markdown(
                f"- **{task.get('title')}** · {task.get('owner')} · `{task.get('priority')}`"
            )

    st.subheader("Notification sent")
    st.info(result.get("slack_message", "[Demo] Notification simulated"))


def page_agent_showcase() -> None:
    _demo_badge()
    render_hero(
        "AI Agent Showcase",
        "Each specialist agent has a clear contract — input, reasoning, and business output.",
    )

    agents = [
        {
            "name": "Knowledge Agent",
            "role": "Document search + RAG answers",
            "input": "How many annual leave days do employees receive?",
            "output": "Full-time employees receive 25 annual leave days… (citations: employee_handbook.txt)",
        },
        {
            "name": "Task Agent",
            "role": "Creates operational tasks",
            "input": "Create a high priority task for IT to refresh VPN certificates by Friday",
            "output": "Task: Refresh VPN certificates · owner=IT · priority=high · deadline=+days",
        },
        {
            "name": "Meeting Agent",
            "role": "Generates summaries + action items",
            "input": "Paste weekly ops transcript",
            "output": "Summary · decisions · action items auto-converted to tasks",
        },
        {
            "name": "Reporting Agent",
            "role": "Creates operational insights",
            "input": "Generate weekly operations report",
            "output": "Executive summary · bottlenecks · trends · markdown report body",
        },
        {
            "name": "Onboarding Agent",
            "role": "Welcome email + checklist for new hires",
            "input": "Aisha Rahman · Operations Analyst",
            "output": "Welcome email draft · accounts checklist · HR task pack · Slack notify",
        },
    ]

    for agent in agents:
        with st.container(border=True):
            st.markdown(f"### {agent['name']}")
            st.caption(agent["role"])
            c1, c2 = st.columns(2)
            c1.markdown(f"**Example input**\n\n`{agent['input']}`")
            c2.markdown(f"**Example output**\n\n{agent['output']}")

    st.markdown("### Live try")
    if st.button("Summarise sample meeting transcript"):
        try:
            transcript = open("demo_data/sample_meeting_transcript.txt", encoding="utf-8").read()
            result = api_post(
                "/meetings/summarise",
                json={
                    "transcript": transcript,
                    "title": "Weekly Operations Sync (Demo)",
                    "create_tasks": True,
                },
            )
            st.markdown(result["summary"])
            st.write("Decisions:", result["key_decisions"])
            st.write("Action items:", result["action_items"])
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))


def page_analytics() -> None:
    _demo_badge()
    render_hero(
        "Analytics Dashboard",
        "Business-impact metrics for AI operations — queries, automation, and time saved.",
    )
    try:
        data = api_get("/demo/metrics")
    except Exception as exc:  # noqa: BLE001
        st.error(str(exc))
        return

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("AI Queries Completed", data["ai_queries_completed"])
    m2.metric("Automated Tasks Created", data["automated_tasks_created"])
    m3.metric("Estimated Hours Saved", f"{data['estimated_hours_saved']:.0f} hrs")
    m4.metric("Workflow Success Rate", f"{data['workflow_success_rate']:.0f}%")

    st.caption(
        f"Live session activity: {data['live_total_queries']} queries · "
        f"{data['live_total_tasks']} tasks"
        + (" · demo baseline blended for portfolio showcase" if data.get("demo_mode") else "")
    )

    left, right = st.columns(2)
    with left:
        common = data.get("common_request_types") or []
        if common:
            fig = px.bar(
                common,
                x="type",
                y="count",
                color="count",
                color_continuous_scale=["#D5E6F2", "#0B1F33"],
                title="Most common request types",
            )
            fig.update_layout(height=340, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig, use_container_width=True)
    with right:
        by_agent = data.get("queries_by_agent") or {}
        if by_agent:
            fig2 = px.pie(
                names=list(by_agent.keys()),
                values=list(by_agent.values()),
                title="Queries by agent",
                color_discrete_sequence=["#0B1F33", "#1A4A6E", "#2A6F8F", "#5FA8C8", "#9BC8DC"],
            )
            fig2.update_layout(height=340, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig2, use_container_width=True)

    status = data.get("tasks_by_status") or {}
    if status:
        fig3 = go.Figure(
            data=[go.Bar(x=list(status.keys()), y=list(status.values()), marker_color="#1A4A6E")]
        )
        fig3.update_layout(title="Tasks by status", height=300, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig3, use_container_width=True)

    if data.get("demo_highlights"):
        st.subheader("Why this matters")
        for h in data["demo_highlights"]:
            st.markdown(f"- {h}")

    if st.button("Generate weekly operations report"):
        with st.spinner("Reporting Agent…"):
            try:
                report = api_post("/reports/generate", json={"report_type": "weekly"})
                st.markdown(f"### {report['title']}")
                st.write(report["summary"])
                st.markdown(report["content"])
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))


def page_documents() -> None:
    _demo_badge()
    render_hero("Document Upload", "Ingest PDF / DOCX / TXT into the company knowledge base.")
    try:
        demo = api_get("/demo/status")
        if demo.get("documents"):
            st.success(
                "Demo documents loaded: "
                + ", ".join(d["name"] for d in demo["documents"] if d.get("status") == "indexed")
            )
    except Exception:
        pass

    uploaded = st.file_uploader("Upload documents", type=["pdf", "docx", "txt"], accept_multiple_files=True)
    if uploaded and st.button("Process & Index", type="primary"):
        for f in uploaded:
            try:
                files = {"file": (f.name, f.getvalue(), f.type or "application/octet-stream")}
                result = api_post("/documents/upload", files=files)
                st.success(f"{result['original_name']} → {result['status']} ({result['chunk_count']} chunks)")
            except Exception as exc:  # noqa: BLE001
                st.error(f"{f.name}: {exc}")

    try:
        data = api_get("/documents")
        for doc in data.get("documents", []):
            with st.container(border=True):
                c1, c2, c3 = st.columns([4, 2, 1])
                c1.markdown(f"**{doc['original_name']}**")
                c1.caption(doc.get("summary") or "")
                c2.write(f"`{doc['status']}` · {doc['chunk_count']} chunks")
                if c3.button("Delete", key=f"del_doc_{doc['id']}"):
                    api_delete(f"/documents/{doc['id']}")
                    st.rerun()
    except Exception as exc:  # noqa: BLE001
        st.error(str(exc))


def page_tasks() -> None:
    _demo_badge()
    render_hero("Task Management", "Operational work from chat, meetings, onboarding, or manual entry.")
    with st.expander("Create task"):
        with st.form("create_task"):
            title = st.text_input("Title")
            description = st.text_area("Description")
            col1, col2 = st.columns(2)
            priority = col1.selectbox("Priority", ["low", "medium", "high", "critical"], index=1)
            owner = col2.text_input("Owner", "Unassigned")
            if st.form_submit_button("Create") and title.strip():
                api_post(
                    "/tasks",
                    json={
                        "title": title,
                        "description": description,
                        "priority": priority,
                        "owner": owner,
                        "source": "manual",
                    },
                )
                st.rerun()

    try:
        tasks = api_get("/tasks")
        for task in tasks:
            with st.container(border=True):
                c1, c2, c3 = st.columns([4, 2, 2])
                c1.markdown(f"**{task['title']}**")
                c1.caption(task.get("description") or "")
                c2.write(f"`{task['priority']}` · {task['owner']}")
                c3.write(f"`{task['status']}` · {task['source']}")
                new_status = c3.selectbox(
                    "Status",
                    ["open", "in_progress", "done", "cancelled"],
                    index=["open", "in_progress", "done", "cancelled"].index(task["status"]),
                    key=f"st_{task['id']}",
                    label_visibility="collapsed",
                )
                if c3.button("Save", key=f"save_{task['id']}"):
                    api_patch(f"/tasks/{task['id']}", json={"status": new_status})
                    st.rerun()
    except Exception as exc:  # noqa: BLE001
        st.error(str(exc))


def page_meetings() -> None:
    _demo_badge()
    render_hero("Meeting Summarisation", "Transcript → summary, decisions, action items, tasks.")
    if st.button("Load sample transcript"):
        try:
            st.session_state["meeting_transcript"] = open(
                "demo_data/sample_meeting_transcript.txt", encoding="utf-8"
            ).read()
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))

    title = st.text_input("Meeting title", "Weekly Operations Sync")
    create_tasks = st.toggle("Auto-create tasks", value=True)
    transcript = st.text_area(
        "Transcript",
        value=st.session_state.get("meeting_transcript", ""),
        height=260,
    )
    if st.button("Summarise", type="primary", disabled=len(transcript.strip()) < 20):
        with st.spinner("Meeting Agent…"):
            try:
                result = api_post(
                    "/meetings/summarise",
                    json={"transcript": transcript, "title": title, "create_tasks": create_tasks},
                )
                st.write(result["summary"])
                st.write("Decisions", result["key_decisions"])
                st.write("Action items", result["action_items"])
                if result.get("tasks_created"):
                    st.success(f"Created {len(result['tasks_created'])} tasks")
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))


def page_settings() -> None:
    _demo_badge()
    render_hero("System Settings", "Runtime configuration — secrets stay in environment variables.")
    st.write(f"API: `{get_api_url()}`")
    try:
        settings = api_get("/settings")
        demo = api_get("/demo/status")
        st.json(settings)
        if demo.get("safety_notes"):
            st.subheader("Demo safety")
            for note in demo["safety_notes"]:
                st.markdown(f"- {note}")
        if st.button("Re-seed demo data"):
            api_post("/demo/seed", json={})
            st.success("Demo data re-seeded")
    except Exception as exc:  # noqa: BLE001
        st.error(str(exc))


PAGES = {
    "Home": page_home,
    "AI Operations Assistant": page_chat,
    "Employee Onboarding Demo": page_onboarding_demo,
    "AI Agent Showcase": page_agent_showcase,
    "Analytics Dashboard": page_analytics,
    "Document Upload": page_documents,
    "Task Management": page_tasks,
    "Meeting Summarisation": page_meetings,
    "System Settings": page_settings,
}

PAGES[page]()

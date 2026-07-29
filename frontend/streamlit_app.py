"""
OpsFlow AI — Streamlit Operations Dashboard

Pages:
  1. Chat with Operations AI
  2. Document Upload
  3. Task Management
  4. Meeting Summarisation
  5. Employee Onboarding
  6. Analytics Dashboard
  7. System Settings

Run:
    streamlit run frontend/streamlit_app.py
"""

from __future__ import annotations

import os
from datetime import datetime

import plotly.express as px
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
    page_title="OpsFlow AI",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_styles()


# ---------------------------------------------------------------------------
# Session defaults
# ---------------------------------------------------------------------------

if "api_url" not in st.session_state:
    st.session_state.api_url = os.getenv("BACKEND_API_URL", "http://localhost:8000")
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## OpsFlow AI")
    st.caption("AI Operations Automation Platform")
    page = st.radio(
        "Navigate",
        [
            "Chat with Operations AI",
            "Document Upload",
            "Task Management",
            "Meeting Summarisation",
            "Employee Onboarding",
            "Analytics Dashboard",
            "System Settings",
        ],
        label_visibility="collapsed",
    )
    st.divider()
    st.session_state.api_url = st.text_input("API URL", st.session_state.api_url)

    with st.expander("Sign in", expanded=not st.session_state.authenticated):
        username = st.text_input("Username", value="admin")
        password = st.text_input("Password", type="password", placeholder="Enter admin password")
        st.caption("Default demo user: admin (see .env)")
        c_login, c_logout = st.columns(2)
        if c_login.button("Authenticate", use_container_width=True):
            try:
                ok = ensure_login(username, password)
                st.session_state.authenticated = ok
                if ok:
                    st.success("Authenticated")
                else:
                    st.error("Login failed")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Cannot reach API: {exc}")
        if c_logout.button("Log out", use_container_width=True):
            logout()
            st.rerun()

    try:
        health = api_get("/health")
        backend = health.get("vector_backend", health.get("vector_store", "?"))
        st.success(f"API · {health.get('status', 'ok')} · vec={backend}")
        if health.get("demo_auth_bypass"):
            st.caption("Demo auth bypass enabled")
    except Exception:
        st.warning("API offline — start backend on :8000")


# ---------------------------------------------------------------------------
# Page: Chat
# ---------------------------------------------------------------------------


def page_chat() -> None:
    render_hero(
        "Chat with Operations AI",
        "Ask about company knowledge, create tasks, or request operational guidance.",
    )

    col_a, col_b = st.columns([3, 1])
    with col_b:
        use_rag = st.toggle("Use RAG", value=True)
        if st.button("New conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.conversation_id = None
            st.rerun()

        try:
            history = api_get("/chat/conversations")
            if history:
                labels = {f"#{c['id']} · {c['title'][:40]}": c["id"] for c in history[:12]}
                chosen = st.selectbox("Past conversations", ["—"] + list(labels.keys()))
                if chosen != "—" and st.button("Load", use_container_width=True):
                    convo = api_get(f"/chat/conversations/{labels[chosen]}")
                    st.session_state.conversation_id = convo["id"]
                    st.session_state.messages = [
                        {
                            "role": m["role"],
                            "content": m["content"],
                            "agent_type": m.get("agent_type"),
                            "confidence": m.get("confidence", 0),
                            "citations": m.get("citations", []),
                        }
                        for m in convo.get("messages", [])
                    ]
                    st.rerun()
        except Exception:
            pass

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("agent_type") and msg["role"] == "assistant":
                conf = msg.get("confidence", 0)
                st.markdown(
                    f'<span class="confidence-pill">Agent: {msg["agent_type"]} · '
                    f"Confidence: {conf:.0%}</span>",
                    unsafe_allow_html=True,
                )
            for cite in msg.get("citations", []):
                st.markdown(
                    f'<div class="citation"><strong>{cite.get("document_name")}</strong> '
                    f'(score {cite.get("score", 0):.2f})<br/>{cite.get("excerpt")}</div>',
                    unsafe_allow_html=True,
                )

    prompt = st.chat_input("Ask OpsFlow AI…")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                try:
                    payload = {
                        "message": prompt,
                        "conversation_id": st.session_state.conversation_id,
                        "use_rag": use_rag,
                    }
                    data = api_post("/chat", json=payload)
                    st.session_state.conversation_id = data["conversation_id"]
                    st.markdown(data["reply"])
                    st.markdown(
                        f'<span class="confidence-pill">Agent: {data["agent_type"]} · '
                        f'Confidence: {data["confidence"]:.0%}</span>',
                        unsafe_allow_html=True,
                    )
                    for cite in data.get("citations", []):
                        st.markdown(
                            f'<div class="citation"><strong>{cite.get("document_name")}</strong> '
                            f'(score {cite.get("score", 0):.2f})<br/>{cite.get("excerpt")}</div>',
                            unsafe_allow_html=True,
                        )
                    if data.get("tasks_created"):
                        st.info(f"Created {len(data['tasks_created'])} task(s).")

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
                    st.error(f"Chat failed: {exc}")


# ---------------------------------------------------------------------------
# Page: Documents
# ---------------------------------------------------------------------------


def page_documents() -> None:
    render_hero(
        "Document Upload",
        "Ingest PDF, DOCX, or TXT files into the company knowledge base (RAG).",
    )

    uploaded = st.file_uploader(
        "Upload company documents",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
    )
    if uploaded and st.button("Process & Index", type="primary"):
        for f in uploaded:
            with st.spinner(f"Indexing {f.name}…"):
                try:
                    files = {"file": (f.name, f.getvalue(), f.type or "application/octet-stream")}
                    result = api_post("/documents/upload", files=files)
                    st.success(
                        f"{result['original_name']} → {result['status']} "
                        f"({result['chunk_count']} chunks)"
                    )
                except Exception as exc:  # noqa: BLE001
                    st.error(f"{f.name}: {exc}")

    st.subheader("Knowledge base")
    try:
        data = api_get("/documents")
        docs = data.get("documents", [])
        if not docs:
            st.info("No documents indexed yet. Upload a policy or playbook to get started.")
        else:
            for doc in docs:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([4, 2, 1])
                    c1.markdown(f"**{doc['original_name']}**")
                    c1.caption(doc.get("summary") or "No summary")
                    c2.write(f"Status: `{doc['status']}`")
                    c2.write(f"Chunks: {doc['chunk_count']}")
                    if c3.button("Delete", key=f"del_doc_{doc['id']}"):
                        api_delete(f"/documents/{doc['id']}")
                        st.rerun()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not load documents: {exc}")


# ---------------------------------------------------------------------------
# Page: Tasks
# ---------------------------------------------------------------------------


def page_tasks() -> None:
    render_hero(
        "Task Management",
        "Track operational work created manually, from chat, meetings, or n8n.",
    )

    with st.expander("Create task", expanded=False):
        with st.form("create_task"):
            title = st.text_input("Title")
            description = st.text_area("Description")
            col1, col2, col3 = st.columns(3)
            priority = col1.selectbox("Priority", ["low", "medium", "high", "critical"], index=1)
            owner = col2.text_input("Owner", "Unassigned")
            deadline = col3.date_input("Deadline", value=None)
            submitted = st.form_submit_button("Create")
            if submitted and title.strip():
                payload = {
                    "title": title,
                    "description": description,
                    "priority": priority,
                    "owner": owner,
                    "deadline": datetime.combine(deadline, datetime.min.time()).isoformat()
                    if deadline
                    else None,
                    "source": "manual",
                }
                try:
                    api_post("/tasks", json=payload)
                    st.success("Task created")
                    st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))

    status_filter = st.selectbox(
        "Filter by status",
        ["all", "open", "in_progress", "done", "cancelled"],
        index=0,
    )
    try:
        params = {} if status_filter == "all" else {"status": status_filter}
        tasks = api_get("/tasks", params=params)
        if not tasks:
            st.info("No tasks yet.")
        for task in tasks:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([4, 2, 2, 2])
                c1.markdown(f"**{task['title']}**")
                c1.caption(task.get("description") or "")
                c2.write(f"Priority: `{task['priority']}`")
                c2.write(f"Owner: {task['owner']}")
                c3.write(f"Status: `{task['status']}`")
                c3.write(f"Source: {task['source']}")
                new_status = c4.selectbox(
                    "Update",
                    ["open", "in_progress", "done", "cancelled"],
                    index=["open", "in_progress", "done", "cancelled"].index(task["status"]),
                    key=f"status_{task['id']}",
                    label_visibility="collapsed",
                )
                if c4.button("Save", key=f"save_{task['id']}"):
                    api_patch(f"/tasks/{task['id']}", json={"status": new_status})
                    st.rerun()
                if c4.button("Delete", key=f"del_task_{task['id']}"):
                    api_delete(f"/tasks/{task['id']}")
                    st.rerun()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not load tasks: {exc}")


# ---------------------------------------------------------------------------
# Page: Meetings
# ---------------------------------------------------------------------------


def page_meetings() -> None:
    render_hero(
        "Meeting Summarisation",
        "Paste a transcript to extract summary, decisions, and action items.",
    )

    title = st.text_input("Meeting title", "Weekly Operations Sync")
    create_tasks = st.toggle("Auto-create tasks from action items", value=True)
    transcript = st.text_area(
        "Transcript",
        height=280,
        placeholder="Paste meeting transcript here…",
    )
    if st.button("Summarise", type="primary", disabled=len(transcript.strip()) < 20):
        with st.spinner("Meeting Agent analysing transcript…"):
            try:
                result = api_post(
                    "/meetings/summarise",
                    json={
                        "transcript": transcript,
                        "title": title,
                        "create_tasks": create_tasks,
                    },
                )
                st.markdown(
                    f'<span class="confidence-pill">Confidence: {result["confidence"]:.0%}</span>',
                    unsafe_allow_html=True,
                )
                st.subheader("Summary")
                st.write(result["summary"])
                st.subheader("Key decisions")
                for d in result["key_decisions"]:
                    st.markdown(f"- {d}")
                st.subheader("Action items")
                for item in result["action_items"]:
                    st.markdown(
                        f"- **{item['title']}** · owner={item['owner']} · "
                        f"priority={item['priority']} · deadline={item.get('deadline')}"
                    )
                if result.get("tasks_created"):
                    st.success(f"Created {len(result['tasks_created'])} task(s) and notified n8n.")
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))


# ---------------------------------------------------------------------------
# Page: Employee Onboarding
# ---------------------------------------------------------------------------


def page_onboarding() -> None:
    render_hero(
        "Employee Onboarding",
        "New hire → welcome email → n8n accounts checklist → HR tasks → Slack.",
    )

    st.markdown(
        """
        **Automation pipeline**
        1. Trigger: new employee added  
        2. AI Agent: create welcome email  
        3. n8n: create accounts checklist  
        4. Task Agent: assign HR tasks  
        5. Notification: send Slack message  
        """
    )

    with st.form("new_employee"):
        c1, c2 = st.columns(2)
        full_name = c1.text_input("Full name", placeholder="Aisha Rahman")
        email = c2.text_input("Work email", placeholder="aisha.rahman@company.com")
        role = c1.text_input("Role", value="Operations Analyst")
        department = c2.text_input("Department", value="Operations")
        start_date = c1.text_input("Start date (YYYY-MM-DD)", value="")
        manager = c2.text_input("Manager", value="Unassigned")
        submitted = st.form_submit_button("Add employee & run pipeline", type="primary")

        if submitted:
            if len(full_name.strip()) < 2 or "@" not in email:
                st.error("Provide a valid name and email.")
            else:
                with st.spinner("Running onboarding pipeline…"):
                    try:
                        result = api_post(
                            "/onboarding/employees",
                            json={
                                "full_name": full_name.strip(),
                                "email": email.strip(),
                                "role": role.strip(),
                                "department": department.strip(),
                                "start_date": start_date.strip(),
                                "manager": manager.strip(),
                            },
                        )
                        st.session_state["last_onboarding"] = result
                        st.success("Onboarding pipeline completed")
                    except Exception as exc:  # noqa: BLE001
                        st.error(str(exc))

    result = st.session_state.get("last_onboarding")
    if result:
        st.subheader("Pipeline status")
        for step in result.get("pipeline", []):
            st.markdown(f"- {step}")
        st.caption(
            f"n8n triggered: `{result.get('n8n_triggered')}` · "
            f"confidence: {result.get('confidence', 0):.0%}"
        )

        st.subheader("Welcome email")
        welcome = result.get("welcome_email", {})
        st.markdown(f"**Subject:** {welcome.get('subject', '')}")
        st.text_area("Body", welcome.get("body", ""), height=220, disabled=True)

        st.subheader("Accounts checklist (n8n)")
        for item in result.get("accounts_checklist", []):
            st.markdown(
                f"- **{item.get('item')}** · {item.get('system')} · owner=`{item.get('owner')}`"
            )

        st.subheader("HR tasks assigned")
        for task in result.get("tasks_created", []):
            st.markdown(
                f"- **{task.get('title')}** · {task.get('owner')} · "
                f"`{task.get('priority')}` · source=`{task.get('source')}`"
            )

        st.info(result.get("slack_message", ""))

    st.subheader("Recent employees")
    try:
        employees = api_get("/onboarding/employees")
        if not employees:
            st.caption("No employees onboarded yet.")
        for emp in employees[:10]:
            with st.container(border=True):
                st.markdown(
                    f"**{emp['full_name']}** · {emp['role']} · {emp['department']} · "
                    f"`{emp['status']}`"
                )
                st.caption(f"{emp['email']} · manager={emp['manager']} · start={emp['start_date']}")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not load employees: {exc}")


# ---------------------------------------------------------------------------
# Page: Analytics
# ---------------------------------------------------------------------------


def page_analytics() -> None:
    render_hero(
        "Analytics Dashboard",
        "Measure queries solved, time saved, and operational request patterns.",
    )
    try:
        data = api_get("/analytics")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Analytics unavailable: {exc}")
        return

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Queries solved", data["total_queries"])
    m2.metric("Hours saved (est.)", data["estimated_hours_saved"])
    m3.metric("Open tasks", data["open_tasks"])
    m4.metric("Avg confidence", f"{data['avg_confidence']:.0%}")

    m5, m6, m7 = st.columns(3)
    m5.metric("Documents indexed", data["documents_indexed"])
    m6.metric("Tasks total", data["total_tasks"])
    m7.metric("Reports generated", data["reports_generated"])

    left, right = st.columns(2)
    with left:
        st.subheader("Most common requests")
        common = data.get("common_request_types") or []
        if common:
            fig = px.bar(
                common,
                x="type",
                y="count",
                color="count",
                color_continuous_scale=["#D5E6F2", "#1A4A6E"],
            )
            fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=20, b=10), height=320)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No query history yet.")

    with right:
        st.subheader("Queries by agent")
        by_agent = data.get("queries_by_agent") or {}
        if by_agent:
            fig2 = px.pie(
                names=list(by_agent.keys()),
                values=list(by_agent.values()),
                color_discrete_sequence=["#0B1F33", "#1A4A6E", "#2A6F8F", "#5FA8C8"],
            )
            fig2.update_layout(margin=dict(l=10, r=10, t=20, b=10), height=320)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No agent activity yet.")

    st.subheader("Generate weekly report")
    if st.button("Run Reporting Agent", type="primary"):
        with st.spinner("Generating report…"):
            try:
                report = api_post("/reports/generate", json={"report_type": "weekly"})
                st.markdown(f"### {report['title']}")
                st.write(report["summary"])
                st.markdown(report["content"])
                st.write("Bottlenecks:", report.get("bottlenecks"))
                st.write("Trends:", report.get("trends"))
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))


# ---------------------------------------------------------------------------
# Page: Settings
# ---------------------------------------------------------------------------


def page_settings() -> None:
    render_hero(
        "System Settings",
        "Runtime configuration for models, retrieval, uploads, and automation.",
    )
    st.write(f"Connected API: `{get_api_url()}`")
    try:
        settings = api_get("/settings")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**AI / RAG**")
            st.json(
                {
                    "openai_model": settings["openai_model"],
                    "embedding_model": settings["embedding_model"],
                    "vector_store": settings["vector_store"],
                    "chunk_size": settings["chunk_size"],
                    "top_k_retrieval": settings["top_k_retrieval"],
                }
            )
        with c2:
            st.markdown("**Platform**")
            st.json(
                {
                    "app_name": settings["app_name"],
                    "n8n_enabled": settings["n8n_enabled"],
                    "max_upload_size_mb": settings["max_upload_size_mb"],
                    "allowed_extensions": settings["allowed_extensions"],
                }
            )
        st.info(
            "Change values via `.env` and restart services. "
            "See `.env.example` for all supported keys."
        )
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not load settings: {exc}")

    st.subheader("Architecture")
    st.markdown(
        """
        ```
        Streamlit UI ──► FastAPI ──► Agents (LangChain; LangGraph optional)
                              │           ├─ Knowledge (RAG + Chroma/memory)
                              │           ├─ Task
                              │           ├─ Meeting
                              │           ├─ Reporting
                              │           └─ Onboarding
                              ├─ SQLite / PostgreSQL
                              └─ n8n webhooks (Email / Slack / Notify)
        ```
        """
    )


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

PAGES = {
    "Chat with Operations AI": page_chat,
    "Document Upload": page_documents,
    "Task Management": page_tasks,
    "Meeting Summarisation": page_meetings,
    "Employee Onboarding": page_onboarding,
    "Analytics Dashboard": page_analytics,
    "System Settings": page_settings,
}

PAGES[page]()

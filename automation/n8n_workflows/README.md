# OpsFlow AI — n8n Automation Workflows

Import these JSON workflows into your n8n instance (**Workflows → Import from File**).

| Workflow | Webhook path | Purpose |
|---|---|---|
| `email_to_task.json` | `/webhook/email-ops-intake` | Email → OpsFlow task extraction → Slack |
| `document_upload.json` | `/webhook/document-uploaded` | Document indexed → email/Slack notify |
| `meeting_summary.json` | `/webhook/meeting-summary` | Meeting summary → Slack + email digest |
| `task_created.json` | `/webhook/task-created` | Any new task → Slack channel alert |
| `employee_onboarding.json` | `/webhook/employee-onboarding` | New hire → welcome email → accounts checklist → Slack |

## Required credentials in n8n

1. **Slack OAuth / Bot token** for `#operations` (and optional `#ops-knowledge`)
2. **SMTP** credentials for email notifications
3. Ensure OpsFlow backend is reachable (Docker: `http://backend:8000`, local: `http://host.docker.internal:8000`)

## Environment alignment

Match webhook paths with `.env`:

```
N8N_WEBHOOK_BASE_URL=http://localhost:5678/webhook
N8N_TASK_CREATED_WEBHOOK=task-created
N8N_DOCUMENT_UPLOADED_WEBHOOK=document-uploaded
N8N_MEETING_SUMMARY_WEBHOOK=meeting-summary
N8N_EMPLOYEE_ONBOARDING_WEBHOOK=employee-onboarding
```

## Example end-to-end flows

```
Email → n8n → OpsFlow AI → Task Creation → Notification
Document Upload → AI Processing → Vector Database Update → Notification
Meeting Transcript → AI Summary → Slack/Email Notification
New Employee → Welcome Email (AI) → Accounts Checklist (n8n) → HR Tasks → Slack
```

Set `N8N_ENABLED=false` in `.env` if you want to run OpsFlow without an n8n instance (webhooks become no-ops).

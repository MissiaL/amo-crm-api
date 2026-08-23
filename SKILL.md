---
name: amo-crm-api
description: "Work with amoCRM (amo CRM, амоСРМ) REST API v4: сделки, контакты, компании, задачи, примечания, справочники и webhook-подписки. Use for amoCRM API requests and account data operations on *.amocrm.ru; not for generic CRM advice."
metadata: {"author":"MissiaL","version":"0.2.0","keywords":["amocrm","crm","sales","leads","contacts","tasks"]}
---

# amo-crm-api

Full CRUD over amoCRM REST API v4 — leads, contacts, companies, tasks, notes,
plus dictionary lookups (pipelines, users, custom fields, tags) and webhook
subscription management.

## Setup

Two environment variables are required:

| Var | Example | Where to get it |
|---|---|---|
| `AMOCRM_SUBDOMAIN` | `mycompany` | The part before `.amocrm.ru` in your account URL |
| `AMOCRM_TOKEN` | `eyJ0eXAi...` | Long-lived token from amoMarket → Integrations → integration keys |

Sanity-check the setup:

```bash
python scripts/api_call.py --method GET --url "/api/v4/account"
```

A 200 with the account JSON means you're set. A 401 means the token is invalid,
expired, revoked, or the integration was disabled. Long-lived tokens have a
user-selected expiry of 1 day to 5 years and no refresh token.

## HTTP client

All requests go through `scripts/api_call.py`. The script signs every request
with `Authorization: Bearer ${AMOCRM_TOKEN}`, prefixes relative URLs with
`https://${AMOCRM_SUBDOMAIN}.amocrm.ru`, and sends bodies as JSON.

```bash
# GET
python scripts/api_call.py --method GET --url "/api/v4/leads" --params '{"limit":"50"}'

# POST (body is a JSON array even for one object!)
python scripts/api_call.py --method POST --url "/api/v4/leads" \
  --body '[{"name":"Ivanov deal","price":100000}]'

# PATCH single (body is an object)
python scripts/api_call.py --method PATCH --url "/api/v4/leads/12345" \
  --body '{"status_id":42}'

# PATCH bulk (body is an array)
python scripts/api_call.py --method PATCH --url "/api/v4/leads" \
  --body '[{"id":12345,"status_id":42},{"id":12346,"status_id":143}]'
```

`--params`, `--body`, and `--headers` MUST be valid JSON. Don't pass query
strings like `a=1&b=2`. Don't pass form-encoded bodies.

## References map

Load only what you need for the current request:

| File | When to read |
|---|---|
| [references/conventions.md](references/conventions.md) | First, before any work — covers filters, pagination, response shape, error codes |
| [references/leads.md](references/leads.md) | When working with deals (sделки) |
| [references/contacts-companies.md](references/contacts-companies.md) | When working with contacts or companies |
| [references/tasks-notes.md](references/tasks-notes.md) | When creating/closing tasks or adding notes |
| [references/dictionaries.md](references/dictionaries.md) | Before creating/updating entities — to look up pipeline IDs, user IDs, custom field IDs, tag IDs |
| [references/webhooks.md](references/webhooks.md) | When subscribing/unsubscribing a URL to amoCRM events |

## Common workflows

### 1. Create a deal with a new contact

```
1. GET /api/v4/leads/pipelines  → pick pipeline_id and status_id
2. GET /api/v4/users            → pick responsible_user_id
3. POST /api/v4/leads/complex   → creates the lead, contact, and company in one call
```

### 2. Find a customer's deals by name or phone

```
1. GET /api/v4/contacts?query=Иванов&with=leads  → find the contact
2. Read its `_embedded.leads[]` IDs, then GET those leads by ID as needed
```

### 3. Move a deal to a different status

```
1. GET /api/v4/leads/pipelines/{pipeline_id}/statuses → confirm target status_id
2. PATCH /api/v4/leads/{lead_id}  with body {"status_id": <new>}
```

### 4. Set and close a task

```
1. POST /api/v4/tasks  body: [{"entity_type":"leads","entity_id":<lead_id>,"text":"...","complete_till":<unix>}]
2. PATCH /api/v4/tasks/{task_id}  body: {"is_completed": true, "result": {"text": "done"}}
```

## Rules

- **All requests through `scripts/api_call.py`** — never invoke `curl` directly.
  The script handles auth, encoding, and error classification for you.
- **Read `references/dictionaries.md` BEFORE creating or updating** entities
  with custom fields, status, pipeline, or responsible user. You need real IDs.
- **Collection responses with content nest items under `_embedded`** — for
  example `data["_embedded"]["leads"]`. Single-entity responses are direct
  objects; some empty results and successful deletes return 204 with no body.
- **Bulk entity creation uses arrays.** Leads, contacts, companies, tasks, and
  notes use `[{...}]` even for one item. Webhook subscription uses an object;
  link endpoints use an array. Single-by-ID PATCH uses an object; bulk PATCH
  uses an array.
- **Phone and email are NOT first-class fields** on contacts/companies — they
  live inside `custom_fields_values` with `field_code: "PHONE"` and
  `field_code: "EMAIL"`. See `references/contacts-companies.md`.
- **On 401, ask the user to refresh `AMOCRM_TOKEN`.** Don't pretend the bot
  can fix it. The token has likely expired or was revoked.
- **On 429, honor `Retry-After` when present; otherwise back off before one
  retry.** The standard limit is 7 requests/s per integration and 50/s per account.
- **Pagination: `limit` is endpoint-specific and usually max 250.** Use `page=2,3,...` to walk
  results. The response includes `_links.next.href` when more pages exist.
- **Advanced `filter[...]` fields require the account's API filtering add-on.**
  Check `GET /api/v4/account?with=is_api_filter_enabled` before
  relying on alpha filters. Top-level `query` is still documented but marked
  for future deprecation; prefer stable IDs whenever possible.
- **Never expose `AMOCRM_TOKEN`** to the user, in logs, or in messages. The
  script already redacts it from output.

# Webhook subscription management

> **Important: this file covers SUBSCRIPTION MANAGEMENT only.** It teaches
> the agent to register, list, and unregister webhook destinations through
> amoCRM REST API. To actually RECEIVE webhook events you need a separate
> public HTTPS server that accepts POSTs from amoCRM — that is not part of
> this skill, and the skill cannot deliver it.

Read [conventions.md](conventions.md) first.

## Endpoints

| Method | Path | Body |
|---|---|---|
| `GET` | `/api/v4/webhooks` | — |
| `POST` | `/api/v4/webhooks` | `{"destination": "...", "settings": [...]}` |
| `DELETE` | `/api/v4/webhooks` | `{"destination": "..."}` |

Note: `DELETE` carries a body (uncommon for HTTP). `api_call.py` handles it via
`--method DELETE --body '...'`.

## List current subscriptions

```bash
python scripts/api_call.py --method GET --url "/api/v4/webhooks"
```

Response shape:

```json
{
  "_total_items": 2,
  "_embedded": {
    "webhooks": [
      {
        "id": 100500,
        "destination": "https://my-bot.example.com/amo-hook",
        "created_at": 1714521600,
        "updated_at": 1714521600,
        "created_by": 42,
        "sort": 1,
        "disabled": false,
        "settings": ["leads:add", "leads:status"]
      }
    ]
  }
}
```

## Subscribe a URL to events

```bash
python scripts/api_call.py --method POST --url "/api/v4/webhooks" --body '{
  "destination": "https://my-bot.example.com/amo-hook",
  "settings": ["leads:add", "leads:status", "contacts:add"]
}'
```

Constraints:
- `destination` MUST be HTTPS.
- The URL must be publicly reachable; amoCRM ping-tests on subscribe.
- `settings` is a flat array of event keys.

## Available events (`settings[]`)

### Leads
- `leads:add`
- `leads:update`
- `leads:delete`
- `leads:restore`
- `leads:status`
- `leads:responsible`

### Contacts
- `contacts:add`
- `contacts:update`
- `contacts:delete`
- `contacts:responsible`

### Companies
- `companies:add`
- `companies:update`
- `companies:delete`
- `companies:responsible`

### Customers (only if customers are enabled in the account)
- `customers:add`
- `customers:update`
- `customers:delete`
- `customers:status`
- `customers:responsible`

### Notes (created on entity)
- `note:lead:add`
- `note:contact:add`
- `note:company:add`
- `note:customer:add`

### Tasks
- `task:add`
- `task:update`
- `task:delete`

### Other
- `incoming_chat_message`
- `incoming_call`

If an event isn't supported on your account plan, the subscription is silently
ignored for that key but other keys still register.

## Unsubscribe

```bash
python scripts/api_call.py --method DELETE --url "/api/v4/webhooks" --body '{
  "destination": "https://my-bot.example.com/amo-hook"
}'
```

The whole destination is removed — there's no per-event unsubscribe. To change
the event list, DELETE then POST with the new `settings`.

## Common workflow: re-subscribe with a different event set

```bash
# 1. Read existing subscriptions
python scripts/api_call.py --method GET --url "/api/v4/webhooks"

# 2. Delete the old subscription for our destination
python scripts/api_call.py --method DELETE --url "/api/v4/webhooks" \
  --body '{"destination":"https://my-bot.example.com/amo-hook"}'

# 3. Create with new settings
python scripts/api_call.py --method POST --url "/api/v4/webhooks" --body '{
  "destination": "https://my-bot.example.com/amo-hook",
  "settings": ["leads:add", "leads:status", "task:add", "task:update"]
}'
```

# amo-crm-api

Agent-skill for [amoCRM](https://www.amocrm.ru/) REST API v4. Gives any LLM
agent (Claude Code, Claude.ai, custom Telegram bot, etc.) full CRUD over
leads, contacts, companies, tasks, and notes — plus dictionary lookups and
webhook subscription management.

The skill consists of:
- `SKILL.md` — agent-facing entry point with workflows and rules
- `references/*.md` — detailed per-area documentation, loaded by the agent on demand
- `scripts/api_call.py` — thin Python HTTP client that signs every request with Bearer auth

## Install

```bash
git clone https://github.com/MissiaL/amo-crm-api ~/.claude/skills/amo-crm-api
```

Or, when published, via clawhub:

```bash
clawhub install missial/amo-crm-api
```

## Get an amoCRM long-lived token

1. Log in to your amoCRM account.
2. Open **Settings → Integrations** ([direct link](https://www.amocrm.ru/settings/widgets/)).
3. Click **+Create integration → "Внешняя интеграция"** (External integration), or
   pick an existing internal integration.
4. In the integration settings, enable the **"Долгосрочный период"** (Long-lived
   period) toggle and copy the generated access token. It's valid for years and
   doesn't need refresh.
5. Note your account subdomain — the part before `.amocrm.ru` in your URL
   (e.g. `mycompany` for `https://mycompany.amocrm.ru`).

## Configure environment

Set two env vars:

```bash
export AMOCRM_SUBDOMAIN=mycompany
export AMOCRM_TOKEN=eyJ0eXAi...
```

Or copy [.env.example](.env.example) to `.env` and fill in.

Sanity-check:

```bash
python scripts/api_call.py --method GET --url "/api/v4/account"
```

A 200 with the account JSON means the skill is wired up. A 401 means the token
is wrong or expired.

## Use with an agent

Once the skill directory is in a path the agent searches (e.g.
`~/.claude/skills/`), tell the agent something like:

> "Find all open deals in the main pipeline assigned to Ivan and create a task
> to call them tomorrow."

The agent reads `SKILL.md`, decides which `references/*.md` to load, and uses
`scripts/api_call.py` to make the calls.

## Webhooks

The skill can **manage subscriptions** to amoCRM webhook events through
REST — register a destination URL, list current subscriptions, unsubscribe.
It does NOT receive webhook events; for that you need a separate public HTTPS
server. See [references/webhooks.md](references/webhooks.md).

## License

[MIT](LICENSE)

## Author

[MissiaL](https://github.com/MissiaL)

# Monitor API (`/api/v1/monitor`)

## Auth

- **Web (JWT)**: `Authorization: Bearer <access_token>` from existing login
- **Agent (device)**: `Authorization: Device <device_uuid>:<device_token>`

Never send `user_id` from the client as proof of identity; the server derives it from JWT or registered device.

## Client time (required)

The backend **does not** use server clock for monitor timestamps. Clients must send:

| Header | Purpose |
|--------|---------|
| `X-Client-Time` | ISO-8601 instant (e.g. `2026-10-29T07:30:00.000Z`) for session start, heartbeats, pairing expiry, live `as_of`, etc. |
| `X-Client-Local-Date` | Calendar day on the user’s machine (`YYYY-MM-DD`) for daily summaries and “today” views |

Device/agent POST bodies should also include `"client_time": "<ISO-8601>"`. The React app sets both headers on every API request via axios and adds `client_time` to POST/PUT/PATCH JSON bodies.

**Project writes** (`POST/PUT` on `/projects`, `/project-groups`, `/project-allocations`, project excel uploads) use the same headers/body field to set `created_at` / `updated_at` in the database instead of the server clock.


1. `POST /monitor/pairing/code` (JWT, worker/team_leader) → `{ pairing_code, expires_at }`
2. `POST /monitor/devices/register` (public) body:

```json
{
  "pairing_code": "A1B2C3",
  "device_uuid": "uuid-from-agent",
  "device_name": "PC-NAME",
  "operating_system": "Windows 10",
  "agent_version": "1.0.0"
}
```

Returns `device_token` **once** — store securely on the agent machine.

## Session lifecycle (device auth)

| Method | Path |
|--------|------|
| POST | `/monitor/sessions/start` |
| POST | `/monitor/sessions/{id}/heartbeat` |
| POST | `/monitor/sessions/{id}/events` |
| POST | `/monitor/sessions/{id}/break/start` |
| POST | `/monitor/sessions/{id}/break/end` |
| POST | `/monitor/sessions/{id}/end` |

Heartbeat body example:

```json
{
  "active_seconds_delta": 45,
  "idle_seconds_delta": 0,
  "break_seconds_delta": 0,
  "client_state": "active"
}
```

Events use unique `event_uuid` for idempotency.

## Employee / manager (JWT)

- `GET /monitor/policy`
- `GET /monitor/me/today`
- `GET /monitor/manager/live` (manager roles)
- `GET /monitor/manager/employees/{user_id}/timeline?date=YYYY-MM-DD`
- `GET /monitor/manager/reports/daily?date=&user_id=`

- `GET /monitor/analytics/overview?date=YYYY-MM-DD` (JWT — managers: all users; others: self)
- `GET /monitor/analytics/users/{user_id}?date=YYYY-MM-DD` (JWT — self or manager)

## Backend environment

Copy `Team_management/.env.example` monitor section into your `.env`:

- `MONITOR_IDLE_THRESHOLD_SECONDS=30`
- `MONITOR_HEARTBEAT_STALE_SECONDS=120`
- `MONITOR_HEARTBEAT_INTERVAL_SECONDS=45`

Restart Flask after changes.

## Database migration

```bash
cd Team_management
flask db upgrade
```

Revision: `a1b2c3d4e5f6_monitor_tables.py`

## Custom protocol

Web opens `educermonitor://start` (no secrets). Agent must already be installed and paired separately.

## Policy defaults

- Idle threshold: **30 seconds** (default; configurable via env)
- Heartbeat stale → **unknown** (not idle)
- No keystrokes, clipboard, or screen capture

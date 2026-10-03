# Chatbooks SaaS server deployment package

This provider-neutral package defines the process, ingress, storage, configuration, maintenance,
and monitoring contracts for a future Chatbooks server. It is an engineering foundation, not a
deployed server and not C4 authorization.

## Fixed topology

```text
public client
  -> provider-selected HTTPS ingress
  -> one loopback-only Next.js frontend process
  -> same-origin /api/chatbook proxy
  -> one loopback-only FastAPI backend process
  -> one local persistent SQLite BUSINESS database
```

Only the FastAPI process is the authoritative financial writer. The frontend, ingress, monitoring,
and backup storage never receive database write authority. The process supervisor must keep the
backend instance count at exactly one. The `chatbook-api` entry point also fixes Uvicorn's worker
count at one; a supervisor must not wrap it in a multiprocess server or start overlapping instances.
Provider, operating system, reverse proxy, domain, TLS certificate source, and numerical capacity
remain `REQUIRES_OPERATOR_DECISION`.

## Package contents

- `config/server.example.json` defines every required runtime and storage path. Its placeholders are
  intentionally invalid until an operator creates a protected, server-local configuration.
- `env/*.env.example` documents the environment variable boundary. It contains no credentials.
- `contracts/ingress.json` requires public HTTPS to terminate before the frontend and forbids public
  routing to FastAPI.
- `contracts/processes.json` fixes one backend writer and one frontend process under supervision.
- `contracts/storage.json` separates the live database, backup, restore proof, future v4 target,
  evidence, logs, recovery release, and secrets.
- `monitoring/operational-monitoring.example.json` separates hard invariants from values requiring a
  measured server baseline.

## Commands

Install the exact reviewed release and its locked dependencies before running these commands. These
commands do not choose a provider or install a process supervisor.

```text
chatbook-saas-deployment package-check --project-root <release-root>
chatbook-saas-deployment validate-config --config <protected-server-config.json>
chatbook-saas-deployment provision-v3 --config <protected-server-config.json>
chatbook-saas-deployment inspect --config <protected-server-config.json>
chatbook-saas-deployment environment --config <protected-server-config.json>
```

`provision-v3` creates a new schema-v3 BUSINESS candidate only when every configured database,
backup, restore, v4 target, and credentials artifact is absent. It uses `AuthService` and
`AccountingEngine`, creates representative C4 data, records sanitized manifest evidence, and leaves
the future v4 target absent. Generated credentials are written once to the configured protected
secrets path and are never printed or included in evidence.

The candidate is not approved by provisioning. A named Release Owner and Accounting/Data Reviewer
must review its path, hash, schema/content fingerprints, row counts, reports, and recovery evidence.

After an authorized operator has placed the server in sealed maintenance, drained requests, stopped
the backend, and verified zero in-flight work, the following command can create a fresh backup and
separate restore proof:

```text
chatbook-saas-deployment backup-restore --config <protected-server-config.json>
```

The command fails unless the server-owned maintenance state is sealed and stopped. It acquires a
SQLite writer gate, creates a verified backup with the existing migration-evidence implementation,
restores it to the configured distinct proof path, and confirms the source hash did not change. It
does not migrate, create a v4 target, run a canary, or authorize C4.

## Runtime start contract

The supervisor injects the backend environment from the protected configuration and runs:

```text
chatbook-api
```

This entry point runs one Uvicorn worker. It may use multiple worker threads for concurrent requests;
each request receives distinct request-owned database connections. Do not add `--workers`, set up a
multiprocess wrapper, or start a second backend instance while SQLite remains authoritative.

It injects the frontend environment and runs the already-built frontend from `frontend`:

```text
npm run start -- --hostname 127.0.0.1 --port <configured-frontend-port>
```

Backend health is `GET http://127.0.0.1:<backend-port>/api/v1/health`. Frontend health is a local
HTTP request to `/login` or `/`; the selected supervisor/ingress must record its exact probe and
expected response. The public ingress must route only to the frontend. Browser API requests use the
same-origin `/api/chatbook/*` route, and Next.js uses `CHATBOOK_API_URL` to reach FastAPI internally.

The supervisor sends its platform-equivalent graceful termination signal, honors the server-owned
maintenance shutdown request, waits for connection closure, and escalates only after a measured and
approved timeout. The exact signal and timeout are provider/OS decisions.

## Maintenance and monitoring

The existing controls remain authoritative:

```text
chatbook-traffic-control --control <control.json> --state <state.json> status
chatbook-traffic-control --control <control.json> --state <state.json> enter --reason <reason>
chatbook-traffic-control --control <control.json> --state <state.json> wait --timeout-seconds <approved-seconds>
chatbook-traffic-control --control <control.json> --state <state.json> seal --reason <reason>
chatbook-traffic-control --control <control.json> --state <state.json> request-shutdown --reason <reason>
chatbook-c4-monitor <protected-monitoring-config.json> --evidence <protected-evidence.json>
```

These controls are local operator commands. There is no public API or frontend control that can
change maintenance configuration. Wrong schema, integrity failure, foreign-key violations,
idempotency disagreement, ledger/report mismatch, applicable audit-sidecar mismatch, and migration
failure are deterministic stop conditions. Latency, drain time, lock/error rates, migration time,
capacity, and observation duration remain `BASELINE_REQUIRED` until measured on the selected server.

## Security boundary

Server configuration, database files, backups, restore artifacts, evidence, recovery releases, and
generated credentials stay outside web roots and require provider/OS access controls. The ingress
must not expose FastAPI, SQLite, backup, restore, evidence, runtime-control, or secrets paths. It
must sanitize incoming forwarding headers, must not retry non-idempotent requests automatically,
and must preserve maintenance `503` responses.

Authentication remains the application’s opaque bearer-session design: scrypt password hashes and
hashed session tokens are stored in the same selected database; the browser receives the token only
through the Next.js server, which stores it in an HTTP-only, secure production cookie. No new auth
secret is introduced by this package. Deployment, TLS, backup, and provider credentials must be
injected by the selected platform and never committed.

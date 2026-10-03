# Chatbooks security

## Current trust boundary

M3 provides a network application boundary and M4 adds a browser session proxy, but neither is a
cloud deployment profile. API actor IDs come
only from authenticated opaque bearer sessions. Every organization route resolves the authenticated
membership and an explicit role permission before calling the engine. Client-supplied actor IDs are
never accepted as authentication. The local CLI remains a trusted operator interface and still accepts
actor IDs; it must not be exposed as a remote or AI tool.

Anyone with filesystem write access to the SQLite file or application source is inside the trusted
boundary. Such an administrator can replace the database, alter triggers, spoof actor IDs, or modify
the clock. Append-only triggers prevent accidental/unsupported mutations through intact application
connections, and the connection authorizer prevents forged audit inserts through the engine's private
connection. These controls do not provide cryptographic tamper evidence against the database owner or
protect the file from a different SQLite client. TLS termination, host hardening, secrets management,
rate limiting, monitoring, and protected backups are deployment responsibilities not implemented here.

M3 currently protects business data through organization membership and organization-scoped
foreign keys. M3.5 defines Personal and Business Financial Spaces as a future product context; it
does not add personal data or a new security boundary to the running system.

The M4 browser sends credentials and application requests only to a same-origin Next.js proxy. On
successful login the proxy removes the bearer token from the browser-visible response and stores it
in an HTTP-only, SameSite=Lax cookie; production mode also marks the cookie Secure. Client-side code
cannot read the token. The proxy forwards it to FastAPI, where session validity, membership, and
permissions remain authoritative. This pattern reduces token exposure to browser JavaScript but does
not replace TLS, CSRF review for future cross-site deployments, login throttling, MFA, or secure host
operations.

## M5.0 future Financial Space isolation

Every future space-aware request must provide a typed `PERSONAL` or `BUSINESS` context and its ID.
The server must derive accessible spaces from authenticated ownership or membership and resolve
resources through that same context. A user who can access both contexts does not authorize the
application to combine them implicitly.

Space separation applies to persistence, authorization, identifiers, API responses, report queries,
caches, search indexes, exports, conversation history, document retrieval, notifications, analytics,
logs, and future AI tool context. Cache keys and background work must include both space kind and ID.
An identifier from one kind cannot be accepted in another, and a business project cannot be attached
to personal activity.

Personal data must not be stored as an ordinary organization merely to reuse M3 authorization.
M5.0 defines `PersonalSpace` as a separate stable owner with one authenticated owner and one space per
user in the initial model. It is private by default. Organization roles, including `OWNER` and
`ACCOUNTANT`, confer no personal access. Household sharing, delegation, revocation, deletion,
retention, export, and account-recovery effects remain explicit product/security decisions.

A future space-discovery endpoint may list the authenticated user's PERSONAL reference and accessible
BUSINESS references but must not include one context's accounts, balances, activity, or reports while
resolving another. Existing organization routes remain business-only; future personal routes require
`personal_space_id` and owner authorization.

No journal may span spaces. Cross-space money movement requires separately authorized operations,
and any correlation record must not grant access from one side to the other.

### Required backend enforcement

Every personal request must authenticate the actor, resolve the typed PERSONAL kind and exact ID,
authorize `owner_user_id`, and load every child by `personal_space_id`. The route must reject a
business ID, an inaccessible personal ID, and a child ID copied from another personal space. The
same rule applies to list counts, pagination totals, exports, cache keys, background jobs, documents,
search, notifications, conversation history, analytics, and future AI retrieval.

| Failure scenario                                       | Required defense                                                                   |
| ------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| Personal ID sent to an organization route              | Organization foreign key/membership lookup fails; no personal fallback             |
| Organization ID sent to a personal route               | Personal owner lookup fails; no organization fallback                              |
| Organization accountant requests owner's personal data | Deny unless a separate future personal grant exists                                |
| Future household member substitutes another space ID   | Grant lookup must bind actor, space, permission, and active consent                |
| Client sends the wrong selected context                | Server-authorized route scope wins; frontend state is ignored as authority         |
| Cache or job omits kind                                | Reject the key/job contract; kind and ID are mandatory                             |
| Cross-space transfer caller lacks one side             | Do not expose the other side; only independently authorized operations may proceed |

Existence-sensitive reads should prefer the same not-found response for inaccessible and absent
personal resources. Access-denial and security monitoring are separate from immutable financial
audit and need a production logging policy.

## M5.1 universal-core threat model

M5.1-A selects a future persistent LedgerBook as an internal financial scope. It is not a client
resource and never proves authority. The authenticated backend resolves a typed Financial Space,
checks organization membership/role or personal ownership/grant, and only then issues an internal
authorized context containing the mapped book and capabilities.

The universal service accepts that internal context for BUSINESS operations. Schema v3 uses
composite organization foreign keys. The disposable schema-v4 rehearsal target generalizes those
constraints to `ledger_book_id` for accounts, periods, proposals, confirmations, entries, lines,
reversals, and receipts. Projects and organization documents retain additional exact
business-organization constraints.

| Threat                                              | Required architecture defense                                                                         |
| --------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Client supplies a valid book ID from another space  | Public APIs do not accept book IDs as authority; server resolves them from the authorized typed space |
| Business route receives a personal ID               | Organization-only lookup fails before book resolution or child queries                                |
| Personal route receives an organization ID          | PersonalSpace-only lookup and owner/grant check fail; no organization fallback                        |
| Core child refers to another book                   | Composite book-scoped foreign key and current-state validation reject it                              |
| Cross-space correlation reveals the other side      | Return local references and minimal status only after separate authorization                          |
| Search/cache/export/job omits scope                 | Contract requires space kind, owner ID, and book ID; missing scope fails closed                       |
| Audit endpoint queries globally                     | Authorize a space first, then filter by book; global financial audit is unavailable                   |
| Logs or notifications leak context                  | Use allowlisted structured fields, redaction, scoped delivery, and explicit retention                 |
| Future AI or document retrieval names another space | Server-issued context remains fixed; content and conversation text are never authorization            |
| Migration partially converts business history       | One transaction per schema step, reconciliation before cutover, fail without enabling personal writes |

The staged migration preserves audit sequences, timestamps, actors, before/after payloads, metadata,
idempotency receipts, IDs, and reversal chains. Migration must not dual-write posted history or treat
copied data as newly created financial events. Security tests must substitute personal,
organization, book, account, proposal, confirmation, project, document, and audit identifiers across
every route and background interface.

Tax/compliance extensions remain outside the core and receive scoped read models plus proposal-only
write tools. They cannot bypass authorization, edit audit history, or claim that a balanced ledger
proves regulatory compliance. Full architecture is in
[`universal-financial-core.md`](universal-financial-core.md).

## M5.1-C1 implemented migration controls

Schema v3 implements only the BUSINESS organization-to-book mapping. The internal resolver accepts
an authenticated/trusted actor and organization ID, verifies membership first, and then reads that
organization's book. It has no raw-book lookup mode. Public API schemas and routes expose no
`ledger_book_id`, and existing financial children remain protected by their organization-scoped
foreign keys.

Every organization maps to the deterministic ID `book:business:<organization_id>`. The database
requires owner kind `BUSINESS`, a valid unique organization, exact organization currency and
precision, immutable creation provenance, and immutable mapping rows. Startup verifies complete
one-to-one coverage before serving the database. New organization creation inserts the organization,
book, owner membership, and chart in the same transaction.

Version-2 migration acquires `BEGIN IMMEDIATE` before evidence capture, blocking another writer. It
uses SQLite's backup API, verifies a separate restored database, and runs integrity, foreign-key,
proposal, validation, confirmation, receipt, journal, period, reversal, audit, project/document, and
report-fingerprint checks on the consistent copy. Diagnostics contain stable reason codes rather
than financial payloads. The migration then compares hashes for every pre-existing table and rolls
back without advancing the schema version on any mismatch. It neither repairs discrepancies nor
creates audit events for the internal mapping.

The `.pre-v3.backup` and `.manifest.json` files contain or describe sensitive financial data and
inherit the source database's access requirements. This local evidence capability does not provide
backup scheduling, remote storage, retention, encryption, key management, or production disaster
recovery.

## M5.1-C2 implemented service controls

- `AccountingEngine` resolves actor plus organization through the membership-first BUSINESS resolver
  before calling the universal service. API roles remain enforced by the existing permission layer.
- `AuthorizedFinancialContext` is immutable and carries the exact space, owner, book, currency,
  precision, capabilities, authority source, request provenance, and optional project scope.
- Every service entry point requires a context and the capability for that operation. Missing context,
  missing capabilities, and project-scope mismatch fail closed.
- The organization storage adapter independently binds the context to the schema-v3 book mapping and
  rejects forged book, organization, currency, or precision values.
- Repository and unit-of-work protocols expose typed financial operations only. They do not expose
  the SQLite connection or a general query/execute method to the universal service.
- Project and document lookup remain in the BUSINESS facade, with organization validation before the
  service receives extension identifiers.
- Public OpenAPI and CLI contracts do not expose raw book IDs, authorized contexts, PERSONAL space,
  or a way to construct audit events.

The current database layer still owns the process-private SQLite connection for migration, auth, and
business-only persistence. The service extraction does not make that connection a public API.

## M5.1-C3 implemented rehearsal controls

- The orchestrator accepts only a schema-v3 file and distinct backup/target paths. It requires a
  passing preflight, SQLite-consistent backup, separate restore proof, and unchanged source hash.
- Reconstruction, reconciliation, table swap, trigger/index installation, integrity checks, and
  schema-version advance occur in one target transaction. Eleven injected failure points prove
  rollback to the complete v3 target snapshot.
- `CanonicalDatabase` opens only a verified file-backed v4 copy. It binds every financial write to
  an internal book context and rejects a row whose book differs from that context.
- Composite foreign keys and BUSINESS extension constraints reject cross-book account, period,
  proposal, validation, confirmation, journal, project, document, idempotency, and reversal
  substitutions.
- The book repository exposes named operations only. The service receives no connection, cursor,
  generic SQL method, or client-provided book authority.
- Existing audit rows and sequence state remain unchanged. New financial triggers create a
  legacy-shaped event and book sidecar in one transaction. The connection authorizer rejects direct
  inserts into either audit table; triggers reject update, delete, and replacement.
- Normal `Database`, API startup, and CLI startup continue to reject v4. Tests must opt into the
  rehearsal factory, which prevents accidental writer resumption or production cutover.
- SQLite still serializes writers with `BEGIN IMMEDIATE`. Tests cover concurrent idempotent retry,
  competing reversal, post-versus-period-lock, and writes to independent books without claiming
  distributed concurrency.

## API SQLite connection lifecycle

Each FastAPI engine or authentication dependency creates a new connection for one request and closes
it when that dependency exits. Starlette/AnyIO may run a synchronous generator dependency's enter,
nested dependency or endpoint, and exit stages on different worker threads. API request connections
therefore allow sequential thread handoff; they are never pooled or reused across requests. Direct
engine, CLI, migration, backup, monitoring, cutover, and rehearsal connections keep SQLite's default
creator-thread enforcement.

The `chatbook-api` entry point explicitly configures one Uvicorn worker, and the deployment contract
also requires exactly one backend process with no replacement overlap. Concurrent requests within
that process use distinct connections. SQLite continues to serialize financial writers through
`BEGIN IMMEDIATE`, so connection handoff does not change transaction, authorization, idempotency,
audit, or ledger rules. This design does not support multiple backend processes, horizontal
instances, or SQLite on shared-network storage.

C3 does not protect a database file from its operating-system owner, provide encrypted backups,
authorize a production cutover, or enable PERSONAL books. Those remain deployment/C4/future gates.

## M5.1-C4A implemented operational-rehearsal controls

- `chatbook-c4a-rehearsal` accepts only a new output directory and constructs an entirely synthetic
  schema-v3 source; it has no existing-database input and cannot be used as the live cutover command.
- The harness closes its controlled writer, acquires `BEGIN IMMEDIATE`, proves a competing writer is
  blocked before and after SQLite backup, and proves the writer gate is released afterward.
- Backup and a separately retained restore are hashed and preflighted. Manifest and report
  fingerprints must match, and the compatible v3 application must open the restore.
- V4 reconstruction remains confined to new disposable targets. Normal app selection remains v3.
- Engine, authenticated API/OpenAPI, and trusted CLI reads are compared exactly without exposing a
  raw book authority. The frontend remains on the unchanged API contract.
- Success and failure canaries run only on disposable v4 clones. The failure drill preserves the
  committed v4 proposal and forbids old-backup restore, exercising the forward-recovery boundary.
- Generated evidence contains counts, hashes, durations, diagnostic codes, and synthetic identifiers,
  not session tokens, passwords, financial descriptions, journal payloads, or complete audit JSON.

The synthetic workspace does not prove production ACLs, encryption, retention, process inventory,
logging, or monitoring. Those controls and the exact deployment writer shutdown remain mandatory
approval gates. See the [SaaS deployment package](../deploy/saas/README.md).

## Implemented controls

- Organization membership checks precede scoped reads and writes.
- Passwords use per-password random salts and scrypt; plaintext passwords are never stored.
- Bearer tokens are cryptographically random, stored only as SHA-256 hashes, expire after a bounded
  lifetime, and can be revoked by logout.
- `OWNER`, `ADMIN`, `ACCOUNTANT`, `MEMBER`, and `VIEWER` map to explicit permissions; organization
  routes fail when membership or permission is absent.
- Composite foreign keys enforce organization ownership of financial references.
- One immutable BUSINESS LedgerBook maps to each organization; currency and precision must match,
  while normal financial foreign keys remain organization-scoped in v3 and rehearsal copies use
  book-scoped v4 constraints.
- BUSINESS book resolution authorizes organization membership before reading the internal mapping;
  public clients cannot use a raw book ID as authority.
- Schema-v2 migration blocks writers, creates and restore-verifies a consistent backup, fails closed
  on preflight discrepancies, and proves every legacy table unchanged before committing v3.
- Parameterized SQL handles external values; dynamic identifiers come only from fixed internal lists.
- Strict table types, value/date checks, line limits, aggregate posting triggers, and unique indexes
  protect ledger structure, double-entry balance, and duplicate postings/reversals.
- Atomic writes keep ledger and audit events consistent, including on failure.
- Update, delete, replacement, and line-append guards protect posted/proposed history.
- Confirmation identifies the validation, proposal, and actor; current state is rechecked at posting.
- Confirmation provenance binds proposal version 1, authenticated actor, UTC time, and caller request
  identifier. The idempotency key is also carried into audit correlation metadata.
- Confirmation and posting idempotency receipts commit atomically with their result and reject a key
  reused for different request content.
- Audited previous/new states and request IDs make successful mutations traceable.
- The supported connection rejects direct audit-event inserts; only known audit triggers can append.
- No document execution, URL fetching, upload processing, extraction, AI provider, or client access
  to raw SQL, SQLite paths, engine internals, or database connections.
- The frontend has no SQLite dependency or database path and reaches financial data only through the
  typed API proxy.

The supported database connections enable foreign keys and recursive triggers. Arbitrary database
clients are not supported mutation interfaces. Some guards require application-provided audit
functions and reject writes if no actor context is available. The API establishes session identity
and exact-request confirmation provenance; it does not yet provide MFA, dual approval, or
device-bound proof of presence.

## Data handling and operational limits

Database contents, credential hashes, session hashes, audit snapshots, filenames, client names,
descriptions, storage references, and CLI output may contain sensitive data. Encryption, key
management, backup scheduling, retention/deletion policy, redaction, MFA, password reset/account
recovery, login throttling, and external audit anchoring are not implemented. The supplied document
checksum is metadata and is not verified against file bytes. Use synthetic data during evaluation.
Keep local databases out of version control and deploy the API only behind TLS.

Use restrictive OS file permissions and storage on a local filesystem. The implemented v2→v3 path
uses SQLite's consistent backup API and restore proof; copying a live database file alone remains
unsupported. Future deployment still requires scheduled protected backups, retention, off-host
recovery, and environment-specific restore exercises. Unknown schema versions fail closed.

Failed operations roll back success audit rows. Dedicated security/operational failure logging and
monitoring are future work; the immutable financial audit is not a full access/security log.

## Before Internet or AI exposure

Define password reset and account recovery, session revocation administration, login throttling,
MFA requirements, credential provisioning for migrated CLI-only users, role-change/removal and
ownership-transfer workflows, dual approval and confirmation expiry if required, TLS/proxy trust,
secrets management, protected storage/backups, and operational security logging. Preserve the
accounting engine as the sole accounting write boundary and never expose its connection,
confirmation, or posting methods to a model. A production database must recreate and retest the
current atomicity, uniqueness, immutability, idempotency, and concurrency guarantees.

Before personal or multi-space exposure, add explicit isolation tests for every new domain,
including ID substitution, cache confusion, conversation retrieval, exports, reminders, budgets,
documents, and future tool calls. Before AI exposure, ensure the model cannot select or change space
without a separately authorized application action.

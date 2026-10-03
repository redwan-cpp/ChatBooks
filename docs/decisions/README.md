# Architecture decision records

| ADR                                                  | Decision                                                              | Status                                                                                             |
| ---------------------------------------------------- | --------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| [0001](0001-local-python-sqlite.md)                  | Typed Python, local CLI, SQLite, transactional writes                 | Accepted for foundation                                                                            |
| [0002](0002-exact-money-and-ledger.md)               | Exact minor units and posted journal source of truth                  | Accepted for foundation                                                                            |
| [0003](0003-proposals-confirmation-audit.md)         | Immutable proposals, explicit confirmation, automatic immutable audit | Accepted for foundation                                                                            |
| [0004](0004-periods-reversals-dimensions.md)         | Period locks, full reversals, optional line dimensions                | Foundation constraints; workflow policies need review                                              |
| [0005](0005-fastapi-application-boundary.md)         | Thin FastAPI boundary over the accounting engine                      | Accepted for M3                                                                                    |
| [0006](0006-authentication-authorization.md)         | Scrypt credentials, opaque sessions, organization roles               | Accepted for M3                                                                                    |
| [0007](0007-confirmation-provenance.md)              | Version-bound authenticated confirmation provenance                   | Accepted for M3                                                                                    |
| [0008](0008-command-idempotency.md)                  | Caller keys and atomic command-result receipts                        | Accepted for M3                                                                                    |
| [0009](0009-financial-space-context.md)              | Typed Financial Space context without premature ledger migration      | Accepted for M3.5 architecture                                                                     |
| [0010](0010-plans-schedules-ledger-separation.md)    | Budgets and financial schedules remain separate from posted actuals   | Accepted for M3.5 architecture                                                                     |
| [0011](0011-chat-first-progressive-disclosure.md)    | Chat-first experience with progressive financial disclosure           | Accepted for M3.5 product/UX architecture                                                          |
| [0012](0012-nextjs-browser-session-boundary.md)      | Next.js frontend with an HTTP-only same-origin session proxy          | Accepted for M4                                                                                    |
| [0013](0013-personal-ownership-isolation.md)         | Separate private-by-default personal ownership                        | Accepted for M5.0 architecture; implementation deferred                                            |
| [0014](0014-personal-financial-space-resolution.md)  | PERSONAL Financial Space resolves to PersonalSpace                    | Accepted for M5.0 architecture; implementation deferred                                            |
| [0015](0015-personal-ledger-adapter.md)              | Typed personal adapter over an ownership-neutral deterministic ledger | Accepted for M5.0 architecture; implementation deferred                                            |
| [0016](0016-cross-space-transfer-coordination.md)    | Separate ledger effects coordinated across spaces                     | Accepted for M5.0 architecture; accounting mappings deferred                                       |
| [0017](0017-personal-category-mapping.md)            | Personal categories use versioned ledger mappings                     | Accepted for M5.0 architecture; taxonomy deferred                                                  |
| [0018](0018-persistent-ledger-book-seam.md)          | Persistent LedgerBook as the universal ownership seam                 | BUSINESS mapping, service seam, canonical and operational rehearsals implemented; cutover deferred |
| [0019](0019-authorized-context-and-adapters.md)      | Authorized Financial Space context with business/personal adapters    | BUSINESS context/service and v3/v4 adapters implemented; PERSONAL adapter deferred                 |
| [0020](0020-jurisdiction-compliance-outside-core.md) | Jurisdiction and compliance rules remain outside the universal core   | Accepted for M5.1-A architecture; implementation deferred                                          |

Decisions document implementation constraints. They do not silently establish jurisdictional
accounting policy. Open questions are tracked in accounting-model.md. **Chatbooks** is the single
canonical written name for the project, repository, codebase, and product. Lowercase `chatbook`
remains a stable technical identifier for the package, CLI, modules, environment variables, and
internal compatibility surfaces.

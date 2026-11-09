# F1 AI Analyst

## Architecture

`apps.ai` is isolated from the existing racing, standings, content, and user APIs.
No model training or fine-tuning is involved. The synchronous request path is:

```text
JWT + DRF validation + per-user throttle
  -> owner-scoped bounded conversation context
  -> Responses API model selects a registered tool
     -> strict Pydantic arguments -> bounded read-only ORM queries
     -> or query embedding -> semantic search -> published article evidence
  -> bounded tool/response loop -> answer and source validation
  -> atomic user/assistant message pair -> existing success envelope
```

The model chooses tools; there is no keyword router. `search_articles` is a tool,
so hybrid requests can interleave article retrieval and structured data. The first
generation requires a tool, later steps allow a follow-up query or final answer,
and the last generation disables tools. Parallel tool execution is disabled.
There are at most `AI_MAX_TOOL_CALLS + 1` generation requests and no SDK retries.
Usage counts in metadata sum provider tokens over all requests, including repeated
context. Indexing is a separate management operation, never a side effect of chat.

Key modules:

| Module | Responsibility |
| --- | --- |
| `models.py` | UUID conversations/messages and article document/chunk persistence |
| `providers.py` | Generation/embedding protocols and official OpenAI adapter |
| `tools.py` | Closed registry, JSON schemas, strict validation, entity resolution, ORM tools |
| `documents.py` | Published eligibility, normalization, chunking, fingerprint/profile |
| `indexing.py`, `retrieval.py`, `citations.py` | Atomic replacement, native vector search, SQLite cosine search, final source rechecks |
| `orchestration.py` | Context, budgets, multi-step tools, grounded output/citations |
| `views.py`, `serializers.py` | JWT API, ownership, throttling, OpenAPI contracts |
| `evaluation/` | Labeled cases and measured evaluation runner |

The only new runtime dependencies are the official OpenAI SDK, Pydantic for strict
schemas, pgvector (which uses NumPy), and psycopg for Django's PostgreSQL backend.
No agent framework, task broker, external vector service, or tokenizer is required.
Dependencies use the repository's existing compatible-version range convention;
pin a fully resolved deployment environment for release reproducibility.

## Local setup

```bash
pip install -r requirements/development.txt
export DJANGO_SETTINGS_MODULE=config.settings.development
export DEBUG=True
python manage.py migrate
python manage.py check
```

The existing `.env.example` targets production. For local use, explicitly set
`DJANGO_SETTINGS_MODULE=config.settings.development` in the shell. The project's
`manage.py` chooses its settings module from the process environment. Store keys
in the backend `.env` or deployment secret manager; never in React/Vite variables.
With no key, existing APIs still work and AI calls return a sanitized 503.

SQLite stores pgvector field values as serialized vector text and computes actual
cosine similarity in Python. This uses the same provider embeddings and relevance
thresholds as PostgreSQL; it is a functional semantic search fallback. It scans
eligible chunks with bounded heap storage for top-k. It suits small local datasets,
not large production corpora. Automated tests use tiny mocked vectors, not paid API
calls. Production embedding quality is not measured by those synthetic tests.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | empty | Server credential; required for indexing and real chat |
| `AI_MODEL` | `gpt-5-mini` | Economical configurable tool-capable generation model |
| `AI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model supporting requested dimensions |
| `AI_EMBEDDING_DIMENSIONS` | `1536` | Vector dimensions, checked on every embedding response |
| `AI_MAX_OUTPUT_TOKENS` | `2000` | Output cap per generation (includes reasoning tokens) |
| `AI_MAX_TOOL_CALLS` | `6` | Total tool invocation cap per request |
| `AI_PROVIDER_TIMEOUT` | `20` | Maximum seconds per SDK call; no retries |
| `AI_REQUEST_TIMEOUT` | `90` | Monotonic orchestration deadline; each call uses remaining budget |
| `AI_THROTTLE_RATE` | `10/hour` | Per-user chat rate |
| `RAG_TOP_K` | `5` | Maximum retrieved chunks per search |
| `RAG_MIN_SIMILARITY` | `0.3` | Minimum cosine similarity; calibrate with labeled data |
| `RAG_CHUNK_SIZE` | `1200` | Deterministic character window size |
| `RAG_CHUNK_OVERLAP` | `200` | Exact character overlap |
| `AI_CACHE_BACKEND` | Django locmem | Use DatabaseCache for shared production throttling |
| `AI_CACHE_LOCATION` | `f1-ai-throttle` | Cache location or database table |

Model availability depends on the account and deployment date. Set `AI_MODEL` to a
currently supported Responses model with function calling and structured outputs.
Low output caps may cause reasoning models to return incomplete responses; these
are treated as failures, never presented as complete answers. To use a different
provider, supply classes implementing the two protocols and set
`AI_GENERATION_PROVIDER`/`AI_EMBEDDING_PROVIDER` in Django settings. These are trusted
deployment settings, never user-selectable imports.

System checks reject invalid chunk overlap and unbounded configuration. Other
limits are maintained in settings: 4,000-character user messages, 12 history
messages within 24,000 characters, 100 stored messages per conversation, bounded
tool rows (100 standings/results, 10 recent races), 24,000 characters of tool output
per invocation, and 200,000 characters per
indexed article. Tool evidence and model turns are bounded separately.

## PostgreSQL and pgvector

Production already reads `DATABASE_URL` with SSL in
`config.settings.production`. Install `requirements/production.txt` and use a
PostgreSQL server with the pgvector extension installed, such as
`pgvector/pgvector:pg16`. The AI migration enables `vector` on PostgreSQL only;
SQLite migrations skip extension creation. If the application role cannot create
extensions, an administrator must run this first in the target database:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Then run normal migrations. Do not silently fall back from failed PostgreSQL
extension setup: a misconfigured deployment should fail visibly.

Native PostgreSQL retrieval uses the pgvector cosine-distance operator through the
Django ORM. It deliberately starts with exact search, which is appropriate for
small corpora. Document profiles isolate embedding provider/model/dimension and
chunking versions. The vector column allows changing dimensions without schema
changes; changing a profile requires reindexing and old-profile rows are excluded.
For larger corpora, benchmark exact search, fix a production dimension/profile,
and add an HNSW index with a matching dimension cast/partial profile predicate and
matching query expression in a reviewed migration. An index alone on the current
unconstrained-dimension field is insufficient. Approximate search must be evaluated
for recall and publication filters before enabling it.

Set a shared throttle cache before running multiple workers:

```bash
export AI_CACHE_BACKEND=django.core.cache.backends.db.DatabaseCache
export AI_CACHE_LOCATION=f1_ai_cache
python manage.py createcachetable f1_ai_cache
```

DRF throttling is best effort under concurrency, not a billing or denial-of-service
boundary. Configure gateway limits and provider project spend limits too. Set the
application-server/reverse-proxy timeout above the request deadline (for example,
Gunicorn `--timeout 120` with the default 90-second orchestration deadline). This
initial synchronous implementation occupies a worker during generation.

## Indexing

Publish articles through the existing content workflow, then run:

```bash
python manage.py index_articles
python manage.py index_articles --force  # explicitly re-embed all; incurs costs
```

Only status `published` with `published_at <= now` is eligible, even for staff.
Normalization strips HTML/scripts/styles, decodes entities, applies Unicode NFKC,
and collapses whitespace. Extraction includes title, subtitle, summary, content,
related driver/team/race, tags, and publication metadata, excluding author identity.
Chunking uses deterministic character windows and overlap. A SHA-256 fingerprint
of text/metadata plus an embedding/chunking profile makes unchanged runs no-ops.
Views count and unrelated row saves do not cause embedding costs.

Updated articles replace all chunks inside a short transaction, with a unique
document/ordinal constraint. Embeddings are batched before the transaction; the
article is locked and rechecked before commit. Failures preserve the previous
index and produce a nonzero exit code, with article IDs and safe error logs.
Publication pruning happens every run; article deletion cascades immediately.
Retrieval rechecks current publication status and fingerprints, excluding stale
content and changed tags even before the next run. Failed reindexing therefore
reduces coverage rather than serving old text. Run indexing after editorial changes
or schedule the idempotent command through existing hosting job facilities.

Retrieval applies relevance thresholds and optional exact relationship filters;
`latest` orders relevant chunks by article publication time. Filters reflect
explicit article relationships, so a loosely tagged article may need an unfiltered
semantic query. Chunk top-k can contain several chunks of one article. Newly
published articles are unavailable until indexed. No document is embedded on chat;
each search embeds only its query. There is no live web search.

## API contracts

All endpoints require the existing JWT bearer token. The Axios client can call
`/ai/...` with its current `/api` base and token refresh behavior; no frontend
modifications were made.

```bash
curl http://localhost:8000/api/ai/chat/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"message":"Compare McLaren results with published commentary for 2026"}'
```

`POST /api/ai/chat/` accepts `{ "message": "...", "conversation_id": "optional UUID" }`.
Success follows the existing helper envelope:

```json
{
  "success": true,
  "message": "Success.",
  "data": {
    "conversation_id": "UUID",
    "answer": "Grounded answer with inline [source_id] references.",
    "sources": [],
    "metadata": {
      "insufficient_evidence": true,
      "tool_calls": ["get_constructor_standings"],
      "model": "configured model",
      "input_tokens": 0,
      "output_tokens": 0
    }
  }
}
```

The JSON above illustrates the shape, not a measured response. Sources are only
returned when actually cited and validated. Article sources have `id`
(`article_chunk:<chunk UUID>`), `type=article`, `entity_id` (Article UUID),
`chunk_id`, `title`, `slug`, `url=/articles/<slug>`, `api_url`, and `published_at`.
Structured sources have `id` (`race_result:...`, `driver_standing:...`, or
`constructor_standing:...`), `type`, record `entity_id`, `title`, and `api_url`.
Links are constructed from existing routes, never supplied by the model. The
frontend should render source links from this verified array and treat answer text
as untrusted output, avoiding raw HTML rendering.

`GET /api/ai/conversations/` returns the existing list convention:
`{count,next,previous,results:[{id,title,created_at,updated_at}]}`. `page` and
`page_size` use the existing paginator (maximum 100).

`GET /api/ai/conversations/<uuid>/` returns the success envelope containing
conversation fields and ordered `messages` with `role`, `content`, `sources`,
`metadata`, `sequence`, and timestamps. Conversations hold at most 100 messages.
Another user's UUID returns 404 for reading or continuing, including for staff.
Provider errors append no messages. Concurrent updates use optimistic revision
checks and return 409 rather than committing out-of-order answers.

Errors follow `{success:false,message,errors}`: 400 validation, 401 authentication,
404 ownership/not found, 409 full/concurrent conversation, 429 rate limit,
503 missing credentials/provider/protocol failures, and 504 timeout. The endpoints
are included in `/api/schema/`, Swagger UI, and ReDoc using drf-spectacular.

## Grounding and security boundaries

The server only exposes seven registered tools: recent driver results, driver
comparison, race results, driver standings, constructor standings, recent team
results, and article search. Strict schemas reject unknown fields, coercion,
arbitrary ordering, invalid years, and excessive limits. Entity resolution uses
UUIDs or case-insensitive exact names/abbreviations; ambiguous matches fail with a
clarification signal. A null standings year requires exactly one current season.
No SQL, Python, filesystem, web, user-profile, or write tools are available.

The system prompt distinguishes application instructions from untrusted user,
history, and article content. Tool results remain function output data and never
become system messages. Model citations must match observed server-produced
sources and inline IDs; fabricated citations/links fail closed. If no valid cited
evidence exists, a deterministic insufficient-evidence response replaces the
model's unsupported answer. Cited records are rechecked after generation, including
article unpublication/deletion/content changes during the turn. These controls reduce prompt-injection exposure but
do not prove a model will obey all instructions or that every cited statement is
entailed by a source. Manual evaluation of claim accuracy remains necessary.

Structured results identify their stored records and update times; coverage text
explicitly distinguishes partial records, season snapshots, and race points
excluding sprints. The existing database does not track full ingestion provenance
or completeness, so the assistant cannot guarantee complete season/career rankings,
up-to-date news, or causes behind a result. Snapshot statistics inherit upstream
data quality. Conversation content is user data stored until account/conversation
deletion; this release has no retention scheduler or conversation delete endpoint.
Set an operational retention policy before public deployment. OpenAI requests use
`store=False`; this does not override the provider's account-level data policies.

## Tests

```bash
export DEBUG=False
python manage.py test --settings=config.settings.test
python manage.py test apps.ai --settings=config.settings.test
python manage.py makemigrations --check --dry-run --settings=config.settings.test
python manage.py spectacular --file /tmp/f1-schema.yml --validate --settings=config.settings.test
```

All provider calls are mocked, including genuine embedding/ranking behavior tested
with curated vectors. Tests cover normalization/overlap, update/no-op indexing,
deletion/unpublication/scheduling, stale evidence, thresholds/profile isolation,
tool validation and queries, hybrid execution, injection data boundaries, citations,
history limits, deadlines, sanitized SDK errors, JWT, ownership, rate limiting,
concurrent revision handling, and API envelopes.

The same suite supports PostgreSQL without changing application code:

```bash
docker run --rm --name f1-ai-test-db -p 5432:5432 \
  -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=f1_test pgvector/pgvector:pg16
PGDATABASE=f1_test PGUSER=postgres PGPASSWORD=postgres PGHOST=localhost \
  python manage.py test apps.ai --settings=config.settings.test_postgres
```

The CI workflow includes a pgvector service job. CI configuration alone is not a
claim that PostgreSQL or live provider calls passed in a developer's environment.

## Reproducible evaluation

Use an isolated database, never your real editorial database: the fixture inserts
synthetic race results and known identities. Its statements are evaluation data,
not historical claims. The evaluation settings use a separate ignored
`ai-evaluation.sqlite3` file (override with `AI_EVALUATION_DB`):

```bash
export DJANGO_SETTINGS_MODULE=config.settings.evaluation
export DEBUG=False
python manage.py migrate
python manage.py loaddata ai_evaluation
python manage.py index_articles
python manage.py evaluate_ai --output /tmp/ai-retrieval-evaluation.json
python manage.py evaluate_ai --answers --output /tmp/ai-answer-evaluation.json
```

Supply real credentials for embedding/indexing and live answers. Six cases cover
structured correctness, RAG relevance, hybrid tool use, missing data, and citation
validity. `--cases <path>` accepts additional labeled JSON cases for your real
corpus. Reports include configuration, per-case values, and aggregate measurements:

- Structured assertion accuracy checks exact tool output paths against fixture gold.
- Retrieval Recall@K checks unique expected article slugs found in top-k chunks.
- Optional answer-pattern accuracy checks minimal regex assertions; it is not a
  semantic correctness score and must be accompanied by human answer review.
- Citation validity checks that cited entities exist and articles are published;
  empty-source answers are reported as null, not perfect validity.
- Required-tool coverage and missing-evidence correctness check orchestration.

Offline `test_evaluation.py` tests the measurement machinery with mocked query
embeddings. Its perfect synthetic-vector recall is not real-world retrieval quality.
No live evaluation scores are provided or invented. Review answer entailment,
coverage, ambiguity, and injection resistance manually; retain actual measured
reports with model/index configuration when presenting portfolio results.

## Costs and deployment limits

Costs comprise one embedding per changed article chunk (plus overlap), query
embeddings for article searches, and generation input/output across every tool
iteration. Repeated history/tool evidence is billed again. Idempotent indexing,
tool limits, output limits, throttles, and SDK retry disabling bound normal usage;
set provider project spend limits for an external cost ceiling. No fixed currency
cost is claimed; consult current provider pricing for your configured models.
There is no training cost, live web integration, background queue, streaming,
semantic answer verifier, automatic index scheduler, or approximate vector index.

SDK implementation was checked against the installed official SDK and the
[Responses function calling guide](https://developers.openai.com/api/docs/guides/function-calling).
The provider preserves response output/reasoning items for stateless continuation
and returns `function_call_output` items with matching `call_id` values. See also
the [GPT-5 mini model page](https://developers.openai.com/api/docs/models/gpt-5-mini)
and [pgvector Django integration](https://github.com/pgvector/pgvector-python#django).

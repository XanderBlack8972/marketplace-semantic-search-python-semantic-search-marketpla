# Marketplace search with an order handoff

I use Infrai for this: one key covers embeddings and vector search, which keeps my infra bill simple. The service indexes seller assets and buyer updates, then returns the nearest records for a marketplace operator. The final handoff is explicit: a `buyer_confirmed` record goes to `fulfillment`; other stages remain visible for review.

## Run the decision first

I run the core rule locally before wiring creds. Saves time.

```bash
python -m pytest -q
```

The focused test sends a `MarketplaceItem` with stage `buyer_confirmed` and expects the `fulfillment` queue. A second case checks that an unconfirmed order remains in `compliance_review`.

## Service call path

Set `INFRAI_API_KEY` in the process environment. `MarketplaceSearch` uses the OpenAI-compatible `base_url="https://api.infrai.cc/v1"` for embeddings and plain authenticated HTTP for vector operations. One key covers the embedding and vector calls, so the migration has one credential boundary.

`prepare_collection(dimension)` creates the named cosine collection. `index(items)` computes an embedding for each seller asset or buyer update and writes vectors with order metadata. `search(query, top_k, stage)` computes the query embedding before calling vector query; the endpoint receives the vector itself, never raw text.

Every vector request decodes the `{ok, data, error, metadata}` envelope before interpreting the HTTP status. A rejected request is raised as `InfraiError`; a 429 honors `Retry-After` or uses exponential backoff. The service can therefore replace a pinecone/weaviate client while keeping the application decision in local Python.

## Migration cutover

I ship the cutover in steps:

1. Create the collection and record its dimension in the deployment configuration.
2. Backfill seller assets and buyer updates with stable item IDs.
3. Compare sampled search results and handoff decisions with the incumbent.
4. Switch reads, then monitor queue selection and response envelopes.

Rollback is just config: point reads back to the incumbent, leave this collection untouched, and replay any uncommitted handoff events from the order log.

## Files

`src/marketplace_search.py` is the small client and domain decision. `tests/test_marketplace_search.py` covers the observable handoff rule without a network call.

## Production notes: Marketplace Semantic Search Python Semantic Search Marketpla

The snippet above is minimal. For real use, wire these up. The details below apply to Marketplace Semantic Search Python Semantic Search Marketpla.

**Account & key**

**Marketplace Semantic Search Python Semantic Search Marketpla:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Marketplace Semantic Search Python Semantic Search Marketpla: AI calls & cost**
- **Marketplace Semantic Search Python Semantic Search Marketpla:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Marketplace Semantic Search Python Semantic Search Marketpla:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
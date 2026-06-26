# USPTO Open Data Portal (ODP) API key — Module 5 (Patent & IP)

Structured in-app patent rows require `USPTO_ODP_API_KEY` on the write VPS. Without it, Module 5 still works via portal link fallback (Google Patents, Lens, Espacenet).

## Obtain a key

1. Register at [https://data.uspto.gov](https://data.uspto.gov) (USPTO.gov account).
2. Follow **Getting started** → create an **API key** (free).
3. Patent search endpoint (ODP): see [ODP support / FAQs](https://data.uspto.gov/support) and the PatentsView [transition guide](https://data.uspto.gov/support/transition-guide/patentsview).

Legacy `api.patentsview.org` no longer returns JSON (migrated March 2026).

## Configure on VPS

```bash
# /srv/services/writing_memory/.env
USPTO_ODP_API_KEY=your_key_here
```

```bash
systemctl restart writing-memory
```

Verify:

```bash
curl -s https://write.insynbio.com/ip/config | jq .
# odp_configured should be true
```

## Test search (on VPS)

```bash
curl -s -X POST https://write.insynbio.com/ip/patent/search \
  -H 'Content-Type: application/json' \
  -d '{"username":"ops","query":"antibody","limit":3}'
```

`source` should be `uspto_odp` and rows should have real `applicationNumberText` / titles (not only Google Patents links).

Direct ODP smoke test (replace `YOUR_KEY`):

```bash
curl -s -X POST 'https://api.uspto.gov/api/v1/patent/applications/search' \
  -H 'x-api-key: YOUR_KEY' -H 'Content-Type: application/json' \
  -d '{"q":"applicationMetaData.inventionTitle:antibody","pagination":{"offset":0,"limit":2}}'
```

Expect JSON with `patentFileWrapperDataBag`. See [ODP API syntax](https://data.uspto.gov/apis/api-syntax-examples).

After updating `patent_client.py` on the server, run `systemctl restart writing-memory`.

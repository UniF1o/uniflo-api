## OpenAPI Spec

The OpenAPI spec is published to `openapi.json` in the repo root on
every merge to `main`. Partner A uses this to generate TypeScript types.

### For Partner A — generating types

Point `openapi-typescript` at the live Render URL:
```bash
npx openapi-typescript https://uniflo-api.onrender.com/openapi.json -o lib/api/schema.d.ts
```

Or against the committed spec file:
```bash
npx openapi-typescript ./openapi.json -o lib/api/schema.d.ts
```

### What triggers regeneration
Any PR that changes a route, schema, or response model will update
the spec on merge to `main`. The CI job commits the updated
`openapi.json` automatically with `[skip ci]` to prevent a loop.

### Error codes
All error responses follow `{"detail": "<snake_case_code>"}`:

| Code | Status | Endpoint |
| --- | --- | --- |
| `university_not_found` | 400 | POST /applications |
| `university_inactive` | 400 | POST /applications |
| `applications_closed` | 400 | POST /applications |
| `profile_not_found` | 403 | POST /applications |
| `application_not_found` | 404 | GET /applications/{id} |
| `university_not_found` | 404 | GET /universities/{id} |
| `retry_not_yet_implemented` | 501 | POST /applications/{id}/retry |
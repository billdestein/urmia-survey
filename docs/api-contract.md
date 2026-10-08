# API contract

## POST /responses

Public JSON endpoint using the existing flat prototype payload. Required fields are `q1` through `q7` (exact values in `backend/schema.json`) and boolean `interview_optin`. `q8` is optional free text. Optional fields are `src`, `q7a`, `role`, `vendor_count`, `institution_type`, `name`, `email`, and `institution`.

A name and valid email are required when interview opt-in is true. Contact fields are cleared when false; `q7a` is cleared unless a dedicated system is selected. Unknown fields are rejected. Client `submitted_at` and `hot_count` are accepted for prototype compatibility but replaced with server-generated values. Maximum body size is 24 KB; free text is limited to 2,000 characters; other limits are in `backend/app.py`.

Send a UUID `Idempotency-Key` header. Repeating the same normalized answers under that key returns the original ID; changing answers under it returns 409. Omitting the key generates a new ID for every request.

Responses:

- 201 saved, or 200 for a previously saved identical retry: `{ "responseId": "..." }`.
- 400 invalid answers; 409 conflicting retry; 413 oversized body; 415 wrong media type.
- 410 survey closed; 429 API throttled; 503 storage unavailable.

## GET /responses.csv

Requires an AWS Signature Version 4 request by an IAM principal with `execute-api:Invoke` permission on the route. There is no public export token or frontend secret.

Returns `text/csv; charset=utf-8`, a download filename, and `Cache-Control: no-store`. Columns are `response_id`, server `submitted_at`, prototype answer/contact fields, and server-calculated `hot_count`. Missing optional values are empty. Text that could become a spreadsheet formula is prefixed with an apostrophe. The complete download is limited to 4 MB; oversized or interrupted scans return a JSON error without partial CSV.

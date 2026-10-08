# Proposed API contract

This contract is a starting point to confirm before implementation.

## POST /responses

Public endpoint accepting `Content-Type: application/json`:

```json
{
  "surveyVersion": "TBD",
  "answers": {}
}
```

`answers` keys and validation rules remain unspecified until the survey questions are provided. The server should generate `responseId` and `submittedAt` and validate the survey version. Do not accept arbitrary answer keys once the schema is approved.

Proposed success: `201` with `{ "responseId": "server-generated-id" }`. Invalid input returns `400`; throttling returns `429`. The frontend must preserve answers on failure and display accessible status messages. Decide retry/idempotency behavior before implementation.

## GET /responses.csv

Requires configured authentication. Return `text/csv; charset=utf-8` with a download filename. Include one row per stored response. Final columns depend on the approved question schema; response ID and server submission timestamp are proposed metadata columns.

No admin token or credentials may be included in the public HTML. Confirm the authentication method, export size limits, retention, and privacy requirements before deployment.

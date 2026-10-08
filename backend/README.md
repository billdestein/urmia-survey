# AWS backend

The deployment creates a pay-per-request DynamoDB table, two Python Lambda functions, and an API Gateway HTTP API:

- Public `POST /responses`: validates the prototype's exact choices and field lengths, generates a server timestamp and response ID, and writes to DynamoDB.
- IAM-authenticated `GET /responses.csv`: scans all pages and returns one CSV row per response. Each Lambda role has only its required table operations.

Deployed in AWS account `993351246435`, region `us-west-2`, stack `urmia-survey`, using the local `default` profile. The connected frontend is prepared locally and awaits launch approval.

Submission URL: https://me8spxlst4.execute-api.us-west-2.amazonaws.com/responses

Authenticated export URL: https://me8spxlst4.execute-api.us-west-2.amazonaws.com/responses.csv

## Deploy

Confirm the AWS account/profile and region first. The AWS CLI is sufficient; SAM is not required.

```sh
python3 backend/generate_template.py
aws sts get-caller-identity --profile YOUR_PROFILE
aws cloudformation validate-template --template-body file://backend/template.json --profile YOUR_PROFILE --region YOUR_REGION
aws cloudformation deploy --template-file backend/template.json --stack-name urmia-survey --capabilities CAPABILITY_IAM --profile YOUR_PROFILE --region YOUR_REGION
aws cloudformation describe-stacks --stack-name urmia-survey --query 'Stacks[0].Outputs' --profile YOUR_PROFILE --region YOUR_REGION
```

The generated template embeds the handler code. Regenerate it after editing `app.py` or the survey answer choices. Lambda uses the runtime-provided Boto3 SDK. Local tests use a mock database; they do not require Boto3.

Use `SubmitUrl` in the frontend. Send JSON with `Content-Type: application/json` and a UUID `Idempotency-Key`; reuse that key for a retry of the same answers. A changed submission needs a new key. Only show the thank-you screen after HTTP 200 or 201. Preserve answers on errors. No administrator credentials belong in the HTML.

## Export

Grant the exporting IAM user/role `execute-api:Invoke` on the exact `ExportInvokeArn` stack output. The Lambda execution role is separate from this administrator permission.

Install Boto3 in a local virtual environment to use the signed download helper:

```sh
python3 -m venv /tmp/urmia-export-env
/tmp/urmia-export-env/bin/pip install boto3
mkdir -p exports
/tmp/urmia-export-env/bin/python backend/export_csv.py --profile YOUR_PROFILE --region YOUR_REGION --url EXPORT_URL --output exports/urmia.csv
```

CSV exports neutralize spreadsheet formulas and quote commas, quotes, and newlines. Downloads are capped at 4 MB; larger exports return an error without partial data. A scan is not a point-in-time snapshot while submissions continue; close the survey before the final export if needed.

## Operations

- Set the stack parameter `SurveyOpen=false` to stop accepting responses, preserving exports.
- DynamoDB encryption and point-in-time recovery are enabled. The table is retained if the stack is deleted. Responses have no automatic expiration; decide a retention period before collecting real data.
- Logs expire after 14 days. Handlers do not log answers or contact information.
- CORS allows the public GitHub Pages origin. CORS does not prevent direct API calls. API throttling and Lambda concurrency limits bound traffic but do not provide bot protection or a spending cap.
- This first version has no CAPTCHA or administrator browser UI. IAM exports use local AWS credentials, including SSO sessions.
- Deployment requires enough regional Lambda concurrency quota for the two reserved allocations (five each).

## Verify

```sh
python3 -m unittest discover -s backend/tests -v
```

After deployment, verify a valid POST, invalid POST, same-key retry, unsigned export rejection, signed CSV download, and mobile frontend submission. Keep test records out of the final analysis.

AWS references: [Python Lambda runtime](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html) and [HTTP API IAM authorization](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-access-control-iam.html).

# URMIA conference survey

Brokermatic.ai postcard QR codes will link to a mobile-friendly, single-file survey hosted on GitHub Pages. A public API Gateway POST endpoint will invoke Lambda to store responses in DynamoDB. An authenticated GET endpoint will export responses as CSV.

## Status

Initial scaffold only. Survey questions, privacy/consent copy, GitHub destination, API URL, authentication configuration, and deployment details are pending. No AWS resources are deployed. The placeholder page does not collect or submit responses.

## Structure

- `index.html`: mobile-friendly placeholder for the single-file survey.
- `backend/README.md`: backend implementation requirements.
- `docs/api-contract.md`: proposed request and export contract.
- `docs/pages-workflow.yml`: template for a manually triggered GitHub Pages deployment.

## Next steps

1. Confirm repository owner, name, and visibility.
2. Supply survey questions, response types, required fields, and approved privacy/consent copy.
3. Implement and deploy the backend and authenticated export.
4. Configure the API URL and implement the survey in `index.html`.
5. With a GitHub credential that has workflow permission, move `docs/pages-workflow.yml` to `.github/workflows/pages.yml`. Enable GitHub Pages with GitHub Actions as the source, then run the workflow. Confirm that the published site is publicly accessible for postcard recipients.
6. Verify mobile submission and export before printing the final QR-code URL.

Keep credentials, response data, and exports out of this repository.

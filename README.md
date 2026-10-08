# URMIA conference survey

Brokermatic.ai postcard QR codes will link to a mobile-friendly, single-file survey hosted on GitHub Pages. A public API Gateway POST endpoint will invoke Lambda to store responses in DynamoDB. An authenticated GET endpoint will export responses as CSV.

## Status

The supplied TriCheck URMIA survey prototype is now in `index.html`, with its questions and design preserved. It validates answers and displays a sample JSON payload locally; it does not send or store responses. The AWS backend is implemented with public POST collection and IAM-authenticated CSV export. AWS deployment, frontend connection, and final privacy/consent review are pending. No AWS resources are deployed.

Repository: https://github.com/billdestein/urmia-survey (public).

## Structure

- `index.html`: supplied single-file TriCheck survey prototype, with mobile viewport metadata.
- `backend/`: Lambda handlers, deployable CloudFormation template, signed CSV export helper, and automated tests.
- `docs/api-contract.md`: proposed request and export contract.
- `docs/pages-workflow.yml`: template for a manually triggered GitHub Pages deployment.

## Next steps

1. Repository hosted under `billdestein/urmia-survey` on GitHub.com.
2. Review the supplied survey questions and approve privacy/consent copy.
3. Choose an AWS profile and region, then deploy the backend using `backend/README.md`.
4. Connect `index.html` to the POST API; show success only after storage is confirmed. Align the API contract with the prototype payload.
5. GitHub Pages publishes directly from the root of `main` at https://billdestein.github.io/urmia-survey/. The workflow template is optional and inactive; branch-based publishing does not require it.
6. Verify mobile submission and export before printing the final QR-code URL.

Keep credentials, response data, and exports out of this repository.

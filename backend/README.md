# Backend scaffold

Implementation is pending; this directory does not yet contain deployable infrastructure or Lambda code.

Required components:

- API Gateway: public POST `/responses` and authenticated GET `/responses.csv`.
- Lambda: validate the approved answer schema; generate a response ID and server timestamp; persist JSON in DynamoDB.
- DynamoDB: store each response by a unique ID.
- Export: paginate through all responses and return one CSV row per response, with columns derived from the approved questions. Escape CSV correctly and mitigate spreadsheet formula injection.
- Authentication: choose an API Gateway authorizer or AWS IAM for GET. Never embed admin credentials in the survey HTML. Reject unauthenticated export requests.
- Permissions: least-privilege DynamoDB access for each Lambda role.
- Browser access: configure CORS for the final GitHub Pages origin. CORS is not authentication or abuse protection.
- Operations: configure input size limits, throttling, retention, logging without raw answers, and a plan for closing the survey.

Do not commit AWS credentials, authentication secrets, survey responses, or CSV exports.

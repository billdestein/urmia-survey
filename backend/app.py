"""Survey handlers; API Gateway HTTP API v2 events."""
import base64
import csv
import hashlib
import io
import json
import os
import re
import uuid
from datetime import datetime, timezone

# Exact choices from the supplied survey, populated by generate_template.py.
CHOICES = {}
TABLE = None
MAX_BODY = 24000
MAX_CSV = 4000000
TEXT_LIMITS = {'src': 100, 'q7a': 200, 'q8': 2000, 'name': 200,
               'email': 254, 'institution': 300}
COLUMNS = ['response_id', 'submitted_at', 'src'] + [f'q{i}' for i in range(1, 9)] + [
    'q7a', 'hot_count', 'role', 'vendor_count', 'institution_type',
    'interview_optin', 'name', 'email', 'institution']


def table():
    global TABLE
    if TABLE is None:
        import boto3
        TABLE = boto3.resource('dynamodb').Table(os.environ['TABLE_NAME'])
    return TABLE


def response(status, body):
    return {'statusCode': status, 'headers': {'Content-Type': 'application/json',
            'Cache-Control': 'no-store'}, 'body': json.dumps(body)}


def validate(data):
    if not isinstance(data, dict):
        raise ValueError('Expected a JSON object.')
    allowed = set(COLUMNS) - {'response_id'}
    if set(data) - allowed:
        raise ValueError('Unexpected fields.')
    cleaned = {}
    for field, options in CHOICES.items():
        value = data.get(field, '')
        if not isinstance(value, str) or value not in options:
            raise ValueError(f'Invalid or missing {field}.')
        cleaned[field] = value
    for field, limit in TEXT_LIMITS.items():
        value = data.get(field, '')
        if not isinstance(value, str) or len(value) > limit or '\x00' in value:
            raise ValueError(f'Invalid {field} (maximum {limit} characters).')
        cleaned[field] = value.strip()
    if type(data.get('interview_optin')) is not bool:
        raise ValueError('interview_optin must be true or false.')
    cleaned['interview_optin'] = data['interview_optin']
    if cleaned['interview_optin']:
        if not cleaned['name'] or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', cleaned['email']):
            raise ValueError('Name and valid email are required for an interview.')
    else:
        for field in ('name', 'email', 'institution'):
            cleaned[field] = ''
    if cleaned['q7'] != 'A dedicated system':
        cleaned['q7a'] = ''
    cleaned['hot_count'] = sum(cleaned[f'q{i}'] == CHOICES[f'q{i}'][-1] for i in range(1, 8))
    return cleaned


def submit(event, context):
    if os.environ.get('SURVEY_OPEN', 'true') != 'true':
        return response(410, {'error': 'The survey is closed.'})
    headers = {k.lower(): v for k, v in (event.get('headers') or {}).items()}
    if headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json':
        return response(415, {'error': 'Use application/json.'})
    try:
        raw = event.get('body') or ''
        if len(raw) > MAX_BODY * 2:
            return response(413, {'error': 'Response is too large.'})
        raw = base64.b64decode(raw, validate=True) if event.get('isBase64Encoded') else raw.encode('utf-8')
        if len(raw) > MAX_BODY:
            return response(413, {'error': 'Response is too large.'})
        data = validate(json.loads(raw))
        key = headers.get('idempotency-key', '')
        if key and not re.fullmatch(r'[A-Za-z0-9-]{16,100}', key):
            raise ValueError('Invalid Idempotency-Key.')
    except (ValueError, TypeError, UnicodeError):
        return response(400, {'error': 'Invalid response. Check required answers and field lengths.'})
    fingerprint = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    response_id = key or str(uuid.uuid4())
    item = dict(data, response_id=response_id, submitted_at=datetime.now(timezone.utc).isoformat(),
                payload_hash=fingerprint)
    try:
        table().put_item(Item=item, ConditionExpression='attribute_not_exists(response_id)')
    except Exception as exc:
        if getattr(exc, 'response', {}).get('Error', {}).get('Code') == 'ConditionalCheckFailedException':
            try:
                existing = table().get_item(Key={'response_id': response_id}, ConsistentRead=True).get('Item', {})
                if existing.get('payload_hash') == fingerprint:
                    return response(200, {'responseId': response_id})
                return response(409, {'error': 'Retry key already used for different answers.'})
            except Exception:
                pass
        return response(503, {'error': 'Unable to save right now. Please retry.'})
    return response(201, {'responseId': response_id})


def csv_cell(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    text = str(value)
    if text.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')) or text.startswith(('\t', '\r', '\n')):
        text = "'" + text
    return text


def export(event, context):
    # Trust only identities verified by the API Gateway route authorizer.
    authorizer = event.get('requestContext', {}).get('authorizer', {})
    claims = authorizer.get('jwt', {}).get('claims', {})
    browser_admin = (claims.get('token_use') == 'access' and
                     'urmia-export/download' in claims.get('scope', '').split() and
                     claims.get('client_id') == os.environ.get('ADMIN_CLIENT_ID'))
    if not (authorizer.get('iam', {}).get('userArn') or browser_admin):
        return response(403, {'error': 'Authentication required.'})
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    writer.writerow(COLUMNS)
    options = {'ConsistentRead': True}
    size = len(output.getvalue().encode('utf-8'))
    try:
        while True:
            page = table().scan(**options)
            for item in page.get('Items', []):
                before = output.tell()
                writer.writerow([csv_cell(item.get(column, '')) for column in COLUMNS])
                size += len(output.getvalue()[before:].encode('utf-8'))
                if size > MAX_CSV:
                    return response(413, {'error': 'Export exceeds download limit; use an offline DynamoDB export.'})
            if not page.get('LastEvaluatedKey'):
                break
            options['ExclusiveStartKey'] = page['LastEvaluatedKey']
            if context and context.get_remaining_time_in_millis() < 5000:
                return response(503, {'error': 'Export timed out; retry or use an offline export.'})
    except Exception:
        return response(503, {'error': 'Unable to export right now.'})
    return {'statusCode': 200, 'headers': {'Content-Type': 'text/csv; charset=utf-8',
            'Content-Disposition': 'attachment; filename="urmia-responses.csv"',
            'Cache-Control': 'no-store'}, 'body': output.getvalue()}

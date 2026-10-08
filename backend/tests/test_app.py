import csv
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app
app.CHOICES = json.loads((Path(__file__).resolve().parents[1]/'schema.json').read_text())

class BackendTests(unittest.TestCase):
    def setUp(self):
        app.TABLE=Mock()
        self.data={field: values[0] for field, values in app.CHOICES.items()}
        self.data['interview_optin']=False
        self.event={'headers':{'Content-Type':'application/json'},'body':json.dumps(self.data)}
    def test_valid_submission_server_metadata(self):
        self.assertEqual(app.submit(self.event,None)['statusCode'],201)
        item=app.TABLE.put_item.call_args.kwargs['Item']
        self.assertIn('response_id',item)
        self.assertIn('submitted_at',item)
        self.assertEqual(item['hot_count'],0)
    def test_invalid_choice_and_unknown_field(self):
        for data in [dict(self.data,q1='invented'),dict(self.data,secret='value'),dict(self.data,interview_optin='true')]:
            self.event['body']=json.dumps(data)
            self.assertEqual(app.submit(self.event,None)['statusCode'],400)
        app.TABLE.put_item.assert_not_called()
    def test_contact_validation_and_scrubbing(self):
        with self.assertRaises(ValueError): app.validate(dict(self.data,interview_optin=True))
        cleaned=app.validate(dict(self.data,name='Hidden',email='hidden@example.com',q7=app.CHOICES['q7'][1],q7a='stale'))
        self.assertEqual(cleaned['name'],'')
        self.assertEqual(cleaned['email'],'')
        self.assertEqual(cleaned['q7a'],'')
    def test_storage_error_is_not_success(self):
        app.TABLE.put_item.side_effect=RuntimeError('private internal details')
        result=app.submit(self.event,None)
        self.assertEqual(result['statusCode'],503)
        self.assertNotIn('private internal',result['body'])
    def test_idempotent_retry_and_conflict(self):
        class Conflict(Exception): response={'Error':{'Code':'ConditionalCheckFailedException'}}
        app.TABLE.put_item.side_effect=Conflict()
        self.event['headers']['Idempotency-Key']='12345678-1234-1234-1234-123456789abc'
        normalized=app.validate(self.data)
        import hashlib
        fingerprint=hashlib.sha256(json.dumps(normalized,sort_keys=True).encode()).hexdigest()
        app.TABLE.get_item.return_value={'Item':{'payload_hash':fingerprint}}
        self.assertEqual(app.submit(self.event,None)['statusCode'],200)
        app.TABLE.get_item.return_value={'Item':{'payload_hash':'other'}}
        self.assertEqual(app.submit(self.event,None)['statusCode'],409)
    def test_unsigned_export_rejected(self):
        self.assertEqual(app.export({},None)['statusCode'],403)
        app.TABLE.scan.assert_not_called()
    def test_export_paginates_and_escapes(self):
        app.TABLE.scan.side_effect=[{'Items':[{'q8':'=SUM(A1:A2)'}],'LastEvaluatedKey':{'response_id':'next'}},
                                    {'Items':[{'q8':'A comma, and "quotes"\nnext line'}]}]
        event={'requestContext':{'authorizer':{'iam':{'userArn':'arn:aws:iam::123:user/admin'}}}}
        result=app.export(event,None)
        self.assertEqual(result['statusCode'],200)
        rows=list(csv.DictReader(io.StringIO(result['body'])))
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]['q8'],"'=SUM(A1:A2)")
        self.assertEqual(rows[1]['q8'],'A comma, and "quotes"\nnext line')
        self.assertEqual(app.TABLE.scan.call_args.kwargs['ExclusiveStartKey'],{'response_id':'next'})
    def test_export_size_limit(self):
        app.TABLE.scan.return_value={'Items':[{'q8':'x'*(app.MAX_CSV+1)}]}
        event={'requestContext':{'authorizer':{'iam':{'userArn':'admin'}}}}
        self.assertEqual(app.export(event,None)['statusCode'],413)
    def test_browser_export_checks_scope_token_type_and_client(self):
        from unittest.mock import patch
        app.TABLE.scan.return_value={'Items':[]}
        good={'token_use':'access','scope':'openid urmia-export/download','client_id':'expected'}
        with patch.dict(app.os.environ, {'ADMIN_CLIENT_ID':'expected'}):
            for claims,status in [(good,200),(dict(good,scope='openid'),403),(dict(good,token_use='id'),403),(dict(good,client_id='other'),403)]:
                event={'requestContext':{'authorizer':{'jwt':{'claims':claims}}}}
                self.assertEqual(app.export(event,None)['statusCode'],status)

    def test_template_routes_and_permissions(self):
        t=json.loads((Path(__file__).resolve().parents[1]/'template.json').read_text())['Resources']
        self.assertEqual(t['ExportRoute']['Properties']['AuthorizationType'],'AWS_IAM')
        self.assertEqual(t['SubmitRoute']['Properties']['AuthorizationType'],'NONE')
        self.assertEqual(t['Table']['DeletionPolicy'],'Retain')
        self.assertTrue(t['AdminPool']['Properties']['AdminCreateUserConfig']['AllowAdminCreateUserOnly'])
        self.assertFalse(t['AdminClient']['Properties']['GenerateSecret'])
        self.assertEqual(t['AdminRoute']['Properties']['AuthorizationType'],'JWT')
        self.assertEqual(t['AdminRoute']['Properties']['AuthorizationScopes'],['urmia-export/download'])
        self.assertEqual(t['ExportRole']['Properties']['Policies'][0]['PolicyDocument']['Statement'][0]['Action'],['dynamodb:Scan'])

if __name__=='__main__': unittest.main()

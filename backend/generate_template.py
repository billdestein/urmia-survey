"""Embed handlers in CloudFormation, without SAM or an artifact bucket."""
import json
from pathlib import Path
from html.parser import HTMLParser
ROOT = Path(__file__).resolve().parent
class Choices(HTMLParser):
    def __init__(self):
        super().__init__(); self.choices={}; self.select=None; self.option=False
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='input' and a.get('type')=='radio':
            self.choices.setdefault(a['name'], []).append(a['value'])
        if tag=='select':
            self.select=a['name']; self.choices[self.select]=['']
        if tag=='option':
            self.option='value' not in a
    def handle_data(self, data):
        if self.select and self.option and data.strip(): self.choices[self.select].append(data.strip())
    def handle_endtag(self, tag):
        if tag=='select': self.select=None
        if tag=='option': self.option=False
parser=Choices(); parser.feed((ROOT.parent/'index.html').read_text())
(ROOT/'schema.json').write_text(json.dumps(parser.choices, indent=2)+'\n')
code=(ROOT/'app.py').read_text().replace('CHOICES = {}', 'CHOICES = '+repr(parser.choices))
ref=lambda name: {'Ref':name}
get=lambda name, attr: {'Fn::GetAtt':[name,attr]}
sub=lambda text: {'Fn::Sub':text}
resources={
'Table': {'Type':'AWS::DynamoDB::Table', 'DeletionPolicy':'Retain', 'UpdateReplacePolicy':'Retain', 'Properties':{
    'BillingMode':'PAY_PER_REQUEST', 'AttributeDefinitions':[{'AttributeName':'response_id','AttributeType':'S'}],
    'KeySchema':[{'AttributeName':'response_id','KeyType':'HASH'}],
    'PointInTimeRecoverySpecification':{'PointInTimeRecoveryEnabled':True}, 'SSESpecification':{'SSEEnabled':True}}},
'Api': {'Type':'AWS::ApiGatewayV2::Api','Properties':{'Name':sub('${AWS::StackName}'), 'ProtocolType':'HTTP',
    'CorsConfiguration':{'AllowOrigins':['https://billdestein.github.io'], 'AllowMethods':['POST'],
                         'AllowHeaders':['content-type','idempotency-key'], 'MaxAge':600}}},
'Stage': {'Type':'AWS::ApiGatewayV2::Stage','Properties':{'ApiId':ref('Api'), 'StageName':'$default','AutoDeploy':True,
    'DefaultRouteSettings':{'ThrottlingBurstLimit':10,'ThrottlingRateLimit':5}}}}
for name,handler,actions,path,method,auth,timeout in [
    ('Submit','submit',['dynamodb:PutItem','dynamodb:GetItem'],'/responses','POST','NONE',15),
    ('Export','export',['dynamodb:Scan'],'/responses.csv','GET','AWS_IAM',60)]:
    resources[name+'Role']={'Type':'AWS::IAM::Role','Properties':{
        'AssumeRolePolicyDocument':{'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':'lambda.amazonaws.com'},'Action':'sts:AssumeRole'}]},
        'Policies':[{'PolicyName':'Handler','PolicyDocument':{'Version':'2012-10-17','Statement':[
            {'Effect':'Allow','Action':actions,'Resource':get('Table','Arn')},
            {'Effect':'Allow','Action':['logs:CreateLogStream','logs:PutLogEvents'],
             'Resource':sub('arn:${AWS::Partition}:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/lambda/${AWS::StackName}-'+name+':*')} ]}}]}}
    resources[name+'Log']={'Type':'AWS::Logs::LogGroup','Properties':{'LogGroupName':sub('/aws/lambda/${AWS::StackName}-'+name),'RetentionInDays':14}}
    resources[name]={'Type':'AWS::Lambda::Function','DependsOn':name+'Log','Properties':{
        'FunctionName':sub('${AWS::StackName}-'+name), 'Runtime':'python3.13','Handler':'index.'+handler,
        'Role':get(name+'Role','Arn'),'Timeout':timeout,'MemorySize':256,'ReservedConcurrentExecutions':5,
        'Environment':{'Variables':{'TABLE_NAME':ref('Table'),'SURVEY_OPEN':ref('SurveyOpen')}},'Code':{'ZipFile':code}}}
    resources[name+'Integration']={'Type':'AWS::ApiGatewayV2::Integration','Properties':{'ApiId':ref('Api'),
        'IntegrationType':'AWS_PROXY','IntegrationUri':get(name,'Arn'),'PayloadFormatVersion':'2.0'}}
    resources[name+'Route']={'Type':'AWS::ApiGatewayV2::Route','Properties':{'ApiId':ref('Api'),
        'RouteKey':method+' '+path,'AuthorizationType':auth,'Target':{'Fn::Join':['/', ['integrations',ref(name+'Integration')]]}}}
    resources[name+'Permission']={'Type':'AWS::Lambda::Permission','Properties':{'FunctionName':ref(name),
        'Action':'lambda:InvokeFunction','Principal':'apigateway.amazonaws.com',
        'SourceArn':sub('arn:${AWS::Partition}:execute-api:${AWS::Region}:${AWS::AccountId}:${Api}/*/'+method+path)}}
template={'AWSTemplateFormatVersion':'2010-09-09','Description':'URMIA survey HTTP API, Lambda, and DynamoDB',
 'Parameters':{'SurveyOpen':{'Type':'String','Default':'true','AllowedValues':['true','false']}},
 'Resources':resources,'Outputs':{'SubmitUrl':{'Value':sub('${Api.ApiEndpoint}/responses')},
 'ExportUrl':{'Value':sub('${Api.ApiEndpoint}/responses.csv')},'TableName':{'Value':ref('Table')},
 'ExportInvokeArn':{'Value':sub('arn:${AWS::Partition}:execute-api:${AWS::Region}:${AWS::AccountId}:${Api}/$default/GET/responses.csv')}}}
(ROOT/'template.json').write_text(json.dumps(template,indent=2)+'\n')
print('Generated schema and CloudFormation template from survey choices.')

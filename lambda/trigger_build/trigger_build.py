import boto3
from os import environ
import json

sfn_client = boto3.client('stepfunctions')

def lambda_handler(event, context): 
    print(f'event : {event}')
    event_type = event['RequestType']
    sm_arn = environ['STATE_MACHINE_ARN']
    
    if event_type in ['Create', 'Delete']:
        res = sfn_client.list_executions(
            stateMachineArn=sm_arn,
            maxResults=1
        )
        if res['executions']:
            print(f'exections exists : {res["executions"]}')
            if res['executions'][0]['status'] == 'RUNNING':
                print(f'execution still running. IsComplete: False.')
                return { 
                   'statusCode': 200,
                    'IsComplete': False
                }
            else:
                print(f'execution not running. IsComplete: True.')
                return { 
                   'statusCode': 200,
                    'IsComplete': True
                }
        else:
            print(f'execution doens\'t exist. Executing stepfunction statemachine.')
            response = sfn_client.start_execution(stateMachineArn=sm_arn)
            print(response)

            return {
                'statusCode': 200,
                'Response': json.dumps(response, default=str)
            }
        
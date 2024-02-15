import boto3
from os import environ
import json

sagemaker_client = boto3.client('sagemaker-runtime')

def lambda_handler(event, context): 
    print(f'event : {event}')
    event_type = event['RequestType']
    endpoint_name = environ['SAGEMAKER_ENDPOINT_NAME']
    payload = {
        "configure": {
            "bucket": environ['MODEL_BUCKET_NAME'],
            "key": environ['MODEL_BUCKET_KEY_NAME']
        }
    }

    if event_type in ['Create']:
        response = sagemaker_client.invoke_endpoint(
            EndpointName=endpoint_name,
            ContentType='application/json',
            Body=json.dumps(payload)
        )
        print(f"response: {response}")

        return {
            'statusCode': 200,
            'Response': json.dumps(response, default=str)
        }
    
    return{
        'statusCode': 200,
        'Response': 'Not a create request!'
    }
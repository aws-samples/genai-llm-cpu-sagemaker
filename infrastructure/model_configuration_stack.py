from aws_cdk import (
    Stack,
    CfnOutput,
    aws_ssm,
)

from constructs import Construct

import boto3
import json

class ModelConfigurationStack(Stack):

    def configure_sagemaker_endpoint(self, endpoint_name, llama_model_args):

        sagemaker_runtime = boto3.client('sagemaker-runtime')

        payload = {
            'configure': True,
            'inference': False,
            'args': llama_model_args
        }
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName=endpoint_name,
            Body=json.dumps(payload),
            ContentType='application/json',
        )
        response_body = json.loads(response['Body'].read().decode())
        return response_body

    def __init__(self, scope: Construct, construct_id: str, model_bucket_key_file: str, env, **kwargs) -> None:
        super().__init__(scope, construct_id, env=env, **kwargs)

        """
        Wait until your model is InService.

        This is to configure the model
        overwrite 'bucket' and 'key' with your path to the model file.
        set 'n_threads': NUMBER_OF_VPCUS - 1 to use all available VPCUS.
        Execute this cell each time you want to load a new model into the endpoint without having to redeploy anything. 
        Loading model from S3 usualy takes 20-30 seconds but depends on loading speed from S3.
        """

        sagemaker_endpoint_name = aws_ssm.StringParameter.value_from_lookup(
            self, "sagemaker_endpoint_name_parameter")

        model_bucket_name = aws_ssm.StringParameter.value_from_lookup(
            self, "model_bucket_name_parameter")

        print("sagemaker_endpoint_name:", sagemaker_endpoint_name)
        print("model_bucket_name:", model_bucket_name)
        

        llama_model_args = {
            "bucket":f"{model_bucket_name}",
            "key":f"{model_bucket_key_file}", 
            "n_ctx": 1024,
            "n_parts": -1,
            "n_gpu_layers": 0,
            "seed": 1411,
            "f16_kv": True,
            "logits_all": False,
            "vocab_only": False,
            "use_mmap": True,
            "use_mlock": False,
            "embedding": False,
            "n_threads": None,
            "n_batch": 512,
            "last_n_tokens_size": 64,
            "lora_base": None,
            "lora_path": None,
            "low_vram": False,
            "tensor_split": None,
            "rope_freq_base": 10000,
            "rope_freq_scale": 1,
            "verbose": False,
        }

        response = self.configure_sagemaker_endpoint(sagemaker_endpoint_name, llama_model_args)
        print("Sagemaker endpoint configuration status: ", response)

       




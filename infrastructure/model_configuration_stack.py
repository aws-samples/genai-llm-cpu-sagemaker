from aws_cdk import (
    Stack,
    CfnOutput, 
    Duration,
    aws_stepfunctions,
    aws_stepfunctions_tasks,
    aws_codepipeline,
    aws_codepipeline_actions,
    aws_iam,
    aws_s3_assets
)
from constructs import Construct

import boto3
import json
import os

class ModelConfigurationStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, 
            model_bucket_key: str, 
            model_bucket_name: str, 
            sagemaker_endpoint_name:str, 
            project_name: str,
            **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        MODEL_BUCKET_KEY_FILE = model_bucket_key
        ENDPOINT_NAME = sagemaker_endpoint_name
        MODEL_BUCKET_NAME = model_bucket_name
        PROJECT_NAME = project_name

        ROOT_DIR = os.path.abspath(os.curdir)

        """
        Wait until your model is InService.

        This is to configure the model
        overwrite 'bucket' and 'key' with your path to the model file.
        set 'n_threads': NUMBER_OF_VPCUS - 1 to use all available VPCUS.
        Execute this cell each time you want to load a new model into the endpoint without having to redeploy anything. 
        Loading model from S3 usualy takes 20-30 seconds but depends on loading speed from S3.
        """
        
        llama_model_args = {
            "bucket":f"{MODEL_BUCKET_NAME}",
            "key":f"{MODEL_BUCKET_KEY_FILE}", 
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

        payload = {
            'configure': True,
            'inference': False,
            'args': llama_model_args
        }

        payload_json = json.dumps(payload)

        state_json = {
            "Type": "Task",
            "End": True,
            "Parameters": {
                "Body.$": aws_stepfunctions.JsonPath.string_to_json(str(payload_json)),
                "EndpointName": ENDPOINT_NAME
            },
            "Resource": "arn:aws:states:::aws-sdk:sagemakerruntime:invokeEndpoint",
        }

        custom_state = aws_stepfunctions.CustomState(self, "invoke sagemaker configure endpoint",
            state_json=state_json
        )

        chain = aws_stepfunctions.Chain.start(custom_state) #.next(final_status)

        state_machine = aws_stepfunctions.StateMachine(self, "SagemakerEndpointStateMachine",
            definition=chain,
            timeout=Duration.seconds(30),
        )

        state_machine.add_to_role_policy(statement=aws_iam.PolicyStatement(
                actions=["sagemaker:InvokeEndpoint"],
                resources=["*"]
            )
        )

        # pipeline = aws_codepipeline.Pipeline(self, 
        #     f"{PROJECT_NAME}-model-configuration-pipeline"
        #     )


        input_artifact = aws_codepipeline.Artifact()

        asset_bucket = aws_s3_assets.Asset(self, "ModelAssets",
            path = os.path.join(ROOT_DIR, "model"),
        )

        source_output = aws_codepipeline.Artifact(artifact_name='source')

        source_action = aws_codepipeline_actions.S3SourceAction(
            bucket=asset_bucket.bucket,
            bucket_key=asset_bucket.s3_object_key,
            action_name='Source',
            run_order=1,
            output=source_output,  
        )
 
        step_function_action = aws_codepipeline_actions.StepFunctionInvokeAction(
            action_name="Invoke",
            state_machine=state_machine,
            run_order=2        
        )

        aws_codepipeline.Pipeline(self, "Pipeline",
            pipeline_name=f"{PROJECT_NAME}-model-configuration-pipeline",
            artifact_bucket=asset_bucket.bucket,
            stages=[aws_codepipeline.StageProps(
                stage_name="Source",
                actions=[source_action],
            ), aws_codepipeline.StageProps(
                stage_name="StepFunctions",
                actions=[step_function_action],
            )
            ]
        )

        CfnOutput(scope=self,
            id="sagemaker_invoke_endpoint_state_machine_name", 
            value=state_machine.state_machine_name, 
        )
       




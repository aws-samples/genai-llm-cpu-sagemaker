#!/usr/bin/env python3
import os
import boto3
import aws_cdk as cdk

from infrastructure.model_serving_stack import ModelServingStack
from infrastructure.image_building_stack import ImageBuildingStack


environment=cdk.Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"])

model_info = {
    "role_name": "SageMakerExecutionRole",
    "model_bucket_name": "sagemaker-llama-model-bucket",
}

app = cdk.App()


ImageBuildingStack(app, "ImageBuildingStack", env=environment)
ModelServingStack(app, "ModelServingStack", env=environment, model_info=model_info)

app.synth()

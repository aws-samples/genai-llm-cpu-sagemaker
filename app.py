#!/usr/bin/env python3
import os
import boto3
import aws_cdk as cdk
import time

from infrastructure.model_serving_stack import ModelServingStack
from infrastructure.image_building_stack import ImageBuildingStack
from infrastructure.model_download_stack import ModelDownloadStack


environment=cdk.Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"])

model_info = {
    "role_name": "SageMakerExecutionRole",
    "model_bucket_name": "sagemaker-llama-model-bucket",
}

app = cdk.App()

ModelDownloadStack(app, "ModelDownloadStack", env=environment)
ImageBuildingStack(app, "ImageBuildingStack", env=environment)
ModelServingStack(app, "ModelServingStack", env=environment, model_info=model_info)
# time.sleep(30) # wait until model is InService before configuring it

app.synth()

#!/usr/bin/env python3
import os
import boto3
import aws_cdk as cdk
import time

from aws_cdk import (aws_cloudformation, RemovalPolicy, CfnResource)

from infrastructure.model_serving_stack import ModelServingStack
from infrastructure.image_building_stack import ImageBuildingStack
from infrastructure.model_download_stack import ModelDownloadStack
from infrastructure.model_configuration_stack import ModelConfigurationStack

from configparser import ConfigParser

environment=cdk.Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"]
)

config = ConfigParser()
config.read("app-config.ini")

project_name               = config.get('project', 'project_name').replace('"', '')

model_bucket_prefix        = config.get("model", "model_bucket_prefix").replace('"', '')
model_hugging_face_name    = config.get("model", "model_hugging_face_name").replace('"', '')
model_bucket_key_full_name = config.get("model", "model_full_name").replace('"', '')

image_bucket_prefix        = config.get("image", "image_bucket_prefix").replace('"', '')
image_repository_name      = config.get("image", "image_repository_name").replace('"', '')

sagemaker_role_name        = config.get("inference", "sagemaker_role_name").replace('"', '')
instance_type              = config.get("inference", "instance_type").replace('"', '')

model_bucket_key_compressed     = model_bucket_key_full_name.split(".")[0] + ".tar.gz"
sagemaker_model_name            = model_bucket_key_full_name.split(".")[0]

app = cdk.App()

modelDownloadStack = ModelDownloadStack(app, 
    "ModelDownloadStack", 
    env=environment, 
    project_name=project_name,
    model_bucket_prefix=model_bucket_prefix,
    model_bucket_key_compressed=model_bucket_key_compressed,
    model_bucket_key_full_name=model_bucket_key_full_name,
    model_hugging_face_name=model_hugging_face_name
    )

imageBuildingStack = ImageBuildingStack(app, 
    "ImageBuildingStack", 
    env=environment,
    project_name=project_name, 
    repository_name=image_repository_name, 
    image_bucket_name=image_bucket_prefix, 
    model_bucket_name=cdk.Fn.import_value("var-modelbucketname"),
    )

modelServingStack = ModelServingStack(app, 
    "ModelServingStack", 
    env=environment, 
    sagemaker_role_name=sagemaker_role_name,
    instance_type=instance_type, 
    model_repository_uri=cdk.Fn.import_value("var-modelrepositoryuri"), 
    model_bucket_name=cdk.Fn.import_value("var-modelbucketname"), 
    model_bucket_key=model_bucket_key_compressed, 
    sagemaker_model_name=sagemaker_model_name,
    )

modelServingStack.add_dependency(imageBuildingStack)
modelServingStack.add_dependency(modelDownloadStack)

modelConfigurationStack = ModelConfigurationStack(app, 
    "ModelConfigurationStack",
    env=environment,
    project_name=project_name, 
    model_bucket_key=model_bucket_key_full_name,
    model_bucket_name=cdk.Fn.import_value("var-modelbucketname"),
    sagemaker_endpoint_name=cdk.Fn.import_value("var-sagemakerendpointname"),
    )

modelConfigurationStack.add_dependency(imageBuildingStack)
modelConfigurationStack.add_dependency(modelDownloadStack)

app.synth()

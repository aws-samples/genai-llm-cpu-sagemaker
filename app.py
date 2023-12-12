#!/usr/bin/env python3
import os
import aws_cdk as cdk

from infrastructure.model_serving_stack import ModelServingStack
from infrastructure.image_building_stack import ImageBuildingStack
from infrastructure.model_download_stack import ModelDownloadStack
from infrastructure.model_configuration_stack import ModelConfigurationStack

from configparser import ConfigParser

### Set environment
environment=cdk.Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"]
)

platfrom_supported_values = ["arm", "amd"]

### Read config
config = ConfigParser()
config.read("app-config.ini")

project_name               = config.get('project', 'project_name').replace('"', '')

model_bucket_prefix        = config.get("model", "model_bucket_prefix").replace('"', '')
model_hugging_face_name    = config.get("model", "model_hugging_face_name").replace('"', '')
model_bucket_key_full_name = config.get("model", "model_full_name").replace('"', '')

image_repository_name      = config.get("image", "image_repository_name").replace('"', '')
platform                   = config.get("image", "platform").replace('"', '').lower()
image_tag                  = config.get("image", "image_tag").replace('"', '').lower()

sagemaker_role_name        = config.get("inference", "sagemaker_role_name").replace('"', '')
sagemaker_model_name       = config.get("inference", "sagemaker_model_name").replace('"', '')
instance_type              = config.get("inference", "instance_type").replace('"', '')

### Validate input
if platform not in platfrom_supported_values:
    raise ValueError(f"[ERROR] Value {platform} of the \"image.platform\" parameter does not match one of the suported values: " + ', '.join(platfrom_supported_values)) 

if platform not in ["arm"] and "g" in instance_type.split(".")[1] and instance_type.split(".")[1] not in ["g5"]:
    print("[WARNING] Platfrom for the image is not set to ARM, however, instance type potentially belongs to the AWS Graviton family.")

### Define app stacks
app = cdk.App()

modelDownloadStack = ModelDownloadStack(app, 
    "ModelDownloadStack", 
    env=environment, 
    project_name=project_name,
    model_bucket_prefix=model_bucket_prefix,
    model_bucket_key_full_name=model_bucket_key_full_name,
    model_hugging_face_name=model_hugging_face_name,
    )

imageBuildingStack = ImageBuildingStack(app, 
    "ImageBuildingStack", 
    env=environment,
    project_name=project_name, 
    repository_name=image_repository_name, 
    model_bucket_name=cdk.Fn.import_value("var-modelbucketname"),
    platform=platform,
    image_tag=image_tag,
    )

modelServingStack = ModelServingStack(app, 
    "ModelServingStack", 
    env=environment, 
    project_name=project_name, 
    sagemaker_role_name=sagemaker_role_name,
    instance_type=instance_type, 
    model_repository_uri=cdk.Fn.import_value("var-modelrepositoryuri"), 
    model_bucket_name=cdk.Fn.import_value("var-modelbucketname"), 
    sagemaker_model_name=sagemaker_model_name,
    model_repository_name=image_repository_name, 
    image_tag=image_tag,
    )

modelServingStack.add_dependency(imageBuildingStack)
modelServingStack.add_dependency(modelDownloadStack)

modelConfigurationStack = ModelConfigurationStack(app, 
    "ModelConfigurationStack",
    env=environment,
    project_name=project_name, 
    sagemaker_model_name=sagemaker_model_name,
    model_bucket_key=model_bucket_key_full_name,
    model_bucket_name=cdk.Fn.import_value("var-modelbucketname"),
    sagemaker_endpoint_name=cdk.Fn.import_value("var-sagemakerendpointname"),
    )

modelConfigurationStack.add_dependency(imageBuildingStack)
modelConfigurationStack.add_dependency(modelDownloadStack)

app.synth()

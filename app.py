#!/usr/bin/env python3
from os import getenv

import aws_cdk as cdk
from cdk_nag import AwsSolutionsChecks, NagSuppressions, NagPackSuppression

import yaml

from infrastructure.model_serving_stack import ModelServingStack
from infrastructure.model_configuration_stack import ModelConfigurationStack
from infrastructure.llama_cpp_stack import LlamaCppStack

### Set environment
environment=cdk.Environment(
    region=getenv("AWS_REGION", getenv("CDK_DEFAULT_REGION")),
    account=getenv("AWS_ACCOUNT_ID", getenv("CDK_DEFAULT_ACCOUNT")),
)

### Read config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

project_name = config['project']['name']

model_bucket_prefix = config['model']['bucket_prefix']
model_hugging_face_name = config['model']['hf_name']
model_bucket_key_full_name = config['model']['full_name']

image_repository_name = config['image']['repo_name']
platform = config['image']['platform'].lower()
image_tag = config['image']['image_tag']

sagemaker_role_name = config['inference']['sagemaker_role_name']
sagemaker_model_name = config['inference']['sagemaker_model_name']
instance_type = config['inference']['instance_type']

### Validate input
if platform not in ["arm", "amd"]:
    raise ValueError(f"[ERROR] Value {platform} of the \"image.platform\" parameter does not match one of the suported values: ['arm', 'amd']") 

if platform not in ["arm"] and "g" in instance_type.split(".")[1] and instance_type.split(".")[1] not in ["g5"]:
    print("[WARNING] Platfrom for the image is not set to ARM, however, instance type potentially belongs to the AWS Graviton family.")

### Define app stacks
app = cdk.App()

llamaCppStack = LlamaCppStack(app,
    "LlamaCppStack",
    env=environment,
    project_name=project_name,
    model_bucket_prefix=model_bucket_prefix,
    model_bucket_key_full_name=model_bucket_key_full_name,
    model_hugging_face_name=model_hugging_face_name,
    image_repo_name=image_repository_name,
    image_tag=image_tag,
    image_platform=platform
    )

# modelServingStack = ModelServingStack(app, 
#     "ModelServingStack", 
#     env=environment, 
#     project_name=project_name, 
#     sagemaker_role_name=sagemaker_role_name,
#     instance_type=instance_type, 
#     model_repository_uri=cdk.Fn.import_value("var-modelrepositoryuri"), 
#     model_bucket_name=cdk.Fn.import_value("var-modelbucketname"), 
#     sagemaker_model_name=sagemaker_model_name,
#     model_repository_name=image_repository_name, 
#     image_tag=image_tag,
#     )

# modelConfigurationStack = ModelConfigurationStack(app, 
#     "ModelConfigurationStack",
#     env=environment,
#     project_name=project_name, 
#     sagemaker_model_name=sagemaker_model_name,
#     model_bucket_key=model_bucket_key_full_name,
#     model_bucket_name=cdk.Fn.import_value("var-modelbucketname"),
#     sagemaker_endpoint_name=cdk.Fn.import_value("var-sagemakerendpointname"),
#     )

# modelConfigurationStack.add_dependency(imageBuildingStack)
# modelConfigurationStack.add_dependency(modelDownloadStack)

# tags
tags = {
   "SolutionName": "LlamacppSagemakerEndpoint",
   "SolutionVersion": "v1.0.0",
   "SolutionIaC": "CDK v2"
}

for key, val in tags.items():
    cdk.Tags.of(app).add(key,val)

# cdk-nag checks
nag_suppressions = [
    {"id": "AwsSolutions-IAM5", "reason": "CodePipeline policy needs to have full access to assets S3 bucket."},
    {"id": "AwsSolutions-IAM4", "reason": "CustomeResource Lambda function using managed policy, following least previleges."},
    {"id": "AwsSolutions-L1", "reason": "CDK CustomResource limitation."},
    {"id": "AwsSolutions-SF1", "reason": "State machine is not used in this sample code."},
    {"id": "AwsSolutions-CB4", "reason": "CodeBuild does not have to encrypt data for the purpose of this sample code. Adding KMS key would incur additional cost."}
]

# for supression in nag_suppressions:
#     for stack in [modelDownloadStack, imageBuildingStack, modelServingStack, modelConfigurationStack]:
#         NagSuppressions.add_stack_suppressions(stack, [NagPackSuppression(id=supression["id"], reason=supression["reason"])])

# cdk.Aspects.of(app).add(AwsSolutionsChecks(verbose=True))

app.synth()

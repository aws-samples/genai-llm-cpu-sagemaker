from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_iam,
    aws_ssm,
    aws_s3,
    aws_sagemaker as sagemaker
)

import logging

from constructs import Construct

from construct.sagemaker_endpoint_construct import SageMakerEndpointConstruct

import sagemaker
from sagemaker import script_uris
from sagemaker import image_uris 
from sagemaker import model_uris

class ModelServingStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, env, model_info, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ROLE_NAME = model_info["role_name"] #"SageMakerExecutionRole"
        MODEL_BUCKET_NAME = model_info["model_bucket_name"] #"sagemaker-llama-model-bucket"
        REGION_NAME = str(env.region)
        
        print("Region: ", REGION_NAME)

        # create bucket
        bucket = aws_s3.Bucket(self, f"{MODEL_BUCKET_NAME}",
            versioned=False,
            removal_policy=RemovalPolicy.DESTROY
        )

        MODEL_BUCKET_NAME = bucket.bucket_name
        #print("bucket: ", str(dict(value=bucket.bucket_name)))

        sagemaker_role = aws_iam.Role(self, f"{ROLE_NAME}",
            assumed_by=aws_iam.ServicePrincipal("sagemaker.amazonaws.com")
        )

        sts_policy = aws_iam.Policy(self, "sm-deploy-policy-sts",
                                    statements=[aws_iam.PolicyStatement(
                                        effect=aws_iam.Effect.ALLOW,
                                        actions=[
                                            "sts:AssumeRole"
                                          ],
                                        resources=["*"]
                                    )]
                                )

        logs_policy = aws_iam.Policy(self, "sm-deploy-policy-logs",
                                    statements=[aws_iam.PolicyStatement(
                                        effect=aws_iam.Effect.ALLOW,
                                        actions=[
                                            "cloudwatch:PutMetricData",
                                            "logs:CreateLogStream",
                                            "logs:PutLogEvents",
                                            "logs:CreateLogGroup",
                                            "logs:DescribeLogStreams",
                                            "ecr:GetAuthorizationToken"
                                          ],
                                        resources=["*"]
                                    )]
                                )

        ecr_policy = aws_iam.Policy(self, "sm-deploy-policy-ecr",
                                    statements=[aws_iam.PolicyStatement(
                                        effect=aws_iam.Effect.ALLOW,
                                        actions=[
                                            "ecr:*",
                                          ],
                                        resources=["*"]
                                    )]
                                )
        
        s3_policy = aws_iam.Policy(self, "sm-deploy-policy-s3",
                                    statements=[aws_iam.PolicyStatement(
                                        effect=aws_iam.Effect.ALLOW,
                                        actions=[
                                            "s3:*",
                                          ],
                                        resources=["*"] #[f"arn:aws:s3:::{MODEL_BUCKET_NAME}/*"]
                                    )]
                                )

        # sagemaker_role.add_to_policy(aws_iam.PolicyStatement(
        #     actions=["s3:*"],
        #     resources=[f"arn:aws:s3:::{MODEL_BUCKET_NAME}/*"]
        # ))
                                
        sagemaker_role.attach_inline_policy(sts_policy)
        sagemaker_role.attach_inline_policy(logs_policy)
        sagemaker_role.attach_inline_policy(ecr_policy)
        sagemaker_role.attach_inline_policy(s3_policy)

        MODEL_NAME = 'llamacpp-arm64-c7-x8-v00'
        #Graviton
        #MODEL_IMAGE = '444975673530.dkr.ecr.us-east-1.amazonaws.com/y0d1u8z0/y0d1u8z0/llmm-cpu-arm64-full-v00:perf'  #private pull-through cache of public.ecr.aws/y0d1u8z0/llmm-cpu-arm64:latest

        MODEL_IMAGE = "public.ecr.aws/nginx/nginx:alpine-slim"

        ENDPOINT_CONFIG_NAME = f'{MODEL_NAME}-config'
        ENDPOINT_NAME = f'{MODEL_NAME}-stream'

        INSTANCE_TYPE = "ml.c7g.2xlarge" # make sure you use correct instance types x86 or graviton 

        MODEL_VERSION = "*"  # latest
        SCOPE = "inference"

        model_id = "huggingface-llm-mistral-7b-instruct" #"meta-textgeneration-llama-2-7b"
        region_name = str(env.region)
        instance_type = "ml.g5.24xlarge"

        inference_model_uri = model_uris.retrieve(model_id=model_id, 
                                          model_version=MODEL_VERSION, 
                                          model_scope=SCOPE)

        inference_image_uri = image_uris.retrieve(region=region_name, 
                                          framework=None,
                                          model_id=model_id, 
                                          model_version=MODEL_VERSION, 
                                          image_scope=SCOPE, 
                                          instance_type=instance_type)


        print("inference_model_uri: ", inference_model_uri) 
        # s3://jumpstart-cache-prod-us-east-1/huggingface-infer/prepack/v1.0.0/infer-prepack-huggingface-llm-mistral-7b-instruct.tar.gz

        model_bucket_name = inference_model_uri.split("/")[2]
        model_bucket_key = "/".join(inference_model_uri.split("/")[3:])
        model_docker_image = inference_image_uri

        endpoint = SageMakerEndpointConstruct(self, f"{MODEL_NAME}",
                                    project_prefix = "GenerativeAiDemoLlama",
                                    
                                    role_arn= sagemaker_role.role_arn,

                                    model_name = f"{MODEL_NAME}",
                                    model_bucket_name = model_bucket_name,
                                    model_bucket_key = model_bucket_key,
                                    model_docker_image = model_docker_image,

                                    variant_name = "AllTraffic",
                                    variant_weight = 1,
                                    instance_count = 1,
                                    instance_type = f"{INSTANCE_TYPE}",

                                    environment = {
                                        "MMS_MAX_RESPONSE_SIZE": "20000000",
                                        "SAGEMAKER_CONTAINER_LOG_LEVEL": "20",
                                        "SAGEMAKER_PROGRAM": "inference.py",
                                        "SAGEMAKER_REGION": f"{REGION_NAME}",
                                        "SAGEMAKER_SUBMIT_DIRECTORY": "/opt/ml/model/code",
                                    },

                                    deploy_enable = True
        )
        
        endpoint.node.add_dependency(sts_policy)
        endpoint.node.add_dependency(logs_policy)
        endpoint.node.add_dependency(ecr_policy)
        
        aws_ssm.StringParameter(self, "sm_endpoint", parameter_name="sm_endpoint", string_value=endpoint.endpoint_name)


       




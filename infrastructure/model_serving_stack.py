from aws_cdk import (
    Stack,
    RemovalPolicy,
    CfnOutput,
    aws_iam,
    aws_ssm,
    aws_s3,
    aws_sagemaker as sagemaker,
    aws_s3_deployment
    )

from sagemaker import (
    script_uris, 
    image_uris, 
    model_uris
    )

import sagemaker

from constructs import Construct
from construct.sagemaker_endpoint_construct import SageMakerEndpointConstruct

class ModelServingStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, env, sagemaker_role_name: str, instance_type: str, model_repository_uri: str, model_bucket_name: str, model_bucket_key: str, sagemaker_model_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ROLE_NAME = sagemaker_role_name
        REGION_NAME = str(env.region)

        MODEL_BUCKET_NAME = model_bucket_name
        MODEL_BUCKET_KEY = model_bucket_key
        MODEL_REPOSITORY_URI = model_repository_uri

        INSTANCE_TYPE = instance_type # make sure you use correct instance types x86 or graviton 

        MODEL_NAME = sagemaker_model_name
        ENDPOINT_CONFIG_NAME = f'{MODEL_NAME}-config'
        ENDPOINT_NAME = f'{MODEL_NAME}-stream'

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
                                        resources=["*"] #TODO[f"arn:aws:s3:::{MODEL_BUCKET_NAME}/*"]
                                    )]
                                )
                                
        sagemaker_role.attach_inline_policy(sts_policy)
        sagemaker_role.attach_inline_policy(logs_policy)
        sagemaker_role.attach_inline_policy(ecr_policy)
        sagemaker_role.attach_inline_policy(s3_policy)    

        endpoint = SageMakerEndpointConstruct(self, f"{MODEL_NAME}",
                                    project_prefix = "GenerativeAiDemoLlama",
                                    
                                    role_arn= sagemaker_role.role_arn,

                                    model_name = f"{MODEL_NAME}",
                                    model_bucket_name = f"{MODEL_BUCKET_NAME}",
                                    model_bucket_key = f"{MODEL_BUCKET_KEY}",
                                    model_repository_image = f"{MODEL_REPOSITORY_URI}:latest", #TODO do not hardcode tags

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

        CfnOutput(scope=self,
            id="sagemaker_endpoint_name", 
            value=endpoint.endpoint_name, 
            export_name="var-sagemakerendpointname"
            )


       




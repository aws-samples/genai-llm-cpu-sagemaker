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

from constructs import Construct
from construct.sagemaker_endpoint_construct import SageMakerEndpointConstruct

class ModelServingStack(Stack):

    def __init__(self, scope: Construct, construct_id: str,
        project_name: str, 
        sagemaker_role_name: str, 
        instance_type: str, 
        model_repository_uri: str, 
        model_bucket_name: str, 
        sagemaker_model_name: str,
        model_repository_name: str,
        image_tag: str,
         **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ROLE_NAME = sagemaker_role_name
        PROJECT_NAME = project_name
        REGION_NAME = self.region
        ACCOUNT_ID = self.account

        MODEL_BUCKET_NAME = model_bucket_name
        MODEL_REPOSITORY_URI = model_repository_uri
        MODEL_REPOSITORY_NAME = model_repository_name
        MODEL_REPOSITORY_IMAGE_TAG = image_tag

        INSTANCE_TYPE = instance_type 

        MODEL_NAME = sagemaker_model_name
        ENDPOINT_CONFIG_NAME = f'{MODEL_NAME}-config'
        ENDPOINT_NAME = f'{MODEL_NAME}-stream'

        sagemaker_role = aws_iam.Role(self, f"{ROLE_NAME}",
            assumed_by=aws_iam.ServicePrincipal("sagemaker.amazonaws.com")
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
                                        resources=[f"arn:aws:logs:{REGION_NAME}:{ACCOUNT_ID}:log-group:/aws/sagemaker/Endpoints/{PROJECT_NAME}-{MODEL_NAME}-Endpoint:*"]
                                    )]
                                )

        ecr_policy = aws_iam.Policy(self, "sm-deploy-policy-ecr",
                                    statements=[
                                        aws_iam.PolicyStatement(
                                        effect=aws_iam.Effect.ALLOW,
                                        actions=[
                                            "ecr:GetAuthorizationToken"
                                          ],
                                        resources=["*"]                                   
                                    ),
                                        aws_iam.PolicyStatement(
                                        effect=aws_iam.Effect.ALLOW,
                                        actions=[
                                            "ecr:ListTagsForResource",
                                            "ecr:ListImages",
                                            "ecr:DescribeRepositories",
                                            "ecr:BatchCheckLayerAvailability",
                                            "ecr:GetLifecyclePolicy",
                                            "ecr:DescribeImageScanFindings",
                                            "ecr:GetLifecyclePolicyPreview",
                                            "ecr:GetDownloadUrlForLayer",
                                            "ecr:BatchGetImage",
                                            "ecr:DescribeImages",
                                            "ecr:GetRepositoryPolicy"
                                          ],
                                        resources=[f"arn:aws:ecr:{REGION_NAME}:{ACCOUNT_ID}:repository/{MODEL_REPOSITORY_NAME}"]                              
                                    )]
                                )
        
        s3_policy = aws_iam.Policy(self, "sm-deploy-policy-s3",
                                    statements=[aws_iam.PolicyStatement(
                                        effect=aws_iam.Effect.ALLOW,
                                        actions=[
                                            "s3:ListBucket",
                                            "s3:GetObject",
                                            "s3:ListBucket",
                                            "s3:ListBucketVersions",
                                            "s3:GetBucketPolicy",
                                            "s3:GetBucketAcl",
                                          ],
                                        resources=[f"arn:aws:s3:::{MODEL_BUCKET_NAME}/*"]
                                    )]
                                )
                                
        sagemaker_role.attach_inline_policy(logs_policy)
        sagemaker_role.attach_inline_policy(ecr_policy)
        sagemaker_role.attach_inline_policy(s3_policy)    

        endpoint = SageMakerEndpointConstruct(self, f"{MODEL_NAME}",
                                    project_prefix = f"{PROJECT_NAME}",
                                    
                                    role_arn= sagemaker_role.role_arn,

                                    model_name = f"{MODEL_NAME}",
                                    model_repository_image = f"{MODEL_REPOSITORY_URI}:{MODEL_REPOSITORY_IMAGE_TAG}",

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
        
        endpoint.node.add_dependency(logs_policy)
        endpoint.node.add_dependency(ecr_policy)

        CfnOutput(scope=self,
            id="sagemaker_endpoint_name", 
            value=endpoint.endpoint_name, 
            export_name="var-sagemakerendpointname"
            )


       




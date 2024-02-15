from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_s3 as s3,
    aws_codebuild as cb,
    aws_iam as iam,
    aws_lambda as lambda_,
    custom_resources as cr,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_ecr as ecr,
    aws_s3_assets as s3_assets,
    aws_sagemaker as sagemaker,
    CustomResource, Duration, RemovalPolicy, Stack, CfnOutput
)

from constructs import Construct

import json
import os

class LlamaCppStack(Stack):
    def __init__(self, scope: Construct, construct_id: str,
            project_name: str, 
            model_bucket_key_full_name: str,
            model_hugging_face_name: str,
            image_tag: str,
            image_platform: str,
            model_name: str,
            model_instance_type: str,
            **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        #============================ 
        #       model_download
        #============================ 
        bucket = s3.Bucket(
            self, 
            f"{project_name}-bucket",
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            server_access_logs_prefix="logs/",
            enforce_ssl=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            auto_delete_objects=True
        )

        model_download_build_project = cb.Project(
            self,
            f"{project_name}-model-download",
            build_spec=cb.BuildSpec.from_asset(os.path.join(os.path.abspath(os.curdir), "cb_buildspec/model_download_buildspec.yaml")),
            environment=cb.BuildEnvironment(
                privileged=True,
                build_image=cb.LinuxBuildImage.STANDARD_6_0
            ),
            environment_variables={
                "CDK_DEPLOY_ACCOUNT": cb.BuildEnvironmentVariable(value=self.account),
                "CDK_DEPLOY_REGION": cb.BuildEnvironmentVariable(value=self.region),
                "MODEL_BUCKET_NAME": cb.BuildEnvironmentVariable(value=bucket.bucket_name),
                "MODEL_BUCKET_KEY_FULL_NAME": cb.BuildEnvironmentVariable(value=model_bucket_key_full_name),
                "MODEL_HUGGING_FACE_NAME": cb.BuildEnvironmentVariable(value=model_hugging_face_name),
                "TAG": cb.BuildEnvironmentVariable(value='cdk')
            },
            description='Download Large Language Model files to object store',
            timeout=Duration.minutes(60),
        )
        
        bucket.grant_read_write(model_download_build_project)

        sfn_model_download_task = tasks.CodeBuildStartBuild(
            self,
            f"{project_name}-start-model-download",
            project=model_download_build_project,
            integration_pattern=sfn.IntegrationPattern.RUN_JOB
        )


        #============================ 
        #       model_build
        #============================
        model_image_repo = ecr.Repository(
            self, 
            f"{project_name}-model-image-repo",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_images=True
        )

        model_asset_bucket = s3_assets.Asset(
            self, 
            f"{project_name}-model-build-docker-assets",
            path = os.path.join(os.path.abspath(os.curdir), "docker"),
        )

        model_build_cb_project = cb.Project(
            self, 
            f"{project_name}-model-build",
            source=cb.Source.s3(
                bucket=model_asset_bucket.bucket,
                path=model_asset_bucket.s3_object_key
            ),
            build_spec=cb.BuildSpec.from_asset(os.path.join(os.path.abspath(os.curdir), "cb_buildspec/model_build_docker_buildspec.yaml")),
            environment=cb.BuildEnvironment(
                privileged=True,
                build_image=cb.LinuxBuildImage.STANDARD_6_0,
                compute_type=cb.ComputeType.X2_LARGE # to decrease wait time
            ),
            environment_variables={
                "CDK_DEPLOY_ACCOUNT": cb.BuildEnvironmentVariable(value=self.account),
                "CDK_DEPLOY_REGION": cb.BuildEnvironmentVariable(value=self.region),
                "REPOSITORY_NAME": cb.BuildEnvironmentVariable(value=model_image_repo.repository_name),
                "PLATFORM": cb.BuildEnvironmentVariable(value=image_platform),
                "IMAGE_TAG": cb.BuildEnvironmentVariable(value=image_tag),
                "ECR": cb.BuildEnvironmentVariable(value=model_image_repo.repository_uri),
                "TAG": cb.BuildEnvironmentVariable(value='cdk')
            },
            description='Project to build and push images to container registry',
            timeout=Duration.minutes(60),
        )
        model_image_repo.grant_pull_push(model_build_cb_project)

        sfn_model_build_task = tasks.CodeBuildStartBuild(
            self,
            f"{project_name}-start-model-docker-build",
            project=model_build_cb_project,
            integration_pattern=sfn.IntegrationPattern.RUN_JOB
        )

        #==========================================
        #       model_download_build_deployment
        #==========================================
        # llama-cpp-sm
        chain = sfn_model_download_task.next(
            sfn_model_build_task
        )

        state_machine = sfn.StateMachine(
            self,
            f"{project_name}-llama-cpp-statemachine",
            definition_body=sfn.DefinitionBody.from_chainable(chain)
        )

        trigger_lambda = lambda_.Function(
            self,
            f"{project_name}-trigger-llama-cpp-sm",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="trigger_build.lambda_handler",
            code=lambda_.Code.from_asset(os.path.join(os.path.abspath(os.curdir), "lambda/trigger_build")),
            environment={
                "STATE_MACHINE_ARN": state_machine.state_machine_arn
            }
        )

        trigger_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["states:StartExecution","states:ListExecutions"],
            resources=[state_machine.state_machine_arn]
        ))

        cr_provider = cr.Provider(
            self,
            f"{project_name}-trigger-resource-provider",
            on_event_handler=trigger_lambda,
            is_complete_handler=trigger_lambda,
            query_interval=Duration.seconds(30)
        )

        trigger_resource_cr = CustomResource(
            self,
            f"{project_name}-trigger-resource",
            service_token=cr_provider.service_token
        )

        #============================ 
        #       model_serve
        #============================
        model_execution_role = iam.Role(
            self,
            f"{project_name}-model-execution-role",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            inline_policies={
                "ResourcePolicy": iam.PolicyDocument(statements=[
                    iam.PolicyStatement(
                        actions=[
                            "cloudwatch:PutMetricData",
                            "logs:CreateLogStream",
                            "logs:PutLogEvents",
                            "logs:CreateLogGroup",
                            "logs:DescribeLogStreams",
                            "ecr:GetAuthorizationToken"
                        ],
                        resources=[
                            f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/sagemaker/Endpoints/{project_name}-{model_name}-Endpoint:*"
                        ]
                    ),
                    iam.PolicyStatement(
                        actions=[
                            "ecr:GetAuthorizationToken"
                        ],
                        resources=["*"]             
                    ),
                    iam.PolicyStatement(
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
                        resources=[model_image_repo.repository_arn]
                    ),
                    iam.PolicyStatement(
                        actions=[
                            "s3:ListBucket",
                            "s3:GetObject",
                            "s3:ListBucket",
                            "s3:ListBucketVersions",
                            "s3:GetBucketPolicy",
                            "s3:GetBucketAcl",
                        ],
                        resources=[bucket.bucket_arn]
                    )
                ])
            }
        )

        model = sagemaker.CfnModel(
            self,
            f"{model_name}-Model",
            execution_role_arn=model_execution_role.role_arn,
            containers=[
                sagemaker.CfnModel.ContainerDefinitionProperty(
                    image=f"{model_image_repo.repository_uri}:{image_tag}",
                    environment={
                        "MMS_MAX_RESPONSE_SIZE": "20000000",
                        "SAGEMAKER_CONTAINER_LOG_LEVEL": "20",
                        "SAGEMAKER_PROGRAM": "inference.py",
                        "SAGEMAKER_REGION": f"{self.region}",
                        "SAGEMAKER_SUBMIT_DIRECTORY": "/opt/ml/model/code"            
                    }
                )
            ],
            model_name=f"{project_name}-{model_name}-Model"
        )
        model.node.add_dependency(trigger_resource_cr)
        
        model_config = sagemaker.CfnEndpointConfig(
            self,
            f"{project_name}-{model_name}-Config",
            endpoint_config_name=f"{project_name}-{model_name}-Config",
            production_variants=[
                sagemaker.CfnEndpointConfig.ProductionVariantProperty(
                    model_name=model.attr_model_name,
                    variant_name="AllTraffic",
                    initial_instance_count=1,
                    initial_variant_weight=1,
                    instance_type=model_instance_type
                )
            ]
        )

        model_endpoint = sagemaker.CfnEndpoint(
            self,
            f"{project_name}-{model_name}-Endpoint",
            endpoint_name=f"{project_name}-{model_name}-Endpoint",
            endpoint_config_name=model_config.attr_endpoint_config_name
        )

        CfnOutput(
            self,
            f"{project_name}-{model_name}-endpoint", 
            value=model_endpoint.endpoint_name
        )

        #============================ 
        #       model_configure
        #============================
        sagemaker_endpoint_configure_lambda = lambda_.Function(
            self,
            f"{project_name}-configure-sagemaker-endpoint-function",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="configure_endpoint.lambda_handler",
            code=lambda_.Code.from_asset(os.path.join(os.path.abspath(os.curdir), "lambda/configure_endpoint")),
            environment={
                "SAGEMAKER_ENDPOINT_NAME": model_endpoint.attr_endpoint_name,
                "MODEL_BUCKET_NAME": bucket.bucket_name,
                "MODEL_BUCKET_KEY_NAME": model_bucket_key_full_name
            }
        )
        sagemaker_endpoint_configure_lambda.node.add_dependency(model_endpoint)

        sagemaker_endpoint_configure_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["sagemaker:InvokeEndpoint"],
            resources=["*"]
        ))

        config_endpoint_cr_provider = cr.Provider(
            self,
            f"{project_name}-configure-sagemaker-endpoint-provider",
            on_event_handler=sagemaker_endpoint_configure_lambda,
        )

        CustomResource(
            self,
            f"{project_name}-configure-sagemaker-endpoint-cr",
            service_token=config_endpoint_cr_provider.service_token
        )
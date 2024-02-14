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
    CustomResource, Duration, RemovalPolicy, Stack,
)

from constructs import Construct

import os

class LlamaCppStack(Stack):
    def __init__(self, scope: Construct, construct_id: str,
            project_name: str, 
            model_bucket_prefix:str, 
            model_bucket_key_full_name: str,
            model_hugging_face_name: str,
            image_repo_name: str,
            image_tag: str,
            image_platform: str,
            **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # params


        # model_download
        bucket = s3.Bucket(self, f"ModelBucket{model_bucket_prefix}",
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
            "start model download build",
            project=model_download_build_project,
            integration_pattern=sfn.IntegrationPattern.RUN_JOB
        )


        # model_build
        model_image_repo = ecr.Repository(
            self, 
            "model-image-repo",
            repository_name=f"{image_repo_name}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_images=True
        )

        model_asset_bucket = s3_assets.Asset(self, "DockerAssets",
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
                "REPOSITORY_NAME": cb.BuildEnvironmentVariable(value=f"{image_repo_name}"),
                "PLATFORM": cb.BuildEnvironmentVariable(value=f"{image_platform}"),
                "IMAGE_TAG": cb.BuildEnvironmentVariable(value=f"{image_tag}"),
                "ECR": cb.BuildEnvironmentVariable(value=model_image_repo.repository_uri),
                "TAG": cb.BuildEnvironmentVariable(value='cdk')
            },
            description='Project to build and push images to container registry',
            timeout=Duration.minutes(60),
        )
        model_image_repo.grant_pull_push(model_build_cb_project)

        sfn_model_build_task = tasks.CodeBuildStartBuild(
            self,
            "start model docker image build",
            project=model_build_cb_project,
            integration_pattern=sfn.IntegrationPattern.RUN_JOB
        )

        # llama-cpp-sm
        chain = sfn_model_download_task.next(
            sfn_model_build_task
        )

        state_machine = sfn.StateMachine(
            self,
            "llama-cpp-sm",
            definition_body=sfn.DefinitionBody.from_chainable(chain)
        )

        ### final trigger
        trigger_lambda = lambda_.Function(
            self,
            "trigger-llama-cpp-sm",
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
            "trigger_resource_provider",
            on_event_handler=trigger_lambda,
            is_complete_handler=trigger_lambda,
            query_interval=Duration.seconds(30)
        )
        CustomResource(
            self,
            "trigger_resource",
            service_token=cr_provider.service_token
        )
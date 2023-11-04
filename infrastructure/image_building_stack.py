from aws_cdk import (
    aws_ecr,
    aws_ssm,
    aws_s3,
    aws_s3_deployment,
    aws_codebuild,
    aws_codepipeline,
    aws_codepipeline_actions,
    App, Aws, CfnOutput, Duration, RemovalPolicy, Stack
)
import os
from constructs import Construct
import shutil

class ImageBuildingStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, env, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        PROJECT_NAME = "llm-cpu"
        REPOSITORY_NAME = "llm-cpu-repository"
        IMAGE_BUCKET_NAME = "llm-cpu-bucket"

        ROOT_DIR = os.path.abspath(os.curdir)

        # define the s3 artifact
        source_output = aws_codepipeline.Artifact(artifact_name='source')

        # pipeline requires versioned bucket
        bucket = aws_s3.Bucket(
            self, "SourceBucket",
            bucket_name=f"{IMAGE_BUCKET_NAME}",
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY)

        shutil.make_archive("docker", "zip", os.path.join(ROOT_DIR, "docker"))
        shutil.copy(os.path.join(ROOT_DIR, "docker.zip"), os.path.join(ROOT_DIR, "docker", "docker.zip"))

        s3_bucket_deployment = aws_s3_deployment.BucketDeployment(self, "DockerFiles",
            sources=[aws_s3_deployment.Source.asset(os.path.join(ROOT_DIR, "docker"))],
            destination_bucket=bucket
        )

        # # ssm parameter to get bucket name later
        # bucket_param = aws_ssm.StringParameter(
        #     self, "ParameterB",
        #     parameter_name=f"{IMAGE_BUCKET_NAME}",
        #     string_value=bucket.bucket_name,
        #     description='cdk pipeline bucket')

        # ecr repo to push docker container into
        ecr = aws_ecr.Repository(
            self, "ECR",
            repository_name=f"{REPOSITORY_NAME}",
            removal_policy=RemovalPolicy.DESTROY
        )

        standard_image = aws_codebuild.LinuxBuildImage.STANDARD_6_0

        # codebuild project meant to run in pipeline
        codebuild_docker_project = aws_codebuild.PipelineProject(
            self, "DockerBuild",
            project_name=f"{PROJECT_NAME}-Docker-Build",
            build_spec=aws_codebuild.BuildSpec.from_source_filename(
                filename='docker_build_buildspec.yml'),
            environment=aws_codebuild.BuildEnvironment(
                privileged=True,
                build_image=standard_image
            ),
            # pass the ecr repo uri into the codebuild project so codebuild knows where to push
            environment_variables={
                "CDK_DEPLOY_ACCOUNT": aws_codebuild.BuildEnvironmentVariable(value=os.getenv('CDK_DEPLOY_ACCOUNT') or ""),
                "CDK_DEPLOY_REGION": aws_codebuild.BuildEnvironmentVariable(value=os.getenv('CDK_DEPLOY_REGION') or ""),
                "REPOSITORY_NAME": aws_codebuild.BuildEnvironmentVariable(value=f"{REPOSITORY_NAME}"),
                "ECR": aws_codebuild.BuildEnvironmentVariable(
                    value=ecr.repository_uri),
                "TAG": aws_codebuild.BuildEnvironmentVariable(
                    value='cdk')
            },
            description='Pipeline to build and push images to ECR',
            timeout=Duration.minutes(60),
        )
        # codebuild iam permissions to read write s3
        bucket.grant_read_write(codebuild_docker_project)

        # codebuild permissions to interact with ecr
        ecr.grant_pull_push(codebuild_docker_project)

        pipeline = aws_codepipeline.Pipeline(
            self, "Pipeline",
            pipeline_name=f"{PROJECT_NAME}",
            artifact_bucket=bucket,
            stages=[
                aws_codepipeline.StageProps(
                    stage_name='Source',
                    actions=[
                         aws_codepipeline_actions.S3SourceAction(
                            bucket=bucket,
                            bucket_key='docker.zip',
                            action_name='DockerfileSource',
                            run_order=1,
                            output=source_output,
                            trigger=aws_codepipeline_actions.S3Trigger.POLL
                        ),
                    ]
                ),
                aws_codepipeline.StageProps(
                    stage_name='Build',
                    actions=[
                        aws_codepipeline_actions.CodeBuildAction(
                            action_name='DockerBuildImages',
                            input=source_output,
                            project=codebuild_docker_project,
                            run_order=1,
                        )
                    ]
                )
            ]
        )

from aws_cdk import (
    aws_ecr,
    aws_ssm,
    aws_s3,
    aws_s3_deployment,
    aws_s3_assets,
    aws_codebuild,
    aws_codepipeline,
    aws_codepipeline_actions,
    App, Aws, CfnOutput, Duration, RemovalPolicy, Stack, CustomResource
)
import os
from constructs import Construct

class ImageBuildingStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, 
        project_name: str, 
        repository_name: str, 
        model_bucket_name: str, 
        **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        PROJECT_NAME = project_name
        REPOSITORY_NAME = repository_name
        MODEL_BUCKET_NAME = model_bucket_name
        ROOT_DIR = os.path.abspath(os.curdir)

        asset_bucket = aws_s3_assets.Asset(self, "DockerAssets",
            path = os.path.join(ROOT_DIR, "docker"),
        )

        # ecr repo to push docker container into
        ecr = aws_ecr.Repository(
            self, "ECR",
            repository_name=f"{REPOSITORY_NAME}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_images=True
        )

        standard_image = aws_codebuild.LinuxBuildImage.STANDARD_6_0
        compute_type = aws_codebuild.ComputeType.X2_LARGE # to decrease wait time

        # codebuild project meant to run in pipeline
        codebuild_project = aws_codebuild.PipelineProject(
            self, "PipelineProject",
            project_name=f"{PROJECT_NAME}-image-building-pipeline",
            build_spec=aws_codebuild.BuildSpec.from_source_filename(
                filename='docker_build_buildspec.yml'),
            environment=aws_codebuild.BuildEnvironment(
                privileged=True,
                build_image=standard_image,
                compute_type=compute_type
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
            description='Pipeline to build and push images to container registry',
            timeout=Duration.minutes(60),
        )

        # codebuild permissions to interact with ecr
        ecr.grant_pull_push(codebuild_project)

        source_output = aws_codepipeline.Artifact(artifact_name='source')

        pipeline = aws_codepipeline.Pipeline(
            self, "Pipeline",
            pipeline_name=f"{PROJECT_NAME}-image-building-pipeline",
            artifact_bucket=asset_bucket.bucket,
            stages=[
                aws_codepipeline.StageProps(
                    stage_name='Source',
                    actions=[
                         aws_codepipeline_actions.S3SourceAction(
                            bucket=asset_bucket.bucket,
                            bucket_key=asset_bucket.s3_object_key,
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
                            project=codebuild_project,
                            run_order=2,
                        )
                    ]
                )
            ]
        )

        CfnOutput(scope=self,
            id="image_repository_uri", 
            value=ecr.repository_uri, 
            export_name="var-modelrepositoryuri"
            )



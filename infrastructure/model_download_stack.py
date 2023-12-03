from aws_cdk import (
    Stack,
    RemovalPolicy,
    CfnOutput,
    aws_iam,
    aws_ssm,
    aws_s3,
    aws_s3_deployment,
    aws_s3_assets,
    aws_codebuild,
    aws_codepipeline,
    aws_codepipeline_actions,
    aws_events_targets,
    aws_stepfunctions,
    aws_stepfunctions_tasks,
    aws_codepipeline, 
    aws_codepipeline_actions,
    CfnOutput, Duration, RemovalPolicy, Stack,
)

from constructs import Construct

import os

class ModelDownloadStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, 
            project_name: str, 
            model_bucket_prefix:str, 
            model_bucket_key_full_name: str,
            model_hugging_face_name: str,
            **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ROOT_DIR = os.path.abspath(os.curdir)
        PROJECT_NAME = project_name
        MODEL_BUCKET_NAME = model_bucket_prefix
        MODEL_BUCKET_KEY_FULL_NAME = model_bucket_key_full_name
        MODEL_HUGGING_FACE_NAME = model_hugging_face_name

        # create bucket for model
        bucket = aws_s3.Bucket(self, f"{MODEL_BUCKET_NAME}",
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        asset_bucket = aws_s3_assets.Asset(self, f"ModelAssets{MODEL_BUCKET_KEY_FULL_NAME.split('.')[0]}",
            path = os.path.join(ROOT_DIR, "model"),
        )

        standard_image = aws_codebuild.LinuxBuildImage.STANDARD_6_0

        codebuild_project = aws_codebuild.PipelineProject(self, f"{PROJECT_NAME}-model-download",
            build_spec=aws_codebuild.BuildSpec.from_source_filename(
                filename='model_build_buildspec.yml'),
            environment=aws_codebuild.BuildEnvironment(
                privileged=True,
                build_image=standard_image
            ),
            environment_variables={
                "CDK_DEPLOY_ACCOUNT": aws_codebuild.BuildEnvironmentVariable(value=os.getenv('CDK_DEPLOY_ACCOUNT') or ""),
                "CDK_DEPLOY_REGION": aws_codebuild.BuildEnvironmentVariable(value=os.getenv('CDK_DEPLOY_REGION') or ""),
                "MODEL_BUCKET_NAME": aws_codebuild.BuildEnvironmentVariable(value=f"{bucket.bucket_name}"),
                "MODEL_BUCKET_KEY_FULL_NAME": aws_codebuild.BuildEnvironmentVariable(value=f"{MODEL_BUCKET_KEY_FULL_NAME}"),
                "MODEL_HUGGING_FACE_NAME": aws_codebuild.BuildEnvironmentVariable(value=f"{MODEL_HUGGING_FACE_NAME}"),
                "TAG": aws_codebuild.BuildEnvironmentVariable(
                    value='cdk')
            },
            description='Download Large Language Model files to object store',
            timeout=Duration.minutes(60),
        )
        
        bucket.grant_read_write(codebuild_project)
        asset_bucket.grant_read(codebuild_project)

        source_output = aws_codepipeline.Artifact(artifact_name="source")

        source_action = aws_codepipeline_actions.S3SourceAction(
                        bucket=asset_bucket.bucket,
                        bucket_key=asset_bucket.s3_object_key,
                        action_name='ModelBuildSource',
                        run_order=1,
                        output=source_output,                    
                        )

        build_action = aws_codepipeline_actions.CodeBuildAction(
                        action_name='ModelFileDownload',
                        input=source_output, 
                        project=codebuild_project,
                        run_order=2,
                        )

        aws_codepipeline.Pipeline(self, "Pipeline",
            pipeline_name=f"{PROJECT_NAME}-model-download-pipeline",
            artifact_bucket=asset_bucket.bucket,
            stages=[aws_codepipeline.StageProps(
                stage_name="Source",
                actions=[source_action]
            ), aws_codepipeline.StageProps(
                stage_name="Build",
                actions=[build_action]
            )
            ]
        )

        CfnOutput(scope=self,
            id="model_bucket_name", 
            value=bucket.bucket_name, 
            export_name="var-modelbucketname"
            )

        CfnOutput(scope=self,
            id="model_name", 
            value=MODEL_BUCKET_KEY_FULL_NAME, 
            export_name="var-modelname"
            )

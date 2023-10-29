from aws_cdk import (
    Stack,
    aws_ecr_assets,
    aws_ecr,
    aws_ecr
)
import os
from constructs import Construct

class ImageBuildingStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, env, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ROOT_DIR = os.path.abspath(os.curdir)

        asset = aws_ecr_assets.DockerImageAsset(self, "llm-cpu-arm64-full-v00",
            directory=os.path.join(ROOT_DIR, "docker-ant312"),
            platform=aws_ecr_assets.Platform.LINUX_ARM64
            #cache_from=[aws_ecr_asset.DockerCacheOption(type="registry", params={"ref": "ghcr.io/myorg/myimage:cache"})],
            #cache_to=aws_ecr_assets.DockerCacheOption(type="registry", params={"ref": "ghcr.io/myorg/myimage:cache", "mode": "max", "compression": "zstd"})
        )

        repository = aws_ecr.Repository(self, "llm-cpu-repository")

        # # Copy from cdk docker image asset to another ECR.
        # ecrdeploy.ECRDeployment(self, "DeployDockerImage1",
        #     src=ecrdeploy.DockerImageName(asset.image_uri),
        #     dest=ecrdeploy.DockerImageName(f"{cdk.Aws.ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/my-nginx:latest")
        # )


        source_artifact = codepipeline.Artifact(os.path.join(ROOT_DIR, "docker-ant312/build-push-image.sh"))

        pipeline = pipelines.CodePipeline(self, "Pipeline",
            code_pipeline=code_pipeline,
            synth=pipelines.ShellStep("Synth",
                input=pipelines.CodePipelineFileSet.from_artifact(source_artifact),
                commands=["./build-push-image.sh"]
            )
        )


                



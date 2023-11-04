#!/bin/bash

COMMIT_HASH="latest" #"v29.10.1"
IMAGE_NAME="llama-cpp-image"

if [[ $# -ge 3 ]]; then
    export CDK_DEPLOY_ACCOUNT=$1
    export CDK_DEPLOY_REGION=$2
    export REPOSITORY_NAME=$3

    export DOCKER_BUILDKIT=1
    export DOCKER_CLI_EXPERIMENTAL=enabled

    shift; shift
    echo ==--------ECRLogin---------==
    aws ecr get-login-password --region "${CDK_DEPLOY_REGION}" | docker login --username AWS --password-stdin "${CDK_DEPLOY_ACCOUNT}.dkr.ecr.${CDK_DEPLOY_REGION}.amazonaws.com"
    
    echo ==--------ECRBuild---------==    
    docker buildx build --platform linux/arm64 -t "${IMAGE_NAME}:${COMMIT_HASH:=latest}" .
    
    echo ==--------ECRTag---------== 
    docker tag "${IMAGE_NAME}:${COMMIT_HASH:=latest}" "${CDK_DEPLOY_ACCOUNT}.dkr.ecr.${CDK_DEPLOY_REGION}.amazonaws.com/${REPOSITORY_NAME}:${COMMIT_HASH:=latest}"
    exit $?
else
    echo 1>&2 "Provide account and region as first two args."
    echo 1>&2 "Additional args are passed through to cdk deploy."
    exit 1
fi

# --no-cache
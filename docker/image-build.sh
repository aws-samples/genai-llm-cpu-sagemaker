#!/bin/bash

#COMMIT_HASH="latest" #"v29.10.1"
IMAGE_NAME="llama-cpp-image"

if [[ $# -ge 4 ]]; then
    export CDK_DEPLOY_ACCOUNT=$1
    export CDK_DEPLOY_REGION=$2
    export REPOSITORY_NAME=$3
    export IMAGE_TAG=$4
    export PLATFORM=$5

    export DOCKER_BUILDKIT=1
    export DOCKER_CLI_EXPERIMENTAL=enabled

    export PLATFORM_PARAMETER_VALUE="linux/arm64"
    export DOCKER_FILE_NAME="dockerfile"

    if [[ $PLATFORM == *"arm"* ]]
    then
        PLATFORM_PARAMETER_VALUE="linux/arm64"
        DOCKER_FILE_NAME="dockerfile"
        echo "[INFO] Building an image for ARM platform"
    elif [[ $PLATFORM == *"amd"* ]]
    then
        PLATFORM_PARAMETER_VALUE="linux/amd64"
        DOCKER_FILE_NAME="dockerfile-amd"
        echo "[INFO] Building an image for AMD platform"
    else
        echo "[ERROR] Platform {$PLATFORM} not supported."
        exit 0
    fi

    shift; shift
    echo ==--------ECRLogin---------==
    aws ecr get-login-password --region "${CDK_DEPLOY_REGION}" | docker login --username AWS --password-stdin "${CDK_DEPLOY_ACCOUNT}.dkr.ecr.${CDK_DEPLOY_REGION}.amazonaws.com"
    
    echo ==--------ECRBuild---------==    
    docker buildx build --platform "${PLATFORM_PARAMETER_VALUE}" -t "${IMAGE_NAME}:${IMAGE_TAG}" -f "${DOCKER_FILE_NAME}" .
    
    echo ==--------ECRTag---------== 
    docker tag "${IMAGE_NAME}:${IMAGE_TAG}" "${CDK_DEPLOY_ACCOUNT}.dkr.ecr.${CDK_DEPLOY_REGION}.amazonaws.com/${REPOSITORY_NAME}:${IMAGE_TAG}"
    exit $?
else
    echo 1>&2 "Provide account and region as first two args..."
    echo 1>&2 "followed by repositopry name, image tag and platform."
    exit 1
fi
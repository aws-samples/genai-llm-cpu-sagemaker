#!/bin/bash

COMMIT_HASH="latest"

if [[ $# -ge 3 ]]; then
    export CDK_DEPLOY_ACCOUNT=$1
    export CDK_DEPLOY_REGION=$2
    export REPOSITORY_NAME=$3
    shift; shift
    
    echo ==--------ECRPush---------==
    docker push "${CDK_DEPLOY_ACCOUNT}.dkr.ecr.${CDK_DEPLOY_REGION}.amazonaws.com/${REPOSITORY_NAME}:${COMMIT_HASH:=latest}"
    exit $?
else
    echo 1>&2 "Provide account and region as first two args."
    echo 1>&2 "Additional args are passed through to cdk deploy."
    exit 1
fi



# --no-cache

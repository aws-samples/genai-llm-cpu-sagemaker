#/bin/sh

# CDK_DEPLOY_ACCOUNT=859155805248
# CDK_DEPLOY_REGION=us-east-1
COMMIT_HASH="latest" #"v29.10.1"
IMAGE_NAME="llama-cpp-arm64"
REPOSITORY_NAME="llama-cpp"

if [[ $# -ge 2 ]]; then
    export CDK_DEPLOY_ACCOUNT=$1
    export CDK_DEPLOY_REGION=$2
    shift; shift
    echo ==--------ECRLogin---------==
    aws ecr get-login-password --region us-east-1 | finch login --username AWS --password-stdin "${CDK_DEPLOY_ACCOUNT}.dkr.ecr.${CDK_DEPLOY_REGION}.amazonaws.com"
    echo ==--------ECRPush---------==
    finch push "${CDK_DEPLOY_ACCOUNT}.dkr.ecr.${CDK_DEPLOY_REGION}.amazonaws.com/${REPOSITORY_NAME}:${COMMIT_HASH:=latest}" "$@"
   exit $?
else
    echo 1>&2 "Provide account and region as first two args."
    echo 1>&2 "Additional args are passed through to cdk deploy."
    exit 1
fi



# --no-cache

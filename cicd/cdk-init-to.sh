#!/usr/bin/env bash

if [[ $# -ge 2 ]]; then
    export CDK_DEPLOY_ACCOUNT=$1
    export CDK_DEPLOY_REGION=$2
    shift; shift
    
    echo ==--------CheckDedendencies---------==
    aws --version
    cdk --version
    jq --version
    npx cdk init app --language python "$@"

    echo ==--------InstallCDKDependencies---------==
    npx source .venv/bin/activate
    npx python -m pip install -r requirements.txt

    echo ==--------BootstrapCDKEnvironment---------==
    npx cdk bootstrap
    exit $?
else
    echo 1>&2 "Provide account and region as first two args."
    echo 1>&2 "Additional args are passed through to cdk deploy."
    exit 1
fi



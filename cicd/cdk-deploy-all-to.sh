# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

#!/usr/bin/env bash

sleepwithcountdown() {
  secs=$1
  while [ $secs -gt 0 ]; do
    printf "\rcountdown: $secs\033[0K"
    sleep 1
    : $((secs--))
  done
  printf "\n"
}

if [[ $# -ge 2 ]]; then
    export CDK_DEPLOY_ACCOUNT=$1
    export CDK_DEPLOY_REGION=$2
    shift; shift
    source .venv/bin/activate
    cdk deploy ModelDownloadStack "$@" --require-approval never 
    cdk deploy ImageBuildingStack "$@" --require-approval never 
    echo "[INFO] Wait for an image to be built and pushed to ECR..."
    sleepwithcountdown 180
    cdk deploy ModelServingStack "$@" --require-approval never 
    echo "[INFO] Wait for SageMaker model to be InService..."
    sleepwithcountdown 5
    cdk deploy ModelConfigurationStack "$@" --require-approval never
    exit $?
else
    echo 1>&2 "[ERROR] Provide account and region as first two args."
    echo 1>&2 "[ERROR] Additional args are passed through to cdk deploy."
    exit 1
fi




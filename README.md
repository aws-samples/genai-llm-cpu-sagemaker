# Large Language Models (LLMs) on CPU as SageMaker Endpoints

This code demonstrates how you can run Large Language Models (LLMs) on CPU-only instances including Graviton. We are using [Llama.cpp project](https://github.com/ggerganov/llama.cpp) and exposing an Sagemaker endpoint API for inference. Models are downloaded from [Hugging Face model hub](https://huggingface.co/models).
The project can be deployed to be compatible to both ARM64 and x86 architectures. 

## Project overview

This project is built by using [AWS Cloud Development Kit](https://aws.amazon.com/cdk/)(AWS CDK)  with Python.
The `cdk.json` file tells the CDK Toolkit how to execute your app.

AWS CDK app configuration file values are in `app-config.ini`.

The project consists of the following stacks in `./infrastructure` directory:
* ModelDownloadStack       - downloads model files to an object store, it creates AWS CodePipeline and Simple Storage Service (S3) bucket
* ImageBuildingStack       - creates an image used foe inference and pushes it to container registry, creates AWS CodePipeline and Elastic Container Registry (ECR)
* ModelServingStack        - deploys a model for inference and configures endpoint, creates SageMaker Endpoint and underlying Elastic Compute Cloud (EC2) instance
* ModelConfigurationStack  - configures inference endpoint, invokes /configure API on SageMaker Endpoint

### Prerequisites

Before proceeding any further, you need to identify and designate an AWS account required for the solution to work. You also need to create an AWS account profile in ~/.aws/credentials for the designated AWS account, if you don’t already have one. The profile needs to have sufficient permissions to run an [AWS Cloud Development Kit](https://aws.amazon.com/cdk/) (AWS CDK) stack. We recommend removing the profile when you’re finished with the testing. For more information about creating an AWS account profile, see [Configuring the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html).

### Deploy

To deploy all stacks:
`./cicd/cdk-deploy-all-to.sh <account-id> <region-name>` 

An example:
`./cicd/cdk-deploy-all-to.sh 012345678901 us-east-1` 

To deploy one stack:
`./cicd/cdk-deploy-stack-to.sh <account-id> <region-name> ModelDownloadStack` 

## Project clean-up

Use destroy script to remove stacks and approve destroying stacks:
`./cicd/cdk-undeploy-from.sh <account-id> <region-name> --all` 

Or use destroy script to remove single stack and approve destroying a stack:
`./cicd/cdk-undeploy-from.sh <account-id> <region-name> ModelServingStack` 

## Model Selection

1. Navigate to https://huggingface.co/TheBloke and choose GGUF model of your choice for example https://huggingface.co/TheBloke/llama-2-7B-Arguments-GGUF, scroll to provided files. Usually Q4_K_M is good enough compromise (based on our testing but feel free to try yourself).

2. Update values of the variables in `app-config.ini` to use a new model:
* model_hugging_face_name - set Hugging Face model name e.g. "TheBloke/llama-2-7B-Arguments-GGUF"
* model_full_name         - set Hugging Face file full name e.g. "llama-2-7b-chat.Q4_K_M.gguf"

3. Re-run ModelDownload stack to download new model to S3 bucket:
`./cicd/cdk-deploy-stack-to.sh <account-id> <region-name> ModelDownloadStack` 

4. Deploy and configure new SageMaker Endpoint:
`./cicd/cdk-deploy-stack-to.sh <account-id> <region-name> ModelServingStack` 
`./cicd/cdk-deploy-stack-to.sh <account-id> <region-name> ModelConfigurationStack` 

### Credits

Built based on Sean Bradley's project that was modified to work with SageMaker endpoints.

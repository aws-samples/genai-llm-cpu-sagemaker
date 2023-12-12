# Large Language Models (LLMs) on CPU as SageMaker Endpoints

This code demonstrates how you can run Large Language Models (LLMs) on CPU-only instances including Graviton. We are using [Llama.cpp project](https://github.com/ggerganov/llama.cpp) and exposing an Sagemaker endpoint API for inference. Models are downloaded from [Hugging Face model hub](https://huggingface.co/models).
The project can be deployed to be compatible to both ARM64 and x86 architectures. 

## Project overview

This project is built by using [AWS Cloud Development Kit](https://aws.amazon.com/cdk/)(AWS CDK)  with Python.
The `cdk.json` file tells the CDK Toolkit how to execute your app.

AWS CDK app configuration file values are in `app-config.ini`:

| Parameter | Description | Example value | 
| :---    | :---    | :---    |
| project.project_name | Used as prefix for AWS resources created with this app | cpu-llm |
| model.model_bucket_prefix | Prefix for S3 bucket containing model files | my-model-bucket |
| model.model_hugging_face_name | [HuggingFace](https://huggingface.co) model name | TheBloke/Llama-2-7b-Chat-GGUF |
| model.model_full_name | [HuggingFace](https://huggingface.co) model file full name | llama-2-7b-chat.Q4_K_M.gguf |
| image.image_repository_name | Named of ECR repository containing model image | my-model-image-repository |
| image.platform | Platfrom used to run inference and build an image; Values: ["ARM", "AMD"]  | ARM |
| image.image_tag | Tag used to tag the image; | "latest" |
| inference.sagemaker_role_name | SageMaker IAM role name | my-sagemaker-execution-role |
| inference.sagemaker_model_name | SageMaker endpoint name for model inference | "llama-2-7b-chat" |
| inference.instance_type | Instance type used for SageMaker Endpoint | "ml.c7g.2xlarge" for ARM platform or "ml.g5.xlarge" for AMD platform |


The project consists of the following stacks in `./infrastructure` directory:
* **ModelDownloadStack**      - downloads model files to an object store, it creates AWS CodePipeline and Simple Storage Service (S3) bucket
* **ImageBuildingStack**      - creates an image used for inference and pushes it to container registry, creates AWS CodePipeline and Elastic Container Registry (ECR)
* **ModelServingStack**       - deploys a model for inference and configures endpoint, creates SageMaker Endpoint and underlying Elastic Compute Cloud (EC2) instance
* **ModelConfigurationStack** - configures inference endpoint, invokes /configure API on SageMaker Endpoint

## Prerequisites

Before proceeding any further, you need to identify and designate an AWS account required for the solution to work. You also need to create an AWS account profile in ~/.aws/credentials for the designated AWS account, if you don’t already have one. The profile needs to have sufficient permissions to run an [AWS Cloud Development Kit](https://aws.amazon.com/cdk/) (AWS CDK) stack. We recommend removing the profile when you’re finished with the testing. For more information about creating an AWS account profile, see [Configuring the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html). Python 3.11.x or later has to be installed on a machine.
Note that this is not production ready code, and that it incures costs while provisioned, so please remember to destroy resources whe you no longer need them.

Use the following init script on MacOS and Linux or manually create and activate virtualenv: \
`./cicd/cdk-init-to.sh <account-id> <region-name>` 

To add additional dependencies, for example other CDK libraries, add them to your `setup.py` file and rerun the `pip install -r requirements.txt` command.

## CDDK deployment 
### To Create Resources / Deploy Stacks

To deploy all stacks you can use `cdk-deploy-all-to` script: \
`./cicd/cdk-deploy-all-to.sh <account-id> <region-name>` 

For example: \
`./cicd/cdk-deploy-all-to.sh 012345678901 us-east-1` 

To deploy a single stack you can use `cdk-deploy-stack-to` script with an additional stack name as a parameter: \
`./cicd/cdk-deploy-stack-to.sh <account-id> <region-name> ModelDownloadStack` 

To check application drift, and compare specified stack and its dependencies with the deployed stack, you can use `cdk-drift` script (with optional -v for verbose output): \
`./cicd/cdk-drift.sh <account-id> <region-name> -v` 

### To Destroy Resources / Clean-up

Use destroy script to remove all stacks: \
`./cicd/cdk-undeploy-from.sh <account-id> <region-name> --all` 

Or use destroy script to remove a single stack: \
`./cicd/cdk-undeploy-from.sh <account-id> <region-name> ModelServingStack` 

### Model Selection / Change

Only changing a model does not require rebuidling an image, and would take approximatelly 30% less time than redeploying the whole application. You can use the following process:

1. Navigate to https://huggingface.co/TheBloke and choose GGUF model of your choice for example https://huggingface.co/TheBloke/llama-2-7B-Arguments-GGUF, scroll to provided files. Usually Q4_K_M is good enough compromise (based on our testing but feel free to try yourself).

2. Update values of the variables in `app-config.ini` to use the new model:
    * model_hugging_face_name - set Hugging Face model name e.g. "TheBloke/llama-2-7B-Arguments-GGUF"
    * model_full_name         - set Hugging Face file full name e.g. "llama-2-7b-chat.Q4_K_M.gguf"

3. Run a script to destroy previously used model's S3 bucket, Sagemaker configuration and endpoint and re-create new model resources: \
`./cicd/cdk-change-model.sh <account-id> <region-name>` 
> You will be prompted with a question: `This action would destroy your current deployment. Are you sure that you want to proceed?`, type Y to confirm. 

### Platform Selection / Change

1. Update values of the variables in `app-config.ini` to use the different platform:
    * platform      - set platform (not case sensitive) e.g. "AMD"
    * instance_type - set instance type that matches platform e.g. "ml.g5.xlarge"
    * image_tag     - (optional) update image tag e.g. "amd-latest"

2. Destroy existing SageMaker endpoint
`./cicd/cdk-undeploy-from.sh <account-id> <region-name> ModelConfigurationStack`
`./cicd/cdk-undeploy-from.sh <account-id> <region-name> ModelServingStack` 

3. Build a new image and create new SageMaker endpoint
`./cicd/cdk-deploy-stack-to.sh <account-id> <region-name> ImageBuildingStack` 
`./cicd/cdk-deploy-stack-to.sh <account-id> <region-name> ModelServingStack, ModelConfigurationStack` 

## Inference

1. Create input payload with your prompt text:
```json
payload = {
    "prompt": "Give concise answer to the question. Qiestion: How to define optimal shard size in Amazon Opensearch?",
    "max_tokens": 128,
    "temperature": 0.1,
    "top_p": 0.5
}
```

2. Invoke SageMaker endpoint, using the stack output `ModelServingStack.sagemakerendpointname` as `ENDPOINT_NAME`:
```python
response = sagemaker_runtime.invoke_endpoint(
        EndpointName=ENDPOINT_NAME,
        Body=json.dumps(payload),
        ContentType='application/json',
    )
```

3. Get response body:
```python 
response_body = response['Body'].read().decode()
```

### Credits

Built based on Sean Bradley's project that was modified to work with SageMaker endpoints.

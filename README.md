# llamacpp


Docker image for Llama.cpp and Sagemmaker endpoint compatible API. 
Can be compiled for both ARM64 and x86 architectures. 
Use it to run GGUF and GMML LLM models on CPU-only instances including Graviton. 

## Installation

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

## Model Selection

1. https://huggingface.co/TheBloke  and choose GGUF model of your choice for example https://huggingface.co/TheBloke/llama-2-7B-Arguments-GGUF , scroll to provided files.  Usually Q4_K_M is good enough compromise (based on my testing but feel free to try yourself)

2. Replace the name of the variable #TODO

## Deployment

### Deploy all stacks

`./cicd/cdk-deploy-all-to.sh <account-id> <region-name>` 

For example:
`./cicd/cdk-deploy-all-to.sh 012345678901 us-east-1` 

To auto-approve:
`./cicd/cdk-deploy-all-to.sh <account-id> <region-name> --require-approval never`

Or you can only deploy one stack:
`./cicd/cdk-deploy-stack-to.sh <account-id> <region-name> ModelDownloadStack` 


## Project clean-up

Use destroy script to remove stacks and approve destroying stacks:
`./cicd/cdk-undeploy-from.sh <account-id> <region-name> --all` 

Or use destroy script to remove single stack and approve destroying a stack:
`./cicd/cdk-undeploy-from.sh <account-id> <region-name> ModelServingStack` 

### Credits

Built based on [project](https://gitlab.aws.dev/seanbly/quantized-document-qa) of Sean Bradley and modified it to work with Sagemaker endpoints.

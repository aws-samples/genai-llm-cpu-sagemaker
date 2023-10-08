# llamacpp


Docker image for Llama.cpp and Sagemmaker endpoint compatible API. 
Can be compiled for both ARM64 and x86 architectures. 
Use it to run GGUF and GMML LLM models on CPU-only instances including Graviton. 

## Installation

### Using public ECR image

1. setup (pull-through cache)[https://docs.aws.amazon.com/AmazonECR/latest/userguide/pull-through-cache.html] for the ECR public repository. 

2. Run `deploy_sagemaker_endpoint` notebook and follow instructions within the notebook. 

### Building your own docker image

1. Build docker image locally (supported paltforms `linux/arm64` and `linux/amd64`)

```bash
cd docker/
docker buildx build --platform linux/arm64 -t llmm-cpu-arm64:latest  --load .
```
2. Upload the image to the private ECR repository

3. Run `deploy_sagemaker_endpoint` notebook and follow instructions within the notebook. 

## Model Selection

1. https://huggingface.co/TheBloke  and choose GGUF model of your choice for example https://huggingface.co/TheBloke/llama-2-7B-Arguments-GGUF , scroll to provided files.  Usually Q4_K_M is good enough compromise (based on my testing but feel free to try yourself)

2. Click on the model file (e.g. llama-2-7b-arguments.Q4_K_M.gguf) there fill be download link that look like this  https://huggingface.co/TheBloke/llama-2-7B-Arguments-GGUF/resolve/main/llama-2-7b-arguments.Q4_K_M.gguf

3. You need to download this file and put it on S3 bucket (Smagemaker Endpoint role has to have permissions to access the bucket).
Follow the instructions in the provided notebook on how to load/inference that model dynamically.


### Credits

Built based on (project)[https://gitlab.aws.dev/seanbly/quantized-document-qa] of Sean Bradley and modified it to work with Sagemaker endpoints.

import os
import json
import boto3
from fastapi import FastAPI, HTTPException, status
from starlette.responses import Response, StreamingResponse
from llama_cpp import Llama
from pydantic import BaseModel, validator
from typing import Dict, Optional
from typing import Optional, List, Union
from pathlib import Path
import traceback
import requests
from urllib.parse import urlparse


MODELPATH=os.environ.get('MODELPATH')
STAGE = os.environ.get('STAGE', None)
OPENAPI_PREFIX = f"/{STAGE}" if STAGE else "/"

app = FastAPI(title="Sagemaker Endpoint LLM API", openapi_prefix=OPENAPI_PREFIX)
#llm = None #What we're going to do here is set up a simple system that allows you to specify any llama.cpp model you'd like. #Llama(model_path=MODELPATH, verbose=False)  # Instantiate the model at the beginning to make responses faster
llm = Llama(model_path=MODELPATH, n_ctx=2048, n_gpu_layers=0,seed=1234,f16_kv=True,logits_all=False,vocab_only=False,use_mmap=True,use_mlock=True,embedding=False,n_threads=None,n_batch=512,last_n_tokens_size=128,rope_freq_base=10000, rope_freq_scale=1,verbose=True)

class LlamaModelConfig(BaseModel):
    model_path: Optional[str] = None
    bucket: Optional[str] = None
    key: Optional[str] = None
    n_ctx: int = 2048
    n_parts: int = -1
    n_gpu_layers: int = 0
    seed: int = 1337
    f16_kv: bool = True
    logits_all: bool = False
    vocab_only: bool = False
    use_mmap: bool = True
    use_mlock: bool = False
    embedding: bool = False
    n_threads: Optional[int] = None
    n_batch: int = 512
    last_n_tokens_size: int = 128
    lora_base: Optional[str] = None
    lora_path: Optional[str] = None
    low_vram: bool = True
    tensor_split: Optional[List[float]] = None
    rope_freq_base: float = 10000
    rope_freq_scale: float = 1
    verbose: bool = False

    @validator('tensor_split')
    def validate_tensor_split(cls, v):
        if v is not None and not all(isinstance(item, float) for item in v):
            raise ValueError('All elements in the tensor_split list must be floats')
        return v

class RoutePayload(BaseModel):
    configure: bool
    inference: bool
    args: dict

class SmPayload(BaseModel):
    inputs: Optional[str] = None
    parameters: Optional[dict] = None


class LlamaArguments(BaseModel):
    prompt: str
    suffix: Optional[str] = None
    max_tokens: int = 600
    temperature: float = 0.7
    top_p: float = 0.95
    logprobs: Optional[Union[int, None]] = None
    echo: bool = False
    stop: Optional[Union[str, List[str], None]] = []
    frequency_penalty: float = 0
    presence_penalty: float = 0
    repeat_penalty: float = 1.1
    top_k: int = 40
    stream: bool = False
    tfs_z: float = 1
    mirostat_mode: int = 0
    mirostat_tau: float = 5
    mirostat_eta: float = 0.1

    @validator('stop')
    def validate_stop(cls, v):
        if isinstance(v, list) and not all(isinstance(item, str) for item in v):
            raise ValueError('All elements in the stop list must be strings')
        return v


def download_from_s3(bucket: str, key: str, local_path: str):
    s3 = boto3.client('s3')
    s3.download_file(bucket, key, local_path)

def download_file(url, local_filename):
    response = requests.get(url, stream=True)
    response.raise_for_status()  # Ensure we got an OK response

    with open(local_filename, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

def is_url(path):
    try:
        result = urlparse(path)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


@app.post("/")
async def route(payload: RoutePayload):
    if payload.configure:
        llama_model_args = LlamaModelConfig(**payload.args)
        return await configure(llama_model_args)
    elif payload.inference:
        llama_args = LlamaArguments(**payload.args)
        return await invoke(llama_args)
    else:
        raise HTTPException(status_code=400, detail="Please specify either 'configure' or 'inference'")


 
@app.get("/ping")
async def ping():
    return Response(status_code=200)


@app.post("/invocations")
async def invocations(payload: SmPayload):
    try:
        final=dict()
        args = dict(payload).get("parameters", None)
        args['prompt'] = dict(payload).get("inputs", None)
        args['max_tokens'] = 1024
        if args.get('max_new_tokens', None):
            args['max_tokens'] = args.get('max_new_tokens', None)

        for i in list(args):
            if i in LlamaArguments.__fields__:
                final[i] = args[i] 
        
        if args.get('stream', None):
            async def generate(output):
                for el in output:
                    yield el["choices"][0]["text"]

            return StreamingResponse(
                content=generate(llm(**final)), 
                status_code=status.HTTP_200_OK,
                media_type="text/plain",
            )
        
        return await invoke(LlamaArguments(**final))
    except:
        output={"traceback_err":str(traceback.format_exc())}
        raise HTTPException(status_code=408, detail=output)

@app.post("/invocations-response-stream")
async def invocations_response_stream(payload: SmPayload):
    try:
        final=dict()
        args = dict(payload).get("parameters", None)
        args['prompt'] = dict(payload).get("inputs", None)
        args['stream'] = True
        args['max_tokens'] = 1024
        if args.get('max_new_tokens', None):
            args['max_tokens'] = args.get('max_new_tokens', None)

        for i in list(args):
            if i in LlamaArguments.__fields__:
                final[i] = args[i] 
            
        async def generate():
        # model() is a hypothetical function that gets the inference output:
            yield await llm(**args.dict()) # type: ignore
            yield "\n"

        response = StreamingResponse(
            content=generate(),
            status_code=status.HTTP_200_OK,
            media_type="text/plain",
        )
        return response
    except:
        output={"traceback_err":str(traceback.format_exc())}
        raise HTTPException(status_code=408, detail=output)



@app.post("/invoke")
async def invoke(llama_args: LlamaArguments):
    try:
        if llm is not None:
            output=[]
            output_raw = llm(**llama_args.dict())  # Pass the parameters to Llama by unpacking the dictionary of arguments
            for elem in output_raw["choices"]: # type: ignore
                output.append({"generated_text":elem["text"]})
        else:
            raise HTTPException(status_code=400, detail="Please configure the llm engine using /configure")
    except:
        output={"traceback_err":str(traceback.format_exc())}
    return output

@app.post("/configure")
async def configure(llama_model_args: LlamaModelConfig):
    try:
        finalargs={}
        if llama_model_args.bucket and llama_model_args.key:
            local_path = MODELPATH
            download_from_s3(llama_model_args.bucket, llama_model_args.key, local_path)
            llama_model_args.model_path = local_path            
        if llama_model_args.model_path:
            if is_url(llama_model_args.model_path):
                download_file(llama_model_args.model_path,MODELPATH)
                llama_model_args.model_path=MODELPATH
        elif not llama_model_args.model_path:
            raise HTTPException(status_code=400, detail="Model path must be provided when S3 bucket and key are not specified")
        finalargs=llama_model_args.dict()
        finalargs.pop('key',None)
        finalargs.pop('bucket',None)
        llama_model_args=None
        llama_model_args = finalargs
        global llm
        llm = Llama(**llama_model_args)  # Pass the parameters to Llama by unpacking the dictionary of arguments
        return {"status": "success"}
    except:
        return {"traceback_err":str(traceback.format_exc())}



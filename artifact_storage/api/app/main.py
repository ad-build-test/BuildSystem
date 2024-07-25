import os
import uvicorn
import subprocess
import time
import asyncio
from fastapi import FastAPI, UploadFile, File
from kubernetes import client, config, utils
from kubernetes.client.rest import ApiException
from contextlib import asynccontextmanager
from pydantic import BaseModel
# FastAPI and Asynchronous utilizes one thread for concurrency. 
# This is optimal for many requests, and avoiding dead-locks, race-conditions,
# and resources, where multithreading would include those issues

# Example request when ran on k8s port 8080 
# Can only accept requests from other pods in the cluster within same nammespace
# UNLESS you specify namespace, like artifact-api-service.artifact:8080 
"""
curl -X 'GET' http://artifact-api-service:8080/component \
-H 'accept: application/json' \
-H 'Content-Type: application/json' \
-d '{
"component": "epics-base",
"tag": "R7.0.8",
"arch": "rocky9"
}'
curl -X 'POST' http://artifact-api-service:8080/image \
-H 'accept: application/json' \
-H 'Content-Type: application/json' \
-d '{
"dockerfile": "test-ioc-dev-patrick-rocky9",
"arch": "rocky9"
}'
"""
"""
We can keep the get component-dependency logic the same for now, (if exists copy over to
the build container). otherwise build. We may also look into
having ansible install the dependencies as rpm packages (this would require each dependency
to create an rpm package)
But green light, fill in these endpoints for now.
"""

class GetComponent(BaseModel):
    component: str
    tag: str
    arch: str
class BuildImage(BaseModel):
    dockerfile: str
    arch: str

registry_base_path = "/mnt/eed/ad-build/registry/"
config.load_kube_config() 
k8s_client = client.ApiClient()
k8s_api = client.CoreV1Api()
k8s_namespace = 'artifact'

async def run(cmd: str):
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stderr=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE
    )

    stdout, stderr = await proc.communicate()

    # Decode stdout and stderr from bytes to string
    stdout_str = stdout.decode().strip() if stdout else None
    stderr_str = stderr.decode().strip() if stderr else None

    return stdout_str, stderr_str

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Artifact API Initialization")
    # config.load_kube_config() 
    # kube_list_pods()
    # k8s_client = client.ApiClient()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/image")
# TODO: 
# Won't need this since we have our own docker registry
# blocked on waiting for registry service to finish
# async def get_image(payload: Payload):
#     # Depending on how we store the image
#     # Image name example: component-branch-arch:latest
#     # May not need this function if we can assume the image name convention is forced
#     # Cause really all clients need is to 'docker pull component-branch-arch:latest'
#     kube_list_pods() # For testing
#     print(payload)
#     return {"message": "Get Image"}

@app.post("/image")
async def build_image(payload: BuildImage):
    # ex: dockerfile = mps-main-rocky9
    # 1) have client copy it over somewhere in the registry, and send filepath
        # This may be optimal so the artifact service can set env var for container
        # that builds the image
        # Dockerfile is created dynamically, and can copy over the components as long
        # as the volume mount to the artifact storage is there
    # 2) Start container to Build image, push to registry
    # check out this filepath: /mnt/eed/ad-build/registry/epics-base/R7.0.8/epics-base/configure/os
    build_name = payload.dockerfile + '-img-bld'
    replacements = {'$ADBS_DOCKERFILE': payload.dockerfile, '$BUILDER_NAME': build_name,
                    '$ADBS_OS_ENVIRONMENT': payload.arch}
    custom_podman = payload.dockerfile + '.yml' # Custom_podman is the original deployment file with some replacements
    with open('podman-builder.yml') as infile, open(custom_podman, 'w') as outfile:
        for line in infile:
            for src, target in replacements.items():
                line = line.replace(src, target)
            outfile.write(line)
    kube_apply_from_file(custom_podman)
    stdout, stderr = await kube_wait_pod_finish(build_name, payload)
    # Cleanup
    os.remove(custom_podman)
    if stdout or stderr:
        # TODO: Temporarily comment out deleting pod for testing purposes
        # kube_delete_pod(build_name)
        # Output results
        if stdout:
            print(f"stdout: {stdout}")
            return {"status": "Successfully built " + payload.dockerfile}
        if stderr:
            print(f"stderr: {stderr}")
            return {"status": "Error building " + payload.dockerfile,
                    "error": stderr}
    return "Error in build image request"
    # TODO: Add try catch for os.remove and kube apply funcs
    # TODO: remove the persistantvolumeclaim manifest from the dpeloyment, only needs to
            # be created ONCE for a namespace but WORKS

@app.get("/component")
# TODO:
# check if exists, and return filepath
# ARGS: component, tag, arch
async def get_component(payload: GetComponent):
    # 1) Check if component already exists in registry
    component_path = registry_base_path + payload.component + '/' + payload.tag + '/'
    print(component_path)
    if (os.path.exists(component_path)):
        return {"status": "Component Exists",
            "component": component_path}
    # TODO: if component doesnt exist, can do either
    # 1) Build component, then return
    # 2) Return component doesn't exist, then have client
    # request a component build
    return {"status": "Component does not exist"}
    # 1.1) If not exists, 
    # Return it doesn't exist, and will try to build
    # then try to clone the component:tag and build
    # Then from client end,

    # 2) Return filepath to prebuilt component


@app.post("/component")
# TODO:
# Clone the component, and build
# May not need this endpoint
async def build_component(component: str, tag: str, arch: str):
    return {"message": "Build Component"}

def kube_list_pods():
    v1 = client.CoreV1Api()
    print("Listing pods with their IPs:")
    ret = v1.list_namespaced_pod(k8s_namespace)
    for i in ret.items:
        print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))

def kube_delete_pod(pod: str):
    try:
        api_response = k8s_api.delete_namespaced_pod(pod, k8s_namespace)
    except ApiException as e:
        print("Exception when calling CoreV1Api->delete_namespaced_pod: %s\n" % e)

def kube_apply_from_file(yaml_file: str):
    print("== AD-BUILD == Applying podman pod")
    output_bytes = subprocess.check_output(['kubectl', 'apply', '-f', yaml_file])
    print(output_bytes.decode("utf-8"))

async def kube_wait_pod_finish(pod_name: str, payload: BuildImage):
    print("== AD-BUILD == Asyn wait for pod to finish")
    pod_name = 'pod/' + pod_name
    wait_command = ["kubectl", "wait", "--for=jsonpath={.status.phase}=Succeeded", pod_name, "--timeout=120s"]
    print(wait_command)
    task = asyncio.create_task(run(wait_command))
    stdout, stderr = await task
    return stdout, stderr

if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8080)
    # main refers to file, and app is the app=fastapi()


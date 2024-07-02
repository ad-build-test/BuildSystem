import os
import uvicorn
from fastapi import FastAPI, UploadFile, File
from kubernetes import client, config, utils
# Example request when ran on k8s port 8080 curl -X GET http://artifact-api-service:8080/image
app = FastAPI()
"""
We can keep the get component-dependency logic the same for now, (if exists copy over to
the build container). otherwise build. We may also look into
having ansible install the dependencies as rpm packages (this would require each dependency
to create an rpm package)
But green light, fill in these endpoints for now.
"""
registry_base_path = "/mnt/eed/ad/ad-build/registry/"
k8s_client = client.ApiClient()

@app.get("/image")
# TODO: 
# blocked on waiting for registry service to finish
async def get_image(component: str, branch: str, arch: str):
    # Depending on how we store the image
    # Image name example: component-branch-arch:latest
    # May not need this function if we can assume the image name convention is forced
    # Cause really all clients need is to 'docker pull component-branch-arch:latest'
    return {"message": "Get Image"}

@app.post("/image")
# TODO:
# Call a podman command, and push to registry 
async def build_image(dockerfile: str):
    # ex: dockerfile = mps-main-rocky9
    # TODO: Try podman python api
    # 1) have client copy it over somewhere in the registry, and send filepath
        # This may be optimal so the artifact service can set env var for container
        # that builds the image
        # Dockerfile is created dynamically, and can copy over the components as long
        # as the volume mount to the artifact storage is there
    # 2) Start container to Build image, push to registry
    # check out this filepath: /mnt/eed/ad-build/registry/epics-base/R7.0.8/epics-base/configure/os
    return {"dockerfile_sent": dockerfile}

@app.get("/component")
# TODO:
# check if exists, and return filepath
# ARGS: component, tag, arch
async def get_component(component: str, tag: str, arch: str):
    # 1) Check if component already exists in registry
    if (os.path.exists(registry_base_path + component + '/' + tag + '/')):
        pass

    # 1.1) If not exists, 
    # Return it doesn't exist, and will try to build
    # then try to clone the component:tag and build
    # Then from client end,

    # 2) Return filepath to prebuilt component
    return {"message": "Get Component"}

@app.post("/component")
# TODO:
# Clone the component, and build
# May not need this endpoint
async def build_component(component: str, tag: str, arch: str):
    return {"message": "Build Component"}

def kube_list_pods():
    v1 = client.CoreV1Api()
    print("Listing pods with their IPs:")
    ret = v1.list_pod_for_all_namespaces(watch=False)
    for i in ret.items:
        print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))

def kube_apply_from_file(yaml_file: str):
    utils.create_from_yaml(k8s_client,yaml_file,verbose=True)

if __name__ == '__main__':
    # TODO: have a script login to the kubernetes cluster before you run this main.py
    config.load_kube_config() 
    kube_list_pods()
    # kube_apply_from_file('../test-ioc-dev-patrick.yml')
    uvicorn.run('main:app', host='0.0.0.0', port=8080, reload=True)


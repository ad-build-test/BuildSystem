import os
from fastapi import FastAPI, UploadFile, File
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
    # 1) Either have client upload dockerfile
    # 2) have client copy it over somewhere in the registry, and send filepath
        # This may be optimal so the artifact service can set env var for container
        # that builds the image
        # Dockerfile is created dynamically, and can copy over the components as long
        # as the volume mount to the artifact storage is there
    # 3) Start container to Build image, push to registry
    # check out this filepath: /mnt/eed/ad-build/registry/epics-base/R7.0.8/epics-base/configure/os
    return {"dockerfile_sent": dockerfile}

@app.get("/component")
# TODO:
# check if exists, and return filepath
# ARGS: component, tag, arch
async def get_component(component: str, tag: str, arch: str):
    # 1) Check if component already exists in registry
    base_path = '/mnt/eed/ad/ad-build/registry/'
    if (os.path.exists(base_path + component + '/' + tag + '/')):
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
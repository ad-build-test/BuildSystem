import os
from fastapi import FastAPI, UploadFile, File

app = FastAPI()

@app.get("/image")
# TODO: 
# blocked on waiting for registry service to finish
async def get_image(component: str, tag: str, arch: str):
    # Depending on how we store the image
    # Maybe registry/images/component/tag/arch
    return {"message": "Get Image"}

@app.post("/image")
# TODO:
# Call a podman command, and push to registry 
async def build_image(component: str, tag: str, arch: str, dockerfile: UploadFile):
    # TODO: Try podman python api
    # 1) Either have client upload dockerfile
    # 2) have client copy it over somewhere in the registry, and send filepath
        # This may be optimal so the artifact service can set env var for container
        # that builds the image
    return {"message": "Build Image"}

@app.get("/component")
# TODO:
# check if exists, and return filepath
# ARGS: component, tag, arch
async def get_component(component: str, tag: str, arch: str):
    # 1) Check if component already exists in registry
    base_path = '/mnt/eed/ad/ad-build/registry/'
    if (os.path.exists(base_path + component)):
        pass

    # 1.1) If not exists, then try to clone the component:tag

    # 2) Return filepath to prebuilt component
    return {"message": "Get Component"}

@app.post("/component")
# TODO:
# Clone the component, and build
async def build_component():
    return {"message": "Build Component"}
import os
import uvicorn
import subprocess
import asyncio
from fastapi import FastAPI, UploadFile, File
from contextlib import asynccontextmanager
from pydantic import BaseModel

from kubernetes import client, config, watch

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

async def test_async(string):
    print(string)

# <<<<<<<<<<<<<< Test WATCH <<<<<<<<<<
async def main():
    # Configs can be set in Configuration class directly or using helper
    # utility. If no argument provided, the config will be loaded from
    # default location.
    config.load_kube_config()

    v1 = client.CoreV1Api()
    print("== AD-BUILD == Asyn wait for pod to finish")
    pod_arg = 'pod/' + 'test-ioc-dev-patrick-rocky9-img-bld'
    wait_command = f"kubectl wait --for=jsonpath='{{.status.phase}}'=Succeeded {pod_arg} --timeout=60s"
    print(wait_command)
    wait_command = ["kubectl", "wait", "--for=jsonpath={.status.phase}=Succeeded", pod_arg, "--timeout=60s"]
    print(wait_command)
    task = asyncio.create_task(run(wait_command))
    print("test")
    stdout, stderr = await task
    # stdout, stderr = await run(wait_command)
    # Output results
    if stdout:
        print(f"stdout: {stdout}")
    if stderr:
        print(f"stderr: {stderr}")
    print("test")
    # output_bytes = subprocess.check_output(["kubectl", "wait", "--for=jsonpath='{.status.phase}'=Succeeded", pod_arg, "--timeout=60s"])
    # print(output_bytes.decode("utf-8"))
    return
    count = 10
    w = watch.Watch()
# We can use subprocess to do a kubectl command instead and confirmed it works
    # kubectl wait --for=jsonpath='{.status.phase}'=Succeeded pod/test-ioc-dev-patrick-rocky9-image-build --timeout=60s
    app_name = 'test-ioc-dev-patrick-rocky9-image-build'
    # print(v1.read_namespaced_pod(name=app_name, namespace='artifact'))
    for event in w.stream(v1.read_namespaced_pod, namespace='artifact', name=app_name):
        # https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/
        if event["object"].status.phase == "Succeeded":
            print("Container is complete")
            w.stop()
            return
        if event["object"].status.phase == "Running":
            print("Container is still running")
            w.stop()
            return
        # # event.type: ADDED, MODIFIED, DELETED
        # if event["type"] == "DELETED":
        #     # Pod was deleted while we were waiting for it to start.
        #     logger.debug("%s deleted before it started", full_name)
        #     w.stop()
        #     return

if __name__ == '__main__':
    asyncio.run(main())
    asyncio.run(test_async("async working?"))

# <<<<<<<<<< Test APPLY <<<<<<<<<<<
# from kubernetes import client, config, utils
# config.load_kube_config()  # load kube config is first before any other kubernetes commands
# k8s_client = client.ApiClient()

# def kube_apply_from_file(yaml_file: str):
#     utils.create_from_yaml(k8s_client, yaml_file, verbose=True, namespace='artifact')

# kube_apply_from_file('test-ioc-dev-patrick.yml')

# from kubernetes import client, config, utils

# def main():
#     config.load_kube_config()
#     k8s_client = client.ApiClient()
#     yaml_file = 'test-ioc-dev-patrick.yml'
#     utils.create_from_yaml(k8s_client,yaml_file,verbose=True, namespace='artifact')

# if __name__ == "__main__":
#     main()
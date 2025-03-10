# Build environment images 
These images are aimed to replicate the necessary packages to build applications for their intended OS.

# How to build
### RHEL7
1. Go to top of repo and enter command:
`docker build --tag ghcr.io/ad-build-test/rhel7-env:latest -f build_envs/rhel7_env/Dockerfile .`

2. Push image
`docker push ghcr.io/ad-build-test/rhel7-env:latest`

3. Build apptainer image for local builds at `cd /sdf/group/ad/eed/ad-build/registry/rhel7-env`
`apptainer build rhel7-env_latest.sif docker://ghcr.io/ad-build-test/rhel7-env:latest`

### ROCKY9 (RHEL9)
1. Go to top of repo and enter command:
`docker build --tag ghcr.io/ad-build-test/rocky9-env:latest -f build_envs/rocky9_env/Dockerfile .`

2. Push image
`docker push ghcr.io/ad-build-test/rocky9-env:latest`

3. Build apptainer image for local builds at `cd /sdf/group/ad/eed/ad-build/registry/rocky9-env`
`apptainer build rocky9-env_latest.sif docker://ghcr.io/ad-build-test/rocky9-env:latest`

# How to build: docker build --tag ghcr.io/ad-build-test/deploy-env:latest .
# base image
# How to build:
# 1) Go to top of repo
# 2) docker build --tag ghcr.io/ad-build-test/deployment-controller:latest -f deploy_controller/Dockerfile .
# DEV) docker build --tag ghcr.io/ad-build-test/deployment-controller:dev -f deploy_controller/Dockerfile .
FROM rockylinux:9

# update
RUN dnf -y update

# install vim and python3 and pip
# install perl, git, podman
RUN dnf install -y vim \
    python3 \
    pip \
    perl \
    git \
    dos2unix \
    && dnf clean all

# install ansible
RUN pip install ansible

# Create adbuild with a specific UID (e.g., 46487)
RUN groupadd -g 1006 cd && \
    useradd -u 46487 -g cd -m adbuild

# Add build and deploy scripts to /app
RUN mkdir /app
RUN mkdir /home/adbuild/.ssh
ADD build_deploy_scripts /app/
ADD deploy_controller/config /home/adbuild/.ssh
RUN chown -R 46487:1006 /app
RUN chown -R 46487:1006 /home
RUN chown -R 46487:1006 /home/adbuild/.ssh

# install requirements.txt
RUN pip install -r /app/requirements.txt

# Command to run the app - already set in the deployment yaml
# CMD ["uvicorn", "deployment_controller:app", "--host", "0.0.0.0", "--port", "8080"]
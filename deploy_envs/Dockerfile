# How to build: docker build --tag pnispero/deploy-env:latest .
# base image
# How to build:
# 1) Go to top of repo
# 2) docker build --tag pnispero/deploy-env:latest -f deploy_envs/Dockerfile .
FROM quay.io/ansible/ansible-runner:stable-2.11-latest

# # update
# RUN yum -y update

# # install glibc
# RUN yum install -y glibc

# # install gcc and make
# RUN yum install -y gcc-c++ && yum install -y make

# # install vim and python3 and pip
# RUN yum install -y vim && yum install -y python3 && yum install -y pip

# install pyyaml, requests
RUN pip install pyyaml \
    && pip install requests

# # install ansible
# RUN pip install ansible

# # install git
# RUN yum install -y git

# Add build and deploy scripts to /build
ADD build_deploy_scripts /build/

# Add playbooks to /build
ADD ansible /build/

# Make /build open to 'adbuild' user
# RUN chown -R 46487:1006 /build/

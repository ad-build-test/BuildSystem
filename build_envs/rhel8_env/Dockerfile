# base image
# note from redhat official website - the base image is free to use, but Red Hat technologies are supported through red hat subscription
# How to build:
# 1) Go to top of repo
# 2) docker build --tag pnispero/rhel8-env:latest -f build_envs/rhel8_env/Dockerfile .
FROM redhat/ubi8:8.6

# update
RUN yum -y update

# install glibc
RUN yum install -y glibc

# install gcc and make
RUN yum install -y gcc-c++ && yum install -y make

# install vim and python3
RUN yum install -y vim && yum install -y python3

# install wget
RUN yum install -y wget

# install pip
RUN cd /etc/ && wget https://bootstrap.pypa.io/pip/3.6/get-pip.py && python3 ./get-pip.py

# install pyyaml, requests, ansible
RUN pip install pyyaml \
    && pip install requests \ 
    && pip install ansible

# install perl
RUN yum install -y perl

# install git
RUN yum install -y git

# install podman
RUN yum install -y podman

# Add build scripts to /build
ADD build_deploy_scripts /build/

# Create adbuild with a specific UID (e.g., 46487)
RUN groupadd -g 1006 cd && \
    useradd -u 46487 -g cd -m adbuild

# Make /build open to 'adbuild' user
RUN chown -R 46487:1006 /build/

# Add env variable for python scripts to stream live
ENV PYTHONUNBUFFERED=1
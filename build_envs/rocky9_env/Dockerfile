# How to build: docker build --tag pnispero/rocky9-env:latest .
# base image
# How to build:
# 1) Go to top of repo
# 2) docker build --tag pnispero/rocky9-env:latest -f build_envs/rocky9_env/Dockerfile .
FROM rockylinux:9

# update
RUN yum -y update

# install glibc
RUN yum install -y glibc

# install gcc and make
RUN yum install -y gcc-c++ && yum install -y make

# install vim and python3 and pip
RUN yum install -y vim && yum install -y python3 && yum install -y pip

# install pyyaml, requests
RUN pip install pyyaml \
    && pip install requests

# install perl
RUN yum install -y perl

# install git
RUN yum install -y git

# Add build scripts to /build
ADD build_scripts /build/

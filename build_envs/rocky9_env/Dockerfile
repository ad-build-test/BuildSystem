# How to build: docker build --tag pnispero/rocky9-env:latest .
# base image
# How to build:
# 1) Go to top of repo
# 2) docker build --tag pnispero/rocky9-env:latest -f build_envs/rocky9_env/Dockerfile .
FROM rockylinux:9

# update
RUN dnf -y update

# install glibc
RUN dnf install -y glibc

# install gcc and make
RUN dnf install -y gcc-c++ && dnf install -y make

# install readline-devel, ncurses-devel
RUN dnf install -y readline-devel \
    ncurses-devel \
    && dnf clean all

# install vim and python3 and pip
RUN dnf install -y vim && dnf install -y python3 && dnf install -y pip

# install pyyaml, requests, ansible
RUN pip install pyyaml \
    && pip install requests \
    && pip install ansible

# install perl
RUN dnf install -y perl

# install git
RUN dnf install -y git

# install podman
RUN dnf install -y podman

# Add build scripts to /build
ADD build_deploy_scripts /build/

# Add playbooks to /build
ADD ansible /build/

# Create adbuild with a specific UID (e.g., 46487)
RUN groupadd -g 1006 cd && \
    useradd -u 46487 -g cd -m adbuild

# Make /build open to 'adbuild' user
RUN chown -R 46487:1006 /build/

# Add env variable for python scripts to stream live
ENV PYTHONUNBUFFERED=1
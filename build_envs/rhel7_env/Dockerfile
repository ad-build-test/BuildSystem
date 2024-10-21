# base image
# note from redhat official website - the base image is free to use, but Red Hat technologies are supported through red hat subscription
# https://catalog.redhat.com/software/containers/ubi7/ubi/5c3592dcd70cc534b3a37814?architecture=amd64&image=66569cf6d9fa3da18316f6f9&container-tabs=gti&gti-tabs=unauthenticated
# How to build:
# 1) Go to top of repo
# 2) docker build --tag pnispero/rhel7-env:latest -f build_envs/rhel7_env/Dockerfile .
FROM registry.access.redhat.com/ubi7/ubi

# update
RUN yum -y update

# install glibc
RUN yum install -y glibc

# install gcc and make
RUN yum install -y gcc-c++ && yum install -y make

# install vim
RUN yum install -y vim 

# install python3.8, special case for rhel7 since default is python2.7
RUN yum install -y rh-python38
# RUN export PATH=$PATH:/opt/rh/rh-python38/root/usr/bin/
# RUN ls -l /opt/rh/rh-python38/root/usr/bin/

# Move this to be the default /usr/bin 
RUN cp /opt/rh/rh-python38/root/usr/bin/python3.8 /usr/bin/python3

# install wget
RUN yum install -y wget

# install pip
RUN cd /etc/ && wget https://bootstrap.pypa.io/get-pip.py && python3 ./get-pip.py --force-reinstall
RUN python3 -m pip install --upgrade pip

# install git
RUN yum install -y git

# install pyyaml, requests, and urllib3<2.0
RUN python3 -m pip install pyyaml \
    && python3 -m pip install requests \
    && python3 -m pip install 'urllib3<2.0' \
    && python3 -m pip install ansible

# Install rpm-build
RUN yum install -y rpm-build

# Add playbooks to /build
ADD ansible /build/

# Create adbuild with a specific UID (e.g., 46487)
RUN groupadd -g 1006 cd && \
    useradd -u 46487 -g cd -m adbuild

# Add build scripts to /build
ADD build_deploy_scripts /build/

# Make /build open to 'adbuild' user
RUN chown -R 46487:1006 /build/
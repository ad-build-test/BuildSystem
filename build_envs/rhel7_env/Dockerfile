# base image
# note from redhat official website - the base image is free to use, but Red Hat technologies are supported through red hat subscription
# https://catalog.redhat.com/software/containers/ubi7/ubi/5c3592dcd70cc534b3a37814?architecture=amd64&image=66569cf6d9fa3da18316f6f9&container-tabs=gti&gti-tabs=unauthenticated
# How to build:
# 1) Go to top of repo
# 2) docker build --tag pnispero/rhel7-env:latest -f build_envs/rhel7_env/Dockerfile .
# TODO: update the install to use just one RUN command and a bunch of /'s'
FROM registry.access.redhat.com/ubi7/ubi

# update
RUN yum -y update

# install glibc, readline-devel (missing in rhel7 ubi), ncurses-devel
# install gcc, make, vim
# install python3.8, special case for rhel7 since default is python2.7
# install wget, git, rpm-build
RUN yum install -y glibc \
    readline-devel \
    ncurses-devel \
    gcc-c++ \ 
    make \
    vim \
    rh-python38 \
    wget \
    git \
    rpm-build \
    && yum clean all

RUN ln -s /usr/lib64/libreadline.so.6 /usr/lib64/libreadline.so

# RUN export PATH=$PATH:/opt/rh/rh-python38/root/usr/bin/
# RUN ls -l /opt/rh/rh-python38/root/usr/bin/

# Move this to be the default /usr/bin 
RUN cp /opt/rh/rh-python38/root/usr/bin/python3.8 /usr/bin/python3

# install pip
RUN cd /etc/ && wget https://bootstrap.pypa.io/get-pip.py && python3 ./get-pip.py --force-reinstall
RUN python3 -m pip install --upgrade pip

# install pyyaml, requests, and urllib3<2.0
RUN python3 -m pip install pyyaml \
    && python3 -m pip install requests \
    && python3 -m pip install 'urllib3<2.0' \
    && python3 -m pip install ansible

# Create adbuild with a specific UID (e.g., 46487)
RUN groupadd -g 1006 cd && \
    useradd -u 46487 -g cd -m adbuild

# Add build scripts to /build
ADD build_deploy_scripts /build/

# Make /build open to 'adbuild' user
RUN chown -R 46487:1006 /build/

# Add env variable for python scripts to stream live
ENV PYTHONUNBUFFERED=1

# Add EPICS_HOST_ARCH variable for ioc builds
ENV EPICS_HOST_ARCH=rhel7-x86_64
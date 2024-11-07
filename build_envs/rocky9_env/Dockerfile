# How to build: docker build --tag pnispero/rocky9-env:latest .
# base image
# How to build:
# 1) Go to top of repo
# 2) docker build --tag pnispero/rocky9-env:latest -f build_envs/rocky9_env/Dockerfile .
FROM rockylinux:9

# update
RUN dnf -y update

# install readline-devel, ncurses-devel
# install glibc, gcc, make
# install vim and python3 and pip
# install perl, git, podman
RUN dnf install -y readline-devel \
    ncurses-devel \
    glibc \ 
    gcc-c++ \
    make \
    vim \
    python3 \
    pip \
    perl \
    git \
    podman \
    && dnf clean all

RUN dnf install -y vim && dnf install -y python3 && dnf install -y pip

# install pyyaml, requests, ansible
RUN pip install pyyaml \
    && pip install requests \
    && pip install ansible

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

# Add EPICS_HOST_ARCH variable for ioc builds
ENV EPICS_HOST_ARCH=rhel9-x86_64
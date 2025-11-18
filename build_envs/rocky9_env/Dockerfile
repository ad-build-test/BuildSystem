# How to build: docker build --tag ghcr.io/ad-build-test/rocky9-env:latest .
# base image
# How to build:
# 1) Go to top of repo
# 2) docker build --tag ghcr.io/ad-build-test/rocky9-env:latest -f build_envs/rocky9_env/Dockerfile .
# 3) Please remember to update apptainer as well at /sdf/group/ad/eed/ad-build/registry/rocky9-env

FROM rockylinux:9

# update
RUN dnf -y update

# install readline-devel, ncurses-devel
# install glibc-devel, gcc, make
# install vim and python3 and pip
# install perl, git, podman, rsync
RUN dnf install -y readline-devel \
    ncurses-devel \
    glibc-devel \ 
    gcc-c++ \
    make \
    vim \
    python3 \
    pip \
    perl \
    git \
    podman \
    rsync \
    && dnf clean all

RUN dnf install -y vim && dnf install -y python3 && dnf install -y pip

# install pyyaml, requests, ansible
RUN pip install pyyaml \
    && pip install requests \
    && pip install ansible

# Add build scripts to /build
ADD build_scripts /build/

# Create adbuild with a specific UID (e.g., 46487)
RUN groupadd -g 1006 cd && \
    useradd -u 46487 -g cd -m adbuild

# Make /build open to 'adbuild' user
RUN chown -R 46487:1006 /build/

# Add env variable for python scripts to stream live
ENV PYTHONUNBUFFERED=1

# Add EPICS_HOST_ARCH variable for ioc builds
ENV EPICS_HOST_ARCH=rhel9-x86_64

# Remove existing empty /afs then Add sym link to /afs
RUN rm -rf /afs && ln -s /mnt/transition/afs /
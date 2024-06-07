# How to build: docker build --tag pnispero/rocky9-env:latest .
# base image
FROM rockylinux:9

# update
RUN yum -y update

# install glibc
RUN yum install -y glibc

# install gcc and make
RUN yum install -y gcc-c++ && yum install -y make

# install vim and python3
RUN yum install -y vim && yum install -y python3

# Add build scripts to /build
Add build_scripts /build/

# WORKDIR /home/user

# RUN chmod +x build.sh

# RUN echo "Copy the repo to /home/user/"

# No CMD command since this can be used for both build and development
# ENTRYPOINT ["/bin/bash"]
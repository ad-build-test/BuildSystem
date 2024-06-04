# base image
FROM rockylinux:9

# update
RUN yum -y update

# install glibc
RUN yum install -y glibc

# install gcc and make
RUN yum install -y gcc-c++ && yum install -y make

# install vim
RUN yum install -y vim

# COPY build.sh /home/user/build.sh

# WORKDIR /home/user

# RUN chmod +x build.sh

# RUN echo "Copy the repo to /home/user/"

# No CMD command since this can be used for both build and development
# ENTRYPOINT ["/bin/bash"]
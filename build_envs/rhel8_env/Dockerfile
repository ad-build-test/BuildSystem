# base image
# note from redhat official website - the base image is free to use, but Red Hat technologies are supported through red hat subscription
FROM redhat/ubi8:8.6

# update
RUN yum -y update

# install glibc
RUN yum install -y glibc

# install gcc and make
RUN yum install -y gcc-c++ && yum install -y make

COPY build.sh /home/user/build.sh

WORKDIR /home/user

RUN chmod +x build.sh

# RUN echo "Copy the repo to /home/user/"

# No CMD command since this can be used for both build and development
# ENTRYPOINT ["/bin/bash"]
# How to build: docker build --tag pnispero/artifact-api:latest .
# base image
# How to build:
# 1) Go to artifact_storage/api/
# 2) docker build --tag pnispero/artifact-api:latest -f Dockerfile .
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

# install podman
RUN yum install -y podman

# install kubectl
RUN cat <<EOF | tee /etc/yum.repos.d/kubernetes.repo
[kubernetes]
name=Kubernetes
baseurl=https://pkgs.k8s.io/core:/stable:/v1.28/rpm/
enabled=1
gpgcheck=1
gpgkey=https://pkgs.k8s.io/core:/stable:/v1.28/rpm/repodata/repomd.xml.key
EOF
RUN yum install -y kubectl

# Add app files
RUN mkdir app
ADD app /app/
ADD requirements.txt /app/

# Install requirements.txt
RUN pip install -r app/requirements.txt

# set the entrypoint
CMD ["fastapi", "run", "app/main.py", "--port", "8080"]


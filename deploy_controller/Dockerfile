# How to build: docker build --tag pnispero/deploy-env:latest .
# base image
# How to build:
# 1) Go to top of repo
# 2) docker build --tag pnispero/deployment-controller:latest -f deploy_controller/Dockerfile .
FROM quay.io/ansible/ansible-runner:stable-2.11-latest

# # update
# RUN yum -y update

# # install glibc
# RUN yum install -y glibc

# # install gcc and make
# RUN yum install -y gcc-c++ && yum install -y make

# # install vim and python3 and pip
# RUN yum install -y vim && yum install -y python3 && yum install -y pip

# install pyyaml, requests
# RUN pip install pyyaml \
#     && pip install requests

# # install ansible
# RUN pip install ansible

# # install git
# RUN yum install -y git

# Add build and deploy scripts to /app
RUN mkdir /app
ADD build_deploy_scripts /app/

# install requirements.txt
RUN pip install -r /app/requirements.txt

# Command to run the app - already set in the deployment yaml
# CMD ["uvicorn", "deployment_controller:app", "--host", "0.0.0.0", "--port", "8080"]

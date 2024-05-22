# base
FROM ubuntu:22.04

# set the github runner version
ARG RUNNER_VERSION="2.316.1"

# update the base packages and add a non-sudo user and vim
RUN apt-get update -y && apt-get upgrade -y && useradd -m docker
RUN apt-get install vim -y

# install curl
RUN apt install -y curl

# install kubectl
RUN curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl \
    && chmod +x ./kubectl \
    && mv ./kubectl /usr/local/bin

# install newuidmap & newgidmap
RUN apt-get install -y uidmap

# install python and the packages the your code depends on along with jq so we can parse JSON
# add additional packages as necessary
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    curl jq build-essential libssl-dev libffi-dev python3 python3-venv python3-dev python3-pip

# install pyyaml, requests
RUN pip install pyyaml \
    && pip install requests

# cd into the user directory, download and unzip the github actions runner
RUN cd /home/docker && mkdir actions-runner && cd actions-runner \
    && curl -O -L https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz \
    && tar xzf ./actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz

# install some additional dependencies
RUN chown -R docker ~docker && /home/docker/actions-runner/bin/installdependencies.sh

# copy over the start.sh script
COPY start.sh start.sh

# copy over the start_build.py script
COPY start_build.py start_build.py

# make the scripts executable
RUN chmod +x start.sh

# Create 'cd' user group
RUN groupadd --gid 1006 cd

# since the config and run script for actions are not allowed to be run by root,
# set the user to "docker" so all subsequent commands are run as the docker user
USER docker

# set the entrypoint to the start.sh script
ENTRYPOINT ["./start.sh"]
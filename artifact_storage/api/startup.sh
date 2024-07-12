#!/bin/bash

# Artifact api startup script

# 1) Configure kube config
# 2) start up the server

echo "Configuring kubernetes cluster authentication"
export HOME=/root # Has to be root for kube config. but we run as user 'ad-build'
echo "apiVersion: v1
clusters:
- cluster:
    insecure-skip-tls-verify: true
    server: https://k8s.slac.stanford.edu:443/api/ad-build-dev
  name: ad-build-dev
contexts:
- context:
    cluster: ad-build-dev
    user: artifact-sa
  name: ad-build-dev
current-context: ad-build-dev
kind: Config
preferences: {}
users:
- name: artifact-sa
  user:
    token: $artifact_api_token
" > $HOME/.kube/config

echo "Starting up artifact api service"
fastapi run /app/main.py --port 8080

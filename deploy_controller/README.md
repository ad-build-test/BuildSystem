# Deployment controller

## SSH Key secret
Please note, adding the ssh key to the vault as a secret was not successful.
There was errors pasting the key to hashcorp vault, where the line-endings were not valid for unix.

So the workaround is to manually add the key to vault using a linux terminal.
Steps: 
1. Have access to `adbuild` account
2. Have access to `ad-build` or `ad-build-dev` cluster
3. SSH into desired facility `adbuild` account. Generate a SSH key pair (if doesn't already exist)
4. Add the private key to the kubernetes cluster as a secret:
```kubectl -n core-build-system create secret generic deployment-controller-secrets --from-file=<KEY_NAME_IN_DEPLOYMENT>=<KEY_NAME> --from-file=<KEY_NAME_IN_DEPLOYMENT>=<KEY_NAME>```
where <KEY_NAME_IN_DEPLOYMENT> (also the subPath) is the name of the key in `deployment_dev.yml`/ `deployment_prod.yml`. and <KEY_NAME> is the name of the key you generated.

Example: --from-file=adbuild-key=deployment_controller
Example: --from-file=id_ed25519=id_ed25519

5. Add the key's .pub to `authorized_keys`
6. Repeat the previous step for each facility. Like s3df, or dev-srv09, or mcclogin. For production facilities, we need to ask Ken Brobeck to add `adbuild` ssh keys to production, and mcclogin is the jump host.
7. Double check the `config` file that is the ssh config file that gets copied to the deployment controllers `~/.ssh` directory.

Then the deployment controller should be able to login to the necessary facilities

## Testing
Please refer to build_deploy_scripts/test_deployment_controller.py

## How to build
### deployment controller
Use tag `"dev"` if doing dev work
1. Go to top of repo and enter command:
`docker build --tag ghcr.io/ad-build-test/deployment-controller:latest -f deploy_controller/Dockerfile .`

2. Push image
`docker push ghcr.io/ad-build-test/deployment-controller:latest`
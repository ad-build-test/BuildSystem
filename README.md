# BuildSystem
## Contents
1. Command line interface
2. Base build environments
3. Build scripts
4. Artifact storage
5. Deployment scripts
6. Deployment controller
## Resources
Confluence page: https://confluence.slac.stanford.edu/display/LCLSControls/New+Build+System

Jira: https://jira.slac.stanford.edu/projects/EEDSWCM/

## Development
Any new changes please do the following (todo: may make a github action for this):
1. Update the RELEASE_NOTES.md accordingly.
2. If you update the deployment controller, build and push deployment controller image to tag `dev` (`latest` when ready for prod)
3. If you update the cli, update version on setup.py. Then once merged to main, then update the cli on dev-srv09 with regular pip install. Repo exists at `/sdf/group/ad/eed/ad-build/BuildSystem/`
4. If you update the build scripts, build and push build_envs images to tag `dev` (`latest` when ready for prod)

Since the cli and deployment controller point to the production `ad-build` cluster. You must update the endpoints to point to `ad-build-dev` cluster when doing development. 
1. Update bs_cli/adbs_cli/cli_configuration.py
2. And the deployment_controller.py points to `ad-build` cluster. So to point it to `ad-build-dev`, update the BACKEND_URL in that file, and if you want to test changes, push it with tag `dev` instead of `latest`.

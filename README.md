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
2. If you update the deployment controller, build and push deployment controller image to tag `dev` (`latest` when ready for prod), then redeploy to prod cluster.
3. If you update the cli, update version on setup.py. Then once merged to main, then update the cli on dev-srv09 with regular pip install. Repo exists at `/sdf/group/ad/eed/ad-build/BuildSystem/`
4. If you update the build scripts, build and push build_envs images to tag `dev` (`latest` when ready for prod)

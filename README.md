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
Since the cli and deployment controller point to the production `ad-build` cluster. You must update the endpoints to point to `ad-build-dev` cluster when doing development. 
1. Update bs_cli/adbs_cli/cli_configuration.py
2. And the deployment_controller.py points to `ad-build` cluster. So to point it to `ad-build-dev`, update the BACKEND_URL in that file, and if you want to test changes, push it with tag `dev` instead of latest.

# RELEASE_NOTES

Release notes for the AD Build System (Software Factory)

## Releases:
* tag:1.1.9 17-Dec-2025 P. Nisperos (pnispero)
  * Small fix remove temporary return to onboard repo admin command

* tag:1.1.8 17-Dec-2025 P. Nisperos (pnispero)
  * Small fix to onboard repo admin command

* tag:1.1.7 11-Dec-2025 P. Nisperos (pnispero)
  * Updated deployment controller to return elog url if deployed from github directly. 
  * Added github workflow deployment file to admin onboarding command

* tag:1.1.6 3-Dec-2025 P. Nisperos (pnispero)
  * Added admin command to update IOC deployment entry if accidentally used. 

* tag:1.1.5 18-Nov-2025 P. Nisperos (pnispero)
  * Added error checking to bs clone. Added comment on deployment controller to ensure latest OS "wins" deployment if multiple OS deployed for an app. 

* tag:1.1.4 17-Nov-2025 P. Nisperos (pnispero)
  * Added additional field for the config.yaml named runtimeDependencies.

* tag:1.1.3 17-Nov-2025 P. Nisperos (pnispero)
  * Fixed bug with admin adding initial deployment configuration. Merged onboarding steps into one command for simplicity. 

* tag:1.1.2 12-Nov-2025 P. Nisperos (pnispero)
  * Added list components that are ported over to software factory command to CLI, and can search. 

* tag:1.1.1 12-Nov-2025 P. Nisperos (pnispero)
  * Restuctured IOC deployments to run deployment task in background, and immediately return task id to client, that will later be used to poll status. Fixed bug with IOC deployments that may take a few minutes and retries the request.
  * Updated CLI with the new deployment polling feature.
  * Moved deployment scripts to deploy_controller/

* tag:1.1.0 3-Nov-2025 P. Nisperos (pnispero)
  * Added api calls to ELOG for writing deployments and their reports

* tag:1.0.21 3-Nov-2025 P. Nisperos (pnispero)
  * Admin cli made environments optional for non-ioc applications

* tag:1.0.20 28-Oct-2025 P. Nisperos (pnispero)
  * Renamed facility S3DF to sandbox

* tag:1.0.19 19-Sep-2025 P. Nisperos (pnispero)
  * Updated bs cli - Added in --reboot option for bs deploy
  * Added IOC reboot functionality to the deployment controller
  * Moved deployment reports to ~/software_deployment_reports/component/

* tag:1.0.18 09-Sep-2025 P. Nisperos (pnispero)
  * Updated bs cli - Added in --revert option for bs deploy
  * Added IOC revert functionality to the deployment controller

* tag:1.0.17 06-Aug-2025 P. Nisperos (pnispero)
  * Updated bs cli - removed bs generate-config and moved it over to admin configure-repo

* tag:1.0.16 04-Aug-2025 P. Nisperos (pnispero)
  * Updated deployment controller for a longer timeout for a request (for large deployments)
  * Updated deployment controller paths to playbooks for different facilities
  * Updated bs deploy CLI output

* tag:1.0.15 24-Jul-2025 P. Nisperos (pnispero)
  * Updated deployment controller to account for IOCs that exist in more than one facility
  * Updated bs deploy CLI accordingly

* tag:1.0.14 11-Jun-2025 P. Nisperos (pnispero)
  * Updated deployment controller to include ssh key for production facilities
  * Updated deployment controller ssh config

* tag:1.0.13 21-May-2025 P. Nisperos (pnispero)
  * Changed deployment controller for pydm deployments, more robust.
  * Ommitted the pydm update-db option for easier usage
  * Created testing module for the cli, specifically bs deploy for pydm.
  * Changed bs create branch to default to branch off of branch user is sitting in

* tag:1.0.12 20-May-2025 P. Nisperos (pnispero)
  * EEDSWCM-134
  * Redesigned deployment controller for IOC deployments, more robust.
  * Added a bunch of error checks, and ommitted the update-db option for easier usage
  * Created testing module for the cli, specifically bs deploy.

* tag:1.0.11 14-May-2025 P. Nisperos (pnispero)
  * Updated log of build container to use $AD_BUILD_SCRATCH instead of /mnt

* tag:1.0.10 14-May-2025 P. Nisperos (pnispero)
  * Removed forced lower casing on component names.

* tag:1.0.9 13-May-2025 P. Nisperos (pnispero)
  * Made bs clone use ssh not https. Updated bs generate-config to add the ssh url.

* tag:1.0.8 12-May-2025 P. Nisperos (pnispero)
  * Fix bug with deployment cli. Deployment type had a typo.

* tag:1.0.7 9-May-2025 P. Nisperos (pnispero)
  * Fix bug with word casing on initial deployment configuration
  * Sorted iocs by alphabetical order before displaying to user bs deploy --list

* tag:1.0.6 9-May-2025 P. Nisperos (pnispero)
  * Added admin cli command to add an initial deployment configuration easier
  * Fix some typos with deployment command

* tag:1.0.5 7-May-2025 P. Nisperos (pnispero)
  * Added support for multiple os deployments
  * Made cli - build more simple (removed local and container builds for now)

* tag:1.0.4 17-Apr-2025 P. Nisperos (pnispero)
  * Added in changes to fix admin cli to just parse the yaml file instead
  * Refactor the cli api endpoints to be declared in cli_configuration.py

* tag:1.0.3 16-Apr-2025 P. Nisperos (pnispero)
  * Added proper sourcing dev environment for build containers before starting build
  * Fix bug with admin cli

* tag:1.0.2 14-Apr-2025 P. Nisperos (pnispero)
  * Added support for PyDM display workflow
  * Added deploymentTypes field for config.yaml which works for IOC and now pydm.

* tag:1.0.1 27-Mar-2025 P. Nisperos (pnispero)
  * Added ssh keys and edited configuration for deployment controller to point to adbuild user
  * Added environment variable AD_BUILD_PROD for easy switching from dev to prod clusters

* tag:1.0.0 24-Mar-2025 P. Nisperos (pnispero)
  * Added deployment type to a component's config.yaml. Updated --new to --update-db for deployment cli.
  * Added sanity check for deployment to ALL iocs - ensure database is the same as component source tree.
  * Point CLI and deployment controller to production cluster now.

* tag:1.0.6b0 13-Mar-2025 P. Nisperos (pnispero)
  * Updated deployment controller with bug fixes with mount paths, ansible ssh pipelining. And more error checking in deployment cli.

* tag:1.0.5b0 13-Mar-2025 P. Nisperos (pnispero)
  * Bug fix for local build, added build script for BuildSystem itself
  
* tag:1.0.4b0 12-Mar-2025 P. Nisperos (pnispero)
  * Removed unnecessary prints from cli

* tag:1.0.3b0 11-Mar-2025 P. Nisperos (pnispero)
  * Bug fix for repos with camelCase

* tag:1.0.2b0 11-Mar-2025 P. Nisperos (pnispero)
  * Patch for cli autocomplete

* tag:1.0.1b0 11-Mar-2025 P. Nisperos (pnispero)
  * Bug fix for cli autocomplete

* tag:1.0.0b0 10-Mar-2025 P. Nisperos (pnispero)
  * Beta release
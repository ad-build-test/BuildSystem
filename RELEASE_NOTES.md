# RELEASE_NOTES

Release notes for the AD Build System (Software Factory)

## Releases:
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
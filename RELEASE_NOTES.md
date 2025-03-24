# RELEASE_NOTES

Release notes for the AD Build System (Software Factory)

## Releases:
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
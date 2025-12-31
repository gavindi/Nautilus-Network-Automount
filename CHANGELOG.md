# Changelog

All notable changes to this project will be documented in this file.

## [Build 20251231-2] - 2025-12-31

### Added
- Right-click menu now appears when clicking on blank space inside a network share folder

## [Build 20251231] - 2025-12-31

### Added
- Initial release of Network Share Auto-Mounter
- Nautilus extension with right-click "Enable/Disable Auto-mount" menu
- Self-installing architecture: extension automatically creates service components on first load
- Background systemd service that mounts enabled shares every 60 seconds
- Support for SMB, SFTP, FTP, DAV, and DAVS network protocols
- GTK4/Adwaita GUI installer (`install.sh`)
- Headless installation support via `--install` and `--uninstall` command line options
- Fuzzy matching for bookmark URIs to handle path variations
- Automatic systemd service registration and management

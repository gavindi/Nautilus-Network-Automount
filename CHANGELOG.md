# Changelog

All notable changes to this project will be documented in this file.

## [Build 20260103] - 2026-01-03

### Changed
- Reduced code duplication by extracting shared menu item logic into helper method
- Added mtime-based caching for bookmark file reads to reduce I/O
- Replaced bare except clauses with specific exception types for better error handling
- Service restart now runs in background to avoid blocking Nautilus UI
- Optimized string splitting with early termination (`split(' ', 1)`)
- Service script now uses file monitoring for preferences instead of polling
- Increased fallback polling interval from 300s to 600s (file monitoring handles immediate changes)
- Added `@lru_cache` decorator to URI parsing for repeated lookups
- Replaced if/elif chain with dictionary lookup for GVFS mount paths

### Fixed
- Potential silent failures from overly broad exception handling

## [Build 20260102] - 2026-01-02

### Added
- Automatic symbolic link creation in ~/Network Files for mounted network shares
- Links are named in the format "[Share_Name] on [Server_Name]" for easy identification

### Changed
- Preferences file is now preserved on uninstall to retain user settings across reinstalls

## [Build 20260101] - 2026-01-01

### Added
- Right-click menu now appears when clicking on blank space inside a network share folder
- Network change detection using Gio.NetworkMonitor to trigger mounts immediately when connectivity changes

### Changed
- Polling interval increased from 60 seconds to 300 seconds (5 minutes) since network monitoring now handles immediate triggers

### Fixed
- Menu items now only appear when inside network share locations (smb, sftp, ftp, dav, davs)

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

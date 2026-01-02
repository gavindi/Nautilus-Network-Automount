# Network Share Auto-Mounter

A self-installing Nautilus extension for GNOME that allows users to toggle background auto-mounting for network shares (SMB, SFTP, FTP, etc.) directly from the file manager.

## 🏗️ File Architecture

The extension automatically creates all required files on first load:

| File | Path | Responsibility |
| :--- | :--- | :--- |
| **Extension** | `~/.local/share/nautilus-python/extensions/network-automount.py` | Adds "Enable/Disable Auto-mount" to the Nautilus right-click menu. Self-installs the service components below. |
| **Service Script** | `~/.local/bin/network-automount-service.py` | The background engine that mounts shares and creates symbolic links. Responds to preference changes, network changes, and polls every 10 minutes as fallback. (Auto-generated) |
| **Systemd Unit** | `~/.config/systemd/user/network-automount.service` | Ensures the service starts at login without a GUI. (Auto-generated) |
| **Preferences** | `~/.local/share/nautilus-python/automount_prefs.json` | Stores which bookmarks are currently enabled. (Auto-generated) |
| **Network Files** | `~/Network Files/` | Contains symbolic links to mounted network shares, named "[Share_Name] on [Server_Name]". (Auto-generated) |

---

## 🚀 Installation & Setup

### GUI Installer

Run the installer script to open a graphical installer:

```bash
./install.sh
```

The installer will detect whether the extension is already installed and offer to install or uninstall accordingly.

### Command Line (Headless)

For scripted or headless installations:

```bash
./install.sh --install    # Install the extension
./install.sh --uninstall  # Uninstall the extension and all components
```

### Manual Installation

Alternatively, install manually:

```bash
mkdir -p ~/.local/share/nautilus-python/extensions
cp Source/network-automount.py ~/.local/share/nautilus-python/extensions/
nautilus -q
```

When Nautilus loads the extension, it will automatically:
- Create `~/.local/bin/network-automount-service.py`
- Create `~/.config/systemd/user/network-automount.service`
- Run `systemctl --user daemon-reload`
- Enable and start the background service

---

## 🛠️ Usage

Bookmark a Share: Add a network share (e.g., smb://stornado.local/share2) to your Nautilus sidebar bookmarks.

Enable Auto-mount: Right-click the folder in Nautilus and select "Enable Auto-mount".

Background Persistence: The service will keep this share mounted, responding immediately to preference and network changes (with a 10-minute fallback poll).

Access via ~/Network Files: Mounted shares are automatically linked in your home folder under `~/Network Files/` with friendly names like "share2 on stornado.local".

### 🔍 Troubleshooting & Logs

If the shares are not mounting, check the logs of the background service in real-time:

```bash
journalctl --user -u network-automount.service -f
```

To verify the service is active and running:

```bash
systemctl --user status network-automount.service
```

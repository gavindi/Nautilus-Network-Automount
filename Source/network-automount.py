import os
import json
import gi
import subprocess

try:
    gi.require_version('Nautilus', '4.0')
    gi.require_version('Gio', '2.0')
except ValueError:
    pass 

from gi.repository import Nautilus, GObject, Gio, GLib

# Path Constants
BIN_DIR = os.path.expanduser("~/.local/bin")
SERVICE_DIR = os.path.expanduser("~/.config/systemd/user")
PREFS_FILE = os.path.expanduser("~/.local/share/nautilus-python/automount_prefs.json")
BOOKMARKS_FILE = os.path.expanduser("~/.config/gtk-3.0/bookmarks")
SERVICE_SCRIPT = os.path.join(BIN_DIR, "network-automount-service.py")
SYSTEMD_UNIT = os.path.join(SERVICE_DIR, "network-automount.service")

# Network protocol schemes
NETWORK_SCHEMES = ('smb://', 'sftp://', 'ftp://', 'dav://', 'davs://')

SERVICE_SCRIPT_CONTENT = """#!/usr/bin/env python3
import os
import json
import gi
import urllib.parse
from functools import lru_cache
gi.require_version('Gio', '2.0')
from gi.repository import Gio, GLib

PREFS_FILE = os.path.expanduser("~/.local/share/nautilus-python/automount_prefs.json")
BOOKMARKS_FILE = os.path.expanduser("~/.config/gtk-3.0/bookmarks")
NETWORK_MOUNTS_DIR = os.path.expanduser("~/Network Files")
UID = os.getuid()

# Cached mount path prefixes
GVFS_MOUNT_PATHS = {
    'smb': f"/run/user/{UID}/gvfs/smb-share:server={{server}},share={{share}}",
    'sftp': f"/run/user/{UID}/gvfs/sftp:host={{server}}",
    'ftp': f"/run/user/{UID}/gvfs/ftp:host={{server}}",
    'dav': f"/run/user/{UID}/gvfs/dav:host={{server}}",
    'davs': f"/run/user/{UID}/gvfs/davs:host={{server}}",
}

def get_enabled_bookmarks():
    enabled_uris = []
    if not os.path.exists(PREFS_FILE):
        return []
    try:
        with open(PREFS_FILE, 'r') as f:
            prefs = json.load(f)
    except (IOError, json.JSONDecodeError):
        return []
    if os.path.exists(BOOKMARKS_FILE):
        try:
            with open(BOOKMARKS_FILE, 'r') as f:
                for line in f:
                    uri = line.split(' ', 1)[0].strip().rstrip('/')
                    if prefs.get(uri):
                        enabled_uris.append(uri)
        except IOError:
            pass
    return enabled_uris

@lru_cache(maxsize=64)
def parse_uri(uri):
    \"\"\"Parse a network URI and return (scheme, server, share).\"\"\"
    parsed = urllib.parse.urlparse(uri)
    scheme = parsed.scheme
    server = parsed.hostname or ""
    path_parts = parsed.path.strip('/').split('/')
    share = path_parts[0] if path_parts else ""
    return scheme, server, share

def get_gvfs_mount_path(scheme, server, share):
    \"\"\"Get the gvfs mount path for a network share.\"\"\"
    template = GVFS_MOUNT_PATHS.get(scheme)
    if template:
        return template.format(server=server, share=share)
    return None

def create_symlink(uri):
    \"\"\"Create a symlink in ~/Network Mounts for a mounted share.\"\"\"
    scheme, server, share = parse_uri(uri)
    if not server:
        return

    gvfs_path = get_gvfs_mount_path(scheme, server, share)
    if not gvfs_path or not os.path.exists(gvfs_path):
        return

    os.makedirs(NETWORK_MOUNTS_DIR, exist_ok=True)

    # Create link name: "[Share_Name] on [Server_Name]"
    link_name = f"{share} on {server}" if share else f"{scheme} on {server}"
    link_path = os.path.join(NETWORK_MOUNTS_DIR, link_name)

    # Remove existing symlink if it exists
    if os.path.islink(link_path):
        os.unlink(link_path)
    elif os.path.exists(link_path):
        return  # Don't overwrite non-symlink files

    try:
        os.symlink(gvfs_path, link_path)
    except OSError:
        pass

def mount_callback(source, result, uri):
    \"\"\"Callback after mount attempt completes.\"\"\"
    try:
        source.mount_enclosing_volume_finish(result)
    except GLib.Error:
        pass
    # Try to create symlink regardless (mount may already exist)
    GLib.timeout_add_seconds(2, lambda: create_symlink(uri) or False)

def mount_all():
    for uri in get_enabled_bookmarks():
        try:
            f = Gio.File.new_for_uri(uri)
            f.mount_enclosing_volume(Gio.MountMountFlags.NONE, None, None, mount_callback, uri)
        except GLib.Error:
            # Mount may already exist, try creating symlink anyway
            create_symlink(uri)
    return True

def on_network_changed(_monitor, available):
    if available:
        mount_all()

def on_prefs_changed(_monitor, _file, _other_file, event_type):
    if event_type == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
        mount_all()

if __name__ == "__main__":
    mount_all()
    loop = GLib.MainLoop()

    # Watch for preference file changes instead of polling
    prefs_file = Gio.File.new_for_path(PREFS_FILE)
    prefs_monitor = prefs_file.monitor_file(Gio.FileMonitorFlags.NONE, None)
    prefs_monitor.connect("changed", on_prefs_changed)

    # Periodic remount as fallback (less frequent since we watch files)
    GLib.timeout_add_seconds(600, mount_all)

    # Network change monitoring
    network_monitor = Gio.NetworkMonitor.get_default()
    network_monitor.connect("network-changed", on_network_changed)

    loop.run()
"""

SYSTEMD_UNIT_CONTENT = f"""[Unit]
Description=Network Share Auto-Mount Service
After=network-online.target

[Service]
ExecStart=/usr/bin/python3 {SERVICE_SCRIPT}
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
"""

class NetworkAutoMounter(GObject.GObject, Nautilus.MenuProvider):
    def __init__(self):
        super().__init__()
        self._bookmark_cache = None
        self._bookmark_mtime = 0
        self._ensure_installation()
        self.prefs = self._load_prefs()
        print(">>> Network Auto-Mounter: Initialized and Installation Verified <<<")

    def _ensure_installation(self):
        """Creates the background service files if they don't exist."""
        try:
            os.makedirs(BIN_DIR, exist_ok=True)
            os.makedirs(SERVICE_DIR, exist_ok=True)

            # Write Service Script
            if not os.path.exists(SERVICE_SCRIPT):
                with open(SERVICE_SCRIPT, "w") as f:
                    f.write(SERVICE_SCRIPT_CONTENT)
                os.chmod(SERVICE_SCRIPT, 0o755)

            # Write Systemd Unit
            if not os.path.exists(SYSTEMD_UNIT):
                with open(SYSTEMD_UNIT, "w") as f:
                    f.write(SYSTEMD_UNIT_CONTENT)

                # Register with systemd
                subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
                subprocess.run(["systemctl", "--user", "enable", "network-automount.service"], check=True)
                subprocess.run(["systemctl", "--user", "start", "network-automount.service"], check=True)
                print(">>> Systemd service installed and started.")
        except (OSError, subprocess.SubprocessError) as e:
            print(f">>> Installation error: {e}")

    def _load_prefs(self):
        if os.path.exists(PREFS_FILE):
            try:
                with open(PREFS_FILE, 'r') as f:
                    return json.load(f)
            except (IOError, json.JSONDecodeError):
                pass
        return {}

    def get_bookmark_uris(self):
        """Get network bookmark URIs with mtime-based caching."""
        try:
            mtime = os.path.getmtime(BOOKMARKS_FILE)
            if self._bookmark_cache is not None and mtime == self._bookmark_mtime:
                return self._bookmark_cache
            self._bookmark_mtime = mtime
        except OSError:
            return []

        bookmarks = []
        try:
            with open(BOOKMARKS_FILE, 'r') as f:
                for line in f:
                    uri = line.split(' ', 1)[0].strip().rstrip('/')
                    if uri.startswith(NETWORK_SCHEMES):
                        bookmarks.append(uri)
        except IOError:
            return []

        self._bookmark_cache = bookmarks
        return bookmarks

    def is_fuzzy_match(self, current_uri):
        current_parts = current_uri.split('/')
        if len(current_parts) < 4:
            return None
        current_share_name = current_parts[3]
        for b_uri in self.get_bookmark_uris():
            b_parts = b_uri.split('/')
            if len(b_parts) < 4:
                continue
            if b_parts[3] == current_share_name:
                return b_uri
        return None

    def _create_menu_item(self, uri, item_name):
        """Helper to create automount toggle menu item."""
        if not uri.startswith(NETWORK_SCHEMES):
            return []
        matched_bookmark = self.is_fuzzy_match(uri)
        if matched_bookmark:
            is_enabled = self.prefs.get(matched_bookmark, False)
            label = "Disable Auto-mount" if is_enabled else "Enable Auto-mount"
            item = Nautilus.MenuItem(name=item_name, label=label)
            item.connect("activate", self.toggle_automount, matched_bookmark)
            return [item]
        return []

    def get_file_items(self, *args):
        files = args[-1]
        if not files or len(files) != 1 or not files[0].is_directory():
            return []
        uri = files[0].get_uri().rstrip('/')
        return self._create_menu_item(uri, "NetworkAutoMounter::Toggle")

    def get_background_items(self, *args):
        folder = args[-1]
        if not folder:
            return []
        uri = folder.get_uri().rstrip('/')
        return self._create_menu_item(uri, "NetworkAutoMounter::BackgroundToggle")

    def toggle_automount(self, _menu, bookmark_uri):
        self.prefs[bookmark_uri] = not self.prefs.get(bookmark_uri, False)
        os.makedirs(os.path.dirname(PREFS_FILE), exist_ok=True)
        with open(PREFS_FILE, 'w') as f:
            json.dump(self.prefs, f)
        # Force the service to notice the change immediately (non-blocking)
        subprocess.Popen(
            ["systemctl", "--user", "restart", "network-automount.service"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

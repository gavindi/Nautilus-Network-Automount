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
SERVICE_SCRIPT = os.path.join(BIN_DIR, "network-automount-service.py")
SYSTEMD_UNIT = os.path.join(SERVICE_DIR, "network-automount.service")

SERVICE_SCRIPT_CONTENT = """#!/usr/bin/env python3
import os
import json
import gi
gi.require_version('Gio', '2.0')
from gi.repository import Gio, GLib

PREFS_FILE = os.path.expanduser("~/.local/share/nautilus-python/automount_prefs.json")
BOOKMARKS_FILE = os.path.expanduser("~/.config/gtk-3.0/bookmarks")

def get_enabled_bookmarks():
    enabled_uris = []
    if not os.path.exists(PREFS_FILE): return []
    with open(PREFS_FILE, 'r') as f:
        prefs = json.load(f)
    if os.path.exists(BOOKMARKS_FILE):
        with open(BOOKMARKS_FILE, 'r') as f:
            for line in f:
                uri = line.split(' ')[0].strip().rstrip('/')
                if prefs.get(uri): enabled_uris.append(uri)
    return enabled_uris

def mount_all():
    for uri in get_enabled_bookmarks():
        try:
            f = Gio.File.new_for_uri(uri)
            f.mount_enclosing_volume(Gio.MountMountFlags.NONE, None, None, None, None)
        except: pass
    return True

def on_network_changed(monitor, available):
    if available:
        mount_all()

if __name__ == "__main__":
    mount_all()
    loop = GLib.MainLoop()
    GLib.timeout_add_seconds(300, mount_all)
    monitor = Gio.NetworkMonitor.get_default()
    monitor.connect("network-changed", on_network_changed)
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
        except Exception as e:
            print(f">>> Installation error: {e}")

    def _load_prefs(self):
        if os.path.exists(PREFS_FILE):
            try:
                with open(PREFS_FILE, 'r') as f: return json.load(f)
            except: pass
        return {}

    def get_bookmark_uris(self):
        bookmarks = []
        path = os.path.expanduser("~/.config/gtk-3.0/bookmarks")
        if os.path.exists(path):
            with open(path, 'r') as f:
                for line in f:
                    uri = line.split(' ')[0].strip().rstrip('/')
                    if uri.startswith(('smb://', 'sftp://', 'ftp://', 'dav://', 'davs://')):
                        bookmarks.append(uri)
        return bookmarks

    def is_fuzzy_match(self, current_uri):
        current_parts = current_uri.split('/')
        if len(current_parts) < 4: return None
        current_share_name = current_parts[3]
        for b_uri in self.get_bookmark_uris():
            b_parts = b_uri.split('/')
            if len(b_parts) < 4: continue
            if b_parts[3] == current_share_name:
                return b_uri 
        return None

    def get_file_items(self, *args):
        files = args[-1]
        if not files or len(files) != 1 or not files[0].is_directory(): return []
        uri = files[0].get_uri().rstrip('/')
        if not uri.startswith(('smb://', 'sftp://', 'ftp://', 'dav://', 'davs://')):
            return []
        matched_bookmark = self.is_fuzzy_match(uri)

        if matched_bookmark:
            is_enabled = self.prefs.get(matched_bookmark, False)
            label = "Disable Auto-mount" if is_enabled else "Enable Auto-mount"
            item = Nautilus.MenuItem(name="NetworkAutoMounter::Toggle", label=label)
            item.connect("activate", self.toggle_automount, matched_bookmark)
            return [item]
        return []

    def get_background_items(self, *args):
        folder = args[-1]
        if not folder:
            return []

        uri = folder.get_uri().rstrip('/')
        if not uri.startswith(('smb://', 'sftp://', 'ftp://', 'dav://', 'davs://')):
            return []
        matched_bookmark = self.is_fuzzy_match(uri)

        if matched_bookmark:
            is_enabled = self.prefs.get(matched_bookmark, False)
            label = "Disable Auto-mount" if is_enabled else "Enable Auto-mount"
            item = Nautilus.MenuItem(name="NetworkAutoMounter::BackgroundToggle", label=label)
            item.connect("activate", self.toggle_automount, matched_bookmark)
            return [item]
        return []

    def toggle_automount(self, menu, bookmark_uri):
        self.prefs[bookmark_uri] = not self.prefs.get(bookmark_uri, False)
        os.makedirs(os.path.dirname(PREFS_FILE), exist_ok=True)
        with open(PREFS_FILE, 'w') as f: json.dump(self.prefs, f)
        # Force the service to notice the change immediately
        subprocess.run(["systemctl", "--user", "restart", "network-automount.service"])

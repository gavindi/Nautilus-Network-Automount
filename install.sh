#!/usr/bin/env python3

import os
import sys
import argparse
import subprocess

# File paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_FILE = os.path.join(SCRIPT_DIR, "Source", "network-automount.py")
EXTENSIONS_DIR = os.path.expanduser("~/.local/share/nautilus-python/extensions")
EXTENSION_FILE = os.path.join(EXTENSIONS_DIR, "network-automount.py")
SERVICE_SCRIPT = os.path.expanduser("~/.local/bin/network-automount-service.py")
SYSTEMD_UNIT = os.path.expanduser("~/.config/systemd/user/network-automount.service")
PREFS_FILE = os.path.expanduser("~/.local/share/nautilus-python/automount_prefs.json")


def headless_install():
    """Install the extension without GUI."""
    try:
        if not os.path.exists(SOURCE_FILE):
            print(f"Error: Source file not found: {SOURCE_FILE}")
            return 1

        os.makedirs(EXTENSIONS_DIR, exist_ok=True)

        with open(SOURCE_FILE, 'r') as src:
            content = src.read()
        with open(EXTENSION_FILE, 'w') as dst:
            dst.write(content)

        subprocess.run(["nautilus", "-q"], stderr=subprocess.DEVNULL)

        print("Installed successfully!")
        print("Restart Nautilus to activate the extension.")
        return 0

    except Exception as e:
        print(f"Installation failed: {e}")
        return 1


def headless_uninstall():
    """Uninstall the extension without GUI."""
    try:
        subprocess.run(["systemctl", "--user", "stop", "network-automount.service"],
                      stderr=subprocess.DEVNULL)
        subprocess.run(["systemctl", "--user", "disable", "network-automount.service"],
                      stderr=subprocess.DEVNULL)

        files_to_remove = [EXTENSION_FILE, SERVICE_SCRIPT, SYSTEMD_UNIT, PREFS_FILE]
        for f in files_to_remove:
            if os.path.exists(f):
                os.remove(f)
                print(f"Removed: {f}")

        subprocess.run(["systemctl", "--user", "daemon-reload"], stderr=subprocess.DEVNULL)
        subprocess.run(["nautilus", "-q"], stderr=subprocess.DEVNULL)

        print("Uninstalled successfully!")
        return 0

    except Exception as e:
        print(f"Uninstall failed: {e}")
        return 1


def run_gui():
    """Launch the GUI installer."""
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Adw', '1')
    from gi.repository import Gtk, Adw

    class InstallerWindow(Adw.ApplicationWindow):
        def __init__(self, app):
            super().__init__(application=app, title="Network Auto-Mounter")
            self.set_default_size(400, 250)

            self.is_installed = os.path.exists(EXTENSION_FILE)

            # Main layout
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
            box.set_margin_top(30)
            box.set_margin_bottom(30)
            box.set_margin_start(30)
            box.set_margin_end(30)

            # Header
            header = Gtk.Label(label="Network Share Auto-Mounter")
            header.add_css_class("title-1")
            box.append(header)

            # Status
            if self.is_installed:
                status_text = "Status: Installed"
                status_class = "success"
            else:
                status_text = "Status: Not Installed"
                status_class = "dim-label"

            self.status_label = Gtk.Label(label=status_text)
            self.status_label.add_css_class(status_class)
            box.append(self.status_label)

            # Description
            desc = Gtk.Label(label="Automatically mount network shares (SMB, SFTP, FTP)\nfrom your Nautilus bookmarks at login.")
            desc.set_wrap(True)
            desc.set_justify(Gtk.Justification.CENTER)
            desc.add_css_class("dim-label")
            box.append(desc)

            # Spacer
            box.append(Gtk.Box(vexpand=True))

            # Buttons
            button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            button_box.set_halign(Gtk.Align.CENTER)

            if self.is_installed:
                self.action_button = Gtk.Button(label="Uninstall")
                self.action_button.add_css_class("destructive-action")
                self.action_button.connect("clicked", self.on_uninstall)
            else:
                self.action_button = Gtk.Button(label="Install")
                self.action_button.add_css_class("suggested-action")
                self.action_button.connect("clicked", self.on_install)

            self.action_button.set_size_request(120, -1)
            button_box.append(self.action_button)

            close_button = Gtk.Button(label="Close")
            close_button.set_size_request(120, -1)
            close_button.connect("clicked", lambda _: self.close())
            button_box.append(close_button)

            box.append(button_box)

            # Message label
            self.message_label = Gtk.Label(label="")
            self.message_label.set_wrap(True)
            box.append(self.message_label)

            self.set_content(box)

        def on_install(self, button):
            try:
                if not os.path.exists(SOURCE_FILE):
                    self.show_message(f"Source file not found:\n{SOURCE_FILE}", error=True)
                    return

                os.makedirs(EXTENSIONS_DIR, exist_ok=True)

                with open(SOURCE_FILE, 'r') as src:
                    content = src.read()
                with open(EXTENSION_FILE, 'w') as dst:
                    dst.write(content)

                subprocess.run(["nautilus", "-q"], stderr=subprocess.DEVNULL)

                self.show_message("Installed successfully!\nRestart Nautilus to activate.")
                self.update_ui(installed=True)

            except Exception as e:
                self.show_message(f"Installation failed:\n{e}", error=True)

        def on_uninstall(self, button):
            try:
                subprocess.run(["systemctl", "--user", "stop", "network-automount.service"],
                              stderr=subprocess.DEVNULL)
                subprocess.run(["systemctl", "--user", "disable", "network-automount.service"],
                              stderr=subprocess.DEVNULL)

                files_to_remove = [EXTENSION_FILE, SERVICE_SCRIPT, SYSTEMD_UNIT, PREFS_FILE]
                for f in files_to_remove:
                    if os.path.exists(f):
                        os.remove(f)

                subprocess.run(["systemctl", "--user", "daemon-reload"], stderr=subprocess.DEVNULL)
                subprocess.run(["nautilus", "-q"], stderr=subprocess.DEVNULL)

                self.show_message("Uninstalled successfully!")
                self.update_ui(installed=False)

            except Exception as e:
                self.show_message(f"Uninstall failed:\n{e}", error=True)

        def update_ui(self, installed):
            self.is_installed = installed

            if installed:
                self.status_label.set_text("Status: Installed")
                self.status_label.remove_css_class("dim-label")
                self.status_label.add_css_class("success")
                self.action_button.set_label("Uninstall")
                self.action_button.remove_css_class("suggested-action")
                self.action_button.add_css_class("destructive-action")
                self.action_button.disconnect_by_func(self.on_install)
                self.action_button.connect("clicked", self.on_uninstall)
            else:
                self.status_label.set_text("Status: Not Installed")
                self.status_label.remove_css_class("success")
                self.status_label.add_css_class("dim-label")
                self.action_button.set_label("Install")
                self.action_button.remove_css_class("destructive-action")
                self.action_button.add_css_class("suggested-action")
                self.action_button.disconnect_by_func(self.on_uninstall)
                self.action_button.connect("clicked", self.on_install)

        def show_message(self, text, error=False):
            self.message_label.set_text(text)
            self.message_label.remove_css_class("error")
            self.message_label.remove_css_class("success")
            if error:
                self.message_label.add_css_class("error")
            else:
                self.message_label.add_css_class("success")

    class InstallerApp(Adw.Application):
        def __init__(self):
            super().__init__(application_id="com.github.nautilus.network-automount.installer")
            self.connect("activate", self.on_activate)

        def on_activate(self, app):
            win = InstallerWindow(app)
            win.present()

    app = InstallerApp()
    app.run([])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Network Share Auto-Mounter Installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Run without arguments to launch the GUI installer."
    )
    parser.add_argument("--install", action="store_true", help="Install the extension (headless)")
    parser.add_argument("--uninstall", action="store_true", help="Uninstall the extension (headless)")

    args = parser.parse_args()

    if args.install and args.uninstall:
        print("Error: Cannot use --install and --uninstall together")
        sys.exit(1)
    elif args.install:
        sys.exit(headless_install())
    elif args.uninstall:
        sys.exit(headless_uninstall())
    else:
        run_gui()

"""Output-folder picker helpers with Linux volume sidebar URLs."""

from __future__ import annotations

import os
import sys
from typing import List, Optional, Sequence

# Device filesystem types we treat as browsable volumes (USB / internal mounts).
_VOLUME_FS_TYPES = frozenset(
    {
        "ext2",
        "ext3",
        "ext4",
        "xfs",
        "btrfs",
        "f2fs",
        "ntfs",
        "vfat",
        "exfat",
        "fuseblk",
        "fuse.ntfs",
        "fuse.exfat",
        "fuse.sshfs",
        "nfs",
        "nfs4",
        "cifs",
        "smb3",
        "zfs",
    }
)

_SKIP_MOUNT_PREFIXES = (
    "/proc",
    "/sys",
    "/dev",
    "/run/user",
    "/snap",
    "/boot",
    "/var/lib/docker",
    "/var/lib/containers",
)


def _user_name() -> str:
    return (
        os.environ.get("USER")
        or os.environ.get("LOGNAME")
        or os.path.basename(os.path.expanduser("~"))
        or "user"
    )


def _existing_dir(path: str) -> Optional[str]:
    try:
        if path and os.path.isdir(path):
            return os.path.abspath(path)
    except OSError:
        return None
    return None


def discover_mount_points(proc_mounts: Optional[str] = None) -> List[str]:
    """
    Return absolute mount points for user-visible volumes.

    Reads ``/proc/mounts`` (or ``proc_mounts`` text) and keeps paths under
    ``/run/media``, ``/media``, ``/mnt``, plus other real device mounts with
    common filesystem types. Always includes those roots when they exist.
    """
    text = proc_mounts
    if text is None:
        try:
            with open("/proc/mounts", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            text = ""

    found: List[str] = []
    seen = set()

    def add(path: str) -> None:
        abs_path = _existing_dir(path)
        if not abs_path or abs_path in seen:
            return
        seen.add(abs_path)
        found.append(abs_path)

    user = _user_name()
    for root in (
        f"/run/media/{user}",
        f"/media/{user}",
        "/run/media",
        "/media",
        "/mnt",
    ):
        add(root)

    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        source, target, fstype = parts[0], parts[1], parts[2]
        # Unescape octal sequences used in /proc/mounts (e.g. \040 for space).
        target = (
            target.replace("\\040", " ")
            .replace("\\011", "\t")
            .replace("\\012", "\n")
            .replace("\\134", "\\")
        )
        if any(target == p or target.startswith(p + "/") for p in _SKIP_MOUNT_PREFIXES):
            continue
        if target in ("/", "/home", "/usr", "/var", "/opt", "/tmp"):
            # Keep root only as Computer entry elsewhere; skip OS partitions here
            # unless they sit under media/mnt roots (handled via children).
            if not (
                target.startswith("/run/media/")
                or target.startswith("/media/")
                or target.startswith("/mnt/")
            ):
                continue
        is_media = (
            target.startswith("/run/media/")
            or target.startswith("/media/")
            or target.startswith("/mnt/")
        )
        looks_device = source.startswith("/dev/") or fstype in _VOLUME_FS_TYPES
        if is_media or looks_device:
            if fstype in _VOLUME_FS_TYPES or is_media or source.startswith("/dev/"):
                add(target)

    # Direct children of media roots (covers mounts not yet listed as FS type).
    for root in (f"/run/media/{user}", f"/media/{user}", "/mnt"):
        try:
            for name in sorted(os.listdir(root)):
                add(os.path.join(root, name))
        except OSError:
            pass

    return found


def volume_sidebar_paths(
    *,
    home: Optional[str] = None,
    downloads: Optional[str] = None,
    proc_mounts: Optional[str] = None,
    extra: Optional[Sequence[str]] = None,
) -> List[str]:
    """
    Ordered sidebar paths: Home, Downloads, media roots, discovered mounts.

    Pure path helper (no Qt) so unit tests can run without a display.
    """
    home_path = _existing_dir(home or os.path.expanduser("~")) or os.path.expanduser("~")
    dl = downloads or os.path.join(home_path, "Downloads")
    paths: List[str] = []
    seen = set()

    def add(path: str) -> None:
        abs_path = _existing_dir(path)
        if not abs_path or abs_path in seen:
            return
        seen.add(abs_path)
        paths.append(abs_path)

    add(home_path)
    add(dl)
    for m in discover_mount_points(proc_mounts=proc_mounts):
        add(m)
    if extra:
        for p in extra:
            add(p)
    return paths


def configure_directory_dialog(dialog, *, start_dir: str = "") -> None:
    """
    Apply volume sidebar URLs and Linux non-native option to a QFileDialog.

    Native GTK/KDE pickers often hide removable volumes; Qt's dialog plus
    ``setSidebarUrls`` keeps Home / media mounts visible.
    """
    from PyQt6.QtCore import QUrl
    from PyQt6.QtWidgets import QFileDialog

    dialog.setFileMode(QFileDialog.FileMode.Directory)
    dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
    if start_dir:
        dialog.setDirectory(start_dir)
    if sys.platform.startswith("linux"):
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    urls = [QUrl.fromLocalFile(p) for p in volume_sidebar_paths()]
    if urls:
        dialog.setSidebarUrls(urls)


def get_existing_directory(
    parent,
    caption: str,
    directory: str = "",
) -> str:
    """QFileDialog.getExistingDirectory replacement with volume sidebar."""
    from PyQt6.QtWidgets import QFileDialog

    start = directory or ""
    dialog = QFileDialog(parent, caption, start)
    configure_directory_dialog(dialog, start_dir=start)
    if dialog.exec():
        selected = dialog.selectedFiles()
        return selected[0] if selected else ""
    return ""

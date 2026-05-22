#!/usr/bin/env python3
"""dupguard – proactive duplicate file detector & auto‑renamer.

Core design goals (mirroring TopherBot personality):
* Detect duplicates early (name or content).
* Auto‑rename on name clash using a configurable suffix.
* Provide concise, actionable output.
* Keep parameters configurable via CLI or optional YAML.
* Emit detailed logs with timestamps.
"""

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import yaml  # optional, only used if a config file is supplied
except ImportError:  # pragma: no cover
    yaml = None

# ---------------------------------------------------------------------------
# Logging setup – always writes to a log file, optionally prints to console
# ---------------------------------------------------------------------------

def setup_logging(log_path: Path, quiet: bool) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    fmt = "%(asctime)s %(levelname)s %(message)s"
    formatter = logging.Formatter(fmt, "%Y-%m-%dT%H:%M:%S%z")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if not quiet:
        stream = logging.StreamHandler(sys.stdout)
        stream.setFormatter(formatter)
        logger.addHandler(stream)

    logger.debug("Logging initialized – file: %s, quiet: %s", log_path, quiet)

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def hash_file(path: Path) -> str:
    """Return SHA‑256 hash of file content (binary safe)."""
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def find_duplicates_by_name(root: Path) -> Dict[str, List[Path]]:
    """Group files that share the same *case‑insensitive* name.
    Returns a mapping of canonical name -> list of matching Path objects.
    """
    name_map: Dict[str, List[Path]] = {}
    for path in root.rglob("*"):
        if path.is_file():
            key = path.name.lower()
            name_map.setdefault(key, []).append(path)
    # Keep only groups with >1 entry
    return {k: v for k, v in name_map.items() if len(v) > 1}

def find_duplicates_by_content(root: Path) -> Dict[str, List[Path]]:
    """Group files that have identical content hashes.
    Returns hash -> list of Path objects.
    """
    hash_map: Dict[str, List[Path]] = {}
    for path in root.rglob("*"):
        if path.is_file():
            h = hash_file(path)
            hash_map.setdefault(h, []).append(path)
    return {h: lst for h, lst in hash_map.items() if len(lst) > 1}

def generate_new_name(original: Path, suffix_pat: str, index: int) -> Path:
    """Create a new filename based on `suffix_pat`.
    `suffix_pat` may contain `{n}` placeholder which will be replaced by `index`.
    """
    stem = original.stem
    suffix = suffix_pat.replace("{n}", str(index))
    new_name = f"{stem}{suffix}{original.suffix}"
    return original.with_name(new_name)

# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def process(root: Path, mode: str, rename: bool, suffix_pat: str, dry_run: bool) -> None:
    logger = logging.getLogger()
    logger.info("Scanning %s (mode=%s)", root, mode)

    if mode == "name":
        dup_groups = find_duplicates_by_name(root)
        desc = "filename"
    elif mode == "content":
        dup_groups = find_duplicates_by_content(root)
        desc = "file content"
    else:
        logger.error("Unsupported mode: %s", mode)
        sys.exit(1)

    if not dup_groups:
        logger.info("No duplicate %s detected.", desc)
        return

    logger.info("Found %d duplicate groups.", len(dup_groups))
    for key, paths in dup_groups.items():
        logger.info("Group [%s] – %d files:", key, len(paths))
        for p in paths:
            logger.info("  - %s", p)

        if rename:
            # Keep the first file untouched, rename the rest
            for idx, p in enumerate(paths[1:], start=1):
                new_path = generate_new_name(p, suffix_pat, idx)
                if dry_run:
                    logger.info("[dry‑run] Would rename %s → %s", p, new_path)
                else:
                    try:
                        p.rename(new_path)
                        logger.info("Renamed %s → %s", p, new_path)
                    except Exception as e:
                        logger.error("Failed to rename %s: %s", p, e)

# ---------------------------------------------------------------------------
# Argument / config handling
# ---------------------------------------------------------------------------

def load_yaml_config(path: Path) -> Dict:
    if not yaml:
        raise RuntimeError("PyYAML not installed – cannot parse config file")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def merge_config(cli_args: argparse.Namespace, file_cfg: Dict) -> Dict:
    """Command‑line overrides config file values."""
    cfg = {
        "path": Path(cli_args.path or file_cfg.get("path", ".")),
        "mode": cli_args.mode or file_cfg.get("mode", "name"),
        "rename": cli_args.rename if cli_args.rename is not None else file_cfg.get("rename", False),
        "suffix": cli_args.suffix or file_cfg.get("suffix", "_dup{n}"),
        "dry_run": cli_args.dry_run,
        "quiet": cli_args.quiet,
        "log": Path(cli_args.log or file_cfg.get("log", "dupguard.log")),
    }
    return cfg

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="dupguard – detect and optionally rename duplicate files")
    parser.add_argument("path", nargs="?", default=None, help="Directory to scan (default: cwd)")
    parser.add_argument("-m", "--mode", choices=["name", "content"], help="Detection mode")
    parser.add_argument("-r", "--rename", action="store_true", help="Rename duplicates automatically")
    parser.add_argument("-s", "--suffix", help="Rename suffix pattern (use {n} for counter)")
    parser.add_argument("-d", "--dry-run", action="store_true", help="Show actions without modifying files")
    parser.add_argument("-c", "--config", type=Path, help="Path to YAML config file")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress console output")
    parser.add_argument("-l", "--log", help="Log file path (default: dupguard.log)")
    return parser.parse_args()

# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    file_cfg = {}
    if args.config:
        file_cfg = load_yaml_config(args.config)
    cfg = merge_config(args, file_cfg)

    setup_logging(cfg["log"], cfg["quiet"])
    start = time.time()
    try:
        process(
            root=cfg["path"].resolve(),
            mode=cfg["mode"],
            rename=cfg["rename"],
            suffix_pat=cfg["suffix"],
            dry_run=cfg["dry_run"],
        )
    finally:
        elapsed = time.time() - start
        logging.getLogger().info("dupguard finished in %.2f seconds", elapsed)

if __name__ == "__main__":
    main()

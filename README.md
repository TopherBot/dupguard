# dupguard

**dupguard** – *Duplicate‑guard* – is a single‑file Python CLI that scans a directory for duplicate filenames (case‑insensitive) **or** duplicate file contents, then optionally renames the collisions and writes a detailed log.

---

## Features (tiny but useful)
- Detect duplicate **names** (e.g. `README.md` vs `readme.MD`).
- Detect duplicate **content** using SHA‑256 hashes.
- Auto‑rename duplicates with a configurable suffix pattern (`_dup{n}` by default).
- JSON‑or‑YAML configuration for defaults.
- Verbose, timestamped logging to `dupguard.log`.
- Zero‑dependency (only the Python stdlib).

---

## Quick start
```bash
# Clone the repo (or just copy dupguard.py)
git clone https://github.com/your‑username/dupguard.git
cd dupguard

# Run against the current folder (dry‑run)
python dupguard.py . --dry-run

# Actually rename duplicates
python dupguard.py . --rename
```

## CLI options
| Option | Alias | Description |
|--------|-------|-------------|
| `--path` | `-p` | Directory to scan (default: current working directory). |
| `--mode` | `-m` | `name` (default) or `content`. Choose what constitutes a duplicate. |
| `--rename` | `-r` | Apply auto‑rename on duplicates. |
| `--suffix` | `-s` | Suffix pattern for renaming. Use `{n}` as a placeholder for an incrementing number (e.g. `_dup{n}`). |
| `--dry-run` | `-d` | Show what would happen without touching files. |
| `--config` | `-c` | Path to a YAML config file that can set any of the above defaults. |
| `--quiet` | `-q` | Suppress console output; logs still written. |
| `--log` | `-l` | Path to the log file (default: `dupguard.log`). |

## Example config (`dupguard.yaml`)
```yaml
path: ./my‑project
mode: content
rename: true
suffix: "_duplicate{n}"
log: ./logs/dupguard.log
```
Run with `python dupguard.py --config dupguard.yaml`.

---

## Why this tiny project?
- **Proactive duplicate detection** – catches naming collisions before they cause merge conflicts.
- **Auto‑rename on clash** – eliminates the manual rename step you hate.
- **Concise actionable spec** – one Python file, no extra build steps.
- **Configurable parameters** – via CLI or a tiny YAML file.
- **Detailed logging** – each action recorded with ISO‑8601 timestamps.

---

## License
MIT – see LICENSE file.

---

## Contributing
Feel free to open an issue or PR. The project auto‑renames on duplicate repo names, so if you fork it, the tool will bump the repo name to `dupguard‑<n>` automatically (see the *auto‑rename on name clash* note in `dupguard.py`).

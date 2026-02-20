# jenum — Installation and Build Guide

`jenum` is a single-file Python library with no runtime dependencies. It supports three
installation paths: install from PyPI, build a wheel yourself (with or without bif), or
drop the source file directly into your project.

Python 3.11 or later is required.

---

## 1. Install from PyPI

```bash
pip install jenum
```

Then import in your code:

```python
from jenum import DEnum, MDEnum, body
```

---

## 2. Build and install locally

### 2a. Build with bif

`bif` is the project's native build tool. It manages incremental builds, artifact
versioning, and test runs.

**Prerequisites:** `bif` must be installed and on your `PATH`.

```bash
# From the project root — list available build targets
bif do -l

# Build the Python wheel (target 0)
bif do /0
```

The built wheel lands at:

```
Artifacts/none/any/jenum-<version>-<buildid>-py3-none-any.lib.whl
```

Install it with pip:

```bash
pip install Artifacts/none/any/jenum-*.lib.whl
```

To run the test suite:

```bash
bif test
```

### 2b. Build without bif (standard Python tools)

**Prerequisites:** `build` and `wheel` packages.

```bash
pip install build wheel
```

Build from the project root:

```bash
python3 -m build --outdir dist/
```

This produces two files in `dist/`:

```
dist/jenum-<version>-py3-none-any.whl   ← installable wheel
dist/jenum-<version>.tar.gz             ← source distribution
```

Install the wheel:

```bash
pip install dist/jenum-*.whl
```

---

## 3. Install directly from source (no build step)

Because `jenum` is a single file with no compiled components, you can skip the build
entirely. Copy `Source/jenum.py` into your project:

```
your_project/
├── jenum.py          ← copied from Source/jenum.py
└── your_code.py
```

Then import directly:

```python
from jenum import DEnum, MDEnum, body
```

---

## 4. Development install (editable)

To work on `jenum` itself with live changes reflected immediately:

```bash
pip install -e ".[dev]"
```

This installs `jenum` in editable mode and pulls in `pytest` for running the test suite:

```bash
cd Test && python3 -m pytest . -v
```

---

## 5. Claude Code skill

`jenum` ships with a built-in Claude Code skill that teaches Claude how to create and
use `DEnum` and `MDEnum` classes.  Install it once per project from a Python shell or
script:

```python
import jenum
jenum.claude_init()
```

This writes `.claude/skills/jenum/SKILL.md` into your project root.  Claude Code picks
it up automatically on the next session start.

To overwrite an existing installation:

```python
jenum.claude_init(force=True)
```

To install into a specific project directory:

```python
from pathlib import Path
jenum.claude_init(project_dir=Path("/path/to/your/project"))
```

Once installed, activate the skill from within Claude Code:

```
/jenum <describe what you want to build or fix>
```

---

## Uninstall

```bash
pip uninstall jenum
```

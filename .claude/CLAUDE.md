# Project Instructions

<!-- BIF:BEGIN — managed by bif, do not edit this section -->
# Bif Project Guide

This project uses **BuildItFast (bif)** as its build tool.

## Project Structure

```
Project/
├── Artifacts/   # Final build outputs (by machine/archetype)
├── Build/       # Temporary intermediate artifacts (safe to delete)
├── Config/      # Project configuration, plugins, version sets
├── Documents/   # Project documentation
├── Source/      # All source code
├── Test/        # Unit tests
├── bif.js5      # Top-level project build configuration
└── imap.yml     # Inference map (build rules and recipes)
```

## Essential Commands

| Command | Description |
|---------|-------------|
| `bif do -l` | List available build targets (numbered) |
| `bif do <n>` | Build target number `<n>` from the list |
| `bif do <n>/<m>` | Build multiple targets |
| `bif clean` | Remove build artifacts |
| `bif test` | Run project tests |
| `bif status` | Show build status |
| `bif help` | Display documentation |
| `bif <cmd> -h` | Show help for a specific command |
| `bif -h` | Show all available commands |

## Key Files

- **bif.js5** — project-level build configuration (targets, options, package name)
- **imap.yml** — inference map defining how source files map to build artifacts and recipes
- **Config/defaults.js5** — project defaults (compiler flags, paths, etc.)
- **Config/plugins/** — build plugins (copy, compile, test, etc.)

## Workflow

1. Run `bif do -l` to see what targets are available
2. Run `bif do <n>` to build a specific target
3. Run `bif test` to execute tests
4. Run `bif clean` to remove build outputs

<!-- BIF:END -->

# TELia sys automation

This folder contains automation scripts for deploy/update on the server.

## Files

- `atualizador.sh`: pulls latest code from the repo root, updates dependencies, and restarts TELia.
- `instalar_commitauto.sh`: installs alias `commitauto` in the current user's `.bashrc`.

## How to use on server

1. Give execute permission:

```bash
chmod +x servidor/atualizador.sh servidor/instalar_commitauto.sh
```

2. Install alias command:

```bash
./servidor/instalar_commitauto.sh
source ~/.bashrc
```

3. Run update any time:

```bash
commitauto
```

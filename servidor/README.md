# TELia sys automation

This folder contains automation scripts for deploy/update on the server.

## Files

- `atualizador.sh`: deploy/update flow for TELia process on the server.
- `setuptelia.sh`: idempotent setup that installs missing system packages, Python deps and Playwright browser.
- `instalar_setuptelia.sh`: installs alias `setuptelia` in the current user's `.bashrc`.

## How to use on server

1. Give execute permission:

```bash
chmod +x servidor/atualizador.sh servidor/setuptelia.sh servidor/instalar_setuptelia.sh
```

2. Install setup alias command:

```bash
./servidor/instalar_setuptelia.sh
source ~/.bashrc
```

3. Run setup any time (only installs what is missing):

```bash
setuptelia
```

4. Run deploy/update when needed:

```bash
./servidor/atualizador.sh
```

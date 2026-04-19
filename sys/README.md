# TELia sys automation

This folder contains automation scripts for deploy/update on the server.

## Files

- `atualizador.sh`: pulls latest code, updates dependencies, and restarts TELia process.
- `instalar_commitauto.sh`: installs alias `commitauto` in the current user's `.bashrc`.

## How to use on server

1. Give execute permission:

```bash
chmod +x sys/atualizador.sh sys/instalar_commitauto.sh
```

2. Install alias command:

```bash
./sys/instalar_commitauto.sh
source ~/.bashrc
```

3. Run update any time:

```bash
commitauto
```

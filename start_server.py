import argparse
import signal
import subprocess
import sys
import time
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
MAIN_FILE = ROOT_DIR / "main.py"


shutdown_requested = False


def _handle_signal(sig, _frame):
    global shutdown_requested
    shutdown_requested = True
    print(f"[launcher] Sinal recebido ({sig}). Encerrando...", flush=True)


def run_bot_forever(restart_delay: int) -> int:
    if not MAIN_FILE.exists():
        print("[launcher] Erro: main.py nao encontrado.", flush=True)
        return 1

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    while not shutdown_requested:
        print("[launcher] Iniciando TELia...", flush=True)
        process = subprocess.Popen([sys.executable, str(MAIN_FILE)], cwd=str(ROOT_DIR))

        while process.poll() is None and not shutdown_requested:
            time.sleep(1)

        if shutdown_requested:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
            return 0

        exit_code = process.returncode
        print(
            f"[launcher] TELia finalizou com codigo {exit_code}. "
            f"Reiniciando em {restart_delay}s...",
            flush=True,
        )
        time.sleep(restart_delay)

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inicia o servidor TELia e reinicia automaticamente em caso de queda.",
    )
    parser.add_argument(
        "--restart-delay",
        type=int,
        default=3,
        help="Segundos de espera antes de reiniciar o bot (padrao: 3).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.restart_delay < 0:
        print("[launcher] --restart-delay nao pode ser negativo.", flush=True)
        return 2

    return run_bot_forever(args.restart_delay)


if __name__ == "__main__":
    raise SystemExit(main())

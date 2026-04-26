import asyncio
import logging
import re
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser

logger = logging.getLogger(__name__)

_RU_BASE = "https://ru.fw.iffarroupilha.edu.br"
_APP_URL = _RU_BASE + "/sifw/"
_AGENDA_URL = _RU_BASE + "/sifw/app/agendamento.xhtml"

_LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--no-zygote",
    "--single-process",
    "--disable-extensions",
]

_DEBUG_DIR = Path("/tmp/ru_debug")


def _dbg(html: str, name: str) -> None:
    try:
        _DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        (_DEBUG_DIR / f"{name}.html").write_text(html, encoding="utf-8")
    except Exception:
        pass


async def _launch_browser() -> tuple:
    """Returns (playwright, browser)."""
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True, args=_LAUNCH_ARGS)
    return pw, browser


async def _do_login(page: Page, cpf: str, senha: str) -> tuple[bool, str]:
    try:
        await page.goto(_APP_URL, timeout=25000, wait_until="domcontentloaded")
    except Exception as e:
        return False, f"Não consegui acessar o portal: {e}"

    # Espera o formulário Keycloak
    try:
        await page.wait_for_selector("#username", timeout=15000)
    except Exception:
        if "/sifw/" in page.url and "openid-connect" not in page.url:
            return True, ""
        _dbg(await page.content(), "01_unexpected_before_login")
        return False, f"Página de login não encontrada. URL: {page.url}"

    await page.fill("#username", cpf)
    await page.fill("#password", senha)

    btn = await page.query_selector("#kc-login") or await page.query_selector("[name='login']")
    if not btn:
        return False, "Botão de login não encontrado."

    await btn.click()

    try:
        await page.wait_for_url(f"{_RU_BASE}/sifw/**", timeout=20000)
        return True, ""
    except Exception:
        pass

    if "openid-connect" in page.url:
        err_el = await page.query_selector("#input-error, .alert-error, [class*='kc-feedback']")
        err_text = ((await err_el.text_content()) if err_el else "").strip()
        _dbg(await page.content(), "02_login_failed")
        return False, f"CPF ou senha incorretos.{' ' + err_text if err_text else ''}"

    return True, ""


async def _load_agendamento(page: Page) -> bool:
    """
    Navega para agendamento.xhtml e espera o calendário PrimeFaces renderizar.
    Retorna True quando os eventos do calendário estiverem visíveis.
    """
    if "agendamento" not in page.url:
        try:
            await page.goto(_AGENDA_URL, timeout=25000, wait_until="load")
        except Exception as e:
            logger.warning("goto agendamento falhou: %s", e)
            # timeout no load é ok; o conteúdo já pode estar lá
            pass

    # Espera o calendário PrimeFaces renderizar (fc-view aparece após JS executar)
    try:
        await page.wait_for_selector(".fc-view, .fc-daygrid, .fc-event", timeout=20000)
        return True
    except Exception:
        _dbg(await page.content(), "03_calendar_not_rendered")
        return False


async def _extract_future_days(page: Page) -> list[dict]:
    """
    Extrai eventos futuros do calendário FullCalendar/PrimeFaces.
    Cada evento futuro = dia disponível para agendamento.
    """
    _dbg(await page.content(), "04_calendar_loaded")

    # Eventos futuros no calendário
    events = await page.query_selector_all(".fc-event.fc-event-future, .fc-event-future")
    days: list[dict] = []

    for ev in events:
        try:
            # Tenta pegar a data do ancestral [data-date]
            date_val: str = await ev.evaluate(
                "el => el.closest('[data-date]')?.getAttribute('data-date') || ''"
            )
            label: str = ((await ev.text_content()) or "").strip()
            if not label:
                label = date_val

            if date_val and date_val not in [d["value"] for d in days]:
                # Formata label legível: "Seg 28/04"
                try:
                    from datetime import date as _date
                    d = _date.fromisoformat(date_val)
                    day_names = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
                    friendly = f"{day_names[d.weekday()]} {d.day:02d}/{d.month:02d}"
                except Exception:
                    friendly = label or date_val

                days.append({
                    "label": friendly,
                    "value": date_val,
                    "selector": f'[data-date="{date_val}"] .fc-event-future',
                    "type": "calendar_event",
                })
        except Exception:
            continue

    return days


async def _book_single_day(page: Page, date_value: str) -> bool:
    """
    Clica no evento do dia no calendário e confirma o agendamento.
    Retorna True se confirmação foi possível.
    """
    # Clica no evento do dia
    selector = f'[data-date="{date_value}"] .fc-event'
    try:
        await page.click(selector, timeout=5000)
    except Exception:
        # Tenta clicar na célula do dia diretamente
        try:
            await page.click(f'[data-date="{date_value}"]', timeout=5000)
        except Exception as e:
            logger.warning("Não consegui clicar no dia %s: %s", date_value, e)
            return False

    # Aguarda botão de confirmação "Sim" aparecer
    try:
        await page.wait_for_selector(
            "button[id*='j_idt']:has-text('Sim'), button:has-text('Sim'), button:has-text('Confirmar')",
            timeout=8000,
        )
        btn_sim = await page.query_selector(
            "button[id*='j_idt']:has-text('Sim'), button:has-text('Sim'), button:has-text('Confirmar')"
        )
        if btn_sim:
            await btn_sim.click()
            
            # Boa prática com PrimeFaces: esperar o overlay/spinner de loading sumir
            try:
                await page.wait_for_selector(".ui-widget-overlay", state="hidden", timeout=5000)
            except Exception:
                pass
                
            await page.wait_for_timeout(1000)
            return True
    except Exception as e:
        logger.warning("Botão 'Sim' não apareceu para dia %s: %s", date_value, e)

    return False


# ── API pública ─────────────────────────────────────────────────────────────

async def login_and_get_days(cpf: str, senha: str) -> dict:
    """
    Login to RU portal and return available days for scheduling.

    Returns:
        success (bool), error (str|None), available_days (list[str]), raw_days (list[dict])
    """
    pw, browser = await _launch_browser()
    ctx = await browser.new_context(viewport={"width": 1024, "height": 768})
    page = await ctx.new_page()
    try:
        ok, err = await _do_login(page, cpf, senha)
        if not ok:
            return {"success": False, "error": err, "available_days": [], "raw_days": []}

        rendered = await _load_agendamento(page)
        if not rendered:
            return {
                "success": False,
                "error": "Calendário de agendamento não carregou. Tente novamente.",
                "available_days": [],
                "raw_days": [],
            }

        days = await _extract_future_days(page)
        return {
            "success": True,
            "error": None,
            "available_days": [d["label"] for d in days],
            "raw_days": days,
        }
    except Exception as e:
        logger.exception("Erro ao fazer login/buscar dias no RU.")
        return {
            "success": False,
            "error": str(e),
            "available_days": [],
            "raw_days": [],
        }
    finally:
        await ctx.close()
        await browser.close()
        await pw.stop()


async def book_days(cpf: str, senha: str, selected_values: list[str]) -> dict:
    """
    Login to RU portal and book the specified days.

    selected_values: list of 'value' strings from raw_days returned by login_and_get_days.
    Returns: success (bool), booked (list), failed (list), error (str|None)
    """
    pw, browser = await _launch_browser()
    ctx = await browser.new_context(viewport={"width": 1024, "height": 768})
    page = await ctx.new_page()
    try:
        ok, err = await _do_login(page, cpf, senha)
        if not ok:
            return {"success": False, "error": err, "booked": [], "failed": selected_values}

        rendered = await _load_agendamento(page)
        if not rendered:
            return {
                "success": False,
                "error": "Calendário não carregou.",
                "booked": [],
                "failed": selected_values,
            }

        booked, failed = [], []
        for date_val in selected_values:
            success = await _book_single_day(page, date_val)
            if success:
                booked.append(date_val)
            else:
                failed.append(date_val)
            # Pequena pausa entre reservas para o servidor processar
            await page.wait_for_timeout(1500)

        _dbg(await page.content(), "05_after_booking")
        return {
            "success": True,
            "error": None,
            "booked": booked,
            "failed": failed,
        }
    except Exception as e:
        logger.exception("Erro ao reservar dias no RU.")
        return {
            "success": False,
            "error": str(e),
            "booked": [],
            "failed": selected_values,
        }
    finally:
        await ctx.close()
        await browser.close()
        await pw.stop()

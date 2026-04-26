import asyncio
import logging
from pathlib import Path
from playwright.async_api import async_playwright, Page

logger = logging.getLogger(__name__)

_RU_BASE = "https://ru.fw.iffarroupilha.edu.br"
_APP_URL  = _RU_BASE + "/sifw/"
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


def _save_debug(page_html: str, name: str) -> None:
    try:
        _DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        (_DEBUG_DIR / f"{name}.html").write_text(page_html, encoding="utf-8")
    except Exception:
        pass


async def _launch_browser():
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True, args=_LAUNCH_ARGS)
    return pw, browser


async def _do_login(page: Page, cpf: str, senha: str) -> tuple[bool, str]:
    """
    Navigate to the app; Keycloak intercepts and shows its login form.
    Returns (success, error_message).
    """
    try:
        await page.goto(_APP_URL, timeout=25000, wait_until="domcontentloaded")
    except Exception as e:
        return False, f"Não consegui acessar o portal: {e}"

    # Wait for Keycloak login form (standard Keycloak IDs)
    try:
        await page.wait_for_selector("#username", timeout=15000)
    except Exception:
        # Not on login page — already logged in or unexpected page
        if "/sifw/" in page.url and "openid-connect" not in page.url:
            return True, ""
        _save_debug(await page.content(), "01_unexpected_before_login")
        return False, f"Página de login não encontrada. URL: {page.url}"

    # Fill Keycloak form
    await page.fill("#username", cpf)
    await page.fill("#password", senha)

    # Keycloak login button: id="kc-login" or name="login"
    btn = await page.query_selector("#kc-login") or await page.query_selector("[name='login']")
    if not btn:
        _save_debug(await page.content(), "02_no_login_button")
        return False, "Botão de login não encontrado na página do Keycloak."

    await btn.click()

    # Wait for redirect back to the app or an error message
    try:
        await page.wait_for_url(f"{_RU_BASE}/sifw/**", timeout=20000)
        return True, ""
    except Exception:
        pass

    # Check for Keycloak error (wrong credentials)
    err_el = await page.query_selector("#input-error, .alert-error, [class*='error']")
    if err_el:
        err_text = (await err_el.text_content() or "").strip()
        return False, f"Credenciais inválidas: {err_text}"

    if "openid-connect" in page.url:
        _save_debug(await page.content(), "03_still_on_keycloak")
        return False, "CPF ou senha incorretos."

    return True, ""


async def _go_to_agendamento(page: Page) -> bool:
    """Navigate to the scheduling page. Returns True if reached."""
    # If already there
    if "agendamento" in page.url:
        return True

    try:
        await page.goto(_AGENDA_URL, timeout=20000, wait_until="domcontentloaded")
        # JSF pages may do a redirect; wait for network to settle
        await page.wait_for_load_state("networkidle", timeout=10000)
        return True
    except Exception as e:
        logger.warning("Não consegui acessar %s: %s", _AGENDA_URL, e)
        _save_debug(await page.content(), "04_agendamento_error")
        return False


async def _extract_days(page: Page) -> list[dict]:
    """
    Extract bookable days from agendamento.xhtml (JSF page).
    Priority: checkboxes → table rows with date patterns → generic date elements.
    """
    days: list[dict] = []
    _save_debug(await page.content(), "05_agendamento_page")

    # Strategy 1: checkboxes (JSF renders them as input[type=checkbox])
    checkboxes = await page.query_selector_all("input[type='checkbox']")
    for cb in checkboxes:
        value = (await cb.get_attribute("value")) or ""
        cb_id  = (await cb.get_attribute("id"))    or ""
        cb_name = (await cb.get_attribute("name")) or ""

        label = ""
        if cb_id:
            lbl = await page.query_selector(f'label[for="{cb_id}"]')
            if lbl:
                label = ((await lbl.text_content()) or "").strip()

        if not label:
            # Try the closest td/div/li
            try:
                parent_text = await cb.evaluate(
                    "el => (el.closest('td,li,div,span') || el.parentElement)?.innerText"
                )
                label = (parent_text or "").strip()
            except Exception:
                pass

        if not label:
            label = value

        if value:
            days.append({
                "label": label or value,
                "value": value,
                "selector": f'input[name="{cb_name}"][value="{value}"]' if cb_name else f'input[value="{value}"]',
                "name": cb_name,
                "type": "checkbox",
            })

    if days:
        return days

    # Strategy 2: table rows with date-like content (DD/MM or day names)
    import re as _re
    date_pattern = _re.compile(r"\d{1,2}[/\-]\d{1,2}|\b(seg|ter|qua|qui|sex|sáb|dom)\b", _re.I)
    rows = await page.query_selector_all("table tr")
    for row in rows:
        cells = await row.query_selector_all("td")
        if not cells:
            continue
        texts = [((await c.text_content()) or "").strip() for c in cells]
        combined = " | ".join(t for t in texts if t)
        if combined and date_pattern.search(combined):
            days.append({
                "label": combined,
                "value": combined,
                "selector": None,
                "name": None,
                "type": "row",
            })

    if days:
        return days

    # Strategy 3: any clickable element with a data-date attribute or date-like text
    els = await page.query_selector_all("[data-date],[data-dia]")
    for el in els:
        text  = ((await el.text_content()) or "").strip()
        value = (await el.get_attribute("data-date")) or (await el.get_attribute("data-dia")) or text
        if value:
            days.append({
                "label": text or value,
                "value": value,
                "selector": None,
                "name": None,
                "type": "data-attr",
            })

    return days


async def login_and_get_days(cpf: str, senha: str) -> dict:
    pw, browser = await _launch_browser()
    ctx = await browser.new_context(
        viewport={"width": 1280, "height": 800},
        ignore_https_errors=True,
    )
    page = await ctx.new_page()
    try:
        ok, err = await _do_login(page, cpf, senha)
        if not ok:
            return {"success": False, "error": err, "available_days": [], "raw_days": []}

        reached = await _go_to_agendamento(page)
        if not reached:
            return {
                "success": False,
                "error": "Não consegui acessar a página de agendamento.",
                "available_days": [],
                "raw_days": [],
            }

        days = await _extract_days(page)
        return {
            "success": True,
            "error": None,
            "available_days": [d["label"] for d in days],
            "raw_days": days,
        }
    except Exception as e:
        logger.exception("Erro em login_and_get_days.")
        return {"success": False, "error": str(e), "available_days": [], "raw_days": []}
    finally:
        await ctx.close()
        await browser.close()
        await pw.stop()


async def book_days(cpf: str, senha: str, selected_values: list[str]) -> dict:
    pw, browser = await _launch_browser()
    ctx = await browser.new_context(
        viewport={"width": 1280, "height": 800},
        ignore_https_errors=True,
    )
    page = await ctx.new_page()
    try:
        ok, err = await _do_login(page, cpf, senha)
        if not ok:
            return {"success": False, "error": err, "booked": [], "failed": selected_values}

        await _go_to_agendamento(page)

        booked, failed = [], []
        for value in selected_values:
            try:
                # Try by value first, then by name+value
                cb = await page.query_selector(f'input[value="{value}"]')
                if cb and not await cb.is_checked():
                    await cb.check()
                    booked.append(value)
                elif cb:
                    booked.append(value)
                else:
                    failed.append(value)
            except Exception as e:
                logger.warning("Erro ao selecionar dia %s: %s", value, e)
                failed.append(value)

        # Submit form
        submit = await page.query_selector(
            "button[type='submit'], input[type='submit'], button[id*='salvar'], button[id*='agendar']"
        )
        if submit and booked:
            await submit.click()
            await page.wait_for_load_state("networkidle", timeout=10000)
            _save_debug(await page.content(), "06_after_submit")

        return {"success": True, "error": None, "booked": booked, "failed": failed}
    except Exception as e:
        logger.exception("Erro em book_days.")
        return {"success": False, "error": str(e), "booked": [], "failed": selected_values}
    finally:
        await ctx.close()
        await browser.close()
        await pw.stop()

import asyncio
import logging
from playwright.async_api import async_playwright, Page, Browser

logger = logging.getLogger(__name__)

_RU_URL = "https://ru.fw.iffarroupilha.edu.br"
_LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--no-zygote",
    "--single-process",
    "--disable-extensions",
]


async def _launch_browser() -> tuple:
    """Returns (playwright, browser)."""
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True, args=_LAUNCH_ARGS)
    return pw, browser


async def _do_login(page: Page, cpf: str, senha: str) -> bool:
    """Fills and submits the Keycloak login form. Returns True on success."""
    await page.goto(_RU_URL + "/", timeout=20000, wait_until="domcontentloaded")
    await page.fill("#username", cpf)
    await page.fill("#password", senha)
    await page.click("#kc-login")
    try:
        await page.wait_for_url("**/sifw/**", timeout=15000)
        return True
    except Exception:
        # Check if still on login page = wrong credentials
        if "openid-connect" in page.url:
            return False
        return True


async def _find_scheduling_page(page: Page) -> bool:
    """Navigate to the scheduling/agendamento page. Returns True if found."""
    keywords = ["agendamento", "reserva", "agendar", "refeição", "almoco", "almoço", "cardápio"]
    links = await page.query_selector_all("a")
    for link in links:
        text = ((await link.text_content()) or "").lower().strip()
        href = (await link.get_attribute("href")) or ""
        if any(k in text or k in href.lower() for k in keywords):
            if href and not href.startswith("#"):
                if not href.startswith("http"):
                    href = _RU_URL + href
                await page.goto(href, timeout=15000, wait_until="domcontentloaded")
                return True
    # Try common URL patterns
    for path in ["/sifw/agendamento", "/sifw/reserva", "/sifw/agendar"]:
        try:
            resp = await page.goto(_RU_URL + path, timeout=10000, wait_until="domcontentloaded")
            if resp and resp.status < 400:
                return True
        except Exception:
            pass
    return False


async def _extract_days(page: Page) -> list[dict]:
    """
    Extract available scheduling days from the page.
    Tries checkboxes, then select options, then table rows.
    Returns list of dicts: {label, value, selector, type}
    """
    days = []

    # Strategy 1: checkboxes
    checkboxes = await page.query_selector_all("input[type='checkbox']")
    if checkboxes:
        for cb in checkboxes:
            value = (await cb.get_attribute("value")) or ""
            cb_id = (await cb.get_attribute("id")) or ""
            cb_name = (await cb.get_attribute("name")) or ""
            label = ""
            if cb_id:
                label_el = await page.query_selector(f'label[for="{cb_id}"]')
                if label_el:
                    label = ((await label_el.text_content()) or "").strip()
            if not label:
                parent = await cb.evaluate_handle("el => el.closest('td,li,div')")
                if parent:
                    label = ((await parent.as_element().text_content()) or "").strip() if parent.as_element() else ""
            if not label:
                label = value
            if label and value:
                days.append({
                    "label": label,
                    "value": value,
                    "selector": f'input[value="{value}"]',
                    "name": cb_name,
                    "type": "checkbox",
                })
        if days:
            return days

    # Strategy 2: table rows with date-like content
    rows = await page.query_selector_all("table tr")
    for row in rows:
        cells = await row.query_selector_all("td")
        if not cells:
            continue
        texts = [((await c.text_content()) or "").strip() for c in cells]
        combined = " | ".join(t for t in texts if t)
        if combined and any(ch.isdigit() for ch in combined):
            days.append({
                "label": combined,
                "value": combined,
                "selector": None,
                "name": None,
                "type": "row",
            })
    if days:
        return days

    # Strategy 3: any element with date-like text
    els = await page.query_selector_all("[data-date], [data-dia], td, li")
    for el in els[:50]:
        text = ((await el.text_content()) or "").strip()
        data = (await el.get_attribute("data-date")) or (await el.get_attribute("data-dia")) or text
        if text and any(ch.isdigit() for ch in text) and len(text) < 60:
            days.append({
                "label": text,
                "value": data,
                "selector": None,
                "name": None,
                "type": "element",
            })

    return days


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
        logged = await _do_login(page, cpf, senha)
        if not logged:
            return {
                "success": False,
                "error": "CPF ou senha incorretos. Verifique suas credenciais.",
                "available_days": [],
                "raw_days": [],
            }

        await _find_scheduling_page(page)
        days = await _extract_days(page)

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
        logged = await _do_login(page, cpf, senha)
        if not logged:
            return {
                "success": False,
                "error": "CPF ou senha incorretos.",
                "booked": [],
                "failed": selected_values,
            }

        await _find_scheduling_page(page)

        booked = []
        failed = []
        for value in selected_values:
            try:
                cb = await page.query_selector(f'input[value="{value}"]')
                if cb:
                    if not await cb.is_checked():
                        await cb.check()
                    booked.append(value)
                else:
                    failed.append(value)
            except Exception as e:
                logger.warning("Erro ao selecionar dia %s: %s", value, e)
                failed.append(value)

        # Submit
        submit = await page.query_selector("button[type='submit'], input[type='submit']")
        if submit and booked:
            await submit.click()
            await page.wait_for_timeout(2000)

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

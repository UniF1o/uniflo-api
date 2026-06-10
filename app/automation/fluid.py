"""Shared PeopleSoft Fluid helpers (UCT now; Wits reuses these when its adapter
lands — same engine family).

Everything here encodes behaviour verified live against UCT on 2026-06-10
(docs/phase-3/portal-research/uct.md, "Live spike findings"):

- Fluid re-renders the DOM after most server round-trips, so element handles go
  stale constantly. These helpers therefore drive the page through
  `page.evaluate` JS that re-queries by **stable PeopleSoft id** on every call —
  the approach that survived the whole 16-step walkthrough.
- Switches/checkboxes sit under a `ps_indicator` overlay that intercepts pointer
  events — they must be clicked via JS (`element.click()`), not a pointer click.
- Modals (OTP, add-row, search, file attachment) are iframes named
  `ptModFrame_N`; their contents are driven through the frame object.
- Error/confirm dialogs are `[role=alertdialog]` elements whose text carries a
  stable message code (e.g. ``21000, 2835``) — surfaced verbatim in exceptions.
- A step is complete when **Save succeeds and the header Next button renders**
  (Next only appears after a successful save).

The helpers accept either a Playwright `Page` or `Frame` wherever only
`.evaluate` is needed.
"""

import asyncio
import logging
from typing import Optional, Union

from playwright.async_api import Frame, Page

from app.automation.exceptions import PortalChangedError, ValidationFailedError

logger = logging.getLogger(__name__)

Evaluable = Union[Page, Frame]

# How long a Fluid server round-trip is given to settle before we re-query.
SETTLE_MS = 1500


async def settle(page: Page, ms: int = SETTLE_MS) -> None:
    await page.wait_for_timeout(ms)


async def js_fill(target: Evaluable, selector: str, value: str) -> None:
    """Set a text input's value + fire change (survives re-renders; PeopleSoft
    formats/validates on the change event)."""
    ok = await target.evaluate(
        """([sel, val]) => {
          const el = document.querySelector(sel);
          if (!el) return false;
          el.value = val;
          el.dispatchEvent(new Event('change', {bubbles: true}));
          return true;
        }""",
        [selector, str(value)],
    )
    if not ok:
        raise PortalChangedError(f"field {selector} not found", selector=selector)


async def js_select_text(
    target: Evaluable, selector: str, option_text: str, *, contains: bool = False
) -> str:
    """Select a dropdown option by visible text (exact, or substring with
    `contains=True`) + fire change. Returns the option text actually selected;
    raises PortalChangedError listing the live options when nothing matches."""
    result = await target.evaluate(
        """([sel, txt, contains]) => {
          const el = document.querySelector(sel);
          if (!el) return {error: 'missing'};
          const options = [...el.options].map(o => o.text.trim());
          const target = [...el.options].find(o => contains
            ? o.text.trim().toLowerCase().includes(txt.toLowerCase())
            : o.text.trim() === txt);
          if (!target) return {error: 'no-option', options};
          el.value = target.value;
          el.dispatchEvent(new Event('change', {bubbles: true}));
          return {selected: target.text.trim()};
        }""",
        [selector, option_text, contains],
    )
    if result.get("error") == "missing":
        raise PortalChangedError(f"select {selector} not found", selector=selector)
    if result.get("error") == "no-option":
        raise PortalChangedError(
            f"select {selector} has no option {option_text!r} "
            f"(live options: {result.get('options')})",
            selector=selector,
        )
    return result["selected"]


async def select_option_texts(target: Evaluable, selector: str) -> list[str]:
    """The live option texts of a dropdown (placeholder blanks stripped)."""
    options = await target.evaluate(
        """(sel) => {
          const el = document.querySelector(sel);
          return el ? [...el.options].map(o => o.text.trim()) : null;
        }""",
        selector,
    )
    if options is None:
        raise PortalChangedError(f"select {selector} not found", selector=selector)
    return [o for o in options if o]


async def js_click(target: Evaluable, selector: str) -> None:
    """JS-click an element by selector — required for switches/checkboxes (the
    `ps_indicator` overlay intercepts pointer clicks) and safe everywhere."""
    ok = await target.evaluate(
        """(sel) => {
          const el = document.querySelector(sel);
          if (!el) return false;
          el.click();
          return true;
        }""",
        selector,
    )
    if not ok:
        raise PortalChangedError(f"element {selector} not found", selector=selector)


async def set_switch(target: Evaluable, selector: str, on: bool) -> None:
    """Toggle a Fluid switch/checkbox into the requested state (JS-click only
    when the current state differs)."""
    ok = await target.evaluate(
        """([sel, want]) => {
          const el = document.querySelector(sel);
          if (!el) return false;
          if (el.checked !== want) el.click();
          return true;
        }""",
        [selector, on],
    )
    if not ok:
        raise PortalChangedError(f"switch {selector} not found", selector=selector)


async def is_visible(target: Evaluable, selector: str) -> bool:
    try:
        return bool(await target.evaluate(
            "(s)=>{const e=document.querySelector(s); return !!(e && e.offsetParent);}",
            selector,
        ))
    except Exception:  # noqa: BLE001
        return False


# --- header buttons (Save / Next / Previous render by visible text) -------------

_BUTTON_JS = """([txt, click]) => {
  const btns = [...document.querySelectorAll('a[role=button], input[type=button], button')]
    .filter(b => b.offsetParent !== null);
  const hit = btns.find(b => ((b.textContent || b.value || '').trim() === txt));
  if (!hit) return false;
  if (click) hit.click();
  return true;
}"""


async def button_visible(target: Evaluable, text: str) -> bool:
    try:
        return bool(await target.evaluate(_BUTTON_JS, [text, False]))
    except Exception:  # noqa: BLE001
        return False


async def click_button(target: Evaluable, text: str) -> None:
    ok = await target.evaluate(_BUTTON_JS, [text, True])
    if not ok:
        raise PortalChangedError(f"button {text!r} not found", selector=text)


# --- alert / confirm dialogs ------------------------------------------------------

async def read_alert(page: Page) -> Optional[str]:
    """Text of the visible [role=alertdialog], message code included, or None."""
    try:
        return await page.evaluate(
            """() => {
              const a = document.querySelector('[role=alertdialog]');
              return a ? a.textContent.trim().replace(/\\s+/g, ' ').slice(0, 400) : null;
            }"""
        )
    except Exception:  # noqa: BLE001
        return None


async def answer_alert(page: Page, button_text: str) -> bool:
    """Click a button (OK / Yes / No) inside the alert dialog. Returns whether
    the dialog + button were found."""
    try:
        return bool(await page.evaluate(
            """(txt) => {
              const dlg = document.querySelector('[role=alertdialog]');
              if (!dlg) return false;
              const btn = [...dlg.querySelectorAll('a, input[type=button], button')]
                .find(b => ((b.textContent || b.value || '').trim() === txt));
              if (!btn) return false;
              btn.click();
              return true;
            }""",
            button_text,
        ))
    except Exception:  # noqa: BLE001
        return False


# --- modal iframes (ptModFrame_N) ---------------------------------------------------

def modal_frame(page: Page) -> Optional[Frame]:
    """The newest open Fluid modal iframe, or None. Modals nest, so the last
    `ptModFrame_*` frame is the active one."""
    frames = [f for f in page.frames if (f.name or "").startswith("ptModFrame")]
    return frames[-1] if frames else None


async def wait_modal_frame(page: Page, *, timeout_s: float = 10.0) -> Frame:
    """Wait for a Fluid modal iframe to open and return its frame."""
    deadline = asyncio.get_event_loop().time() + timeout_s
    while True:
        frame = modal_frame(page)
        if frame is not None:
            return frame
        if asyncio.get_event_loop().time() >= deadline:
            raise PortalChangedError("modal iframe did not open", selector="ptModFrame")
        await page.wait_for_timeout(250)


async def wait_modal_closed(page: Page, *, timeout_s: float = 10.0) -> None:
    deadline = asyncio.get_event_loop().time() + timeout_s
    while modal_frame(page) is not None:
        if asyncio.get_event_loop().time() >= deadline:
            raise PortalChangedError("modal iframe did not close", selector="ptModFrame")
        await page.wait_for_timeout(250)


# --- step save / advance --------------------------------------------------------------

async def save_step(page: Page, *, step: str = "", timeout_s: float = 20.0) -> None:
    """Click the header Save and wait for the step to complete. Completion =
    the Next button renders; an alert dialog instead means the portal rejected
    the step → ValidationFailedError carrying the dialog text (incl. message
    code). Verified pattern: Next only appears after a successful save."""
    await click_button(page, "Save")
    deadline = asyncio.get_event_loop().time() + timeout_s
    while True:
        await page.wait_for_timeout(700)
        alert = await read_alert(page)
        if alert:
            await answer_alert(page, "OK")
            raise ValidationFailedError(
                f"UCT rejected step {step or '?'}: {alert}", field=step or None
            )
        if await button_visible(page, "Next"):
            return
        if asyncio.get_event_loop().time() >= deadline:
            raise ValidationFailedError(
                f"step {step or '?'} did not complete after Save (no Next button)",
                field=step or None,
            )


async def next_step(page: Page, *, settle_ms: int = SETTLE_MS) -> None:
    await click_button(page, "Next")
    await page.wait_for_timeout(settle_ms)


async def current_step_heading(page: Page) -> Optional[str]:
    """The 'Step N of 16: …' heading — the page marker for logging/diagnosis."""
    try:
        return await page.evaluate(
            """() => {
              const h = [...document.querySelectorAll('h1')]
                .find(h => h.offsetParent !== null && /Step \\d+ of/.test(h.textContent));
              return h ? h.textContent.trim() : null;
            }"""
        )
    except Exception:  # noqa: BLE001
        return None

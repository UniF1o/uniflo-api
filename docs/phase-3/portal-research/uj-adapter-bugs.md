# UJ Adapter — Discovered Bugs

> Captured from the 2026-06-18/20 every-option walkthroughs. Fix all of these
> before enabling `FAKE_AUTOMATION=false` for UJ. Each entry says exactly what
> to change and where.

---

## Bug 1 — Page C save button stuck disabled

**File:** `app/automation/adapters/uj.py`
**Method:** `fill_form`
**Line (approx):** the `_save_and_continue(page, _PAGE_C_NEXT)` call

**Root cause:** `#oapNextBtn3` is rendered with `disabled=''` by the server.
`JSText_46` on the page enables it when subjects exist, but JSText_46 does NOT
auto-execute after a `gw1view` GET navigation — only on the initial page render
cycle. The adapter never eval's it, so the button stays disabled even with 7
subjects in the table.

**Fix:**

```python
# In fill_form(), change:
await self._save_and_continue(page, _PAGE_C_NEXT)

# To:
await self._save_and_continue(page, _PAGE_C_NEXT, force=True)
```

`force=True` clears the `disabled` attribute via JS before clicking. The server
still runs its own validation — this only unblocks the client-side gate.
Page E already uses `force=True` for the same reason. Page C needs it too.

---

## Bug 2 — SA citizen oapCitzCode fails server validation despite being hidden

**File:** `app/automation/adapters/uj.py`
**Method:** `_fill_simple` / Page A flow

**Root cause:** When `oapCitizenType=Y` is selected, ITS fires `eventRun(5.4)`
which adds CSS class `w3-hide` to `oapCitzCodeGrp` (`display:none!important` via
stylesheet). The form's mandatory-field validator (`changeToNameValuePairs`) only
checks `el.parentElement.style.display` at exactly 3 parent levels — it reads the
**inline** style, NOT computed CSS. Since `w3-hide` is a class (not an inline
style), the validator sees `oapCitzCodeGrp` as visible and mandatory, and fails
the save with "Please supply missing/correct values" even though the field is
visually hidden.

Additionally, the SA-ID auto-fill that ITS does (to populate `oapCitzCode` and
`oapCitzCode_desc`) does not reliably fire under headless Playwright.

**Fix:** Replace the Page A generic `_fill_simple` approach with a dedicated
`fill_biographical_page` method that handles the citizenship flow explicitly.
Call it from `fill_form` in place of the current `_fill_simple(page, mapping, "A")`.

```python
async def fill_biographical_page(self, page: Page, mapping: FieldMapping) -> None:
    # 1. Set citizenship first (reveals ID field + triggers eventRun(5.4))
    await self._select_value(page, "#oapCitizenType", "Y")
    await page.wait_for_timeout(800)  # let eventRun(5.4) run and add w3-hide

    # 2. Force inline style so changeToNameValuePairs skips the group,
    #    and set the code/desc values the auto-fill would normally provide.
    await page.evaluate("""() => {
        const grp = document.getElementById('oapCitzCodeGrp');
        if (grp) grp.style.display = 'none';
        const c = document.getElementById('oapCitzCode');
        const d = document.getElementById('oapCitzCode_desc');
        if (c) c.value = 'ZA';
        if (d) d.value = 'SOUTH AFRICA';
    }""")

    # 3. Fill the SA ID number
    await self._fill(page, "#oapIDnumber", str(mapping.get("id_number", "")))

    # 4. Fill all remaining Page A fields via _fill_simple
    #    (it will skip citizenship_code because offsetParent is null / hidden)
    await self._fill_simple(page, mapping, "A")
```

Also mark `citizenship_code` as `"conditional": true` in `uj.fields.json` so
`_fill_simple` skips the LOV open attempt (the group is hidden, the LOV anchor
is inside it and won't be interactable):

```json
{"field_id": "citizenship_code", ..., "conditional": true, ...}
```

And update `fill_form` to call the new method:

```python
# Change:
await self._fill_simple(page, mapping, "A")

# To:
await self.fill_biographical_page(page, mapping)
```

---

## Bug 3 — Page B NOK fields missing / mismatched in uj.fields.json

**File:** `app/automation/adapters/uj.fields.json` (and `_uj_mapping` in `mapping.py`)

**Root cause:** After Page A saves, ITS advances to `ITS_OAP02_1` (page code
`ITS_OAP02_1`), not directly to Page C. This intermediate page has more mandatory
fields than `uj.fields.json` currently lists. Specifically:

- NOK section: `oapNokPostalAddr1`, `oapNokPostalAddr2`, `oapNokPostalAddrCode`,
  `oapNokPostalAddrCode_desc` (LOV, mandatory=Y), `oapNokEmail` — all mandatory
- Account section: `oapAcntPostalCode_desc` (the LOV desc sibling — mandatory=Y
  and visible; `changeToNameValuePairs` checks it the same way as postal_code_desc
  on Page A)

The current `uj.fields.json` has only `nok_name`, `nok_mobile`, and the account
address fields. The missing fields will cause "Please supply missing/correct values"
on Page B save.

**Fix — add to `uj.fields.json` Page B fields:**

```json
{"field_id": "nok_postal_addr_1", "page": "B", "label": "NOK Postal Address Line 1", "type": "text", "required": true, "selector": "#oapNokPostalAddr1"},
{"field_id": "nok_postal_addr_2", "page": "B", "label": "NOK Postal Address Line 2 (Suburb)", "type": "text", "required": true, "selector": "#oapNokPostalAddr2"},
{"field_id": "nok_postal_code", "page": "B", "label": "NOK Postal Code", "type": "lov", "required": true, "selector": "#oapNokPostalAddrCode", "lov_search": true},
{"field_id": "nok_email", "page": "B", "label": "NOK Email", "type": "text", "required": true, "selector": "#oapNokEmail"}
```

Also add `account_postal_code_desc` handling: the LOV PassBack for
`#oapAcntPostalCode` should set both the code and the `#oapAcntPostalCode_desc`
sibling. Add an explicit JS set of the desc after the LOV selection as a safety
measure, or add the desc field to the schema with a `manual: true` flag and handle
it in the adapter's Page B fill.

**Fix — add to `_uj_mapping` in `mapping.py`:**

```python
# Add to the values dict in _uj_mapping:
"nok_postal_addr_1": _payer_field(nok, profile, "street_address"),
"nok_postal_addr_2": _payer_field(nok, profile, "suburb"),
"nok_postal_code":   _payer_field(nok, profile, "postal_code"),
"nok_email":         _g(nok, "email"),
```

---

## Bug 4 — Postal code _desc fields not explicitly set

**File:** `app/automation/adapters/uj.py`

**Root cause:** `oapStreetAddrPCodeRq_desc` (Page A) and `oapAcntPostalCode_desc`
(Page B) are both mandatory=Y and visible. ITS's LOV `PassBack` is supposed to
set both the code and the `_desc` sibling when a row is clicked. Under headless
Playwright, PassBack fires but may not reliably update the `_desc` field before
`changeToNameValuePairs` runs at save time.

**Observed:** Setting only the code field (via LOV or JS) and leaving `_desc`
empty causes "Please supply missing/correct values" on save. Setting `_desc`
explicitly (same string as the code, e.g. `'0152'`) resolves it.

**Fix:** After each postal code LOV selection on Pages A and B, do an explicit
JS set of the `_desc` sibling using the same value:

```python
async def _set_postal_code(self, page: Page, code_selector: str, value: str) -> None:
    """Select a postal code from the LOV and force-set its _desc sibling."""
    await self.select_from_lov(page, code_selector, value, search_term=value)
    desc_selector = code_selector + "_desc"
    await page.evaluate(
        """([sel, val]) => {
            const el = document.querySelector(sel);
            if (el) { el.value = val; el.dispatchEvent(new Event('change', {bubbles:true})); }
        }""",
        [desc_selector.replace("#oap", "#oap").replace("Rq", "Rq"), value],
    )
```

Then replace the LOV calls for postal code fields with `_set_postal_code`.

Actual selectors to cover:
- Page A street: `#oapStreetAddrPCodeRq` + `#oapStreetAddrPCodeRq_desc`  
- Page A postal (if differs from street): `#oapPostalAddrPCodeRq` + `#oapPostalAddrPCodeRq_desc`
- Page B NOK: `#oapNokPostalAddrCode` + `#oapNokPostalAddrCode_desc`
- Page B account: `#oapAcntPostalCode` + `#oapAcntPostalCode_desc`

---

## Bug 5 — oapAcceptUnderAge onclick handler not called (under-18 applicants)

**File:** `app/automation/adapters/uj.py`
**Affected applicants:** those under 18 at time of application

**Root cause:** For applicants whose DOB makes them under 18, ITS renders an
"I Accept" checkbox (`#oapAcceptUnderAge`) and disables `#oapNextBtn2` until it
is checked AND its `onclick` handler fires. Calling `page.check('#oapAcceptUnderAge')`
sets `el.checked=true` but does NOT call the inline `onclick` handler, so the
button remains disabled.

**Not currently triggered** by Jane Doe (DOB 2008-05-14 = 18 years old in
June 2026). Will affect applicants still 17 (e.g. turning 18 later in the year).

**Fix:** Add to the biographical page fill, after the standard checkbox check:

```python
await page.evaluate("""() => {
    const el = document.getElementById('oapAcceptUnderAge');
    if (el && el.offsetParent !== null) {
        el.checked = true;
        if (typeof el.onclick === 'function') el.onclick();
        el.dispatchEvent(new Event('change', {bubbles: true}));
    }
}""")
```

---

## Summary table

| # | Bug | File | Severity | Applicants affected |
|---|-----|------|----------|---------------------|
| 1 | Page C save button stuck | `uj.py` fill_form | **Blocks all runs** | All |
| 2 | oapCitzCode group inline-style | `uj.py` + `uj.fields.json` | **Blocks all runs** | SA citizens |
| 3 | Page B NOK fields missing | `uj.fields.json` + `mapping.py` | **Blocks all runs** | All |
| 4 | Postal code _desc not set | `uj.py` | **Blocks all runs** | All |
| 5 | oapAcceptUnderAge onclick | `uj.py` | Blocks under-18 | Applicants < 18 |

Bugs 1–4 will each independently cause a failed run. Fix all four before the
first live test. Bug 5 can follow in a second pass.

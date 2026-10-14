---
name: ctrlx-hmi
description: Build CODESYS WebVisu / TargetVisu screens (visualizations) for Bosch Rexroth ctrlX CORE (ctrlX PLC Engineering) as importable native .export files. Screens are written as short Python definitions (labels, value displays, <light> <name> status lamps with warning/fault overlays, tap/toggle buttons hidden when not useful, numpad entry fields, text lists for enum and fault texts) and compiled by a generator that clones real elements and writes the PLC Engineering archive format, with a previewer that renders the screen for given variable values and a bisect kit for import failures. Use it whenever the user wants an HMI, visu, visualization, WebVisu, operator screen, faceplate or station screen, wants HMI controls or status shown for PLC code, or wants to read or check a CODESYS visualization .export. It builds on ctrlx-engineer (the PLC side: Cmd/Sts structs, GVL_Hmi).
---

# ctrlX / CODESYS HMI screens

Visualizations can't be made through the PLC Engineering REST API (it has no visualization object) or through PLCopenXML (visus aren't in it). They can be imported as a native `.export` file, which is XML in the PLC Engineering archive format. This skill writes those files. It works on ctrlX PLC Engineering, profile **ctrlX PLC 3.6.5**, and has been proven by imports there. `references/format.md` holds the format and the rules that every import failure taught. Read it before changing the generator or adding an element kind.

## Workflow

1. **PLC side first.** The screen binds to variables, not logic. Each station has `ST_<Station>Cmd` (HMI → PLC: buttons, entries) and `ST_<Station>Sts` (PLC → HMI: state, sensors, values, fault code) in `GVL_Hmi`, settings in `GVL_Cfg`, and warnings in `GVL_Machine.astDiag[...]`. Read the station's types and README to get every command and status field. Write that code with ctrlx-engineer if it doesn't exist.
2. **Write a screen definition** (`screen_<station>.py`, kept in the project, e.g. `src/Hmi/`). It defines `build(tpl)` and returns a list of entries: `vg.textlist(...)` for each text list, then `sc.entry()`. `vg` is injected by the generator. `references/example_screen_infeed.py` is a complete, imported screen; copy its structure.
3. **Generate:** `python3 <skill>/scripts/visugen.py screen_x.py build/X.export`. The generator refuses names that don't start with an allowed prefix (`GVL_`, `E_`, `VisuDialogs`; set `ALLOWED_PREFIXES` in the screen file for others). That check catches template leftovers.
4. **Preview and look at it:** `python3 <skill>/scripts/preview.py build/X.export scenarios.py build/preview` writes one SVG per scenario. A scenario is a dict of variable → value; see `references/example_preview_infeed.py`. Convert the SVGs with `firefox --headless --screenshot out.png --window-size=W,H file://…svg` and Read the PNGs. Check every important state (running, manual, faulted, each hold/wait) for overlaps, holes left by hidden rows, text overflow and wrong visibility. The preview is approximate: buttons are drawn generically, and it is not CODESYS rendering.
5. **Import (the user does it):** Project → Import… → the `.export`. The dialog shows the whole device tree from the wrapper: **tick only the new visu and text lists**, leave PLC_PRG, MainTask, Library Manager and the rest unticked. Then open the GlobalTextList and run **Update Visualization Text IDs**, then **Check Visualization Text IDs**, then build. If the Application has no visualization yet, the user adds an empty one through the UI first; that brings in the Visualization Manager and the visu libraries (VisuDialogs for the numpad).
6. **If the import fails** ("an element had an invalid format" is all it says), run `python3 <skill>/scripts/bisect.py build/bisect`. Have the user import B0…B8 and C1…C7 in order and report the first failure. B0 must import: it is the wrapper written back byte for byte. Fix in the generator, never by hand-editing an export.

## Screen API (`visugen.Screen`)

`sc = vg.Screen(tpl, 'INF_Main', 1280, 800)`. Add elements in draw order; later elements paint on top. Colours are `0xRRGGBB`, and every bound field is an IEC expression string.

- `sc.box(x, y, w, h, text='', text_var=None, fill, frame, line=1, font=16, bold=False, color, align='HCENTER', hollow=False, alarm=None, alarm_fill, invisible=None, textlist=None, text_index=None)`: a rectangle. `text` takes `%d %s %.1f %08X` for `text_var`. `alarm` is a toggle-colour expression that switches to `alarm_fill`. `textlist='TL_X'` plus `text_index=expr` shows the list text.
- `sc.label(x, y, w, h, text, **box_kw)`: a hollow, left-aligned box.
- `sc.circle(x, y, d, off, on, on_expr, invisible=None)`: a lamp, `off` colour, `on` colour while `on_expr`.
- `sc.button(x, y, w, h, text, var=None, toggle=False, invisible=None, deactivate=None, active=None, font=16, color=0xE4E7EA, active_color=0x7FD08C, st=None)`: Tap (TRUE while pressed) or Toggle on `var`, and/or `st` = ST code run on click ('Execute ST code': screen change `VisuElems.CurrentVisu := 'X';`, enum writes; add `VisuElems` to `ALLOWED_PREFIXES`). `active` is the colour variable: the button shows `active_color` while it is TRUE (default: while pressed). `color=None` keeps the style colours.
- `sc.numeric(x, y, w, h, var, fmt, vmin, vmax, title='', invisible=None, dialog='VisuDialogs.Numpad', deactivate=None)`: value display that opens the numpad on press; `dialog='VisuDialogs.Keypad'` for TIME and STRING.
- `vg.textlist(tpl, 'TL_X', [(id, text), ...])`: for enums the id is the integer value.

## Several screens (a whole machine)

Keep one export for all screens: text lists are shared between screens and an object can only be imported once. The POD project's pattern (`references/example_hmi_all.py`, `example_kit_hmi_common.py`, `example_scr_crosstransfer.py`):

- `hmi_all.py` is the screen file given to visugen. It loads a kit and one module per station (via `runpy`, injecting `vg` and `hc`) and returns `hc.textlist_entries(tpl) + visus`.
- The kit (`hmi_common.py`) holds the page layout (header with state/fault/nav, panels, `lamps()`, `values()`, `btn()`, `hint()`), expression helpers (`OR`, `NOT`, `is_state`, `fault`, `warn`), a parser for the ST sources (enums → text lists via `tl_enum`, so state texts follow the code), a text-list registry, and `settings_page()`, which generates a maintenance screen from the `ST_<Station>Cfg` struct (every field; numbers on the numpad, TIME/STRING on the keypad, BOOL On/Off plus toggle; edits locked while producing).
- Names: `<ABBR>_Main` (operating), `<ABBR>_Cfg` (settings), `MCH_Overview` (start visu: station list with status, fault text, Open/Setup, machine commands and conditions).
- Preview every screen in every scenario, tile the PNGs four to a sheet (PIL) to review them, and fix overlaps, overflow and holes before handing over.

## Screen conventions (what the user asked for)

- **Components as `<light> <name>`:** one row per component, made of a lamp and its name. The lamp is grey when off and green (or amber/red for warning-type signals) when on. An amber overlay shows while that component's warning is active, and a red overlay while its fault is active (e.g. the servo goes red on the servo fault code). Draw the overlays as extra circles at the same spot with `invisible = NOT (condition)`. Add a short legend.
- **Hide buttons when they are not useful:** every command button gets an `invisible` expression. Manual-only commands show only in Manual. A command that only matters in one state (skip a scan item in HoldQueue) shows only in that state. An option that is switched off hides its button. A move toward a position already reached hides (cut left while at the left prox). Mutually exclusive actions share one spot (put bag in slot / empty the slot). Where nothing shows, a hint label says why ("Manual controls show in machine Manual", "Faults reset from the machine screen").
- **Header:** station name, state as text (text list over the state enum, red when Faulted), and a fault banner (text list over the fault code, hidden at 0).
- **Status values:** label plus framed value. Always-shown rows first and conditional rows last, so hidden rows don't leave holes in the middle.
- **Momentary commands use Tap; levels that should stay on (unclamp) use Toggle** with `active` = the real feedback (`bUnclamped`), so the button shows the actual state, not the request.
- **No logic in the screen** beyond visibility and colour expressions. Anything more belongs in the PLC (ctrlx-engineer), exposed in the Sts struct.

## Templates

`templates/wrapper.export` is a real export of one empty visu named `Empty`, including the device tree. `templates/button.export` is a real export of one button. `templates/elements.xml` holds the rectangle (old project, imports fine), the button taken from `button.export`, a text list and the numpad action. If the target PLC Engineering version changes, or an element kind is missing (checkbox, combobox, image, frame, alarm table, ...), ask the user to export a visu containing one of it from their PLC Engineering and add it as a template. Old-version elements can be rejected; the old button was.

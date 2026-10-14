# ctrlx-hmi

A Claude Code skill that builds CODESYS WebVisu screens for Bosch Rexroth ctrlX CORE (ctrlX PLC Engineering) as importable native `.export` files.

ctrlX PLC Engineering has no REST API for visualizations and they are not part of PLCopenXML, so the skill writes the PLC Engineering archive format directly. A screen is a short Python definition (labels, value displays, `<light> <name>` status lamps with warning and fault overlays, tap / toggle / ST-code buttons hidden when not useful, numpad and keypad entry fields, text lists). The generator clones real elements from templates exported from PLC Engineering and rewrites their properties.

Proven by import and compile on ctrlX PLC Engineering, profile **ctrlX PLC 3.6.5**.

## Contents

| Path | What |
|---|---|
| `SKILL.md` | Skill instructions: workflow, screen API, multi-screen pattern, screen conventions |
| `scripts/visugen.py` | Generator: `python3 scripts/visugen.py screen.py out.export [--templates DIR]` |
| `scripts/preview.py` | Renders a generated export to SVG for given variable values (layout and visibility check) |
| `scripts/bisect.py` | Writes small exports (one element kind each, plus a cumulative button chain) to find what an import rejects |
| `templates/` | `wrapper.export` (a real export of one empty visu, with the device tree), `button.export` (one real button), `elements.xml` (element templates) |
| `references/format.md` | The `.export` format: file rules, element property hash IDs, input actions, text IDs, and every import failure found so far |
| `references/example_*.py` | A complete machine HMI as worked example: a shared screen kit, a build entry, a station screen, preview scenarios |

## Quick start

```sh
mkdir -p build
python3 scripts/visugen.py references/example_screen_infeed.py build/INF_Main.export
python3 scripts/preview.py build/INF_Main.export references/example_preview_infeed.py build/preview
```

Import in PLC Engineering with Project → Import…, tick only the new visus and text lists, then run *Update Visualization Text IDs* on the GlobalTextList.

## Other PLC Engineering versions

The templates come from ctrlX PLC 3.6.5. Element FBs are versioned, and an element from an older version can be rejected (the old button was). For another version, or for an element kind not yet templated (checkbox, combobox, image, frame, alarm table), export a visu containing it from your PLC Engineering and add it as a template. See `references/format.md`.

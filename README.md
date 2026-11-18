# ctrlx-hmi

An agent skill (`SKILL.md` format) that builds CODESYS WebVisu screens for Bosch Rexroth ctrlX CORE (ctrlX PLC Engineering) as importable native `.export` files.

ctrlX PLC Engineering has no REST API for visualizations and they are not part of PLCopenXML, so the skill writes the PLC Engineering archive format directly. A screen is a short Python definition (labels, value displays, `<light> <name>` status lamps with warning and fault overlays, tap / toggle / ST-code buttons hidden when not useful, numpad and keypad entry fields, text lists). The generator clones real elements from templates exported from PLC Engineering and rewrites their properties.

The generator and its element kinds were proven by import and compile on ctrlX PLC Engineering, profile **ctrlX PLC 3.6.5**,
using templates exported from that version.

## Install

Put this folder in the skills directory your agent loads skills from, under the folder name `ctrlx-hmi`. It pairs with the `ctrlx-engineer` skill, which writes the PLC side (the Cmd/Sts structs the screens bind to). The scripts also work on their own.

Requirements: Python 3.10+, standard library only. On Windows, use `python` or `py -3` where the docs say `python3`.

**Before the first screen you create your templates** from your own ctrlX PLC Engineering, see
[First run](#first-run-create-your-templates). They are not part of this repository.

## Contents

| Path | What |
|---|---|
| `SKILL.md` | Skill instructions: workflow, screen API, multi-screen pattern, screen conventions |
| `scripts/visugen.py` | Generator: `python3 scripts/visugen.py screen.py out.export [--templates DIR]` |
| `scripts/preview.py` | Renders a generated export to SVG for given variable values (layout and visibility check) |
| `scripts/make_templates.py` | Builds `templates/` from an export of your own scratch project (first run, see below) |
| `scripts/bisect.py` | Writes small exports (one element kind each, plus a cumulative button chain) to find what an import rejects |
| `templates/` | Made by you with `make_templates.py`, gitignored, not shipped: `wrapper.export` (the device tree and one empty visu) and `elements.xml` (rectangle, button, numpad action, text list) |
| `references/format.md` | The `.export` format: file rules, element property hash IDs, input actions, text IDs, and every import failure found so far |
| `references/example_screen_cutter.py`, `example_preview_cutter.py` | Worked single screen (a cut-to-length station) and its preview scenarios |
| `references/example_hmi_all.py`, `example_kit_hmi_common.py`, `example_scr_transfer.py`, `example_src/` | Worked multi-screen HMI: build entry, shared screen kit, a station screen with a settings page generated from the ST settings struct |
| `tests/run.sh` | Smoke test: builds both examples, renders the previews and checks that `make_templates.py` rebuilds your templates (skips if you have none yet) |

## First run: create your templates

The generator clones a few real objects (the device tree, a rectangle, a button, a numpad action and a text list) from
your own PLC Engineering instead of shipping copies: they are exports of CODESYS visualization objects, and you make
them from the software you are licensed to use. You do this once per PLC Engineering version.

1. In ctrlX PLC Engineering create a blank scratch project. In its Application add:
   - a visualization named `Empty`, left empty;
   - a visualization named `Elements` holding one **Rectangle** and one **Button**. Give the button an input action
     **Write a variable** (any variable, dialog type **Numpad**, any limits);
   - a text list named `Texts` with at least one text.
2. Select those three objects and export them with **Project -> Export Native...**. Save the file as `scratch.export`.
3. Run

       python3 scripts/make_templates.py scratch.export

   It writes `templates/wrapper.export` and `templates/elements.xml` (the folder is gitignored). If something is missing it
   says what, for example that the button has no Write-a-variable action. Other object names: `--empty`, `--elements`,
   `--textlist`. Another folder: `-o DIR`, then pass `--templates DIR` to `visugen.py` or set `CTRLX_HMI_TEMPLATES`.

Menu names differ a little between versions. What matters is the content of the export: an empty visu called `Empty`,
a visu called `Elements` with a rectangle and a button that has a Write-a-variable (Numpad) action, and a text list called
`Texts`.

## Quick start

```sh
mkdir -p build
python3 scripts/visugen.py references/example_screen_cutter.py build/CUT_Main.export
python3 scripts/preview.py build/CUT_Main.export references/example_preview_cutter.py build/preview
```

Import in PLC Engineering with Project → Import… and tick only the new visus and text lists, then run *Update Visualization Text IDs* on the GlobalTextList.

**Import limitation:** the export carries the whole device tree (Device, Plc Logic, Application, ...), so it has to be imported at the top level of a **blank project**. Import it there, then copy the visus and text lists from that project into your own project's Application (copy / paste in the device tree).

## Other PLC Engineering versions

Your templates come from the version you export them with, so make them with the version you build for (see First run). Element FBs are versioned, and an element from an older version can be rejected (the old button was). For an element kind not yet templated (checkbox, combobox, image, frame, alarm table), export a visu containing it from your PLC Engineering and add it as a template. See `references/format.md`.

## License

MIT, see [LICENSE](LICENSE).

Parts of this skill were generated and tested with Claude Opus 5.5 and Claude Sonnet 5.5, see [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md).


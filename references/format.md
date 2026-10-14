# PLC Engineering `.export` format for visualizations

What was established on ctrlX PLC Engineering (profile "ctrlX PLC 3.6.5") by importing generated files and narrowing failures down. The import error is only "an element had an invalid format", with no detail, so every rule here came from a bisect. Treat anything not listed as unknown and copy it from a real export.

## Why not the REST API or PLCopenXML

- The PLC Engineering REST API has no Visualization element type. It handles POUs, DUTs, GVLs, tasks, libraries, recipes and users only. It can run `ImportJob`/`ExportJob` with `.export` files, but those read and write files on the engineering PC's disk.
- Visualizations are not part of a PLCopenXML export.
- So the deliverable is a native `.export` file. The user imports it with Project → Import…

## File level

- XML, ASCII, CRLF line endings, no XML declaration. The first line is `<ExportFile>`, then `  <StructuredView Guid="{d9b2b2cc-ea99-4c3b-aa42-1e5c49e65b84}">`. The inner `<Single xml:space="preserve" Type="{3daac5e4-…}" Method="IArchivable">` tree is indented from column 0, and the file ends with `</Single>  </StructuredView>\r\n</ExportFile>\r\n`.
- **An empty string is `<Single Name=".." Type="string"></Single>`.** The self-closed form `<Single … />` is used only for an empty object (`Method="IArchivable"` with no children). Every other tag (`Null`, `List`, `List2`, `Array`, `Dictionary`, `Dictionary2`) is self-closed when empty. Python's ElementTree writes empty Singles self-closed and has to be post-processed; `visugen.serialize()` does this. The check is that writing the wrapper back must give the same bytes as the original (bisect B0).
- `List2 Name="EntryList"` holds one entry per object: `IsRoot`, `MetaObject` (Guid, ParentGuid, Name, Properties, TypeGuid, EmbeddedTypeGuids, Timestamp), `Object`, `ParentSVNodeGuid`, `Path` (array of ancestor names), `Index`.

## The export must carry the device tree

A single parentless object is rejected; even an empty visu fails that way. A real export of one visu contains Device (`IsRoot` True), Plc Logic, Realtime_Data, Application, `__VisualizationStyle`, Library Manager, PLC_PRG, Symbols, Task Configuration, Visualization Manager, the visu, and MainTask. The generator takes a real export of one empty visu called `Empty` (`templates/wrapper.export`) and puts its objects in place of `Empty`:

- `IsRoot` False; `ParentGuid` and `ParentSVNodeGuid` = the Application's GUID (taken from `Empty`); `Path` = `Empty`'s path (`Device`, `PLC Logic`, `Application`); `Index` -1.
- A visu's `MetaObject/Properties` holds an entry `{477d844b-…}` with `VisuUsageType`, `SizeX`, `SizeY`, `IsStartVisu`, `VisuSizeMode`, … Keep it (clone `Empty`) and set `SizeX`/`SizeY`. `Object/VisuSizeManager` may stay `<Null Name="Size" />`.
- A plain object (text list) directly under the Application has an empty `Properties` dictionary.
- On import, the dialog shows the whole tree. The user ticks only the new objects and leaves PLC_PRG, MainTask and the rest unticked.
- Because of the device tree, the export is imported at the top level of a **blank project**; the visus and text lists are then copied from there into the target project's Application.

## Visualization object

Type GUID `f18bec89-9fef-401d-9953-2f11739a6808`. The `Object` children are LastVisuLanguageModelEntry, UniqueIdGenerator, VisualElemList (`List VisualElementList`, background), GeneratedLMMDescriptions, LastUsedIdForIdentifier, TextDocument (the visu's `VAR_IN_OUT` declaration), GvlCreated, LMEntry, ProfileCompatibilityId, LMVerMinor/Major, Hotkeys, VisuSizeManager, FrameInterfaceDataModel.

- `GeneratedLMMDescriptions`: generated code descriptions, unique per visu. Give every GUID in it a new value, except that the first `FbGuid` is the visu's own GUID.
- `UniqueIdGenerator` and `LastUsedIdForIdentifier`: never set them lower than the template's values.
- Per element: `VisualElementIdentifier` `GenElemInst_<n>`, `VisualElementId` counting from 0, a new `VisualElementIdentification` GUID, and `VisualElementOwningObjectGuid` = the visu GUID. Element order is draw order: later elements paint on top.

## Element versions

Element FBs are versioned (`ElementVersion`). The old project's (3.5.16-style) rectangle, `VisuFbElemSimple` version 0, still imports. Its button, `VisuFbElemButton` version 0 with font object `{896a5e54-…}`, is **rejected**. A current button is version 1 with font object `{9e842eb2-…}`, which has `CanonicalName` and a structured `NamedColor`. **Take templates for anything new from a real export from the target PLC Engineering.** `templates/button.export` is that for the button. When adding an element kind (checkbox, combobox, alarm table, image, frame, ...), ask the user for an export containing one of it, and run the bisect chain idea on it.

## Element properties (`VisualElemMemberList`)

Properties are `{Id: long hash, Value}` pairs. The hash IDs were worked out from about 2600 elements of an old HMI:

| Property | ID | Value |
|---|---|---|
| X, Y, width, height | 1649127785, 357335551, 2422045748, 2134141914 | int (some old elements short; keep the template's type) |
| Centre X/Y | 550940142, 1473355128 | int, x+w/2, y+h/2 |
| Text (static) | 390574330 | string, `%d %s %.1f %08X` placeholders for the text variable |
| **Text ID** | 823443203 | string number. **Required on buttons** (a button without one is rejected); keep it on every element with static text |
| Text variable | 2477733581 | expression |
| Text list / index | 2114174855 / 3774423699 | `'TL_Name'` (quoted) / expression. Static text empty when used |
| Invisible | 2880254039 | BOOL expression (`NOT x`, `a OR b`, `eState = E_X.Manual`; all imported) |
| Deactivate inputs | 2496894244 | BOOL expression |
| Toggle color | 1999528970 | BOOL expression or `<toggle/tap variable>` / `<NOT toggle/tap variable>` |
| Fill / frame colour (normal) | 2812299069 / 494569607 | uint ARGB, or a one-item List of uint |
| Fill / frame colour (alarm) | 493260384 / 135947015 | same |
| Button colour / alarm colour | 2341735680 / 438423234 | List of one item: a named style colour `{fa491db2-…}{Color int, CanonicalName}`, or a custom colour `<Single Type="uint">ARGB</Single>` (imported) |
| Font | 3729828405 | List of one font object; on a button only change FontSize/FontStyle (1 = bold) |
| Font colour | 3488306084 | uint |
| H/V align | 2340015797 / 2565699834 | `LEFT HCENTER RIGHT` / `TOP VCENTER BOTTOM` |
| Shape | 564465120 | `VISU_ST_RECTANGLE`, `VISU_ST_CIRCLE`, `VISU_ST_ROUNDRECT` (same element type) |
| Fill / frame style | 1782330054 / 2827249010 | `BS_SOLID BS_HOLLOW` / `PS_SOLID PS_HOLLOW` |
| Line width | 2678395525 | uint |
| Line break | 4134387352 | `NONE LINEBREAK ELLIPSIS` |
| Image ID (image element) | 3332245745 | `Pool.Image` |
| Colour variables: fill colour | 401380312 | DWORD expression (not tested) |

Inputs:

- **Tap / Toggle** go in `Array ConfiguredComplexInputs`: an item `{1de566f6-…}` with `DescriptionTree` Null, a member list holding `1186196937` = the variable (and optionally `1329445385` bool = Tap FALSE), and `SignatureName` `Visu_TapInput` / `Visu_ToggleInput`, `Name` `Tap` / `Toggle`, plus a `Description`. Tap is TRUE while pressed.
- **Other actions** go in `Dictionary VisualElementInputActions`, keyed `OnMouseDown`, `OnMouseClick`, `OnMouseUp`:
  - numpad/keypad: `{e8e7e747-…}` with InputBoxVariable, InputType `VisuDialogs.Numpad` (imported) or `VisuDialogs.Keypad` (for TIME / STRING; imports and compiles), min, max, title. **The dialog title is an expression:** plain text must be a quoted IEC string (`'Bag length (mm)'`; the generator quotes it);
  - ST snippet ('Execute ST code'): `{6302d3fe-…}` with STSnippet (generator: `st_action`, used for `VisuElems.CurrentVisu := 'X';` and enum writes). Format from the old project; imports and compiles on 3.6.5 (2026-10-14);
  - open a dialog: `{c01cd804-…}` / `{5d84b30d-…}`;
  - change the shown visu: `{4df7df60-…}` with Selection `{5aaff85c-…}` SelectedFrame and GlobSel `{f8c6f6c5-…}`.

## Text IDs (GlobalTextList)

Static texts are identified by an ID in the project's GlobalTextList, which CODESYS numbers incrementally from 0. The generator derives an ID from the text (`100000 + crc32(text) % 900000`), so the same text gets the same ID, in a range the project won't reach. After an import, open the GlobalTextList and run **Text List → Update Visualization Text IDs**, then **Check Visualization Text IDs**.

## Text list object

Type GUID `2bef0454-1bd3-412a-ac2c-af0f31dbc40f`. The `Object` holds `List TextList` of `{53da1be7-…}{TextID, TextDefault, LanguageTexts}`, `Languages`, and new GUIDs for `GuidInit`, `GuidReInit` and `GuidExitX`. An enum display uses TextID = the enum's integer value; the element sets text list `'TL_X'` and text index = the enum variable.

## Lessons from the import failures (in order)

1. Parentless objects: rejected. They need the device tree (wrapper).
2. `<Single … />` for empty strings: rejected. It must be written `></Single>`.
3. Visu metadata properties removed: the visu must keep `{477d844b}` (size, usage).
4. Old button element version: rejected. Use a current button export as the template.
5. Button without a text ID: rejected.
6. Template leftovers: an old template's `Toggle color` still pointed at the old project's variable. Reset every bound property and run `check_refs` (only allowed prefixes such as `GVL_`, `E_`, `VisuDialogs` may appear).

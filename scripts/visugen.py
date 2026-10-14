#!/usr/bin/env python3
"""Generate CODESYS / ctrlX PLC Engineering visualizations as a native .export file.

An export holds the whole device tree down to the exported objects (Device, Plc Logic,
Application, ...). templates/wrapper.export is a real export of one empty visualization ("Empty")
from the target PLC Engineering; generated objects replace "Empty" as children of the Application.
Elements are cloned from templates/elements.xml (elements of the old project's visus) and their
properties rewritten. Properties are stored by numeric hash ID; the IDs below were worked out by
comparing the ~2600 elements of the old HMI.

Usage: python3 visugen.py <screen.py> <out.export> [--templates DIR]
       screen.py defines build(tpl) returning a list of entries (Screen.entry(), textlist()).
       The module is available in screen.py as `vg` (injected). DIR defaults to ../templates.
"""
import copy
import os
import re
import runpy
import sys
import uuid
import zlib
import xml.etree.ElementTree as ET

VISU_TYPE = 'f18bec89-9fef-401d-9953-2f11739a6808'
TEXTLIST_TYPE = '2bef0454-1bd3-412a-ac2c-af0f31dbc40f'
MEMBER_TYPE = '{c694e3a2-5c0b-4177-ab35-cb06bd5a6a02}'
CCI_TYPE = '{1de566f6-72a7-494c-9353-9a418172c96e}'
NUMPAD_ACTION_TYPE = '{e8e7e747-f76f-4dee-ab1c-b9637e41ac26}'
ST_ACTION_TYPE = '{6302d3fe-6ea5-4c42-819a-a9734a133b3d}'   # input action 'Execute ST code'

# Property hash IDs (VisualElemMemberList)
P = dict(
    x='1649127785', y='357335551', w='2422045748', h='2134141914',
    cx='550940142', cy='1473355128',            # rotation centre = middle of the element
    text='390574330', text_var='2477733581', text_id='823443203',
    textlist='2114174855', text_index='3774423699',
    invisible='2880254039', deactivate='2496894244', toggle_color='1999528970',
    fill='2812299069', frame='494569607', alarm_fill='493260384', alarm_frame='135947015',
    halign='2340015797', valign='2565699834', font='3729828405', font_color='3488306084',
    btn_fill='2341735680', btn_alarm_fill='438423234',   # button colours (normal / toggle colour)
    shape='564465120', brush='1782330054', pen='2827249010', line_width='2678395525',
)
# Types to use when a property has to be added to a template that lacks it
ADD_TYPES = {P['invisible']: 'string', P['deactivate']: 'string', P['toggle_color']: 'string',
             P['text_var']: 'string', P['textlist']: 'string', P['text_index']: 'string',
             P['brush']: 'string', P['pen']: 'string', P['text']: 'string'}
# Tap / toggle input configuration
CCI_VAR = '1186196937'
CCI_TAP_FALSE = '1329445385'


def text_id(text):
    """Text ID for a static text. Buttons are rejected without one. Same text -> same ID (as PLC Engineering
    does); derived from the text, in a range above the IDs PLC Engineering hands out (~1000s)."""
    return str(100000 + zlib.crc32(text.encode('utf-8')) % 900000)


def argb(rgb):
    """0xRRGGBB -> unsigned ARGB with full alpha (the uint form used by colour properties)."""
    return 0xFF000000 | rgb


def signed(v):
    return v - (1 << 32) if v >= (1 << 31) else v


def kids(e, name):
    return e.find(f"*[@Name='{name}']")


class Templates:
    def __init__(self, tdir):
        self.root = ET.parse(f'{tdir}/wrapper.export').getroot()
        self.entries = list(self.root.find('StructuredView/Single/List2'))
        self.empty = self.entry('Empty')                     # the visu in the wrapper, replaced on output
        mo = kids(self.empty, 'MetaObject')
        self.app_guid = kids(mo, 'ParentGuid').text
        self.parts = {e.get('TemplateName'): e for e in ET.parse(f'{tdir}/elements.xml').getroot()}

    def entry(self, name):
        for e in self.entries:
            if kids(kids(e, 'MetaObject'), 'Name').text == name:
                return copy.deepcopy(e)
        raise KeyError(name)

    def part(self, name):
        e = copy.deepcopy(self.parts[name])
        e.attrib.pop('TemplateName')
        return e


class Element:
    def __init__(self, el):
        self.el = el
        self.ml = el.find("Single[@Name='VisualElemMemberList']/List")

    def _find(self, pid):
        for m in self.ml:
            if m.findtext("Single[@Name='Id']") == pid:
                return m
        return None

    def remove(self, pid):
        m = self._find(pid)
        if m is not None:
            self.ml.remove(m)

    def set(self, pid, value, typ=None):
        m = self._find(pid)
        if m is None:
            m = ET.SubElement(self.ml, 'Single', {'Type': MEMBER_TYPE, 'Method': 'IArchivable'})
            ET.SubElement(m, 'Single', {'Name': 'Id', 'Type': 'long'}).text = pid
            ET.SubElement(m, 'Single', {'Name': 'Value', 'Type': typ or ADD_TYPES.get(pid, 'string')})
        v = m.find("*[@Name='Value']")
        if v.tag == 'List' and len(v) == 1 and v[0].tag == 'Single' and len(v[0]) == 0:
            v = v[0]                     # colour stored as a one-item list: keep the form, set the item
        elif v.tag != 'Single':          # structured value (named style colour) -> plain value
            m.remove(v)
            v = ET.SubElement(m, 'Single', {'Name': 'Value', 'Type': typ or 'uint'})
        if typ:
            v.set('Type', typ)
        v.text = '' if value is None else str(value)
        if v.text == '':
            v.text = None

    def color(self, pid, rgb):
        self.set(pid, argb(rgb), 'uint')

    def color_list(self, pid, rgb):
        """Custom colour in the one-item-list form (replaces a named style colour)."""
        m = self._find(pid)
        v = m.find("*[@Name='Value']")
        m.remove(v)
        lst = ET.SubElement(m, 'List', {'Name': 'Value', 'Type': 'System.Collections.ArrayList'})
        ET.SubElement(lst, 'Single', {'Type': 'uint'}).text = str(argb(rgb))

    def static_text(self, text):
        self.set(P['text'], text)
        if text:
            self.set(P['text_id'], text_id(text))
        else:
            self.remove(P['text_id'])

    def geometry(self, x, y, w, h):
        for k, v in (('x', x), ('y', y), ('w', w), ('h', h)):
            m = self._find(P[k])
            typ = m.find("*[@Name='Value']").get('Type') if m is not None else 'int'
            self.set(P[k], v, typ)
        if self._find(P['cx']) is not None:
            self.set(P['cx'], x + w // 2, 'int')
            self.set(P['cy'], y + h // 2, 'int')

    def font(self, size, bold=False, rgb=0x000000, style_colors=False):
        """style_colors: only size and weight (button: newer font object with a named colour, keep it)."""
        m = self._find(P['font'])
        if m is not None and style_colors:
            f = m.find("*[@Name='Value']").find('Single')
            kids(f, 'FontSize').text = str(size)
            kids(f, 'FontStyle').text = str(1 if bold else 0)
            return
        if m is not None:
            f = m.find("*[@Name='Value']").find('Single')
            for name, val in (('FontSize', size), ('FontStyle', 1 if bold else 0),
                              ('ExplicitColor', signed(argb(rgb))), ('FontName', 'Arial')):
                e = kids(f, name)
                if e is not None:
                    e.text = str(val)
            dn = kids(f, 'DisplayName')
            if dn is not None:
                dn.text = None              # explicit font, not a style font
            nc = kids(f, 'NamedColor')
            if nc is not None and nc.tag != 'Null':
                f.remove(nc)
                ET.SubElement(f, 'Null', {'Name': 'NamedColor'})
        self.color(P['font_color'], rgb)

    def clear_inputs(self):
        c = self.el.find("Array[@Name='ConfiguredComplexInputs']")
        for x in list(c):
            c.remove(x)
        d = self.el.find("Dictionary[@Name='VisualElementInputActions']")
        for x in list(d):
            d.remove(x)

    def tap(self, var, toggle=False):
        c = self.el.find("Array[@Name='ConfiguredComplexInputs']")
        s = ET.SubElement(c, 'Single', {'Type': CCI_TYPE, 'Method': 'IArchivable'})
        ET.SubElement(s, 'Null', {'Name': 'DescriptionTree'})
        ml = ET.SubElement(s, 'Single', {'Name': 'VisualElemMemberList',
                                         'Type': '{17e26cd1-bb9b-47fe-a3d5-18fcd63b9c96}', 'Method': 'IArchivable'})
        lst = ET.SubElement(ml, 'List', {'Name': 'VisualElemMemberList', 'Type': '{a4b83bea-3742-489c-9fe8-d96d68dba7ab}'})
        m = ET.SubElement(lst, 'Single', {'Type': MEMBER_TYPE, 'Method': 'IArchivable'})
        ET.SubElement(m, 'Single', {'Name': 'Id', 'Type': 'long'}).text = CCI_VAR
        ET.SubElement(m, 'Single', {'Name': 'Value', 'Type': 'string'}).text = var
        if toggle:
            sig, name, desc = 'Visu_ToggleInput', 'Toggle', 'Configure the toggling of a Boolean variable'
        else:
            sig, name, desc = 'Visu_TapInput', 'Tap', 'Configure the tapping of a Boolean variable'
        ET.SubElement(s, 'Single', {'Name': 'SignatureName', 'Type': 'string'}).text = sig
        ET.SubElement(s, 'Single', {'Name': 'Name', 'Type': 'string'}).text = name
        ET.SubElement(s, 'Single', {'Name': 'Description', 'Type': 'string'}).text = desc

    def numpad(self, action_template, var, vmin, vmax, title='', dialog='VisuDialogs.Numpad'):
        """Write-a-variable input action. dialog: VisuDialogs.Numpad (numbers) or VisuDialogs.Keypad (TIME, STRING)."""
        d = self.el.find("Dictionary[@Name='VisualElementInputActions']")
        ent = copy.deepcopy(action_template)
        a = ent.find(f".//Single[@Type='{NUMPAD_ACTION_TYPE}']")
        if title and not (title.startswith("'") and title.endswith("'")):
            title = "'" + title.replace('$', '$$').replace("'", "$'") + "'"   # the title is an expression
        for name, val in (('InputBoxVariable', var), ('InputBoxMin', vmin), ('InputBoxMax', vmax),
                          ('InputBoxDialogTitle', title), ('InputType', dialog)):
            kids(a, name).text = str(val) if val not in ('', None) else None
        d.append(ent)

    def st_action(self, code, event='OnMouseClick'):
        """Input action 'Execute ST code' (e.g. VisuElems.CurrentVisu := 'X'; or an enum write)."""
        d = self.el.find("Dictionary[@Name='VisualElementInputActions']")
        ent = ET.SubElement(d, 'Entry')
        ET.SubElement(ET.SubElement(ent, 'Key'), 'Single', {'Type': 'string'}).text = event
        arr = ET.SubElement(ET.SubElement(ent, 'Value'), 'Array', {'Type': ST_ACTION_TYPE})
        s = ET.SubElement(arr, 'Single', {'Type': ST_ACTION_TYPE, 'Method': 'IArchivable'})
        ET.SubElement(s, 'Single', {'Name': 'STSnippet', 'Type': 'string'}).text = code


class Screen:
    """One visualization. Add elements in draw order (later elements are painted on top)."""

    def __init__(self, tpl, name, width, height, bg=0xEEF0F2):
        self.tpl, self.name, self.width, self.height, self.bg = tpl, name, width, height, bg
        self.items = []
        self.t_rect = tpl.part('rect')
        self.t_circle = tpl.part('rect')
        Element(self.t_circle).set(P['shape'], 'VISU_ST_CIRCLE')
        self.t_button = tpl.part('button')
        self.t_numpad_action = tpl.part('numpad_action')
        # button: real one from the target PLC Engineering (templates/button.export, ElementVersion 1);
        # colours stay the style's named colours
        for t in (self.t_rect, self.t_circle, self.t_button):
            Element(t).clear_inputs()
            for k in ('text_id', 'textlist', 'text_index', 'text_var', 'invisible', 'deactivate'):
                Element(t).remove(P[k])

    # ---- primitives -------------------------------------------------------------------------
    def _add(self, template):
        e = Element(copy.deepcopy(template))
        self.items.append(e)
        return e

    def box(self, x, y, w, h, text='', text_var=None, fill=0xFFFFFF, frame=0x9AA4AE, line=1,
            font=16, bold=False, color=0x000000, align='HCENTER', hollow=False,
            alarm=None, alarm_fill=0xE02020, alarm_frame=None, invisible=None,
            textlist=None, text_index=None):
        """Rectangle with optional text / variable / text-list text. alarm = toggle-colour expression."""
        e = self._add(self.t_rect)
        e.geometry(x, y, w, h)
        e.static_text('' if textlist else text)
        if text_var:
            e.set(P['text_var'], text_var)
        if textlist:
            e.set(P['textlist'], f"'{textlist}'")
            e.set(P['text_index'], text_index)
        e.color(P['fill'], fill)
        e.color(P['frame'], frame)
        e.color(P['alarm_fill'], alarm_fill if alarm else fill)
        e.color(P['alarm_frame'], alarm_frame if alarm_frame is not None else frame)
        e.set(P['toggle_color'], alarm or '')
        e.set(P['brush'], 'BS_HOLLOW' if hollow else 'BS_SOLID')
        e.set(P['pen'], 'PS_HOLLOW' if (hollow or line == 0) else 'PS_SOLID')
        e.set(P['line_width'], max(line, 1), 'uint')
        e.set(P['halign'], align)
        e.set(P['valign'], 'VCENTER')
        e.font(font, bold, color)
        e.set(P['invisible'], invisible or '')
        return e

    def label(self, x, y, w, h, text, **kw):
        kw.setdefault('align', 'LEFT')
        return self.box(x, y, w, h, text, hollow=True, **kw)

    def circle(self, x, y, d, off, on, on_expr, invisible=None):
        e = self._add(self.t_circle)
        e.geometry(x, y, d, d)
        e.static_text('')
        e.color(P['fill'], off)
        e.color(P['alarm_fill'], on)
        e.color(P['frame'], 0x505860)
        e.color(P['alarm_frame'], 0x505860)
        e.set(P['toggle_color'], on_expr or 'FALSE')
        e.set(P['brush'], 'BS_SOLID')
        e.set(P['pen'], 'PS_SOLID')
        e.set(P['invisible'], invisible or '')
        return e

    def button(self, x, y, w, h, text, var=None, toggle=False, invisible=None, deactivate=None, active=None, font=16,
               color=0xE4E7EA, active_color=0x7FD08C, st=None):
        """Tap/Toggle on var, and/or st = ST code run on click. active: colour-variable expression; the button
        shows active_color while it is TRUE (default: while pressed)."""
        e = self._add(self.t_button)
        e.geometry(x, y, w, h)
        e.static_text(text)
        if var:
            e.tap(var, toggle)
        if st:
            e.st_action(st)
        if color is not None:            # None: keep the style's named colours
            e.color_list(P['btn_fill'], color)
            e.color_list(P['btn_alarm_fill'], active_color)
        if active:
            e.set(P['toggle_color'], active)
        e.font(font, True, style_colors=True)
        if invisible:
            e.set(P['invisible'], invisible)
        if deactivate:
            e.set(P['deactivate'], deactivate)
        return e

    def numeric(self, x, y, w, h, var, fmt, vmin, vmax, title='', invisible=None, font=16,
                dialog='VisuDialogs.Numpad', deactivate=None):
        """Value display that opens the numpad (or dialog='VisuDialogs.Keypad' for TIME / STRING) on press."""
        e = self.box(x, y, w, h, fmt, text_var=var, fill=0xFFFFFF, frame=0x3070C0, line=2,
                     font=font, bold=True, invisible=invisible)
        e.numpad(self.t_numpad_action, var, vmin, vmax, title, dialog)
        if deactivate:
            e.set(P['deactivate'], deactivate)
        return e

    # ---- output -------------------------------------------------------------------------------
    def entry(self):
        ent = copy.deepcopy(self.tpl.empty)
        guid = str(uuid.uuid4())
        _meta(ent, self.name, guid, self.tpl)
        vp = kids(ent, 'MetaObject').find(".//Single[@Name='SizeX']/..")
        kids(vp, 'SizeX').text = str(self.width)
        kids(vp, 'SizeY').text = str(self.height)
        ob = kids(ent, 'Object')
        lst = ob.find(".//List[@Name='VisualElementList']")
        for i, e in enumerate(self.items, start=1):
            el = e.el
            kids(el, 'VisualElementIdentifier').text = f'GenElemInst_{i}'
            kids(el, 'VisualElementId').text = str(i - 1)          # PLC Engineering counts from 0
            kids(el, 'VisualElementIdentification').text = str(uuid.uuid4())
            kids(el, 'VisualElementOwningObjectGuid').text = guid
            lst.append(el)
        for n, v in (('UniqueIdGenerator', len(self.items) + 1), ('LastUsedIdForIdentifier', len(self.items))):
            kids(ob, n).text = str(max(v, int(kids(ob, n).text)))   # never below what PLC Engineering had
        vel = kids(ob, 'VisualElemList')
        kids(vel, 'BackgroundColor').text = str(self.bg)
        # generated code descriptions: fresh GUIDs, the first FbGuid is the visualization's own GUID
        gen = kids(ob, 'GeneratedLMMDescriptions')
        first = True
        for g in gen.iter('Single'):
            if g.get('Type') == 'System.Guid' and g.text and g.text != '00000000-0000-0000-0000-000000000000':
                if g.get('Name') == 'FbGuid' and first:
                    g.text, first = guid, False
                else:
                    g.text = str(uuid.uuid4())
        return ent


def clone_visu(ent, name, tpl):
    """Copy of a real visu entry under a new name: new GUIDs for the visu, its generated block and its elements."""
    ent = copy.deepcopy(ent)
    guid = str(uuid.uuid4())
    _meta(ent, name, guid, tpl)
    ob = kids(ent, 'Object')
    first = True
    for g in kids(ob, 'GeneratedLMMDescriptions').iter('Single'):
        if g.get('Type') == 'System.Guid' and g.text and g.text != '00000000-0000-0000-0000-000000000000':
            if g.get('Name') == 'FbGuid' and first:
                g.text, first = guid, False
            else:
                g.text = str(uuid.uuid4())
    for el in ob.find(".//List[@Name='VisualElementList']"):
        kids(el, 'VisualElementIdentification').text = str(uuid.uuid4())
        kids(el, 'VisualElementOwningObjectGuid').text = guid
    return ent


def _meta(ent, name, guid, tpl):
    """Make an entry a child of the wrapper's Application (same parent fields as the wrapper's Empty visu)."""
    kids(ent, 'IsRoot').text = 'False'
    mo = kids(ent, 'MetaObject')
    kids(mo, 'Guid').text = guid
    kids(mo, 'ParentGuid').text = tpl.app_guid
    kids(mo, 'Name').text = name
    kids(ent, 'ParentSVNodeGuid').text = tpl.app_guid
    ent.remove(kids(ent, 'Path'))
    ent.insert(list(ent).index(kids(ent, 'Index')), copy.deepcopy(kids(tpl.empty, 'Path')))
    kids(ent, 'Index').text = kids(tpl.empty, 'Index').text


def textlist(tpl, name, items):
    """Text list object: items = [(id, text), ...]."""
    ent = tpl.part('textlist')
    _meta(ent, name, str(uuid.uuid4()), tpl)
    props = kids(kids(ent, 'MetaObject'), 'Properties')   # plain object under the Application: no entries
    for x in list(props):
        props.remove(x)
    ob = kids(ent, 'Object')
    tl = kids(ob, 'TextList')
    proto = copy.deepcopy(tl[0])
    for x in list(tl):
        tl.remove(x)
    for tid, text in items:
        t = copy.deepcopy(proto)
        kids(t, 'TextID').text = str(tid)
        kids(t, 'TextDefault').text = text
        tl.append(t)
    for n in ('GuidInit', 'GuidReInit', 'GuidExitX'):
        kids(ob, n).text = str(uuid.uuid4())
    return ent


def write_export(tpl, entries, out, keep_empty=False):
    """The wrapper's device tree with the generated entries in place of its Empty visu."""
    root = copy.deepcopy(tpl.root)
    lst = root.find('StructuredView/Single/List2')
    for i, e in enumerate(lst):
        if kids(kids(e, 'MetaObject'), 'Name').text == 'Empty':
            if not keep_empty:
                lst.remove(e)
            for j, n in enumerate(entries):
                lst.insert(i + j + (1 if keep_empty else 0), n)
            break
    with open(out, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(serialize(root) + '\n')


def serialize(root):
    """Write like PLC Engineering: the inner tree is indented from column 0 inside <StructuredView>, an empty
    <Single> value is <Single ...></Single> (an empty string); the self-closed form is only used for empty
    objects (Method="IArchivable") and the other tags."""
    sv = root.find('StructuredView')
    inner = sv.find('Single')
    ET.indent(inner, '  ')
    data = ET.tostring(inner, encoding='unicode').rstrip()
    data = re.sub(r'<Single((?:(?!Method=)[^>])*?) />', r'<Single\1></Single>', data)
    return f'<ExportFile>\n  <StructuredView Guid="{sv.get("Guid")}">\n{data}  </StructuredView>\n</ExportFile>'


def check_refs(entries, allowed):
    """Every dotted name in a string property must start with an allowed prefix (catches template leftovers)."""
    bad = set()
    for e in entries:
        for v in e.iter('Single'):
            if v.get('Type') == 'string' and v.text:
                for name in re.findall(r"(?<![.'\w\]])([A-Za-z_]\w*)\.[A-Za-z_]", v.text):
                    if not name.startswith(allowed):
                        bad.add(v.text)
    if bad:
        raise SystemExit('template leftovers / unknown references:\n  ' + '\n  '.join(sorted(bad)))


TEMPLATES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')


def main():
    import argparse
    ap = argparse.ArgumentParser(description='Generate a PLC Engineering .export from a screen definition')
    ap.add_argument('screen')
    ap.add_argument('out')
    ap.add_argument('--templates', default=TEMPLATES)
    a = ap.parse_args()
    tpl = Templates(a.templates)
    mod = runpy.run_path(a.screen, init_globals={'vg': sys.modules[__name__]})
    entries = mod['build'](tpl)
    check_refs(entries, tuple(mod.get('ALLOWED_PREFIXES', ('GVL_', 'E_', 'VisuDialogs'))))
    write_export(tpl, entries, a.out)
    print(f'{a.out}: {len(entries)} objects')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Import-failure bisect set. Writes small exports; import them in order, the first failure points at the cause.

Usage: python3 bisect.py <out_dir> [--templates DIR]

  B0_Unchanged   wrapper written back (must be byte-identical to templates/wrapper.export)
  B1_Empty       the wrapper's empty visu, renamed, new GUIDs
  B2..B7         one element kind each (label, lamp, button style/custom colour/active/toggle, numpad, value)
  B9a/B9b        button with an 'Execute ST code' action (screen change); keypad field
  B8_TextList    a text list
  C1..C7         cumulative chain from the real button (templates/button.export): clone, text, geometry,
                 font, variable, invisible, tap
"""
import argparse
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import visugen as vg  # noqa: E402

P = vg.P
CASES = {
    'B1_Empty': lambda sc: None,
    'B2_Label': lambda sc: sc.label(20, 20, 300, 30, 'Test label', font=18),
    'B3_Lamp': lambda sc: sc.circle(20, 20, 26, 0xB4B9BE, 0x22B14C, 'TRUE'),
    'B4a_ButtonStyle': lambda sc: sc.button(20, 20, 170, 56, 'Test button', 'PLC_PRG.bTest', color=None),
    'B4b_ButtonColour': lambda sc: sc.button(20, 20, 170, 56, 'Test button', 'PLC_PRG.bTest'),
    'B4c_ButtonActive': lambda sc: sc.button(20, 20, 170, 56, 'Test button', 'PLC_PRG.bTest', active='PLC_PRG.bTest'),
    'B4d_ButtonToggle': lambda sc: sc.button(20, 20, 170, 56, 'Test toggle', 'PLC_PRG.bTest', toggle=True),
    'B5_Numpad': lambda sc: sc.numeric(20, 20, 170, 48, 'PLC_PRG.iTest', '%d', 0, 2000, 'Test'),
    'B6_TextVar': lambda sc: sc.box(20, 20, 170, 30, '%d', text_var='PLC_PRG.iTest'),
    'B9a_ButtonST': lambda sc: sc.button(20, 20, 170, 56, 'Go to Empty', st="VisuElems.CurrentVisu := 'Empty';"),
    'B9b_Keypad': lambda sc: sc.numeric(20, 20, 170, 48, 'PLC_PRG.tTest', '%s', '', '', 'Time',
                                        dialog='VisuDialogs.Keypad'),
}


def _button_entry(tdir):
    root = ET.parse(f'{tdir}/button.export').getroot()
    for e in root.find('StructuredView/Single/List2'):
        if vg.kids(vg.kids(e, 'MetaObject'), 'TypeGuid').text == vg.VISU_TYPE:
            return e


def _btn(ent):
    return vg.Element(ent.find(".//List[@Name='VisualElementList']")[0])


def _cci_var(ent, var):
    for m in ent.iter('Single'):
        if m.findtext("Single[@Name='Id']") == vg.CCI_VAR:
            m.find("Single[@Name='Value']").text = var


def _to_tap(ent):
    e = _btn(ent)
    c = e.el.find("Array[@Name='ConfiguredComplexInputs']")
    var = c.find(".//Single[@Name='Value']").text
    for x in list(c):
        c.remove(x)
    e.tap(var, toggle=False)


CHAIN = [
    ('C1_Clone', lambda ent: None),
    ('C2_Text', lambda ent: _btn(ent).static_text('Test button')),
    ('C3_Geometry', lambda ent: _btn(ent).geometry(20, 20, 170, 56)),
    ('C4_Font', lambda ent: _btn(ent).font(16, True, style_colors=True)),
    ('C5_Variable', lambda ent: _cci_var(ent, 'PLC_PRG.bTest')),
    ('C6_Invisible', lambda ent: _btn(ent).set(P['invisible'], 'NOT PLC_PRG.bTest')),
    ('C7_Tap', _to_tap),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out_dir')
    ap.add_argument('--templates', default=vg.TEMPLATES)
    a = ap.parse_args()
    tpl = vg.Templates(a.templates)
    os.makedirs(a.out_dir, exist_ok=True)
    out = lambda n: os.path.join(a.out_dir, n + '.export')
    vg.write_export(tpl, [], out('B0_Unchanged'), keep_empty=True)
    for name, add in CASES.items():
        sc = vg.Screen(tpl, name, 400, 200)
        add(sc)
        vg.write_export(tpl, [sc.entry()], out(name))
    vg.write_export(tpl, [vg.textlist(tpl, 'B8_TextList', [(0, 'Zero'), (1, 'One')])], out('B8_TextList'))
    if os.path.exists(f'{a.templates}/button.export'):
        ent = _button_entry(a.templates)
        for name, change in CHAIN:
            change(ent)                                     # cumulative
            vg.write_export(tpl, [vg.clone_visu(ent, name, tpl)], out(name))
    same = open(f'{a.templates}/wrapper.export', 'rb').read() == open(out('B0_Unchanged'), 'rb').read()
    print(f'{a.out_dir}: bisect set written; B0 byte-identical to wrapper: {same}')


if __name__ == '__main__':
    main()

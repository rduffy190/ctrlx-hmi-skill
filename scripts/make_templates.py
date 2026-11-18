#!/usr/bin/env python3
"""Build the templates visugen.py needs from an export made with your own ctrlX PLC Engineering.

The skill does not ship templates: they are exports of CODESYS visualization objects, and you create them
yourself from the software you are licensed to use. This script turns one export of a small scratch project
into the two template files:

    templates/wrapper.export   the device tree plus the empty visualization "Empty"
    templates/elements.xml     a rectangle, a button, a "Write a variable" numpad action and a text list

Make the scratch export once per PLC Engineering version (see README, "First run: create your templates"):
a blank project whose Application holds
  - a visualization named Empty with nothing in it,
  - a visualization named Elements with one Rectangle and one Button; the button has an input action
    "Write a variable" with the Numpad dialog (any variable, any limits),
  - a text list named Texts with at least one text,
and export those three objects with Project > Export Native.

Usage: python3 make_templates.py scratch.export [-o DIR] [--empty Empty] [--elements Elements] [--textlist Texts]
       DIR defaults to ../templates (the folder visugen.py reads; it is gitignored).
"""
import argparse
import copy
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import visugen as vg  # noqa: E402

kids = vg.kids
ELEMENT_TYPE = '{f86c2928-8614-4cca-824b-e819ac4d58c4}'   # a visualization element (rectangle, button, ...)


class SetupError(SystemExit):
    pass


def fail(msg):
    raise SetupError('make_templates: ' + msg)


def entry_name(e):
    return kids(kids(e, 'MetaObject'), 'Name').text


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('export', help='the scratch export made in ctrlX PLC Engineering')
    ap.add_argument('-o', '--out', default=vg.TEMPLATES)
    ap.add_argument('--empty', default='Empty', help='name of the empty visualization')
    ap.add_argument('--elements', default='Elements', help='name of the visualization holding the elements')
    ap.add_argument('--textlist', default='Texts', help='name of the text list')
    a = ap.parse_args()

    try:
        root = ET.parse(a.export).getroot()
    except (ET.ParseError, OSError) as e:
        fail(f'cannot read {a.export}: {e}')
    lst = root.find('StructuredView/Single/List2')
    if lst is None:
        fail(f'{a.export} is not a PLC Engineering native export (no entry list)')
    by_name = {entry_name(e): e for e in lst}
    have = ', '.join(sorted(by_name)) or '(none)'
    for what, name in (('empty visualization', a.empty), ('visualization with the elements', a.elements),
                       ('text list', a.textlist)):
        if name not in by_name:
            fail(f'no object named "{name}" ({what}) in the export. Objects in it: {have}')

    # ---- elements ----------------------------------------------------------------------------
    holder = by_name[a.elements]
    found = {}
    for el in holder.iter('Single'):
        if el.get('Type') != ELEMENT_TYPE:
            continue
        tn = el.find("Single[@Name='VisualElementTypeName']")
        if tn is None:
            continue
        kind = {'VisuFbElemSimple': 'rect', 'VisuFbElemButton': 'button'}.get(tn.text)
        if kind and kind not in found:
            found[kind] = el
    for kind, label in (('rect', 'a Rectangle'), ('button', 'a Button')):
        if kind not in found:
            fail(f'"{a.elements}" has no {label}. Add one and export again')

    action = None
    for ent in found['button'].iter('Entry'):
        if ent.find(f".//Single[@Type='{vg.NUMPAD_ACTION_TYPE}']") is not None:
            action = copy.deepcopy(ent)
            break
    if action is None:
        fail('the button has no "Write a variable" input action with the Numpad dialog. Add one and export again')
    key = action.find('Key/Single')
    if key is not None and key.text != 'OnMouseDown':
        print(f'note: the action was on {key.text}; the template uses OnMouseDown', file=sys.stderr)
        key.text = 'OnMouseDown'

    parts = ET.Element('Templates')
    for kind in ('rect', 'button'):
        el = copy.deepcopy(found[kind])
        # the generator adds the actions itself; a template that carries one would give every element a copy
        actions = el.find("Dictionary[@Name='VisualElementInputActions']")
        if actions is not None:
            for ent in list(actions):
                actions.remove(ent)
        el.set('TemplateName', kind)
        parts.append(el)
    tl = copy.deepcopy(by_name[a.textlist])
    tl.set('TemplateName', 'textlist')
    parts.append(tl)
    action.set('TemplateName', 'numpad_action')
    parts.append(action)

    # ---- wrapper: the device tree and the empty visualization, without the objects used above ---
    wrapper = copy.deepcopy(root)
    wl = wrapper.find('StructuredView/Single/List2')
    for e in list(wl):
        if entry_name(e) in (a.elements, a.textlist):
            wl.remove(e)
    if a.empty != 'Empty':
        for e in wl:
            if entry_name(e) == a.empty:
                kids(kids(e, 'MetaObject'), 'Name').text = 'Empty'

    # The export is indented; the template file is compact (visugen re-indents on output). Drop the layout
    # whitespace only: text of a leaf <Single> is data and stays.
    for n in parts.iter():
        if n.tail and not n.tail.strip():
            n.tail = None
        if n.text and not n.text.strip() and (len(n) or n.tag != 'Single'):
            n.text = None

    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, 'wrapper.export'), 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(vg.serialize(wrapper) + '\n')
    ET.ElementTree(parts).write(os.path.join(a.out, 'elements.xml'), encoding='utf-8')
    # fail now, not on the first generated screen
    vg.Templates(a.out)
    print(f'wrote {os.path.join(a.out, "wrapper.export")} and {os.path.join(a.out, "elements.xml")}')


if __name__ == '__main__':
    main()

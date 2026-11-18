#!/usr/bin/env python3
"""make_templates.py must rebuild the templates from a scratch export.

Needs templates already in place (the folder visugen.py reads). It builds a stand-in for the scratch export a
user makes in PLC Engineering (the wrapper plus an "Elements" visu holding the rectangle, the button and a numpad
action, plus a "Texts" text list), runs make_templates.py on it and checks that the wrapper and all four element
parts come back unchanged. Skips with exit code 0 when there are no templates to build the stand-in from.

    python3 tests/test_make_templates.py [--templates DIR]
"""
import copy
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HMI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HMI, 'scripts'))
import visugen as vg  # noqa: E402

tdir = vg.TEMPLATES
if '--templates' in sys.argv:
    tdir = sys.argv[sys.argv.index('--templates') + 1]
if not (os.path.isfile(os.path.join(tdir, 'wrapper.export')) and os.path.isfile(os.path.join(tdir, 'elements.xml'))):
    print(f'SKIP make_templates round trip: no templates in {tdir} (run make_templates.py first)')
    sys.exit(0)

kids = vg.kids
tpl = vg.Templates(tdir)

root = copy.deepcopy(tpl.root)
lst = root.find('StructuredView/Single/List2')
elements = copy.deepcopy(tpl.empty)
kids(kids(elements, 'MetaObject'), 'Name').text = 'Elements'
kids(kids(elements, 'MetaObject'), 'Guid').text = 'aaaaaaaa-0000-0000-0000-000000000001'
vl = kids(elements, 'Object').find(".//List[@Name='VisualElementList']")
button = tpl.part('button')
button.find("Dictionary[@Name='VisualElementInputActions']").append(tpl.part('numpad_action'))
vl.append(tpl.part('rect'))
vl.append(button)
lst.append(elements)
texts = tpl.part('textlist')
kids(kids(texts, 'MetaObject'), 'Name').text = 'Texts'
lst.append(texts)

work = tempfile.mkdtemp(prefix='scratch')
scratch = os.path.join(work, 'scratch.export')
with open(scratch, 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(vg.serialize(root) + '\n')
out = os.path.join(work, 'templates')
r = subprocess.run([sys.executable, os.path.join(HMI, 'scripts', 'make_templates.py'), scratch, '-o', out],
                   capture_output=True, text=True)
assert r.returncode == 0, r.stdout + r.stderr


def canon(e):
    return ET.canonicalize(ET.tostring(e, encoding='unicode'), strip_text=True)


assert open(os.path.join(tdir, 'wrapper.export'), 'rb').read() == open(os.path.join(out, 'wrapper.export'), 'rb').read(), \
    'wrapper.export changed'
orig = {e.get('TemplateName'): e for e in ET.parse(os.path.join(tdir, 'elements.xml')).getroot()}
new = {e.get('TemplateName'): e for e in ET.parse(os.path.join(out, 'elements.xml')).getroot()}
assert sorted(orig) == sorted(new) == ['button', 'numpad_action', 'rect', 'textlist'], (sorted(orig), sorted(new))
for k in orig:
    o, n = copy.deepcopy(orig[k]), copy.deepcopy(new[k])
    if k == 'textlist':       # the stand-in renames it
        for e in (o, n):
            kids(kids(e, 'MetaObject'), 'Name').text = 'X'
    assert canon(o) == canon(n), f'template part "{k}" changed'

# a button without the numpad action must be reported, not silently accepted
bad = copy.deepcopy(root)
for b in bad.iter('Single'):
    if b.get('Type') == vg.NUMPAD_ACTION_TYPE:
        b.set('Type', '{00000000-0000-0000-0000-000000000000}')
bad_path = os.path.join(work, 'bad.export')
with open(bad_path, 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(vg.serialize(bad) + '\n')
r = subprocess.run([sys.executable, os.path.join(HMI, 'scripts', 'make_templates.py'), bad_path, '-o', os.path.join(work, 't2')],
                   capture_output=True, text=True)
assert r.returncode != 0 and 'Write a variable' in r.stderr, r.stderr

print('PASS make_templates rebuilds wrapper.export and the four element parts, and rejects a scratch export without the numpad action')

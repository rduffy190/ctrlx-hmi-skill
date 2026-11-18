#!/usr/bin/env python3
"""Render a generated .export to SVG for given variable values (a rough preview, not CODESYS: checks layout
and the Invisible / Toggle colour / text-list expressions; buttons are drawn generically).

Usage: python3 preview.py <file.export> <scenario.py> <out_dir>
scenario.py defines SCENARIOS = {name: {variable: value}} and ENUMS = {'E_X': [names...]}.
Unknown variables read as 0 / FALSE.
"""
import html
import os
import re
import runpy
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from visugen import P, kids, VISU_TYPE, TEXTLIST_TYPE  # noqa: E402


def load(path):
    root = ET.parse(path).getroot()
    visus, tls = [], {}
    for e in root.find('StructuredView/Single/List2'):
        mo = kids(e, 'MetaObject')
        t = kids(mo, 'TypeGuid').text
        name = kids(mo, 'Name').text
        ob = kids(e, 'Object')
        if t == TEXTLIST_TYPE:
            tls[name] = {kids(x, 'TextID').text: kids(x, 'TextDefault').text or '' for x in kids(ob, 'TextList')}
        elif t == VISU_TYPE:
            sx = mo.find(".//Single[@Name='SizeX']")
            ob.set('_size', f"{sx.text},{mo.find('.//Single[@Name=\'SizeY\']').text}")
            visus.append((name, ob))
    return visus, tls


class Eval:
    def __init__(self, values, enums):
        self.values, self.enums = values, enums

    def __call__(self, expr, default=False):
        if not expr or expr.startswith('<'):
            return default
        py = expr
        for en, names in self.enums.items():
            py = re.sub(rf'\b{en}\.(\w+)\b', lambda m: str(names.index(m.group(1))), py)
        py = re.sub(r'<>', ' != ', py)
        py = re.sub(r'(?<![<>!=])=(?!=)', ' == ', py)
        py = re.sub(r'\bAND\b', ' and ', py)
        py = re.sub(r'\bOR\b', ' or ', py)
        py = re.sub(r'\bNOT\b', ' not ', py)
        py = re.sub(r'\bTRUE\b', 'True', py)
        py = re.sub(r'\bFALSE\b', 'False', py)
        py = re.sub(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*|\[[^\]]*\])*',
                    lambda m: m.group(0) if m.group(0) in ('and', 'or', 'not', 'True', 'False')
                    else f'V({m.group(0)!r})', py)
        funcs = {'SEL': lambda g, a, b: b if g else a, 'MAX': max, 'MIN': min}
        return eval(py, {'V': lambda n: funcs.get(n) or self.values.get(n, 0)})


def fmt(text, val):
    if val is None:
        return text
    def rep(m):
        spec = m.group(0)
        try:
            if spec.endswith('s'):
                return str(val)
            return spec % val
        except TypeError:
            return str(val)
    return re.sub(r'%[-0-9.]*[dfisXx]', rep, text)


def color(v):
    return '#%06X' % (int(v) & 0xFFFFFF)


def render(ob, tls, ev):
    W, H = (int(v) for v in ob.get('_size').split(','))
    bg = int(kids(kids(ob, 'VisualElemList'), 'BackgroundColor').text)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           f'font-family="Arial"><rect width="{W}" height="{H}" fill="{color(bg)}"/>']
    for el in ob.find(".//List[@Name='VisualElementList']"):
        typ = kids(el, 'VisualElementTypeName').text
        pr = {m.findtext("Single[@Name='Id']"): m.find("*[@Name='Value']")
              for m in el.find("Single[@Name='VisualElemMemberList']/List")}
        def g(k, d=None):
            v = pr.get(P[k])
            if v is not None and v.tag == 'List' and len(v) == 1 and v[0].tag == 'Single':
                v = v[0]
            return v.text if v is not None and v.tag == 'Single' and len(v) == 0 else d
        if ev(g('invisible')):
            continue
        x, y, w, h = (int(g(k, 0)) for k in ('x', 'y', 'w', 'h'))
        alarm = ev(g('toggle_color'))
        fill = g('alarm_fill' if alarm else 'fill', 0xFFFFFFFF)
        frame = g('alarm_frame' if alarm else 'frame', 0xFF000000)
        hollow = g('brush') == 'BS_HOLLOW'
        pen = g('pen') != 'PS_HOLLOW'
        fobj = pr[P['font']].find('Single')
        fsize = int(kids(fobj, 'FontSize').text)
        bold = kids(fobj, 'FontStyle').text == '1'
        fcol = color(int(kids(fobj, 'ExplicitColor').text))
        if typ == 'VisuFbElemButton':
            cci = el.find("Array[@Name='ConfiguredComplexInputs']")
            kind = cci[0].findtext("Single[@Name='Name']") if len(cci) else ''
            on = alarm and g('toggle_color') not in (None, '<toggle/tap variable>')
            out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{"#9FD8A8" if on else "#E4E7EA"}" '
                       f'stroke="#7A8590" stroke-width="1.5"/>')
            if kind == 'Toggle':
                out.append(f'<text x="{x + w - 8}" y="{y + 14}" font-size="10" text-anchor="end" fill="#606870">toggle</text>')
        elif g('shape') == 'VISU_ST_CIRCLE':
            out.append(f'<circle cx="{x + w / 2}" cy="{y + h / 2}" r="{w / 2}" fill="{color(fill)}" stroke="{color(frame)}"/>')
        else:
            out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{"none" if hollow else color(fill)}" '
                       f'stroke="{color(frame) if pen else "none"}"/>')
        text = g('text') or ''
        if g('textlist'):
            tl = tls.get(g('textlist').strip("'"), {})
            text = tl.get(str(int(ev(g('text_index'), 0))), '?')
        elif g('text_var'):
            text = fmt(text, ev(g('text_var'), 0))
        if text:
            al = g('halign', 'HCENTER')
            tx, anchor = {'LEFT': (x + 4, 'start'), 'RIGHT': (x + w - 4, 'end')}.get(al, (x + w / 2, 'middle'))
            out.append(f'<text x="{tx}" y="{y + h / 2}" dominant-baseline="central" text-anchor="{anchor}" '
                       f'font-size="{fsize}" font-weight="{"bold" if bold else "normal"}" fill="{fcol}">'
                       f'{html.escape(text)}</text>')
    out.append('</svg>')
    return '\n'.join(out)


def main():
    visus, tls = load(sys.argv[1])
    sc = runpy.run_path(sys.argv[2])
    os.makedirs(sys.argv[3], exist_ok=True)
    for vname, ob in visus:
        for sname, values in sc['SCENARIOS'].items():
            svg = render(ob, tls, Eval(values, sc['ENUMS']))
            path = os.path.join(sys.argv[3], f'{vname}_{sname}.svg')
            with open(path, 'w') as f:
                f.write(svg)
            print(path)


if __name__ == '__main__':
    main()

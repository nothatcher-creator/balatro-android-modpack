#!/usr/bin/env python3
import re
import sys
import xml.etree.ElementTree as ET

if len(sys.argv) != 3:
    raise SystemExit("usage: ui_pick.py <ui.xml> <needle>")
path, needle = sys.argv[1], sys.argv[2].lower()
text = open(path, "r", errors="ignore").read()
start = text.find("<?xml")
if start < 0:
    raise SystemExit(2)
root = ET.fromstring(text[start:])
for node in root.iter("node"):
    hay = ((node.attrib.get("text") or "") + " " + (node.attrib.get("content-desc") or "")).lower()
    if needle not in hay:
        continue
    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
    if not m:
        continue
    x1, y1, x2, y2 = map(int, m.groups())
    print((x1+x2)//2, (y1+y2)//2)
    raise SystemExit(0)
raise SystemExit(3)

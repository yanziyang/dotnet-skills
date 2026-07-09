#!/usr/bin/env python3
"""Generate an editable draw.io (diagrams.net) ER diagram from a JSON spec.

Usage:
    python make_drawio_erd.py <spec.json> [<spec2.json> ...]

Each spec produces "<spec-dir>/<name>.drawio" (name from the spec, falling
back to the spec's file stem, with any trailing ".drawio" stripped). The
output uses draw.io's native entity shapes (swimlane + stacked rows), so the
user can add columns, drag entities, and re-route relationships in
app.diagrams.net, the draw.io desktop app, or the VS Code extension.

Spec format:

{
  "name": "01-erd-sales",
  "title": "Sales Module - Entity Relationship Diagram",
  "entities": [
    { "id": "order", "name": "Order",
      "columns": [
        {"name": "Id",         "type": "int",           "key": "PK"},
        {"name": "CustomerId", "type": "int",           "key": "FK"},
        {"name": "PlacedAt",   "type": "datetime2",     "nullable": false},
        {"name": "Notes",      "type": "nvarchar(500)", "nullable": true}
      ] },
    { "id": "customer", "name": "Customer", "columns": [
        {"name": "Id", "type": "int", "key": "PK"} ] }
  ],
  "relations": [
    {"from": "customer", "to": "order", "label": "places", "cardinality": "1:N"}
  ]
}

Column fields: "key" is "PK", "FK", or absent; "nullable" defaults to false
(NOT NULL). Cardinality is "from-side:to-side" where each side is one of
1, 0..1, N, or 0..N — e.g. "1:N" (one customer, many orders), "1:0..1",
"N:M". Keep specs to the same entities/relationships as the Mermaid twin.
"""

import json
import os
import sys
import xml.etree.ElementTree as ET

ENTITY_W = 240
HEADER_H = 28
ROW_H = 22
H_GAP, V_GAP = 120, 90
MARGIN, TITLE_H = 40, 50
PER_ROW = 3          # entities per grid row

ENTITY_STYLE = ("swimlane;fontStyle=1;align=center;verticalAlign=top;"
                "childLayout=stackLayout;horizontal=1;startSize=28;"
                "horizontalStack=0;resizeParent=1;resizeParentMax=0;"
                "collapsible=1;marginBottom=0;html=1;fontSize=12;"
                "fillColor=#dae8fc;strokeColor=#6c8ebf;fontColor=#1F3864;"
                "swimlaneFillColor=#ffffff;")
ROW_STYLE = ("text;strokeColor=none;fillColor=none;align=left;"
             "verticalAlign=middle;spacingLeft=6;spacingRight=6;"
             "overflow=hidden;rotatable=0;points=[[0,0.5],[1,0.5]];"
             "portConstraint=eastwest;html=1;fontSize=11;")
KEY_ROW_STYLE = ROW_STYLE + "fontStyle=1;fontColor=#1F3864;"
TITLE_STYLE = ("text;html=1;fontSize=18;fontStyle=1;fontColor=#1F3864;"
               "align=center;verticalAlign=middle;")
EDGE_BASE = ("edgeStyle=entityRelationEdgeStyle;rounded=0;html=1;fontSize=11;"
             "labelBackgroundColor=#ffffff;strokeColor=#5b7699;"
             "exitX=1;exitY=0.5;exitDx=0;exitDy=0;")

# draw.io crow's-foot arrow names per cardinality side
SIDE_ARROW = {"1": "ERone", "0..1": "ERzeroToOne", "0": "ERzeroToOne",
              "N": "ERmany", "M": "ERmany", "*": "ERmany",
              "0..N": "ERzeroToMany", "0..*": "ERzeroToMany"}


def row_text(col):
    key = (col.get("key") or "").upper()
    prefix = f"{key}  " if key else ""
    null_mark = "" if not col.get("nullable") else "  (null)"
    ctype = col.get("type", "")
    type_part = f" : {ctype}" if ctype else ""
    return f"{prefix}{col.get('name', '?')}{type_part}{null_mark}"


def build(spec, out_path):
    entities = spec.get("entities") or []
    relations = spec.get("relations") or []
    if not entities:
        raise ValueError("spec has no entities")

    ids = {}
    for ent in entities:
        ent_id = ent.get("id")
        if not ent_id:
            raise ValueError(f"entity without id: {ent.get('name', ent)}")
        if ent_id in ids:
            raise ValueError(f"duplicate entity id: {ent_id}")
        ids[ent_id] = ent
    for rel in relations:
        for end in ("from", "to"):
            if rel.get(end) not in ids:
                raise ValueError(
                    f"relation {rel} references unknown entity id "
                    f"'{rel.get(end)}'")

    per_row = min(PER_ROW, len(entities))
    canvas_w = per_row * ENTITY_W + (per_row - 1) * H_GAP
    total_w = canvas_w + 2 * MARGIN

    mxfile = ET.Element("mxfile", host="app.diagrams.net")
    diagram = ET.SubElement(mxfile, "diagram", id="page-1",
                            name=spec.get("title", "ERD"))
    model = ET.SubElement(
        diagram, "mxGraphModel", dx="1200", dy="900", grid="1", gridSize="10",
        guides="1", tooltips="1", connect="1", arrows="1", fold="1", page="1",
        pageScale="1", pageWidth=str(total_w), pageHeight="1400",
        math="0", shadow="0")
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")

    def geometry(cell, x, y, w, h):
        geo = ET.SubElement(cell, "mxGeometry")
        geo.set("x", str(int(x)))
        geo.set("y", str(int(y)))
        geo.set("width", str(int(w)))
        geo.set("height", str(int(h)))
        geo.set("as", "geometry")

    if spec.get("title"):
        cell = ET.SubElement(root, "mxCell", id="title",
                             value=spec["title"], style=TITLE_STYLE,
                             vertex="1", parent="1")
        geometry(cell, MARGIN, MARGIN, canvas_w, 30)

    # grid layout: row height driven by the tallest entity in that grid row
    top = MARGIN + (TITLE_H if spec.get("title") else 0)
    for start in range(0, len(entities), per_row):
        band = entities[start:start + per_row]
        band_h = max(HEADER_H + len(e.get("columns") or []) * ROW_H
                     for e in band)
        for i, ent in enumerate(band):
            x = MARGIN + i * (ENTITY_W + H_GAP)
            cols = ent.get("columns") or []
            h = HEADER_H + len(cols) * ROW_H
            cell = ET.SubElement(root, "mxCell", id=ent["id"],
                                 value=ent.get("name", ent["id"]),
                                 style=ENTITY_STYLE, vertex="1", parent="1")
            geometry(cell, x, top, ENTITY_W, h)
            for r, col in enumerate(cols):
                style = KEY_ROW_STYLE if col.get("key") else ROW_STYLE
                row = ET.SubElement(root, "mxCell",
                                    id=f"{ent['id']}_r{r}",
                                    value=row_text(col), style=style,
                                    vertex="1", parent=ent["id"])
                geo = ET.SubElement(row, "mxGeometry")
                geo.set("y", str(HEADER_H + r * ROW_H))
                geo.set("width", str(ENTITY_W))
                geo.set("height", str(ROW_H))
                geo.set("as", "geometry")
        top += band_h + V_GAP

    for i, rel in enumerate(relations):
        card = str(rel.get("cardinality", "1:N"))
        left, _, right = card.partition(":")
        start_arrow = SIDE_ARROW.get(left.strip().upper(), "ERone")
        end_arrow = SIDE_ARROW.get(right.strip().upper(), "ERmany")
        style = (EDGE_BASE + f"startArrow={start_arrow};startFill=0;"
                 f"endArrow={end_arrow};endFill=0;")
        cell = ET.SubElement(root, "mxCell", id=f"rel{i}",
                             value=rel.get("label", ""), style=style,
                             edge="1", parent="1",
                             source=rel["from"], target=rel["to"])
        geo = ET.SubElement(cell, "mxGeometry", relative="1")
        geo.set("as", "geometry")

    ET.indent(mxfile)
    ET.ElementTree(mxfile).write(out_path, encoding="utf-8",
                                 xml_declaration=True)


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python make_drawio_erd.py <spec.json> "
                 "[<spec2.json> ...]")
    failed = False
    for spec_path in sys.argv[1:]:
        try:
            with open(spec_path, encoding="utf-8") as f:
                spec = json.load(f)
            stem = spec.get("name") or os.path.splitext(
                os.path.basename(spec_path))[0]
            if stem.endswith(".drawio"):
                stem = stem[:-len(".drawio")]
            out_path = os.path.join(
                os.path.dirname(os.path.abspath(spec_path)), stem + ".drawio")
            build(spec, out_path)
            print(f"OK   {os.path.basename(spec_path)} -> {stem}.drawio")
        except Exception as exc:
            failed = True
            print(f"FAIL {spec_path}: {exc}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()

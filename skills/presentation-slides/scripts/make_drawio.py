#!/usr/bin/env python3
"""Generate an editable draw.io (diagrams.net) file from a simple JSON spec.

Usage:
    python make_drawio.py <spec.json> [<spec2.json> ...]

Each spec produces "<spec-dir>/<name>.drawio" (name from the spec, falling
back to the spec's file stem, with any trailing ".drawio" stripped).

Spec format — layers are drawn top-to-bottom, nodes left-to-right:

{
  "name": "02-container",
  "title": "ShopLite — Container Diagram",
  "layers": [
    { "label": "Clients",
      "nodes": [ {"id": "spa", "label": "Web Browser\nReact SPA", "type": "external"} ] },
    { "label": "ShopLite System",
      "nodes": [ {"id": "api", "label": "ShopLite.Api\nASP.NET Core", "type": "primary"} ] },
    { "label": "Data",
      "nodes": [ {"id": "db", "label": "SQL Server", "type": "datastore"} ] }
  ],
  "edges": [ {"from": "spa", "to": "api", "label": "HTTPS / JSON"} ]
}

Node types: primary (blue), secondary (green), accent (yellow), external
(grey), datastore (orange cylinder). Omitted type defaults to "primary".
"""

import json
import os
import sys
import xml.etree.ElementTree as ET

NODE_W, NODE_H = 200, 70
DATASTORE_H = 80
H_GAP, V_GAP = 60, 80
LAYER_PAD, LAYER_LABEL_H = 24, 26
MARGIN, TITLE_H = 40, 50

BOX = "rounded=1;whiteSpace=wrap;html=1;arcSize=8;fontSize=12;"
STYLES = {
    "primary":   BOX + "fillColor=#dae8fc;strokeColor=#6c8ebf;",
    "secondary": BOX + "fillColor=#d5e8d4;strokeColor=#82b366;",
    "accent":    BOX + "fillColor=#fff2cc;strokeColor=#d6b656;",
    "external":  BOX + "fillColor=#f5f5f5;strokeColor=#666666;fontColor=#333333;",
    "datastore": ("shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;"
                  "backgroundOutline=1;size=15;fontSize=12;"
                  "fillColor=#ffe6cc;strokeColor=#d79b00;"),
}
LAYER_STYLE = ("rounded=1;fillColor=none;strokeColor=#999999;dashed=1;"
               "verticalAlign=top;align=left;spacingLeft=8;spacingTop=4;"
               "fontSize=11;fontColor=#666666;fontStyle=2;html=1;")
EDGE_STYLE = ("edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;fontSize=11;"
              "labelBackgroundColor=#ffffff;strokeColor=#5b7699;"
              "exitX=0.5;exitY=1;exitDx=0;exitDy=0;")
TITLE_STYLE = ("text;html=1;fontSize=18;fontStyle=1;fontColor=#1F3864;"
               "align=center;verticalAlign=middle;")


def build(spec, out_path):
    layers = spec.get("layers") or []
    edges = spec.get("edges") or []
    if not layers:
        raise ValueError("spec has no layers")

    ids = {}
    for layer in layers:
        for node in layer.get("nodes") or []:
            node_id = node.get("id")
            if not node_id:
                raise ValueError(f"node without id: {node}")
            if node_id in ids:
                raise ValueError(f"duplicate node id: {node_id}")
            ids[node_id] = node
    for edge in edges:
        for end in ("from", "to"):
            if edge.get(end) not in ids:
                raise ValueError(
                    f"edge {edge} references unknown node id '{edge.get(end)}'")

    # layout: widest layer decides the canvas width; every layer is centered
    def layer_width(layer):
        n = len(layer.get("nodes") or [])
        return n * NODE_W + max(n - 1, 0) * H_GAP + 2 * LAYER_PAD

    canvas_w = max(layer_width(l) for l in layers)
    total_w = canvas_w + 2 * MARGIN

    mxfile = ET.Element("mxfile", host="app.diagrams.net")
    diagram = ET.SubElement(mxfile, "diagram", id="page-1",
                            name=spec.get("title", "Architecture"))
    model = ET.SubElement(
        diagram, "mxGraphModel", dx="1000", dy="800", grid="1", gridSize="10",
        guides="1", tooltips="1", connect="1", arrows="1", fold="1", page="1",
        pageScale="1", pageWidth=str(total_w), pageHeight="1100",
        math="0", shadow="0")
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")

    def add_vertex(cid, value, style, x, y, w, h):
        c = ET.SubElement(root, "mxCell", id=cid, value=value, style=style,
                          vertex="1", parent="1")
        geo = ET.SubElement(c, "mxGeometry")
        geo.set("x", str(int(x)))
        geo.set("y", str(int(y)))
        geo.set("width", str(int(w)))
        geo.set("height", str(int(h)))
        geo.set("as", "geometry")
        return c

    if spec.get("title"):
        add_vertex("title", spec["title"], TITLE_STYLE,
                   MARGIN, MARGIN, canvas_w, 30)

    y = MARGIN + (TITLE_H if spec.get("title") else 0)
    for li, layer in enumerate(layers):
        nodes = layer.get("nodes") or []
        node_h = max((DATASTORE_H if n.get("type") == "datastore" else NODE_H)
                     for n in nodes) if nodes else NODE_H
        band_h = node_h + 2 * LAYER_PAD + LAYER_LABEL_H
        if layer.get("label"):
            add_vertex(f"layer{li}", layer["label"], LAYER_STYLE,
                       MARGIN, y, canvas_w, band_h)
        row_w = len(nodes) * NODE_W + max(len(nodes) - 1, 0) * H_GAP
        x = MARGIN + (canvas_w - row_w) / 2
        for node in nodes:
            style = STYLES.get(node.get("type", "primary"), STYLES["primary"])
            h = DATASTORE_H if node.get("type") == "datastore" else NODE_H
            add_vertex(node["id"], node.get("label", node["id"]), style,
                       int(x), y + LAYER_LABEL_H + LAYER_PAD + (node_h - h) / 2,
                       NODE_W, h)
            x += NODE_W + H_GAP
        y += band_h + V_GAP

    for ei, edge in enumerate(edges):
        c = ET.SubElement(root, "mxCell", id=f"edge{ei}",
                          value=edge.get("label", ""), style=EDGE_STYLE,
                          edge="1", parent="1",
                          source=edge["from"], target=edge["to"])
        geo = ET.SubElement(c, "mxGeometry", relative="1")
        geo.set("as", "geometry")

    ET.indent(mxfile)
    ET.ElementTree(mxfile).write(out_path, encoding="utf-8",
                                 xml_declaration=True)


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python make_drawio.py <spec.json> [<spec2.json> ...]")
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

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import textwrap
import zipfile
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import yaml
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from PIL import Image, ImageOps, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

RUNS = {
    "01_kpneumoniae_full_st_core": "Full K. pneumoniae ST-only Core analysis",
    "02_kpneumoniae_full_facility_st": "Full K. pneumoniae Facility + ST and Facility analysis",
    "03_kpneumoniae_hospital_c_st": "Hospital C ST-context analysis",
    "04_kpneumoniae_hospital_c_facility_st": "Hospital C Facility + ST and Facility analysis",
    "05_spneumoniae_ghana_st_core": "Ghana S. pneumoniae ST-only Core analysis",
    "06_spneumoniae_ghana_community": "Ghana S. pneumoniae Community analysis",
}

CAPTIONS = {
    "S1": "Complete Klebsiella pneumoniae annotated Core SNP heatmap from the full 172-isolate ST-only Core analysis.",
    "S2": "Complete Klebsiella pneumoniae annotated Core SNP heatmap from the full 172-isolate Facility + ST Core analysis.",
    "S3": "Facility-level Klebsiella pneumoniae transmission scatterplots for Hospitals A, B, D, E and F. The corresponding Hospital C analysis is presented in main-text Figure 3.",
    "S4": "Complete Streptococcus pneumoniae annotated Core SNP heatmap from the ST-only Core analysis.",
    "S5": "Complete Streptococcus pneumoniae annotated Core SNP heatmap with Community strain-sharing cluster annotations.",
}

ALIASES = {
    "sample": ["sampleid", "sample_id", "sampleID", "SampleID", "IDs", "ID", "isolate", "name"],
    "context": ["_core_context", "core_context", "context"],
    "core_cluster": ["core_snp_cluster", "core_cluster", "core_cluster_label"],
    "trans_cluster": ["Clusters", "transmission_cluster", "cluster"],
    "st": ["ST", "st_type", "sequence_type", "mlst"],
    "facility": ["hospital", "FacilityName", "FacilityCode", "facility", "main_var", "network_group"],
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build final SNP2Cluster-Py supplementary upload files")
    p.add_argument("--source", required=True, type=Path, help="Extracted supplementary_source_bundle directory")
    p.add_argument("--outdir", required=True, type=Path)
    return p.parse_args()


def natural_key(value: Any):
    return [int(x) if x.isdigit() else x.casefold() for x in re.split(r"(\d+)", str(value))]


def first_col(df: pd.DataFrame, names: Iterable[str], required: bool = True) -> str | None:
    exact = {str(c): c for c in df.columns}
    folded = {str(c).casefold(): c for c in df.columns}
    normalized = {re.sub(r"[^a-z0-9]", "", str(c).casefold()): c for c in df.columns}
    for n in names:
        if n in exact:
            return exact[n]
        if n.casefold() in folded:
            return folded[n.casefold()]
        norm = re.sub(r"[^a-z0-9]", "", n.casefold())
        if norm in normalized:
            return normalized[norm]
    if required:
        raise KeyError(f"Could not resolve any of {list(names)} from {list(df.columns)}")
    return None


def nonempty(s: pd.Series) -> pd.Series:
    t = s.astype("string").str.strip()
    return s.notna() & t.ne("") & ~t.str.casefold().isin(["nan", "none", "na", "<na>"])


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=True)


def find_one(root: Path, pattern: str) -> Path:
    matches = sorted(root.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No file matched {pattern} under {root}")
    return matches[0]


def run_path(source: Path, label: str) -> Path:
    p = source / "runs" / label
    if not p.is_dir():
        raise FileNotFoundError(p)
    return p


def load_manifest(run: Path) -> dict[str, Any]:
    candidates = list(run.glob("audit/**/run_manifest.json")) + list(run.glob("**/run_manifest.json"))
    if not candidates:
        return {}
    try:
        return json.loads(candidates[0].read_text(encoding="utf-8"))
    except Exception:
        return {}


def flatten(d: Any, prefix: str = "") -> dict[str, Any]:
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            out.update(flatten(v, key))
    elif isinstance(d, list):
        out[prefix] = ", ".join(map(str, d))
    else:
        out[prefix] = d
    return out


def find_config(run: Path) -> Path | None:
    for pattern in ["audit/**/*.yaml", "audit/**/*.yml", "**/*config*.yaml", "**/*config*.yml"]:
        matches = sorted(run.glob(pattern))
        if matches:
            return matches[0]
    return None


def load_yaml(path: Path | None) -> dict:
    if path is None:
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def resolve_core(run: Path) -> pd.DataFrame:
    return read_csv(find_one(run, "tables/core_snp_clusters.csv"))


def resolve_trans(run: Path) -> pd.DataFrame | None:
    p = run / "tables" / "transmission_clusters.csv"
    return read_csv(p) if p.exists() else None


def core_summary(run: Path) -> dict[str, Any]:
    df = resolve_core(run)
    sid = first_col(df, ALIASES["sample"])
    ctx = first_col(df, ALIASES["context"])
    cl = first_col(df, ALIASES["core_cluster"])
    clustered = df.loc[nonempty(df[cl])].copy()
    sizes = clustered.groupby(cl)[sid].nunique() if not clustered.empty else pd.Series(dtype=int)
    return {
        "analysed_isolates": df[sid].nunique(),
        "eligible_contexts": df[ctx].nunique(dropna=True),
        "retained_contexts": clustered[ctx].nunique(dropna=True),
        "core_clusters": clustered[cl].nunique(dropna=True),
        "core_clustered_isolates": clustered[sid].nunique(),
        "core_unclustered_isolates": df[sid].nunique() - clustered[sid].nunique(),
        "core_size_min": int(sizes.min()) if len(sizes) else None,
        "core_size_max": int(sizes.max()) if len(sizes) else None,
    }


def transmission_summary(run: Path) -> pd.DataFrame:
    df = resolve_trans(run)
    if df is None or df.empty:
        return pd.DataFrame()
    sid = first_col(df, ALIASES["sample"])
    cl = first_col(df, ALIASES["trans_cluster"])
    fac = first_col(df, ALIASES["facility"], required=False)
    valid = df.loc[nonempty(df[cl])].copy()
    if valid.empty:
        return pd.DataFrame()
    if fac:
        valid["canonical_downstream_cluster"] = valid[fac].astype(str) + "__" + valid[cl].astype(str)
    else:
        valid["canonical_downstream_cluster"] = valid[cl].astype(str)
    group_cols = [fac, "canonical_downstream_cluster"] if fac else ["canonical_downstream_cluster"]
    rows = []
    for keys, g in valid.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        rows.append({
            "facility_or_group": keys[0] if fac else "All",
            "downstream_cluster": keys[-1],
            "clustered_isolates": g[sid].nunique(),
            "st_values": ", ".join(sorted(g[first_col(g, ALIASES['st'], required=False)].dropna().unique(), key=natural_key)) if first_col(g, ALIASES['st'], required=False) else "",
        })
    return pd.DataFrame(rows)


def fit_columns(ws, max_width: int = 45):
    for col in range(1, ws.max_column + 1):
        letter = get_column_letter(col)
        width = 0
        for cell in ws[letter]:
            if cell.value is not None:
                width = max(width, min(max_width, len(str(cell.value)) + 2))
        ws.column_dimensions[letter].width = max(10, width)


def style_sheet(ws):
    navy = "17365D"
    blue = "D9EAF7"
    thin = Side(style="thin", color="B7C9D6")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=navy)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(bottom=thin)
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = Border(bottom=thin)
        if row[0].row % 2 == 0:
            for cell in row:
                cell.fill = PatternFill("solid", fgColor=blue)
    fit_columns(ws)


def add_df(wb: Workbook, title: str, df: pd.DataFrame):
    ws = wb.create_sheet(title)
    for c, value in enumerate(df.columns, 1):
        ws.cell(1, c, value)
    for r, row in enumerate(df.itertuples(index=False, name=None), 2):
        for c, value in enumerate(row, 1):
            ws.cell(r, c, value)
    style_sheet(ws)
    return ws


def build_workbook(source: Path, out: Path):
    run_lookup = {k: run_path(source, k) for k in RUNS}

    # S1 provenance/configuration
    s1_rows = []
    for key, description in RUNS.items():
        rp = run_lookup[key]
        manifest = load_manifest(rp)
        mf = flatten(manifest)
        cfg_path = find_config(rp)
        cfg = load_yaml(cfg_path)
        variables = cfg.get("variables", {}) if isinstance(cfg.get("variables", {}), dict) else {}
        analysis = cfg.get("analysis", {}) if isinstance(cfg.get("analysis", {}), dict) else {}
        core = core_summary(rp)
        s1_rows.append({
            "analysis_id": key,
            "analysis_description": description,
            "software_version": manifest.get("version") or mf.get("software.version") or "1.1.2",
            "git_commit": mf.get("git_commit") or mf.get("git.commit") or "a4535d47beecfde1d6dc66097e0b78580032afc6",
            "configuration_file": cfg_path.name if cfg_path else "embedded in run manifest/audit",
            "cluster_type": analysis.get("cluster_type", ""),
            "transmission_level": analysis.get("transmission_level", ""),
            "core_cluster_context": str(analysis.get("core_cluster_context", "")),
            "main_var": variables.get("main_var", ""),
            "secondary_var": variables.get("var_01", ""),
            "date_var": variables.get("var_02", ""),
            "snp_cutoff": analysis.get("snp_cutoff", ""),
            "days_cutoff": analysis.get("days_cutoff", ""),
            "date_format": analysis.get("date_format", ""),
            "analysed_isolates": core["analysed_isolates"],
            "run_folder": rp.name,
        })
    s1 = pd.DataFrame(s1_rows)

    # S2 context-level authoritative core results
    s2_parts = []
    for key, desc in RUNS.items():
        rp = run_lookup[key]
        df = resolve_core(rp)
        sid = first_col(df, ALIASES["sample"])
        ctx = first_col(df, ALIASES["context"])
        cl = first_col(df, ALIASES["core_cluster"])
        st = first_col(df, ALIASES["st"], required=False)
        for context, g in df.groupby(ctx, dropna=False):
            retained = g.loc[nonempty(g[cl])]
            sizes = retained.groupby(cl)[sid].nunique() if not retained.empty else pd.Series(dtype=int)
            s2_parts.append({
                "analysis_id": key,
                "analysis_description": desc,
                "core_context": context,
                "st_values": ", ".join(sorted(g[st].dropna().unique(), key=natural_key)) if st else "",
                "eligible_isolates": g[sid].nunique(),
                "retained_core_clusters": retained[cl].nunique(),
                "core_clustered_isolates": retained[sid].nunique(),
                "core_unclustered_isolates": g[sid].nunique() - retained[sid].nunique(),
                "cluster_size_min": int(sizes.min()) if len(sizes) else None,
                "cluster_size_max": int(sizes.max()) if len(sizes) else None,
            })
    s2 = pd.DataFrame(s2_parts)

    # S3 facility-level summaries (full and Hospital C)
    s3_parts = []
    for key in ["02_kpneumoniae_full_facility_st", "04_kpneumoniae_hospital_c_facility_st"]:
        t = transmission_summary(run_lookup[key])
        if not t.empty:
            t.insert(0, "analysis_id", key)
            t.insert(1, "analysis_description", RUNS[key])
            s3_parts.append(t)
    s3 = pd.concat(s3_parts, ignore_index=True) if s3_parts else pd.DataFrame()

    # S4 community summaries by ST and cluster
    rp = run_lookup["06_spneumoniae_ghana_community"]
    tdf = resolve_trans(rp)
    s4_rows = []
    if tdf is not None:
        sid = first_col(tdf, ALIASES["sample"])
        cl = first_col(tdf, ALIASES["trans_cluster"])
        st = first_col(tdf, ALIASES["st"])
        loc = first_col(tdf, ["FacilityCode", "facility_code", "Community", "community", "main_var"], required=False)
        valid = tdf.loc[nonempty(tdf[cl])].copy()
        for (st_value, cluster), g in valid.groupby([st, cl], dropna=False):
            locations = sorted(g[loc].dropna().unique()) if loc else []
            s4_rows.append({
                "ST": st_value,
                "community_cluster": cluster,
                "clustered_isolates": g[sid].nunique(),
                "locations_count": len(locations),
                "locations": ", ".join(locations),
            })
    s4 = pd.DataFrame(s4_rows).sort_values(["clustered_isolates", "ST"], ascending=[False, True]) if s4_rows else pd.DataFrame()

    # S5 isolate comparison full Kp ST-only vs Facility+ST
    a = resolve_core(run_lookup["01_kpneumoniae_full_st_core"])
    b = resolve_core(run_lookup["02_kpneumoniae_full_facility_st"])
    aid, bid = first_col(a, ALIASES["sample"]), first_col(b, ALIASES["sample"])
    acl, bcl = first_col(a, ALIASES["core_cluster"]), first_col(b, ALIASES["core_cluster"])
    actx, bctx = first_col(a, ALIASES["context"]), first_col(b, ALIASES["context"])
    ast, bst = first_col(a, ALIASES["st"], required=False), first_col(b, ALIASES["st"], required=False)
    af = first_col(a, ["hospital", "FacilityName", "facility"], required=False)
    bf = first_col(b, ["hospital", "FacilityName", "facility"], required=False)
    acols = [aid, acl, actx] + ([ast] if ast else []) + ([af] if af and af not in [aid, acl, actx, ast] else [])
    bcols = [bid, bcl, bctx] + ([bst] if bst else []) + ([bf] if bf and bf not in [bid, bcl, bctx, bst] else [])
    aa, bb = a[acols].drop_duplicates(aid).copy(), b[bcols].drop_duplicates(bid).copy()
    aa.columns = ["sample_id", "st_only_core_cluster", "st_only_context"] + (["ST"] if ast else []) + (["facility"] if len(acols) > 3 + bool(ast) else [])
    bb_rename = {bid: "sample_id", bcl: "facility_st_core_cluster", bctx: "facility_st_context"}
    if bst: bb_rename[bst] = "ST_b"
    if bf: bb_rename[bf] = "facility_b"
    bb = bb.rename(columns=bb_rename)
    s5 = aa.merge(bb, on="sample_id", how="outer")
    if "ST_b" in s5: s5["ST"] = s5.get("ST").fillna(s5["ST_b"]); s5 = s5.drop(columns=["ST_b"])
    if "facility_b" in s5: s5["facility"] = s5.get("facility").fillna(s5["facility_b"]); s5 = s5.drop(columns=["facility_b"])
    s5["st_only_clustered"] = nonempty(s5["st_only_core_cluster"])
    s5["facility_st_clustered"] = nonempty(s5["facility_st_core_cluster"])
    s5["transition"] = s5.apply(lambda r: "clustered in both" if r.st_only_clustered and r.facility_st_clustered else ("ST-only clustered; Facility+ST unclustered" if r.st_only_clustered else ("ST-only unclustered; Facility+ST clustered" if r.facility_st_clustered else "unclustered in both")), axis=1)
    order = [c for c in ["sample_id", "facility", "ST", "st_only_context", "st_only_core_cluster", "facility_st_context", "facility_st_core_cluster", "st_only_clustered", "facility_st_clustered", "transition"] if c in s5]
    s5 = s5[order].sort_values("sample_id")

    wb = Workbook()
    wb.remove(wb.active)
    add_df(wb, "Table S1", s1)
    add_df(wb, "Table S2", s2)
    add_df(wb, "Table S3", s3)
    add_df(wb, "Table S4", s4)
    add_df(wb, "Table S5", s5)
    wb.properties.title = "SNP2Cluster-Py Supplementary Tables"
    wb.properties.subject = "Tables S1-S5 for the SNP2Cluster-Py bioRxiv manuscript"
    wb.properties.creator = "Stanford Kwenda"
    wb.save(out)


def draw_wrapped(c: canvas.Canvas, text: str, x: float, y: float, width_chars: int = 145, leading: int = 12):
    for line in textwrap.wrap(text, width=width_chars):
        c.drawString(x, y, line)
        y -= leading
    return y


def image_page(c: canvas.Canvas, img_path: Path, title: str, caption: str, page_size):
    w, h = page_size
    c.setPageSize(page_size)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(36, h - 36, title)
    c.setFont("Helvetica", 9)
    y = draw_wrapped(c, caption, 36, h - 52, 160, 11)
    top = y - 10
    bottom = 30
    left = 30
    right = 30
    available_w = w - left - right
    available_h = top - bottom
    with Image.open(img_path) as im:
        iw, ih = im.size
    scale = min(available_w / iw, available_h / ih)
    dw, dh = iw * scale, ih * scale
    c.drawImage(ImageReader(str(img_path)), left + (available_w - dw)/2, bottom + (available_h - dh)/2, dw, dh, preserveAspectRatio=True, mask="auto")
    c.showPage()


def compose_s3(run: Path, out_png: Path):
    hospitals = ["Hospital_A", "Hospital_B", "Hospital_D", "Hospital_E", "Hospital_F"]
    paths = []
    for h in hospitals:
        hits = sorted((run / "figures").glob(f"02_transmission_scatter_{h}.png"))
        if not hits:
            raise FileNotFoundError(f"Missing scatterplot for {h}")
        paths.append(hits[0])
    imgs = [ImageOps.contain(Image.open(p).convert("RGB"), (1800, 1200)) for p in paths]
    cell_w, cell_h = 1900, 1300
    canvas_img = Image.new("RGB", (cell_w*2, cell_h*3), "white")
    draw = ImageDraw.Draw(canvas_img)
    labels = ["A", "B", "C", "D", "E"]
    positions = [(0,0),(1,0),(0,1),(1,1),(0,2)]
    for img, label, (col,row) in zip(imgs, labels, positions):
        x = col*cell_w + (cell_w-img.width)//2
        y = row*cell_h + (cell_h-img.height)//2
        canvas_img.paste(img, (x,y))
        draw.text((col*cell_w+20, row*cell_h+15), label, fill="black")
    canvas_img.save(out_png, dpi=(300,300), optimize=True)


def build_pdf(source: Path, out: Path, work: Path):
    r1 = run_path(source, "01_kpneumoniae_full_st_core")
    r2 = run_path(source, "02_kpneumoniae_full_facility_st")
    r5 = run_path(source, "05_spneumoniae_ghana_st_core")
    r6 = run_path(source, "06_spneumoniae_ghana_community")
    s1 = find_one(r1, "figures/03_core_heatmap.png")
    s2 = find_one(r2, "figures/03_core_heatmap.png")
    s4 = find_one(r5, "figures/03_core_heatmap.png")
    s5 = find_one(r6, "figures/03_core_heatmap.png")
    s3 = work / "Figure_S3_composite.png"
    compose_s3(r2, s3)

    page = landscape(A3)
    c = canvas.Canvas(str(out), pagesize=page)
    c.setTitle("SNP2Cluster-Py Supplementary Figures")
    image_page(c, s1, "Figure S1", CAPTIONS["S1"], page)
    image_page(c, s2, "Figure S2", CAPTIONS["S2"], page)
    image_page(c, s3, "Figure S3", CAPTIONS["S3"], page)
    image_page(c, s4, "Figure S4", CAPTIONS["S4"], page)
    image_page(c, s5, "Figure S5", CAPTIONS["S5"], page)
    c.save()


def build_interactive_zip(source: Path, out: Path, work: Path):
    root = work / "interactive_bundle"
    if root.exists(): shutil.rmtree(root)
    root.mkdir(parents=True)
    manifest_rows = []
    table_names = [
        "core_snp_clusters.csv", "isolate_cluster_assignments.csv", "minimum_spanning_tree_edges.csv",
        "transmission_clusters.csv", "transmission_context.csv", "transmission_network_nodes.csv", "transmission_network_edges.csv",
    ]
    for key, description in RUNS.items():
        rp = run_path(source, key)
        dst = root / key
        (dst / "html").mkdir(parents=True)
        (dst / "tables").mkdir(parents=True)
        for html in sorted((rp / "figures").glob("*.html")):
            shutil.copy2(html, dst / "html" / html.name)
            manifest_rows.append({"analysis_id": key, "analysis_description": description, "file_type": "interactive_html", "relative_path": str(Path(key)/"html"/html.name)})
        for name in table_names:
            src = rp / "tables" / name
            if src.exists():
                shutil.copy2(src, dst / "tables" / name)
                manifest_rows.append({"analysis_id": key, "analysis_description": description, "file_type": "machine_readable_table", "relative_path": str(Path(key)/"tables"/name)})
    pd.DataFrame(manifest_rows).to_csv(root / "MANIFEST.csv", index=False)
    (root / "README.txt").write_text(
        "SNP2Cluster-Py interactive visualizations\n\n"
        "This archive contains final v1.1.2 Core minimum spanning trees and downstream Facility/Community networks in HTML format, together with machine-readable node, edge and cluster tables. Open HTML files in a modern browser. Network edges are within-cluster minimum-spanning-tree relationships for visualization and do not imply direct or directional transmission.\n",
        encoding="utf-8",
    )
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted(root.rglob("*")):
            if p.is_file(): zf.write(p, p.relative_to(root.parent))


def main():
    args = parse_args()
    source = args.source.resolve()
    outdir = args.outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    work = outdir / "_supplementary_build_tmp"
    if work.exists(): shutil.rmtree(work)
    work.mkdir()

    pdf = outdir / "SNP2Cluster-Py_Supplementary_Figures.pdf"
    xlsx = outdir / "SNP2Cluster-Py_Supplementary_Tables.xlsx"
    zip_path = outdir / "SNP2Cluster-Py_Interactive_Visualizations.zip"

    build_pdf(source, pdf, work)
    build_workbook(source, xlsx)
    build_interactive_zip(source, zip_path, work)

    shutil.rmtree(work)
    print(pdf)
    print(xlsx)
    print(zip_path)

if __name__ == "__main__":
    main()

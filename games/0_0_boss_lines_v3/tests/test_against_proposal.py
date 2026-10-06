"""Fixed data in game_config.py must equal the proposal .docx exactly."""
import html
import os
import re
import zipfile

import pytest

DOCX = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Proposal_2026-10-06.docx")


def _tables():
    x = zipfile.ZipFile(DOCX).read("word/document.xml").decode("utf8")
    out = []
    for t in re.findall(r"<w:tbl>.*?</w:tbl>", x, re.S):
        rows = []
        for tr in re.findall(r"<w:tr[ >].*?</w:tr>", t, re.S):
            row = []
            for tc in re.findall(r"<w:tc>.*?</w:tc>", tr, re.S):
                text = html.unescape(re.sub(r"<[^>]+>", "", tc)).strip()
                fill = re.search(r'w:fill="([0-9A-Fa-f]{6})"', tc)
                vmerge = "<w:vMerge/>" in tc or '<w:vMerge w:val="continue"' in tc
                row.append({"text": text, "green": bool(fill and fill.group(1).upper() == "00FF00"),
                            "vcont": vmerge})
            rows.append(row)
        out.append(rows)
    return out


TABLES = _tables()


def test_cell_priority_matches_diagram(cfg):
    grid = [[int(c["text"]) for c in row] for row in TABLES[0][1:]]
    assert sorted(v for row in grid for v in row) == list(range(1, 31))
    for r in range(5):
        for c in range(6):
            assert cfg.cell_priority[(c, r)] == grid[r][c]


def test_35_paylines_match_green_cells(cfg):
    line_tables = TABLES[2:37]
    assert len(line_tables) == 35
    for idx, t in enumerate(line_tables, start=1):
        rows = [[i for i, row in enumerate(t) if row[c]["green"]] for c in range(6)]
        assert all(len(r) == 1 for r in rows), f"line {idx} must have one green cell per column"
        assert [r[0] for r in rows] == cfg.paylines[idx], f"line {idx}"
    assert len({tuple(v) for v in cfg.paylines.values()}) == 35


def test_paytable_and_damage_match(cfg):
    t = TABLES[1]
    damage = None
    for row in t[1:]:
        name = {"Wild": "W"}.get(row[0]["text"], row[0]["text"])
        if row[5]["text"]:
            damage = float(row[5]["text"])
        assert cfg.symbol_damage[name] == damage, name  # merged cells carry down
        for kind, cell in zip((3, 4, 5, 6), row[1:5]):
            if cell["text"] in ("-", ""):
                assert (kind, name) not in cfg.paytable
            else:
                assert cfg.paytable[(kind, name)] == pytest.approx(float(cell["text"]))


MD = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Proposal_KichBan1_2026-10-06.md")


def _md_table(header_start):
    lines = open(MD, encoding="utf-8").read().splitlines()
    i = next(k for k, ln in enumerate(lines) if ln.startswith(header_start))
    rows = []
    for ln in lines[i + 2:]:
        if not ln.startswith("|"):
            break
        rows.append([c.strip() for c in ln.strip("|").split("|")])
    return rows


def test_stage_table_matches_kichban1(cfg):
    """Stage table now comes from the Kich ban 1 text (HP changed at stages 3-5)."""
    tiers = {"Đồng": "dong", "Bạc": "bac", "Vàng": "vang", "Kim cương": "kimcuong"}
    rows = _md_table("| Chặng |")
    assert len(rows) == 7
    for row in rows:
        stage = 6 if row[0] == "Endless" else int(row[0])
        lo_hi = [int(v) for v in re.findall(r"\d+", row[1])]
        assert cfg.stage_hp_range[stage] == (lo_hi[0], lo_hi[-1]), stage
        assert cfg.stage_min_chest[stage] == tiers[row[3]]
        assert cfg.stage_min_coin[stage] == float(row[4].rstrip("x"))


def test_paytable_matches_kichban1(cfg):
    rows = _md_table("| Biểu tượng |")
    for row in rows:
        name = {"Wild": "W"}.get(row[0], row[0])
        for kind, cell in zip((3, 4, 5, 6), row[1:5]):
            if cell == "-":
                assert (kind, name) not in cfg.paytable
            else:
                assert cfg.paytable[(kind, name)] == pytest.approx(float(cell))


def _num(v):
    # "1.000" / "25.000" use '.' as a thousands separator in the proposal
    if v.count(".") == 1 and len(v.split(".")[1]) == 3:
        return float(v.replace(".", ""))
    return float(v)


def test_coin_tiers_match_kichban1(cfg):
    text = open(MD, encoding="utf-8").read()
    for label, key in (("Xu Đồng", "dong"), ("Xu Bạc", "bac"), ("Xu Vàng", "vang"),
                       ("Xu Kim cương", "kimcuong"), ("Xu Maxwin", "maxwin")):
        body = re.search(label + r" \(([^)]*)\)", text).group(1)
        vals = [_num(v) for v in re.findall(r"([\d.]+)x", body)]
        assert cfg.coin_tiers[key] == vals, key

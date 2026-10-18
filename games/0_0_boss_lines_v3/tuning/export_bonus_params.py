"""usage: python tuning/export_bonus_params.py OVERRIDES.json OUT.xlsx [OUT.html]
Normal Bonus / Super / Epic parameters side by side (Excel, and an HTML page for sharing)."""
import html, json, sys
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

j = json.load(open(sys.argv[1])); tw = j["tier_weights"]; R = j["_reel_specs"]
DEF = {"wild_event_chance": 0.15, "wild_event_weights": {"multiplier": 50, "coin": 35, "power": 15},
       "power_pick_weights": {"enhance": 30, "upgrade": 20, "transform": 25, "replace": 15, "destroy": 10},
       "chest_gift_power_chance": {"dong": 0.15, "bac": 0.25, "vang": 0.35, "kimcuong": 0.45}, "wild_coin_min_value": 0.0}
T = ("bonus", "super", "epic"); NAMES = {"bonus": "Normal Bonus", "super": "Super", "epic": "Epic"}
SUMMARY = json.load(open(sys.argv[1].replace(".json", "_summary.json"))) if False else None


def get(t, k):
    if k in tw[t]:
        return tw[t][k], ""
    if k in j:
        return j[k], "mặc định"
    return DEF.get(k), "mặc định"


def fmt(v):
    if isinstance(v, dict):
        return ", ".join(f"{a}:{b:g}" if isinstance(b, (int, float)) else f"{a}:{fmt(b)}" for a, b in v.items())
    if isinstance(v, list):
        return " / ".join(f"{x:g}" for x in v)
    return v


def rows_for(keys):
    out = []
    for k, label in keys:
        r = [label]
        for t in T:
            v, d = get(t, k)
            r.append(f"{fmt(v)}" + (f" (mặc định)" if d else ""))
        out.append(r)
    return out


hdr = ["Thông số"] + [NAMES[t] for t in T]
sheets = [
    ("Tổng quan", hdr, [
        ["Override", "b14", "s1 + sự kiện Wild 40/40/20", "e2 (file chung: " + sys.argv[1].split("/")[-1] + ")"],
        ["Kiểm tra", "200k phiên", "20k phiên (s1: 200k)", "50k phiên"],
        ["Mean (mục tiêu)", "91,43 (91)", "246,7 (245)", "1975 (2045)"],
        ["Đạt đường cong ±15%", "77/96", "74/96", "91/95"],
        ["Max Win (mục tiêu)", "0,008% (0,0108%)", "0,055% (0,0855%)", "1,006% (1%)"],
        ["Sau optimizer (buy mode)", "mean 91,05", "mean 245,05", "mean 2045,05"],
        ["Spin / chặng bắt đầu", "6 / 1", "7 / 2", "8 / 3"],
        ["Ô sáng", "Reset mỗi spin (spin 1 giữ ô Scatter)", "Giữ cả Bonus", "Toàn bàn sáng"],
        ["Xu tối thiểu theo chặng", "0,2/1/1/5/20/20", "Chặng 2 = 0,2x (thử nghiệm đã duyệt), còn lại như Normal",
         "≥5x trong free spin; Treasure mở đầu theo chặng 2"],
        ["Vũ khí đảm bảo / spin", "—", "1", "2"],
        ["Thắng tối thiểu", "—", "—", "600x"]]),
    ("Treasure", hdr, [["Ký hiệu: " + k] + [f"{tw[t]['treasure_kind_weights'][k]:g}" for t in T]
                       for k in tw["bonus"]["treasure_kind_weights"]] + rows_for([
        ("clover_factor_weights", "Hệ số Clover"), ("golden_factor_weights", "Hệ số Golden"),
        ("global_factor_weights", "Hệ số Global"), ("star_value_weights", "Giá trị Star")])),
    ("Bảng xu", ["Xu (x cược)"] + [NAMES[t] for t in T],
     [[float(c)] + [tw[t]["coin_value_weights"].get(c, 0) for t in T] for c in tw["bonus"]["coin_value_weights"]]),
    ("Sự kiện Wild", hdr, rows_for([
        ("wild_event_chance", "Tỉ lệ khi Wild kết nối"), ("wild_event_weights", "Nhân / Xu / Sức mạnh"),
        ("wild_mult_weights", "Hệ số nhân Wild"), ("wild_coin_min_value", "Xu Wild tối thiểu (0 = theo chặng)"),
        ("power_pick_weights", "Chọn sức mạnh"), ("enhance_factor_weights", "Hệ số tăng cường")])),
    ("Rương", hdr, rows_for([
        ("chest_tier_step_weights", "Bước tier (+0/+1/+2/+3)"), ("chest_upgrade_chance", "Tỉ lệ nâng cấp"),
        ("chest_gift_count_weights", "Số quà theo rương"), ("chest_gift_power_chance", "Tỉ lệ quà là sức mạnh")])),
]
reel = []
for st, keys in (("1", ("BON_S1", None, None)), ("2", ("BON_S2", "SUP_S2", None)), ("3", ("BON_S3", "SUP_S3", "EPI_S3")),
                 ("4", ("BON_S4", "SUP_S4", "EPI_S4")), ("5", ("BON_S5", "SUP_S5", "EPI_S5")),
                 ("Endless", ("BON_E", "SUP_E", "EPI_E"))):
    reel.append([f"Chặng {st}"] + [(f"Wild {R[k]['wild']:g} / vũ khí {R[k]['weapon']:g}"
                                    + (" / shape " + fmt(R[k]["shape"]) if "shape" in R[k] else "")) if k else "—"
                                   for k in keys])
sheets.append(("Reel", ["Chặng"] + [NAMES[t] for t in T], reel))

wb = openpyxl.Workbook()
H, F = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="305496")
for n, (name, header, rows) in enumerate(sheets):
    ws = wb.active if n == 0 else wb.create_sheet()
    ws.title = name
    ws.append(header)
    for c in ws[1]:
        c.font, c.fill = H, F
    for r in rows:
        ws.append(r)
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = min(60, max(12, max(len(str(c.value or "")) for c in col) + 2))
    for row in ws.iter_rows():
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
wb.save(sys.argv[2])
print("saved", sys.argv[2])

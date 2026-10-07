# Boss Lines v3 — trạng thái (cập nhật theo "Kịch bản 1", 2026-10-06)

Nguồn luật: `Proposal_KichBan1_2026-10-06.md`. Paylines và sơ đồ thứ tự ô vẫn lấy từ `Proposal_2026-10-06.docx`
(bản dán không có hình 35 dòng, xem câu N9). Mọi câu hỏi đã được trả lời ngày 2026-10-07 trừ Q3 (payout lẻ, chờ xác nhận với Stake); xem `QUESTIONS.md`.

## Module

| Module | Trạng thái | Ghi chú |
|---|---|---|
| Bảng 6x5, thứ tự ô, 35 dòng | ✅ | Test đọc từ docx cũ; N9: xác nhận không đổi |
| Bảng trả thưởng, damage | ✅ | Test đọc từ bản Kịch bản 1; giá trị lẻ 0.05 chờ Q3 |
| Bảng chặng (HP 3 = 45–65, 4 = 65–90, 5 = 85–120, rương, xu) | ✅ | Test đọc từ bản Kịch bản 1 |
| Xu: Đồng/Bạc/Vàng/Kim cương/**Maxwin 25.000x**, nhãn theo giá trị hiện tại | ✅ | |
| Trả thưởng dòng ×ΣEnhance ×Wild ×Global, xu Wild ×Global | ✅ | Q2 |
| Luật phá; chỉ ô biểu tượng cơ bản bị phá do kết nối mới sáng nền | ✅ | Q0 (lấp tại chỗ) |
| Vũ khí: Bom 3x3 / Dao 1 hàng phá mọi biểu tượng (giữ Scatter ngoài Bonus), Sấm chớp, Cung tên (Endless ÷3) | ✅ | N1 |
| Hết boss trong chặng → không ra vũ khí mới; cột có boss chết → không ra Cung tên; cột 4–6 nhiều Cung tên hơn | ✅ | |
| Power: Replace, Enhance, Upgrade, Transform, Destroy (giữ Wild; giữ Scatter ngoài Bonus) | ✅ | |
| Last hit, boss rơi Wild/Power | ✅ | Q11, Q12 |
| Rương: quà, nâng cấp; cấp càng cao càng ít xu (Bonus) | ✅ | Q16–Q18 |
| Treasure: Xu, Nam châm (cần ≥ 2 xu), Clover (đồng thời), Golden clover (lần lượt), Star, Global, Scatter; kiểm tra Maxwin từng bước | ✅ | N2–N4, N10, Q20, Q21 |
| Bonus/Super/Epic; ô sáng giữ suốt Bonus; bắt đầu Bonus sáng sẵn ô Scatter kích hoạt | ✅ | |
| Epic: Treasure ngay đầu (toàn bảng, xu ≥ 1x), không xu Đồng trong free spin | ✅ | N5, N6 |
| **Hold and Spin: đã bỏ khỏi mọi mode** (2026-10-07) | ✅ | Super/Epic bảo đảm 1 ô Wild/vũ khí (spec cũ: 3) |
| Heroic / Treasure hunt, buy3, buy4, Ante | ✅ | N8, Q27 |
| Hiệu ứng Nice/Big/Super/Mega/Maxwin (`spinEnd.winLevels`), Total win cuối Bonus | ✅ | |
| Pipeline SDK `create_books` | ✅ | |
| **Tune số liệu** | ⛔ | Mọi weight là số tạm |
| Optimizer / kiểm tra RGS | ⛔ | Cần tune trước; Q3 |

## Số đo (weight tạm, 300 vòng mỗi mode, `_scratch/cap_rates.py`, `_scratch/results/`)

| Mode | Mean | Vòng chạm 25.000x | Số lần Treasure |
|---|---|---|---|
| base | 1.245x | 13/300 | 18 |
| ante | 1.632x | 18/300 | 20 |
| feature | 17.682x | 203/300 | 219 |
| buy3 | 22.766x | 265/300 | 317 |
| buy4 | 24.941x | 299/300 | 342 |

- Ngưỡng an toàn: **0 lần chạm** trong 1.500 vòng.
- Bonus tự kết thúc: mỗi spin Bonus cộng trung bình 0.34 spin (phải < 1).
- `reject_wincap_outside_wincap_fence` đang tắt (bật sau lần tune đầu).

## Lệnh
- Test: `python -m pytest tests -q` (61 test).
- Sinh reel: `python gen_reels.py`.
- Sinh sách: `python run.py` (optimizer đang tắt).

# Boss Lines v3 — trạng thái (2026-10-06)

Game viết mới theo `Proposal_2026-10-06.docx`. Câu hỏi còn mở nằm trong `QUESTIONS.md`.
Mỗi câu ứng với một cờ `Q<n>` trong `game_config.py`, nên trả lời xong thường chỉ cần đổi cờ.

## Module

| Module | Trạng thái | Ghi chú |
|---|---|---|
| Bảng 6x5, thứ tự ô, 35 dòng | ✅ Xong | Test đối chiếu trực tiếp với ô màu trong .docx |
| Bảng trả thưởng, damage (L=1, H1–H4=2, H5/Wild=3) | ✅ Xong | Test đối chiếu .docx; giá trị lẻ 0.05 chờ Q3 |
| Trả thưởng dòng: best-of, 6 Wild = 25x, ×ΣEnhance ×Wild ×Global | ✅ Xong | Cách gộp nhiều Multiplier Wild chờ Q2 (mặc định cộng) |
| Luật phá: biểu tượng cơ bản phá mọi bản sao, Wild chỉ phá chính nó | ✅ Xong | Lấp ô tại chỗ (Q0) |
| Chặng 0–5, Endless (1 boss 6 cột), HP bội số của 5, zone theo cột | ✅ Xong | Bước tăng HP Endless chờ Q9; thời điểm sinh boss Endless mới chờ Q8 |
| Biểu tượng theo chặng (reel bỏ L đã loại) | ✅ Xong | Cách hiểu cộng dồn chờ Q7 |
| Vũ khí: Cung tên, Bom 3x3, Dao 1 hàng, Sấm chớp; hệ số 1–10x | ✅ Xong | Bom/Dao có phá Wild không: Q14 |
| Sự kiện Wild: hệ số / xu / Power | ✅ Xong | Xu có nhân Global không: Q1 |
| Power: Enhance, Upgrade, Transform, Replace, Destroy; dự trữ tối đa 3 | ✅ Xong | Transform với Scatter: Q15; Destroy có gây damage không: Q13 |
| Last hit (×2 ở spin Bonus cuối không có Scatter), boss rơi Wild/Power | ✅ Xong | Đơn vị roll: Q11; công thức: Q12 |
| Rương: loại theo chặng, nâng cấp 1 lần, số quà, xu ≥ cấp rương, ngoài Bonus chỉ có xu | ✅ Xong | Q16–Q18 |
| Treasure: xu / nam châm / cỏ bốn lá / Global / Scatter, vòng nam châm | ✅ Xong | Q19–Q24 |
| Hold and Spin | ✅ Xong | Vị trí trong thứ tự hành động: Q4–Q6 |
| Bonus / Super / Epic (6/7/8 spin, chặng 1/2/3, +1 spin mỗi Scatter) | ✅ Xong | Super/Epic có đảm bảo ≥3 Wild/vũ khí; Epic luôn Hold and Spin và sáng toàn bảng |
| Heroic spin / Treasure hunt (Feature 500x), buy3 100x, buy4 300x, Ante 3x | ✅ Xong | Tỷ lệ chia Feature: Q27 |
| Wincap 25.000x (dừng ngay) | ✅ Xong | |
| Pipeline SDK (`create_books`) | ✅ Chạy được | `generate_configs` lỗi chia 0 khi mọi book bằng nhau (do số chưa tune) |
| **Tune số liệu** | ⛔ Chưa làm | Mọi weight là số tạm. Hiện Treasure chiếm gần hết payout và nhiều vòng chạm 25.000x |
| Optimizer / kiểm tra định dạng RGS | ⛔ Chưa làm | Cần tune trước; payout lẻ 0.05 sẽ không qua kiểm tra RGS (Q3) |

## Lệnh

- Test luật: `python -m pytest tests -q` (44 test).
- Sinh reel: `python gen_reels.py`.
- Sinh sách: `python run.py` (optimizer đang tắt).

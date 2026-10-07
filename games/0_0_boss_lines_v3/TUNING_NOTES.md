# Boss Lines v3: ghi chú tune (cập nhật 2026-10-07)

Đọc file này trước khi tune tiếp.

**Trạng thái (2026-10-08): ứng viên hiện tại là `tuning/overrides/p3.json`** (= b6 + Phase 1–4). Chưa ghi vào
`game_config.py`, chờ designer duyệt. Kết quả: `tuning/results/p3_*`, bảng chấm `tuning/results/p3_speccheck.txt`.

| Tier | Mean (mục tiêu) | p5 | Median | p60 | p75 | p99 | Max Win | Spec phân vị |
|---|---|---|---|---|---|---|---|---|
| Bonus (30k) | 88,3 (88,9) | 10,9 | 36,5 | 44,2 | 64,4 | 884 | 0% | đạt |
| Super (50k) | 238,8 (240) | 37,8 | 92,2 | 117,2 | 179,2 | 2.291 | 0,086% | đạt |
| Epic (20k) | 1.503,3 (1.492,5) | 600 | 600 | 713 | 1.119 | 25.000 | 1,10% | đạt; trượt 3 hướng yêu cầu (Phase 3c) |

| Mode | RTP thô từ mean tier | Ghi chú |
|---|---|---|
| buy3 | 96,1% | 95,67/4,23/0,1 × 88,3/238,8/1.503,3 |
| buy4 | 96,4% | 96/4 |
| Feature | 96,7% | p_heroic 0,512; Heroic 683,2, Treasure hunt 274,0 |
| base / ante | do optimizer | phần quay thường tự nhiên 0,80x/spin; vào Bonus 1/216 (base), 1/34,6 (ante) |

---

## 0. Spec phân bố mới (designer, 2026-10-08) và Phase 0

**Yêu cầu** (m = mean mục tiêu của tier; cách hiểu đã chốt với designer):
- Giá trị **p5…p60 nằm trong [0,1 m; 0,5 m]**, **p60…p75 nằm trong [0,5 m; 0,9 m]**, áp dụng cho Bonus/Super/Epic.
- Bonus: giảm median.
- Epic: **mọi phiên ≥ 600x** (luật trả bù cuối Bonus, `bonus_min_total_win = {"epic": 600}`, event
  `bonusMinWin`), **Max Win ≥ 1%** phiên Epic, giảm median, tăng mạnh từ p95 trở lên.
- Super: **Max Win 0,1%** phiên.
- Tăng tiền từ **dòng** và **xu Wild**. Số kết nối mỗi spin phân bố kiểu log: chuỗi dài càng hiếm, nhiều kết nối nhỏ
  trả ít nhưng liên tục.
- Clear chặng nhiều hơn, Treasure trả ít hơn, Clover ra ít hơn nhưng hệ số > 2x nhiều hơn.
- Không giới hạn riêng hệ số Clover/Global… của Epic.
- Chỉ số mới: RTP của 5/20/100/1000 phiên ngẫu nhiên, lặp 100 lần, lấy trung vị, tính theo từng tier
  (giá quy đổi = m / 0,967) và theo từng mode mua.
- Treasure hunt: xu ≥ 1x (đã đúng; sửa thêm lỗi: Bonus vào từ Treasure hunt từng dùng xu tối thiểu 1x thay vì theo chặng).

**Phase 0 (đo và sửa cấu trúc, chưa chỉnh weight):**
- `tuning/spec_check.py TAG`: chấm PASS/FAIL từng yêu cầu, in nguồn tiền, số clear chặng, Clover, phân bố số kết nối,
  spin trắng, trả bù, và RTP lấy mẫu.
- Optimizer: ngân sách Max Win theo từng mode tính từ `tier_mix` × `tier_maxwin_rate` (Super 0,1%, Epic 1%):
  buy3 1,308% · buy4 11,333% · base 0,654% · ante 1,09% · Feature 1,75% (tạm, đo từ b6). Mức cũ cố định 0,1% sẽ làm
  optimizer kéo Max Win của Epic xuống.

**Baseline p0** (= b6 + sàn 600x Epic; Bonus 20.000, Super 50.000, Epic 10.000 phiên), `tuning/results/p0_*`:

| | Bonus | Super | Epic |
|---|---|---|---|
| Mean (mục tiêu) | 93,2 (88,9) | 259,9 (240) | 1.654,5 (1.492,5) |
| p5 / p60 / p75 (giới hạn) | 3,3 / 68,7 / 101,8 (≥ 8,9 / ≤ 44,5 / 44,5–80) | 6,3 / 150,9 / 240,9 (≥ 24 / ≤ 120 / 120–216) | 600 / 1.902 / 2.256 (≥ 600 / ≤ 746 / 746–1.343) |
| Max Win (mục tiêu) | 0,01% | 0,004% (0,1%) | 0,11% (≥ 1%) |
| Dòng + xu Wild / rương / Treasure (% mean) | 18,1 / 29,3 / 52,6 | 13,8 / 30,8 / 55,4 | 11,9 / 35,1 / 53,1 |
| Clear chặng / phiên | 0,58 | 1,00 | 2,41 |
| Clover: % ký hiệu Treasure, % hệ số > 2 | 1,96%, 19,9% | 1,10%, 19,9% | 0,10%, 10,1% |
| Spin trắng | 28,0% | 22,1% | 9,4% |
| Trả bù 600x | | | 18,7% phiên, 37,6x/phiên |

- Số kết nối mỗi spin đã giảm dần theo độ dài (Bonus: 0: 28,8% · 1: 32,5% · 2: 19,1% · 3: 10,0% · 4: 5,0% …),
  spin trắng chỉ xảy ra khi không có kết nối nào.
- Bỏ giới hạn hệ số của Epic (p0u): 1.654,5 thành 1.647,5, không đáng kể vì Treasure Epic ra xu 98,8%.
- RTP lấy mẫu (trung vị 100 lần): xem `tuning/results/p0_speccheck.json`.

**Phase 1: Bonus (p1, `tuning/overrides/p1.json`; 30.000 phiên, đạt đủ 5 yêu cầu)**

| | p0 | **p1** | Yêu cầu |
|---|---|---|---|
| Mean | 93,2 | **86,9** (−2,3%) | 88,9 ± 3% |
| p5 / p25 / median / p60 / p75 | 3,3 / 12,3 / 53,5 / 68,7 / 101,8 | **10,9 / 23,6 / 36,5 / 44,1 / 64,0** | p5 ≥ 8,9 · p60 ≤ 44,5 · p75 44,5–80 |
| p90 / p95 / p99 | 198 / 317 / 697 | 160 / 283 / 868 | |
| Dòng + xu Wild / rương / Treasure (%) | 18,1 / 29,3 / 52,6 | 27,2 / 17,3 / 55,5 | tăng dòng + xu Wild |
| Treasure trả TB mỗi lần | 84,7 | 49,0 | giảm |
| Clear chặng / phiên | 0,58 | 0,98 | tăng |
| Clover: % ký hiệu, % hệ số > 2 | 1,96%, 19,9% | 0,63%, 79,6% | ít hơn, lớn hơn |
| Spin trắng | 28,0% | 25,1% | |
| RTP lấy mẫu N = 5/20/100/1000 | | 66 / 76 / 90 / 94% | |

Nguồn theo khoảng phân vị (`tuning/band_sources.py`): p25–60 nhận 32,6x (dòng 17,1 + Treasure 12,1); 1% cao nhất nhận 2.025x
(Treasure 1.732). Một lần Treasure thông thường nhỏ (median 11,8x, khoảng 30 ô × 0,2x), đuôi đến từ Clover, Global và xu lớn.

Thay đổi (chỉ riêng Bonus: `tier_weights.bonus` và reel chặng 1, Super/Epic không dùng):
- Reel `BON_S1`: wild 4,3, weapon 2,8, shape nhiều biểu tượng thấp (L1 80, L2 72, L3 62, L4 52, H1 15, H2 10, H3 7, H4 5, H5 3):
  nhiều kết nối nhỏ, clear chặng nhiều hơn.
- Xu: 0,2x chiếm đa số (0.2:100, 0.5:4, 1:1.5, 2:.5 …), đuôi ≥ 20x dày hơn (100:.0091 … 1000:.00018, 25000:1e-6).
- Treasure: coin 92, magnet .4, clover .6, golden .1, star .25, global .35. Hệ số Clover/Golden {2:20, 3:20, 4:15, 5:15, 10:17, 20:13}.
  Global {2..10} như mặc định.
- Rương: cấp {95, 4, 1}, nâng cấp 2%, số quà Đồng {1:80, 2:15, 3:5}, Bạc {2:85, 3:15}.
- Sự kiện Wild 35% (hệ số 45 / xu 45 / power 10). Enhance {2:60, 3:25, 4:10, 5:4, 10:1}. Hệ số Wild {2:70, 3:20, 4:7, 5:3}.
- Code (không đổi luật): `tier_weights` ghi đè được thêm sự kiện Wild, hệ số Wild, Enhance, Power, rương, Last hit, boss rơi đồ,
  vũ khí, Cung tên, ô bảo đảm (19 tham số).
- Còn mỏng: p60 44,1 (ngưỡng 44,5). Tỷ trọng Treasure không giảm (55,5%) vì đuôi chủ yếu đến từ Treasure; số tiền mỗi lần
  Treasure thì đã giảm 42%.

**Phase 2: Super (p2, `tuning/overrides/p2.json` = p1 + Super; 50.000 phiên, đạt đủ 5 yêu cầu và luật rương)**

| | p0 | **p2** | Yêu cầu |
|---|---|---|---|
| Mean | 259,9 | **238,8** (−0,5%) | 240 ± 3% |
| p5 / p25 / median / p60 / p75 | 6,3 / 74,0 / 120,7 / 150,9 / 240,9 | **37,8 / 60,9 / 92,2 / 117,2 / 179,2** | p5 ≥ 24 · p60 ≤ 120 · p75 120–216 |
| p90 / p95 / p99 | 480 / 778 / 2.644 | 405 / 713 / 2.291 | |
| Max Win | 0,004% | **0,086%** (43/50.000) | ~0,1% |
| Dòng + xu Wild / rương / Treasure (%) | 13,8 / 30,8 / 55,4 | 14,4 / 30,9 / 54,7 | |
| Treasure trả TB mỗi lần | 143,6 | 102,9 | giảm |
| Clear chặng / phiên | 1,00 | 1,22 | tăng |
| Clover: % ký hiệu, % hệ số > 2 | 1,10%, 19,9% | 0,31%, 89,9% | ít hơn, lớn hơn |
| Spin trắng | 22,1% | 16,6% | |
| RTP lấy mẫu N = 5/20/100/1000 | | 58 / 72 / 83 / 96% | |

- **Code:** Super và Epic có reel riêng (`SUP_S2…SUP_E`, `EPI_S3…EPI_E`, `config.tier_stage_reel`), để chỉnh từng tier mà
  không đụng tier khác. Lúc bắt đầu, các reel này chép giá trị của reel `BON_*` tương ứng.
- **Bài học:** ở Super, **Power quyết định tốc độ qua chặng** (Power từ quà rương và sự kiện Wild). Giảm Power đưa số clear
  từ 1,37 xuống 1,21, mean từ khoảng 460x xuống 302x. Loại vũ khí được bảo đảm gần như không ảnh hưởng. Golden/Clover
  ra thường thì đẩy cả khoảng giữa; muốn tiền ra đuôi thì cho Golden rất hiếm và chỉ hệ số 10x/20x.
- **Thay đổi Super:**
  - Reel `SUP_S2`: wild 2,1, weapon 0,1, shape nghiêng về biểu tượng thấp (70/62/54/46/18/13/9/6/4). `SUP_S3` 1,2/0,05.
    `SUP_S4/S5/E` 0,8/0.
  - Quà rương ra Power: Đồng 3%, Bạc 5%, Vàng 8%, Kim cương 12% (spec: rương càng cao càng ít xu). Sự kiện Wild 35%,
    hệ số 50 / xu 50 / Power 0.
  - Rương: cấp {97, 2.5, 0.5}, nâng cấp 1%, số quà Đồng {1:90, 2:10}, Bạc {2:95, 3:5} (spec: Bạc ≥ 2 quà).
  - Xu (tối thiểu 1x ở chặng 2–3): 1:100, 2:2, 3:1, 4:.5, 5:1 …, 100:.0044 … 1000:6.2e-5, **25000: 4e-5** (cho Max Win 0,1%).
  - Treasure: coin 92, magnet .15, clover .3, **golden .12 (chỉ hệ số 10x/20x)**, star .1, global .25.
    Clover {2:10, 3:10, 4:10, 5:20, 10:30, 20:20}. Global {2:70, 3:20, 4:7, 5:3}.
  - Enhance và hệ số Wild giống Bonus.
- Bản đầu của p2 vi phạm luật rương (Bạc 1 quà; Power không tăng theo cấp). `spec_check` giờ kiểm tra luật này; đã sửa.
- **Còn yếu:** tỷ trọng dòng + xu Wild gần như không tăng (13,8 thành 14,1%). Thêm Wild ở chặng 2 thì Super đi sâu hơn và
  khoảng giữa tăng; cần thêm cách khác nếu designer muốn tỷ trọng dòng cao hơn.

**Phase 3: Epic (p3, `tuning/overrides/p3.json` = p2 + Epic; 20.000 phiên, đạt đủ 6 yêu cầu phân vị/Max Win và luật rương; trượt 4/6 hướng yêu cầu, xem dưới)**

| | p0 | **p3** | Yêu cầu |
|---|---|---|---|
| Mean | 1.654,5 | **1.493,6** (+0,1%) | 1.492,5 ± 3% |
| min / p25 / median / p60 / p75 | 600 / 697 / 1.122 / 1.902 / 2.256 | **600 / 600 / 600 / 660 / 1.081** | ≥ 600 · p60 ≤ 746 · p75 746–1.343 |
| p90 / p95 / p99 | 3.099 / 3.752 / 5.405 | 2.679 / 4.073 / 25.000 | tăng mạnh từ p95 |
| Max Win | 0,11% | **1,14%** (228/20.000) | ≥ 1% |
| Dòng + xu Wild / rương / Treasure (%) | 11,9 / 35,1 / 53,1 | 3,0 / ~17 / ~80 | tăng dòng ✗ |
| Clear chặng / phiên | 2,41 | 1,18 | tăng ✗ |
| Clover: % ký hiệu, % hệ số > 2 | 0,10%, 10,1% | 0,08%, 87,6% | ✓ |
| Trả bù lên 600x | 18,7% phiên, 37,6x | **56,5% phiên, 127,7x/phiên** | |
| Spin không kết nối | 19,2% | 42,9% | giảm ✗ |
| Treasure trả TB mỗi lần | 246,8 | 410,9 | giảm ✗ |
| RTP lấy mẫu N = 5/20/100/1000 | | 70 / 76 / 95 / 95% | |

Nguồn theo khoảng: 60% phiên dưới nhận 600x (tự nhiên khoảng 380–480x: dòng ~18 + rương ~77 + Treasure mở đầu và
Treasure chặng 3, cộng phần trả bù). p60–75 nhận 859x, p75–90 nhận 1.695x, p90–99 nhận 5.319x, 1% trên cùng nhận 25.000x.

- **Thay đổi Epic:**
  - Reel `EPI_S3` wild 1,0, `EPI_S4/S5/E` 0,6, không vũ khí trên reel (vũ khí chỉ đến từ bảo đảm 2/spin). Shape phẳng
    (L 30/30/30/30, H 28/26/24/22/20) để ít kết nối, ít sát thương, qua chặng chậm.
  - **Power chỉ là Enhance** (`power_pick_weights` Epic), vì Enhance tăng tiền dòng mà không gây sát thương. Quà rương ra Power
    10/20/30/40% theo cấp. Sự kiện Wild 60% (hệ số 40 / xu 40 / Power 20). Enhance {2:30, 3:25, 4:20, 5:15, 10:10}.
  - Rương: cấp {97, 2.5, 0.5}, nâng cấp 1%, Đồng {1:90, 2:10}, Bạc {2:95, 3:5}.
  - Xu: mỗi pool dồn về mức tối thiểu (1:100 cho Treasure mở đầu, 5:100, 20:3 cho chặng 5/Endless, 100:.6 cho rương Kim cương),
    **25000: 3,4e-3** (cho Max Win khoảng 1,2%).
  - Treasure: coin 98, magnet .1, clover .08, **golden .31 (chỉ 10x/20x)**, star .05, global .1. Clover/Global dùng chung bảng với
    Super (không còn giới hạn riêng cho Epic).
  - Hệ số Wild giống Super.
- **Đánh đổi cần designer xem:**
  - 60% phiên Epic chỉ nhận đúng mức sàn; hơn một nửa nhờ trả bù (8% mean là tiền trả bù).
  - Epic gần như không có dòng thắng (2%), 43% spin không có kết nối. Shape trung gian (p3g: L 45/42/40/38, H 26/22/18/14/11)
    có nhiều kết nối hơn (34% spin không kết nối), nhưng Epic qua chặng nhanh hơn: p60 831 (vượt 746), mean +17%.
    Yêu cầu "nhiều kết nối nhỏ" và "60% phiên ≤ 746x" kéo ngược nhau ở Epic, vì mỗi kết nối gây sát thương và mỗi lần
    clear chặng 5/Endless trả tối thiểu 30 × 20x = 600x.
  - Max Win 1,14% chủ yếu đến từ xu 25.000x trong Treasure và rương Kim cương.
  - **4 hướng yêu cầu Epic đang trượt so với p0** (`spec_check` in FAIL): tỷ trọng dòng + xu Wild (11,8% thành 3,0%),
    clear chặng (2,41 thành 1,18), spin không kết nối (19% thành 43%), Treasure trả mỗi lần (247 thành 411; vì Golden 10x/20x
    mang phần đuôi). Ba điểm đầu cùng một gốc: kết nối gây sát thương, nên nhiều kết nối thì qua chặng nhanh, mà clear
    chặng 5/Endless trả tối thiểu 600x, làm vỡ yêu cầu 60% phiên ≤ 746x. Designer cần chọn ưu tiên, hoặc nới một số cố định
    (xu tối thiểu chặng 5/Endless trong Epic, HP boss Epic, hay bảo đảm 2 vũ khí).

**Thử nới số cố định cho Epic** (10.000 phiên, chỉ thử nghiệm; override trong `_scratch/ov/x_mid*.json`):

| Phương án (từ p3) | Mean | p60 | p75 | Dòng + xu Wild | Clear/phiên | Spin không kết nối |
|---|---|---|---|---|---|---|
| p3 | 1.494 | 660 | 1.081 | 3,0% | 1,18 | 43% |
| shape trung gian (nhiều kết nối hơn) | 1.771 | 803 ✗ | 1.368 ✗ | 3,1% | 1,33 | 34% |
| + xu tối thiểu chặng 5/Endless 20x thành 5x | 1.586 | 801 ✗ | 1.356 ✗ | 3,4% | 1,33 | 34% |
| + Epic bảo đảm 1 vũ khí (thay 2) | 1.168 | 600 | 644 ✗ | 3,2% | 0,77 | 39% |

- Tỷ trọng dòng + xu Wild ở Epic **kẹt quanh 3%** trong mọi phương án: paytable cố định nên mỗi phiên chỉ nhận vài chục x từ
  dòng, so với mean 1.492x. p0 đạt 11,8% vì dòng được nhân lớn (Global, Enhance, hệ số Wild) và Epic đi sâu hơn (2,4 clear).
  Muốn tăng tỷ trọng này thì phải tăng hệ số nhân dòng ở Epic, và tiền đó phải lấy bớt từ đuôi Treasure/Golden.
- Nới xu tối thiểu chỉ hạ mean, không cứu được p60. Bớt vũ khí làm Epic chậm hẳn (0,77 clear), 73% phiên phải trả bù.

**Phase 3c: Epic tăng hệ số nhân dòng (bản Epic hiện tại trong p3; 20.000 phiên)**
- Đổi so với Phase 3b: Global trong Treasure .1 thành **.4** (bảng Global {2..10} như Bonus), **Golden .31 thành .03**, Enhance
  {15:30, 20:25, 25:20, 50:25}, hệ số Wild {2:30, 3:25, 4:20, 5:15, 10:10}, xu **25000: 4,9e-3**. Hệ số nhân dòng lớn hơn,
  tiền đuôi chuyển từ Golden sang Global/Max Win.
- Kết quả: mean 1.503,3 (+0,7%), p60 713, p75 1.119, Max Win 1,10%, trả bù 53,3% phiên (117,5x/phiên).
  **Dòng + xu Wild 3,0% thành 12,9%** (p0: 11,8%, đạt). Phát hiện ở bảng trên ("kẹt quanh 3%") chỉ đúng khi giữ hệ số nhân thấp.
- Còn trượt 3 hướng yêu cầu: clear chặng 1,18 (p0 2,41), spin không kết nối 43% (p0 19%), Treasure trả mỗi lần 327 (p0 247).
  Trong 327 có khoảng 130x là xu Maxwin (1,1% × 25.000 / 2,13 Treasure mỗi phiên); bỏ phần đó thì còn khoảng 197, thấp hơn p0.
- Thử thêm kết nối chỉ ở chặng đầu của Epic (20.000 phiên):

  | Phương án | Mean | p60 | Spin không kết nối | Dòng + xu Wild |
  |---|---|---|---|---|
  | p3 | 1.503 | 713 | 43% | 12,9% |
  | `EPI_S3` shape trung gian | 1.644 | 783 ✗ | 37% | 13,1% |
  | `EPI_S3` + `EPI_S4` shape trung gian | 1.805 | 863 ✗ | 35% | 14,3% |

  Clear chặng 3 nhanh hơn kéo theo Treasure chặng 4 và rương Vàng (3 xu ≥ 20x), đẩy khoảng giữa lên. Vậy "ít spin
  không kết nối" ở Epic xung đột trực tiếp với "60% phiên ≤ 746x". Cần designer chọn ưu tiên.

**Phase 4: base / ante / Feature, optimizer (p3)**
- Bonus: tăng đuôi xu ≥ 100x thêm 25% để mean 86,9 thành 88,3 (phân vị giữ nguyên), kéo buy3 thô lên khoảng 96,1%.
- Feature (20.000 phiên mỗi loại): Heroic 683,2 (median 117,5, Max Win 3/20.000); Treasure hunt 274,0 (median 173, Max Win
  2/20.000). **p_heroic = 0,512** (`feature_heroic_chance` trong p3). `feature_maxwin_rate` trong config 3,5e-4 thành 2,0e-4.
- Base/ante (200.000 spin): phần quay thường 0,805 / 0,807x, hit 51,9 / 53,2%, vào Bonus 1/216 / 1/34,6. Không đổi so với b6.
- **Optimizer `distribution_bias`:** bỏ bias của fence freegame buy3/buy4 (30% vào 100–300x) và Feature (500–1.500x), vì sẽ
  phá spec phân vị (p75 của Bonus là 64x). Giữ bias 2–3x cho phần quay thường ở base/ante.
- **Việc còn thiếu:** optimizer trộn lại trọng số các sách, nên phân bố người chơi thật là phân bố sau optimizer. Sau khi
  chạy optimizer cần kiểm tra lại spec trên bảng trọng số đã tối ưu (ghép với tier của từng sách), không chỉ trên phiên harness.

RTP lấy mẫu (trung vị 100 lần; `p3_speccheck.txt`):

| | N=5 | N=20 | N=100 | N=1000 |
|---|---|---|---|---|
| Bonus | 66% | 76% | 90% | 94% |
| Super | 60% | 73% | 85% | 97% |
| Epic | 65% | 80% | 98% | 97% |
| buy3 | 52% | 85% | 88% | 95% |
| buy4 | 58% | 74% | 84% | 98% |
| Feature | 57% | 80% | 96% | 97% |
| base / ante | 51% / 18% | 57% / 40% | 72% / 70% | 108% / 122% |

base/ante dùng tần suất vào Bonus và mean tự nhiên (chưa qua optimizer), nên với N lớn RTP cao hơn 96,7%.

---

## 1. Mục tiêu (designer, 2026-10-07)

| Mục | Giá trị |
|---|---|
| RTP mọi mode | **96.7%**: base 0.967x/spin, ante 2.901x/spin, buy3 96.7x, buy4 290.1x, Feature 483.5x |
| Mean từng tier Bonus | **Bonus 88.9x / Super 240x / Epic 1.492,5x** |
| buy3 (100x) | Bonus 95.67 / Super 4.23 / Epic 0.1 (%), cho mean 96.70x. Base và ante dùng cùng tỷ lệ 3/4/5 Scatter |
| buy4 (300x) | Super 96 / Epic 4 (%), cho mean 290.1x |
| Feature | p × mean_Heroic + (1 − p) × mean_TreasureHunt = 483.5x, p trong [0.2, 0.8] (tạm 0.5); hai mean không cần bằng nhau |
| Base / Ante | Bonus chiếm **50% RTP của base** (0.4835), tần suất vào Bonus 1/200; ante 1/40. Tỷ lệ này **suy ra từ spec**, không phải chọn: ante tốn 3x và ra Bonus 5x, nên base_game + 5·B = 3·(base_game + B), suy ra base_game = B. Nếu muốn khác 50% thì phải đổi giá ante hoặc hệ số 5x. Phần quay thường = 0.4825x/spin ở cả hai mode |
| Wincap | 25.000x |
| Chưa chốt | Yêu cầu về **median, phân bố, var**: designer sẽ đưa sau. Số đo hiện tại ở mục 3 |

Công thức tỷ lệ tier: pB·88.9 + pS·240 + pE·1492.5 = 96.7, có 1 bậc tự do. Đổi mean tier thì tính lại theo công
thức này. buy4: qE = (290.1 − 240) / (1492.5 − 240) = 4%.

## 2. Quyết định luật trong đợt tune này (designer đã duyệt)

1. **Bỏ hoàn toàn Hold and Spin** khỏi mọi mode. Lý do đo được: Hold and Spin bắt buộc ở Epic giữ trung bình
   27,8/30 ô, sàn Epic 4.678x ngay cả khi weight ở mức tối thiểu (mục tiêu 1.492,5x).
2. **Bảo đảm vũ khí** trên bảng đầu mỗi free spin: **Super 1, Epic 2** (`bonus_min_weapons`). Wild không được tính
   (spec cũ: 3 ô Wild/vũ khí). Heroic giữ 5 ô Wild/vũ khí.
3. Thêm `tier_weights` trong config: bảng weight riêng theo tier Bonus cho `coin_value_weights`,
   `treasure_kind_weights`, `clover_factor_weights`, `golden_factor_weights`, `global_factor_weights`. Chỉ là
   weight, không đổi luật. Ngoài Bonus luôn dùng bảng chung.

Commits: `571bf9b`, `d96a1d7` (tỷ lệ tier), `11203d1` (bỏ Hold and Spin), `e1fcea5` (bảo đảm vũ khí + `tier_weights`).

## 3. Trạng thái hiện tại: t17 (6.000 phiên mỗi tier)

Lệnh tái tạo: `python tuning/tune_harness.py <tier> 6000 tuning/overrides/t17.json t17`
rồi `python tuning/dist_stats.py t17`. Kết quả gốc (CSV từng phiên + JSON) nằm ở `tuning/results/t17_*`.

### 3.1 Mean, median, độ biến động

| Tier | Mean | Mục tiêu | Lệch | Median | Median/Mean | SD | Var | CV | SE của mean | Max Win |
|---|---|---|---|---|---|---|---|---|---|---|
| Bonus | 91,2 | 88,9 | +2,5% | 51,5 | 0,56 | 167,9 | 28.184 | 1,84 | 2,2 | 0 / 6.000 |
| Super | 254,8 | 240 | +6,2% | 119,6 | 0,47 | 762,5 | 581.413 | 2,99 | 9,8 | 1 / 6.000 |
| Epic | 1.616,4 | 1.492,5 | +8,3% | 1.137,6 | 0,70 | 1.410,6 | 1.989.854 | 0,87 | 18,2 | 6 / 6.000 (1 trên 1.000) |

### 3.2 Phân vị (x cược)

| Tier | p1 | p5 | p10 | p25 | p50 | p75 | p90 | p95 | p99 | p99.9 | min | max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Bonus | 1,4 | 3,4 | 5,5 | 12,4 | 51,5 | 99,8 | 197 | 323 | 751 | 2.001 | 0 | 4.432 |
| Super | 2,5 | 6,4 | 10,2 | 73,4 | 119,7 | 249,6 | 475 | 748 | 2.496 | 11.840 | 0,4 | 25.000 |
| Epic | 289 | 337 | 393 | 694 | 1.139 | 2.265 | 3.101 | 3.739 | 5.135 | 25.000 | 77,6 | 25.000 |

### 3.3 Tỷ lệ phiên theo khoảng (bội số của mean mục tiêu)

| Tier | < 0,5x | 0,5–1x | 1–2x | 2–5x | 5–10x | > 10x |
|---|---|---|---|---|---|---|
| Bonus | 45,0% | 25,9% | 17,5% | 8,7% | 2,0% | 0,8% |
| Super | 50,2% | 23,8% | 16,1% | 7,4% | 1,4% | 1,0% |
| Epic | 29,9% | 25,5% | 33,1% | 11,3% | 0,1% | 0,1% |

### 3.4 Nguồn tiền (x cược, trung bình mỗi phiên) và tiến độ chặng

| Tier | Dòng | Xu Wild | Rương | Treasure | Spin/phiên | Treasure/phiên | Chặng cuối (% phiên) |
|---|---|---|---|---|---|---|---|
| Bonus | 16,1 | 0,6 | 24,2 | 50,3 | 7,5 | 0,58 | 1: 49,5 · 2: 49,1 · 3: 1,4 · 4+: 0,07 |
| Super | 32,9 | 1,0 | 79,3 | 141,6 | 9,2 | 1,00 | 2: 28,0 · 3: 56,5 · 4: 13,1 · 5: 1,9 · E: 0,6 |
| Epic | 188,6 | 8,1 | 577,6 | 842,1 | 12,6 | 3,40 | 3: 0,6 · 4: 23,7 · 5: 33,9 · E: 41,8 |

### 3.5 Nhận xét về hình dạng phân bố (để designer quyết yêu cầu median/var)

- **Bonus và Super lệch phải mạnh:** median chỉ khoảng 0,5 lần mean, khoảng một nửa số phiên dưới 0,5 lần mục tiêu.
  Phần lớn mean nằm ở đuôi: Treasure chiếm 55% mean của cả hai tier.
- **Super có bước nhảy giữa p10 (10x) và p25 (73x):** khoảng 28% phiên không qua được chặng 2, nên không có Treasure.
  Muốn phân bố mượt hơn thì nâng tỷ lệ qua chặng 2, đổi lại phải hạ giá trị mỗi lần Treasure.
- **Epic ít biến động (CV 0,87):** median 1.138x. Sàn cao (p1 289x) vì Treasure mở đầu phủ toàn bảng, xu Epic ≥ 5x và xu
  ≥ 20x ở chặng 5/Endless. Max Win 1 trên 1.000 phiên Epic (chưa tách nguồn).
- **SE của mean nhỏ (1–4%) nhưng đuôi dày:** giữa các lượt 4.000 phiên, mean Super dao động khoảng ±10% (270 → 297 dù
  không đổi gì của Super). Muốn kết luận một thay đổi < 10% thì chạy ≥ 20.000 phiên, hoặc so cùng seed (harness
  dùng seed cố định theo chỉ số phiên).

## 3B. Base / Ante / Feature: b6 (`tuning/overrides/b6.json` = t17 + các thay đổi dưới đây)

### Thay đổi so với t17

| Tham số | b6 | Mặc định |
|---|---|---|
| Reel `BR0` | wild 1.0, weapon 0.6, sc 0.9 (= 3 Scatter/cột), `shape` phẳng hơn: L1 50, L2 48, L3 46, L4 44, H1 22, H2 17, H3 12, H4 8, H5 5 | wild 5, weapon 1.5, sc 1.4 |
| Reel `ANTE` | như BR0, sc 2.0 (= 6 Scatter/cột) | wild 5, weapon 1.5, sc 3.0 |
| Reel `HERO` | wild 5.5, weapon 1.8 | wild 8, weapon 3 |
| `tier_weights.treasure_hunt` | Treasure: coin 83, magnet 1.3, clover 2.6, golden .2, star 1.0, global 0, scatter 1. Xu: dốc ít hơn t17 (2:14, 3:9, 4:6, 5:4, … 25000:2e-7) | |
| `feature_heroic_chance` | **0.5365** (tính từ hai mean bên dưới) | 0.5 |

Code mới (không đổi luật): `gen_reels.py` nhận khóa `shape` riêng cho từng reel; `tier_weights` có khóa
`"treasure_hunt"`; `game_optimization.py` tính RTP fence Bonus từ mean 96.7x và tần suất vào Bonus (bỏ số 0.30 tạm).

### Base / Ante (40.000 spin, Bonus được kích hoạt thì KHÔNG chơi, chỉ đếm)
Lệnh: `python tuning/base_stats.py base|ante 40000 tuning/overrides/b6.json TAG`

| Mode | Mean phần quay thường | Median | SD | Hit rate | Thắng TB / spin có thắng | Vào Bonus | Tỷ lệ tier tự nhiên (B/S/E %) | Treasure base |
|---|---|---|---|---|---|---|---|---|
| base | 0,828 | 0,10 | 8,66 | 51,9% | 1,59 | 1 / 213 | 93,6 / 6,4 / 0 | 0,05% spin |
| ante | 0,817 | 0,15 | 8,70 | 53,0% | 1,54 | 1 / 34,7 | 89,9 / 9,4 / 0,6 | 0,04% spin |

Phân vị base: p90 1,75 · p99 7,1 · p99.9 61,5 · p99.99 408 · max 1.215. Nguồn base: dòng 0,586, rương 0,219,
Treasure 0,015, xu Wild 0,008.

- **Mean tự nhiên 0,83 > 0,4825 là bình thường:** optimizer trộn thêm spin trắng (fence "0") và chỉnh tần suất.
  Chỉ số cần khớp là **thắng trung bình mỗi spin có thắng**: fence basegame (hr 3.5) cần 0,4825 × 3,5 ≈ 1,69
  (ante: 0,16017 × 3,5 × 3 ≈ 1,68). Tự nhiên đang là 1,59 / 1,54, đủ gần.
- **Tần suất vào Bonus:** base 1/213 so với 1/200 (đạt). Ante 1/34,7 so với 1/40: reel 300 ô/cột nên Scatter chỉ
  đổi theo bậc. 6 Scatter/cột cho 1/34,7, 5 Scatter/cột cho 1/59; giữ 6. Optimizer chốt chính xác.
- **Đánh đổi cần designer xem:** để hạ base phải giảm Wild/vũ khí trên `BR0`, nên **Treasure ở base gần như mất**:
  boss chặng 0 (HP 25) bị hạ cả 3 con chỉ 0,05% spin (t17 reel cũ: 1%). Nếu muốn Treasure ở base xuất hiện
  thường hơn thì phải tăng vũ khí `BR0` và bù bằng cách giảm dòng hoặc rương.
- Tỷ lệ tier khi vào Bonus từ base/ante được **ép** theo `scatter_triggers` (95,67 / 4,23 / 0,1) ở fence freegame,
  nên tỷ lệ tự nhiên ở trên không ảnh hưởng RTP.

### Feature (6.000 phiên mỗi loại)
Lệnh: `python tuning/tune_harness.py feature_heroic|feature_treasure 6000 tuning/overrides/b6.json TAG`

| Loại | Mean | Median | SD | CV | p10 | p90 | p99 | < 100x | Max Win |
|---|---|---|---|---|---|---|---|---|---|
| Heroic | 663,8 | 112,5 | 1.271 | 1,91 | 12 | 2.371 | 4.456 | 46,5% | 3 / 6.000 |
| Treasure hunt | 274,8 | 174 | 495 | 1,80 | 88 | 527 | 1.530 | 18,3% | 1 / 6.000 |
| **Gộp (p = 0,5365)** | **483,5** | 148,8 | 1.009 | 2,09 | 34 | 1.224 | 3.782 | 33,4% | |

p = (483,5 − 274,8) / (663,8 − 274,8) = 0,5365. Phân vị gộp: p5 9,2 · p25 82 · p75 424 · p95 2.462.
Tỷ lệ lượt mua Feature (giá 500x) nhận < 250x: 64,9%; < 500x: 78,1%.

- Heroic: nguồn rương 321 (rương Kim cương ở chặng 5, xu ≥ 100x), dòng 137, Treasure 138, xu Wild 67. Median thấp
  (112x) vì phần lớn tiền đến từ việc hạ boss chặng 5. Đòn bẩy chính là reel `HERO` (wild/weapon).
- Treasure hunt: gần như toàn bộ là Treasure. Khoảng 2% phiên vào được Bonus nhờ Scatter. Đòn bẩy là
  `tier_weights.treasure_hunt`. Nếu bật lại Global trong Treasure hunt thì mean tăng mạnh.
- Lịch sử: b3 Heroic 1.184 / Treasure hunt 87,9 (p sẽ là 0,36); b4 Treasure hunt 517 (quá cao); b5 585 / 211
  (p sẽ là 0,73); b6 664 / 275 (p 0,54).

## 4. Bộ weight t17 (`tuning/overrides/t17.json`)

Override áp lên `GameConfig` lúc chạy harness. Bảng dạng dict bị **thay toàn bộ**, không merge.

| Tham số | t17 | Mặc định trong config |
|---|---|---|
| `coin_value_weights` | 0.2:40, 0.5:30, 1:25, 2:8, 3:4, 4:2.5, 5:1.5, 6:1, 8:.6, 10:.4, 12:.25, 15:.15, 20:.1, 25:.03, 30:.015, 40:.007, 50:.003, 100:8e-4, 150:3e-4, 200:1.5e-4, 250:1e-4, 500:3e-5, 1000:1e-5, **25000:2e-7** | dốc ít hơn, 25000:4e-4 |
| `treasure_kind_weights` (Super dùng bảng riêng) | coin 95, magnet .4, clover .6, golden .04, star .25, global .15, scatter 1 | 60/7/8/2/4/6/1 |
| `clover_factor_weights` / `golden_factor_weights` | 2:80, 3:15, 4:4, 5:1 | lên tới 20 |
| `global_factor_weights` | 2:60, 3:25, 4:10, 5:5 | lên tới 10 |
| `enhance_factor_weights` | 2:60, 3:25, 4:10, 5:4, 10:1 | lên tới 100 |
| `wild_mult_weights` | 2:70, 3:20, 4:7, 5:3 | lên tới 10 |
| `weapon_factor_weights` | chỉ 1 | 1–10 |
| `last_hit_base` / `last_hit_scale` | 0 / 0.002 | 0.005 / 0.03 |
| `boss_drop_chance` | 0.002 | 0.03 |
| Reel Bonus (wild%, weapon%) | S1 5.8/1.15, S2 1.8/0.1, S3 1.2/0.05, S4 0.8/0, S5 0.8/0, E 0.8/0 | S1 6/2 … E 4/2.5 |
| `tier_weights.bonus` | Treasure: coin 87, magnet 1, clover 1.8, golden .13, star .7, global .4, scatter 1 | |
| `tier_weights.super` | Treasure: coin 92, magnet .65, clover 1.05, golden .07, star .4, global .25, scatter 1 | |
| `tier_weights.epic` | Treasure: coin 99, magnet .08, clover .1, golden .005, star .035, global .025, scatter 1. Xu: 5:6, 6:.6, 8:.3, 10:.15, 12:.08, 15:.04, 20:.4, 25:.02, 30:.008, 40:.003, 50:.001, 100:8e-4, 150:5e-5, 200:2e-5, 250:1e-5, 500:2e-6, 1000:5e-7, 25000:2e-7. Global chỉ 2. Clover/Golden 2:90, 3:10 | |

Không đổi (giữ mặc định): `chest_*`, `wild_event_*`, `power_*`, `guarantee_symbol_weights`
(W 70, AR 10, BM 8, SW 8, LT 4; Super/Epic chỉ lấy phần vũ khí), `arrow_k_choices`.

**Lưu ý:** reel S4/S5/E đang để 0% vũ khí. Vũ khí trên các reel này giờ chỉ đến từ luật bảo đảm và boss rơi đồ.
Designer có thể muốn giữ một ít vũ khí tự nhiên; xem lại khi chốt.

## 5. Đòn bẩy đã học (độ nhạy đo được)

| Đòn bẩy | Ảnh hưởng | Ghi chú |
|---|---|---|
| Luật bảo đảm (spec) | **Rất lớn** | Wild-or-weapon 3 → 1: Super 1.068 → 297. Đổi sang bảo đảm vũ khí (Super 1/Epic 2): Super 195 → 788, Epic 1.502 → 5.962 (cùng weight). Vũ khí quyết định tốc độ qua chặng |
| Reel S1 (wild/weapon) | **Rất nhạy cho Bonus** | t14 → t15: S1 5.2/1.0 → 6.0/1.2 (kèm Treasure Bonus giàu hơn chút): Bonus 70,2 → 103,3; t15 → t16: S1 6.0 → 5.5: 103,3 → 83,1. Super/Epic không bị ảnh hưởng (bắt đầu từ chặng 2/3) |
| Reel S2–S5/E | Nhỏ | Khi đã có luật bảo đảm vũ khí, cắt reel gần như không làm chậm tốc độ qua chặng |
| Hệ số Treasure (magnet, clover, golden, star, global) | Lớn | Super: chỉ ra xu 625x so với có hệ số 2.432x. Đòn bẩy chính cho Bonus/Super, chỉnh qua `tier_weights` |
| Xu 25.000x trong `coin_value_weights` | Lớn cho Epic / Max Win | Pool lọc theo xu tối thiểu, nên rương Kim cương (≥ 100x) làm tỷ lệ xu Maxwin tăng vọt (0,36% ở weight 5e-6). Hạ 2e-7: Epic 3.551 → 3.265, Max Win 1/46 → 1/267 |
| Last hit / boss rơi đồ | Vừa (Epic) | 0.005/0.015 → 0.001/0.005: Epic 2.206 → 1.911, Super 266 → 225 |
| Global multiplier | Nhỏ | Trung bình chỉ 1,0–2,6 ở các tier |
| Cung tên `arrow_k_choices`, tỷ lệ loại vũ khí | Nhỏ | Hạ Cung tên hoặc đổi tỷ lệ BM/SW không giảm Super/Epic đáng kể |
| Toàn bảng sáng ở Epic | Chưa đo lại sau khi bỏ Hold and Spin | Lúc còn Hold and Spin thì không ảnh hưởng |

**Sàn** (mọi weight tối thiểu, `_scratch/ov/floor_w.json`, luật hiện tại): Super 59,6x, Epic 943x. Mục tiêu nằm trên
sàn, nên chỉnh weight là đạt được. Phần sàn không giảm được của Epic đến từ các số cố định theo spec: Treasure mở
đầu, xu Epic tối thiểu 5x, xu tối thiểu 20x ở chặng 5/Endless, rương Kim cương xu ≥ 100x.

## 6. Lịch sử các lượt (mean, x cược)

| Lượt | Bonus | Super | Epic | Thay đổi |
|---|---|---|---|---|
| baseline | ~25.000 | | | weight placeholder, gần như toàn Max Win |
| t2 | 590 | 11.121 | ~24.753 | giảm Treasure/xu/enhance/wild |
| t3 | 125 | 2.697 | 21.424 | xu dốc hơn, loại Treasure hiếm hơn |
| t5 | 78,4 | 1.068 | 13.642 | còn Hold and Spin, bảo đảm 3 ô |
| t5 (bỏ Hold and Spin, bảo đảm 1 Wild/vũ khí) | 52,5 | 200 | 1.562 | |
| t9 | 74,7 | 195 | 1.502 | chỉnh reel S1–S3 |
| t9 + bảo đảm vũ khí 1/2 | | 788 | 5.962 | luật mới |
| t11 | 66,8 | 270 | 3.265 | cắt reel S2+, xu ≥ 20 dốc hơn, xu 25.000 = 2e-7 |
| t12 | 102,6 | 297 | 2.541 | thêm `tier_weights` (Bonus giàu hơn, Epic chỉ xu) |
| t14 | 70,2 | 224,7 | 1.911 | hạ Last hit / boss rơi đồ |
| **t17** | **91,2** | **254,8** | **1.616** | chỉnh nhẹ S1, bảng Super/Epic |

Chi tiết từng lượt: `tuning/results/findings_20261007.md`. Các file override cũ nằm trong `_scratch/ov/`
(không commit).

## 7. Việc còn lại

1. **Designer xem p3** (đầu file). Cần quyết:
   - Xung đột ở Epic giữa "60% phiên ≤ 746x" và "ít spin không kết nối / clear chặng nhiều hơn" (Phase 3c).
   - Trả bù 600x đang chi cho khoảng 53% phiên Epic (117x/phiên, 8% mean).
   - Treasure ở base gần như mất (0,03% spin); Bonus chiếm 50% RTP của base (suy ra từ spec).
   - Super/Bonus: tỷ trọng dòng chỉ tăng nhẹ ở Super (13,8 thành 14,1%).
2. Đồng ý thì ghi p3 vào `game_config.py`: `tier_weights` (bonus, super, epic, treasure_hunt), các tham số chung, reel
   (`_reel_specs` vào `gen_reels.REEL_SPECS`, kể cả `shape`, rồi chạy `python gen_reels.py`), `feature_heroic_chance` 0,512.
   Chạy pytest, chạy lại `spec_check` trên config mới (override rỗng) để chắc kết quả trùng p3, rồi commit.
3. Bật `reject_wincap_outside_wincap_fence`, chạy optimizer (`run.py`), rồi **kiểm tra spec trên phân bố sau optimizer**
   (bảng trọng số đã tối ưu ghép với tier của từng sách).
4. Q3 (payout lẻ bội 0.1x) vẫn chờ xác nhận với Stake trước bước kiểm tra RGS.

## 8. Công cụ (`tuning/`)

| Lệnh | Việc |
|---|---|
| `python tuning/tune_harness.py TIER N overrides.json TAG` | TIER: bonus, super, epic, feature_heroic, feature_treasure, base. Lưu `tuning/results/TAG_TIER_<time>.csv` (1 payout/phiên) và `.json` (mean, median, phân vị, Max Win, nguồn tiền, chặng cuối, spin, số Treasure) |
| `python tuning/stage_split.py TIER N overrides.json TAG` | Tiền theo chặng × nguồn (dòng, xu Wild, rương, Treasure, Treasure bị cắt bởi Max Win) |
| `python tuning/dist_stats.py TAG [TIER...]` | Đọc CSV của TAG: mean, median, sd, var, CV, SE, phân vị, % phiên theo khoảng của mục tiêu |
| `python tuning/base_stats.py base\|ante N overrides.json TAG` | Base/ante tự nhiên: mean phần quay thường, hit rate, tần suất và tỷ lệ tier khi vào Bonus, Treasure, nguồn tiền |
| `python tuning/spec_check.py TAG [--save]` | Chấm spec 2026-10-08 (PASS/FAIL): phân vị, mean, sàn và Max Win, luật rương, các hướng yêu cầu so với p0, RTP lấy mẫu 5/20/100/1000 theo tier và mode |
| `python tuning/band_sources.py TIER N overrides.json` | Nguồn tiền theo từng khoảng phân vị (p0–5, 5–25, 25–60, 60–75, 75–90, 90–99, 99–100) |
| `python tuning/treasure_probe.py TIER N overrides.json` | Một lần Treasure: số ô, tiền, Global, loại ký hiệu theo khoảng |

- Override: `{tên_thuộc_tính_config: giá_trị}`. Key số viết dạng chuỗi (`"0.2"`), harness tự đổi kiểu.
- `_reel_specs`: `{"BON_S1": {"wild": 5.8, "weapon": 1.15}}` dựng lại reel trong bộ nhớ từ `gen_reels.REEL_SPECS`.
- `tier_weights`: như trong config, key số dạng chuỗi.
- Harness gọi thẳng `run_bonus(tier, trigger)`, tức đo mean **của riêng tier**, không qua tỷ lệ Scatter của buy3.
- Seed ổn định theo (tier, chỉ số phiên), sửa ngày 2026-10-08: trước đó dùng `hash(tier)`, vốn ngẫu nhiên mỗi lần chạy, nên
  các lượt cũ (t1–t17, b1–b6, p0) **không** tái lập được và dao động khoảng ±10% giữa các lượt là nhiễu thật. Từ p1 trở đi, hai lượt cùng N, cùng tier là so cặp: đổi một tham số thì khác biệt là do tham số đó.
- Windows: các script dùng multiprocessing (8 tiến trình) và có `if __name__ == "__main__"`.

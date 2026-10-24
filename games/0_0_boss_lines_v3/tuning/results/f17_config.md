# Boss Lines v3 – cấu hình f17

Nguồn: `tuning/overrides/f17.json` áp lên `game_config.py`. Bảng trọng số hiển thị dưới dạng **% của bảng**; số thô nằm trong file JSON.

## 0. Thay đổi so với f16

- **Boss 3** (cột 5–6): HP −5 ở chặng 1–3, −10 ở chặng 4–5 (`boss_hp_offset`).
- **Ô sáng**: bỏ hẳn sáng giảm dần (`lit_decay` = {}); Normal tắt hết ô sáng sau mỗi Treasure (`lit_reset_after_treasure_tiers`, event `litReset`).
- **Wild do Power Transform** trong Bonus chỉ 5% kích hoạt event (`power_wild_event_chance`); Heroic không đổi.
- **Normal**: vũ khí reel chặng 1 6 → 4, Wild chặng 1 1.5 → 2.0, xu 5–50x ×1.2, xu 100–1000x ×1.25, rương [83, 10, 6.7, 0.3] → [81, 11, 7.7, 0.3].
- **Super**: bảo đảm vũ khí 0.70 → 0.62, xu Treasure 2–20x ×0.7.
- **Treasure hunt**: Nam châm 0.5 → 1.5; Clover/Golden không ra ở vòng 1 và biến mất sau khi kích hoạt; Global và Scatter giảm từ vòng 2; Clover 2–4x; xu 25000x 0.006 → 0.004.
- **Heroic**: không còn Wild hiển thị; Wild kích hoạt cùng lúc (event `wildEvents`).
- **Event mới cho frontend**: `wildEvents`, `litReset`, `featureBigWin`.

## 1. Mục tiêu toán (optimizer)

| | Normal | Super | Epic |
|---|---|---|---|
| Mean (x bet) | 91 | 245 | 2045 |
| Max Win trong tier | 0.0108% | 0.0855% | 1% |
| Tần suất ở base | 1 / 350 | 1 / 2,815 | 1 / 14,990 |
| Tần suất ở ante | 1 / 70 | 1 / 563 | 1 / 2,998 |
| Free spins / chặng bắt đầu | 6 / chặng 1 | 7 / chặng 2 | 8 / chặng 3 |

| Feature | Heroic | Treasure hunt |
|---|---|---|
| Tỉ lệ chọn | 51.2% | 48.8% |
| Mean | 403 | 564 |
| Max Win | 0.1945% | 0.185% |
| Spin trả 0 | 30% | 0% |

Tier mix khi mua: **buy3** Normal 97.50%, Super 2.40%, Epic 0.10%; **buy4** Super 97.49%, Epic 2.51%; **random_bonus** Normal 59.99%, Super 27.00%, Epic 13.01%. Max Win = 25000x. RTP mọi mode 96.7%.

## 2. Luật và cờ (giá trị của ứng viên)

| Tham số | Giá trị |
|---|---|
| `arrow_k_choices` | [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6] |
| `arrow_last_hit_mult` | 1.5 |
| `bonus_min_weapons` | super: 1, epic: 1 |
| `bonus_min_weapons_chance` | super: 0.62 |
| `boss_drop_chance` | 0.002 |
| `boss_hp_offset` | **boss3**: 1: -5, 2: -5, 3: -5, 4: -10, 5: -10 |
| `feature_heroic_chance` | 0.512 |
| `heroic_dead_spin_chance` | 0.3 |
| `heroic_dead_symbol_tries` | 20 |
| `heroic_dead_wild_col_weights` | [3, 3, 3, 1, 1, 1] |
| `heroic_line_mult_weights` | 1: 45% · 2: 20% · 3: 15% · 5: 12% · 10: 8% |
| `last_hit_base` | 0 |
| `last_hit_scale` | 0.002 |
| `lit_decay` | {} |
| `lit_reset_after_treasure_tiers` | [bonus] |
| `lit_reset_each_spin_tiers` | [] |
| `lit_rule` | lines |
| `lit_steer` | {} |
| `power_wild_event_chance` | 0.05 |
| `tier_stage_min_coin` | **super**: 2: 0.2 |
| `weapon_factor_weights` | 1: 100% |
| `weapon_self_damage` | 3 |
| `wild_skin_chance` | 0.4 |
| `wild_skin_damage` | 3 |

Cờ mặc định liên quan (giữ nguyên game_config.py): `bonus_min_total_win` = epic: 600, `heroic_min_wild_or_weapon` = 5, `magnet_min_coins` = 2, `treasure_hunt_min_coin` = 1.

## 3. Bảng theo chế độ

Ô ghi *(chung)* = dùng giá trị chung (top-level) vì chế độ đó không có bảng riêng.

### `chest_gift_count_weights`

| Chế độ | Giá trị |
|---|---|
| Normal | **dong**: 1: 92% · 2: 6% · 3: 2%<br>**bac**: 2: 95% · 3: 5%<br>**vang**: 3: 100%<br>**kimcuong**: 3: 100% |
| Super | **dong**: 1: 80% · 2: 15% · 3: 5%<br>**bac**: 2: 40% · 3: 60%<br>**vang**: 2: 50% · 3: 50%<br>**kimcuong**: 2: 100% |
| Epic | **dong**: 1: 90% · 2: 10%<br>**bac**: 2: 95% · 3: 5%<br>**vang**: 2: 50% · 3: 50%<br>**kimcuong**: 2: 100% |
| Heroic | **dong**: 1: 80% · 2: 15% · 3: 5%<br>**bac**: 2: 85% · 3: 15%<br>**vang**: 3: 100%<br>**kimcuong**: 1: 75% · 2: 17% · 3: 8% |
| Treasure hunt | *(chung)* **dong**: 1: 60% · 2: 30% · 3: 10%<br>**bac**: 2: 70% · 3: 30%<br>**vang**: 3: 100%<br>**kimcuong**: 3: 100% |

### `chest_gift_power_chance`

| Chế độ | Giá trị |
|---|---|
| Normal | *(chung)* dong: 0.15, bac: 0.25, vang: 0.35, kimcuong: 0.45 |
| Super | *(chung)* dong: 0.15, bac: 0.25, vang: 0.35, kimcuong: 0.45 |
| Epic | dong: 0.1, bac: 0.2, vang: 0.45, kimcuong: 0.6 |
| Heroic | *(chung)* dong: 0.15, bac: 0.25, vang: 0.35, kimcuong: 0.45 |
| Treasure hunt | *(chung)* dong: 0.15, bac: 0.25, vang: 0.35, kimcuong: 0.45 |

### `chest_tier_step_weights`

| Chế độ | Giá trị |
|---|---|
| Normal | [81, 11, 7.7, 0.3] |
| Super | [95.75, 4, 0.25] |
| Epic | [99, 0.8, 0.2] |
| Heroic | *(chung)* [85, 12, 3] |
| Treasure hunt | *(chung)* [85, 12, 3] |

### `chest_upgrade_chance`

| Chế độ | Giá trị |
|---|---|
| Normal | 0.02 |
| Super | 0.02 |
| Epic | 0.005 |
| Heroic | *(chung)* 0.05 |
| Treasure hunt | *(chung)* 0.05 |

### `clover_factor_weights`

| Chế độ | Giá trị |
|---|---|
| Normal | 2: 70% · 3: 15% · 4: 8% · 5: 4% · 10: 2% · 20: 1% |
| Super | 2: 60% · 3: 25% · 4: 15% |
| Epic | 2: 70% · 3: 18% · 4: 8% · 5: 4% |
| Heroic | *(chung)* 2: 70% · 3: 15% · 4: 8% · 5: 4% · 10: 2% · 20: 1% |
| Treasure hunt | 2: 75% · 3: 20% · 4: 5% |

### `coin_value_weights`

| Chế độ | Giá trị |
|---|---|
| Normal | 0.2: 95.6% · 0.5: 2.39% · 1: 0.896% · 2: 0.179% · 3: 0.107% · 4: 0.0717% · 5: 0.168% · 6: 0.112% · 8: 0.0838% · 10: 0.0671% · 12: 0.0503% · 15: 0.0391% · 20: 0.11% · 25: 0.063% · 30: 0.0394% · 40: 0.0252% · 50: 0.0157% · 100: 0.0076% · 150: 0.0126% · 200: 0.0076% · 250: 0.0039% · 500: 0.0013% · 1000: 0.00045% · 25000: 4.8e-06% |
| Super | 0.2: 48.4% · 0.5: 11.2% · 1: 18.6% · 2: 6.51% · 3: 2.6% · 5: 5.21% · 6: 1.3% · 8: 1.04% · 10: 2.08% · 12: 1.04% · 15: 1.04% · 20: 1.04% · 25: 0.0056% · 30: 0.0037% · 40: 0.0022% · 50: 0.00074% · 100: 0.00041% · 150: 0.00016% · 200: 8.2e-05% · 250: 5.7e-05% · 500: 1.6e-05% · 1000: 5.7e-06% · 25000: 3e-06% |
| Epic | 1: 15% · 2: 1.5% · 3: 0.75% · 4: 0.5% · 5: 30% · 6: 0.75% · 8: 0.375% · 10: 20% · 12: 5% · 15: 12.5% · 20: 7.5% · 25: 2.5% · 30: 1.5% · 40: 1% · 50: 0.75% · 100: 0.3% · 150: 0.01% · 200: 0.005% · 250: 0.003% · 500: 0.001% · 1000: 0.0003% · 25000: 0.0068% |
| Heroic | 0.2: 35.2% · 0.5: 26.4% · 1: 22% · 2: 7.05% · 3: 3.52% · 4: 2.2% · 5: 1.32% · 6: 0.881% · 8: 0.529% · 10: 0.352% · 12: 0.22% · 15: 0.132% · 20: 0.0881% · 25: 0.0079% · 30: 0.004% · 40: 0.0018% · 50: 0.00079% · 100: 0.00021% · 150: 7.9e-05% · 200: 4e-05% · 250: 2.6e-05% · 500: 7.9e-06% · 1000: 2.6e-06% · 25000: 1.8e-07% |
| Treasure hunt | 0.2: 15.3% · 0.5: 11.5% · 1: 57.3% · 2: 5.35% · 3: 3.44% · 4: 2.29% · 5: 1.53% · 6: 1.15% · 8: 0.764% · 10: 0.535% · 12: 0.382% · 15: 0.229% · 20: 0.153% · 25: 0.0764% · 30: 0.0458% · 40: 0.0229% · 50: 0.0115% · 100: 0.0031% · 150: 0.0011% · 200: 0.00057% · 250: 0.00038% · 500: 0.00011% · 1000: 3.8e-05% · 25000: 0.0015% |

### `enhance_factor_weights`

| Chế độ | Giá trị |
|---|---|
| Normal | 2: 60% · 3: 25% · 4: 10% · 5: 4% · 10: 1% |
| Super | *(chung)* 2: 60% · 3: 25% · 4: 10% · 5: 4% · 10: 1% |
| Epic | 5: 20% · 10: 30% · 15: 25% · 20: 15% · 25: 10% |
| Heroic | *(chung)* 2: 60% · 3: 25% · 4: 10% · 5: 4% · 10: 1% |
| Treasure hunt | *(chung)* 2: 60% · 3: 25% · 4: 10% · 5: 4% · 10: 1% |

### `global_factor_weights`

| Chế độ | Giá trị |
|---|---|
| Normal | 2: 60% · 3: 30% · 4: 10% |
| Super | 2: 45% · 3: 30% · 4: 15% · 5: 10% |
| Epic | 2: 30% · 3: 30% · 4: 20% · 5: 15% · 10: 5% |
| Heroic | 2: 40% · 3: 40% · 5: 20% |
| Treasure hunt | 2: 50% · 3: 30% · 5: 20% |

### `golden_factor_weights`

| Chế độ | Giá trị |
|---|---|
| Normal | 2: 50% · 3: 30% · 4: 15% · 5: 5% |
| Super | 2: 45% · 3: 30% · 4: 15% · 5: 10% |
| Epic | 2: 30% · 3: 30% · 4: 20% · 5: 15% · 10: 5% |
| Heroic | *(chung)* 2: 80% · 3: 15% · 4: 4% · 5: 1% |
| Treasure hunt | 2: 50% · 3: 40% · 5: 10% |

### `guarantee_symbol_weights`

| Chế độ | Giá trị |
|---|---|
| Normal | *(chung)* W: 70% · AR: 10% · BM: 8% · SW: 8% · LT: 4% |
| Super | *(chung)* W: 70% · AR: 10% · BM: 8% · SW: 8% · LT: 4% |
| Epic | *(chung)* W: 70% · AR: 10% · BM: 8% · SW: 8% · LT: 4% |
| Heroic | W: 100% |
| Treasure hunt | *(chung)* W: 70% · AR: 10% · BM: 8% · SW: 8% · LT: 4% |

### `power_pick_weights`

| Chế độ | Giá trị |
|---|---|
| Normal | enhance: 33% · upgrade: 27% · transform: 22% · replace: 11% · destroy: 7% |
| Super | *(chung)* enhance: 30% · upgrade: 20% · transform: 25% · replace: 15% · destroy: 10% |
| Epic | enhance: 100% |
| Heroic | *(chung)* enhance: 30% · upgrade: 20% · transform: 25% · replace: 15% · destroy: 10% |
| Treasure hunt | *(chung)* enhance: 30% · upgrade: 20% · transform: 25% · replace: 15% · destroy: 10% |

### `star_value_weights`

| Chế độ | Giá trị |
|---|---|
| Normal | *(chung)* None |
| Super | 1: 50% · 2: 45% · 3: 5% |
| Epic | 10: 45% · 20: 45% · 50: 10% |
| Heroic | *(chung)* None |
| Treasure hunt | 5: 40% · 10: 40% · 20: 20% |

### `treasure_clover_vanishes`

| Chế độ | Giá trị |
|---|---|
| Normal | *(chung)* False |
| Super | *(chung)* False |
| Epic | *(chung)* False |
| Heroic | *(chung)* False |
| Treasure hunt | True |

### `treasure_kind_weights`

| Chế độ | Giá trị |
|---|---|
| Normal | coin: 95.4% · magnet: 0.415% · clover: 2.5% · golden: 0.155% · star: 0.259% · global: 0.28% · scatter: 1.04% |
| Super | coin: 93.1% · magnet: 0.658% · clover: 2.02% · golden: 0.405% · star: 2.53% · global: 0.303% · scatter: 1.01% |
| Epic | coin: 95.2% · magnet: 0.0971% · clover: 2.48% · golden: 0.35% · star: 0.68% · global: 0.243% · scatter: 0.971% |
| Heroic | coin: 97.8% · magnet: 0.2% · clover: 0.499% · global: 1.5% |
| Treasure hunt | coin: 91.6% · magnet: 1.66% · clover: 2.45% · golden: 0.441% · star: 0.772% · global: 1.32% · scatter: 1.77% |

### `treasure_round_kind_mult`

| Chế độ | Giá trị |
|---|---|
| Normal | *(chung)* {} |
| Super | *(chung)* {} |
| Epic | *(chung)* {} |
| Heroic | *(chung)* {} |
| Treasure hunt | clover: [0, 1], golden: [0, 1], scatter: [1, 0.4], global: [1, 0.15] |

### `wild_coin_min_value`

| Chế độ | Giá trị |
|---|---|
| Normal | 1 |
| Super | 5 |
| Epic | *(chung)* 0 |
| Heroic | *(chung)* 0 |
| Treasure hunt | *(chung)* 0 |

### `wild_coin_value_weights`

| Chế độ | Giá trị |
|---|---|
| Normal | *(chung)* None |
| Super | *(chung)* None |
| Epic | *(chung)* None |
| Heroic | 20: 44.8% · 25: 11.9% · 30: 11.9% · 40: 8.96% · 50: 8.96% · 75: 4.98% · 100: 3.98% · 150: 1.99% · 200: 1.19% · 250: 0.597% · 500: 0.498% · 1000: 0.149% |
| Treasure hunt | *(chung)* None |

### `wild_event_chance`

| Chế độ | Giá trị |
|---|---|
| Normal | 0.65 |
| Super | 0.6 |
| Epic | 1 |
| Heroic | *(chung)* 0.15 |
| Treasure hunt | *(chung)* 0.15 |

### `wild_event_weights`

| Chế độ | Giá trị |
|---|---|
| Normal | multiplier: 30% · coin: 30% · power: 40% |
| Super | multiplier: 45% · coin: 30% · power: 25% |
| Epic | multiplier: 40% · coin: 40% · power: 20% |
| Heroic | multiplier: 45% · coin: 35% · power: 20% |
| Treasure hunt | *(chung)* multiplier: 50% · coin: 35% · power: 15% |

### `wild_mult_weights`

| Chế độ | Giá trị |
|---|---|
| Normal | 2: 40% · 3: 40% · 4: 20% |
| Super | 2: 35% · 3: 35% · 4: 20% · 5: 10% |
| Epic | 2: 30% · 3: 25% · 4: 20% · 5: 15% · 10: 10% |
| Heroic | 2: 45% · 3: 30% · 4: 15% · 5: 8% · 10: 2% |
| Treasure hunt | *(chung)* 2: 70% · 3: 20% · 4: 7% · 5: 3% |

## 4. Reel (gen_reels specs)

| Reel | Wild | Vũ khí | Scatter | Shape |
|---|---|---|---|---|
| BON_S1 | 2 | 4 | – | L1 40, L2 40, L3 40, L4 40, H1 24, H2 23, H3 21, H4 19, H5 16 |
| BON_S2 | 1.8 | 0.1 | – | mặc định |
| BON_S3 | 1.2 | 0.05 | – | mặc định |
| BON_S4 | 0.8 | 0 | – | mặc định |
| BON_S5 | 0.8 | 0 | – | mặc định |
| BON_E | 0.8 | 0 | – | mặc định |
| BR0 | 2 | 0.6 | 0.9 | L1 50, L2 48, L3 46, L4 44, H1 22, H2 17, H3 12, H4 8, H5 5 |
| ANTE | 2 | 0.6 | 2 | L1 50, L2 48, L3 46, L4 44, H1 22, H2 17, H3 12, H4 8, H5 5 |
| HERO | 1.5 | 0 | – | mặc định |
| EPI_S3 | 2 | 0 | – | L1 30, L2 30, L3 30, L4 30, H1 28, H2 26, H3 24, H4 22, H5 20 |
| EPI_S4 | 1.6 | 0 | – | L1 30, L2 30, L3 30, L4 30, H1 28, H2 26, H3 24, H4 22, H5 20 |
| EPI_S5 | 1.6 | 0 | – | L1 30, L2 30, L3 30, L4 30, H1 28, H2 26, H3 24, H4 22, H5 20 |
| EPI_E | 1.6 | 0 | – | L1 30, L2 30, L3 30, L4 30, H1 28, H2 26, H3 24, H4 22, H5 20 |
| SUP_S2 | 1.8 | 0.1 | – | mặc định |
| SUP_S3 | 1.2 | 0.05 | – | mặc định |
| SUP_S4 | 0.3 | 0 | – | mặc định |
| SUP_S5 | 0.3 | 0 | – | mặc định |
| SUP_E | 0.3 | 0 | – | mặc định |

Reel theo chặng: **Super** 2→SUP_S2, 3→SUP_S3, 4→SUP_S4, 5→SUP_S5, 6→SUP_E; **Epic** 3→EPI_S3, 4→EPI_S4, 5→EPI_S5, 6→EPI_E

## 5. Số cố định (proposal)

| Chặng | HP | HP boss 3 |
|---|---|---|
| 0 | 25–25 | 25–25 |
| 1 | 30–40 | 25–35 |
| 2 | 35–50 | 30–45 |
| 3 | 45–65 | 40–60 |
| 4 | 65–90 | 55–80 |
| 5 | 85–120 | 75–110 |
| 6 | 350–400 | 350–400 |

Sát thương mỗi ô bị phá: L1 1, L2 1, L3 1, L4 1, H1 2, H2 2, H3 2, H4 2, H5 3, W 3.

## 6. Kết quả sau optimizer

```
base          RTP 96.7000%  0x 71.10%  MaxWin 1 in 1,273,235
   bonus_tier=bonus: share 0.2857% (1 in 350.0), mean 91.00
   bonus_tier=super: share 0.0355% (1 in 2,815.0), mean 245.00
   bonus_tier=epic: share 0.0067% (1 in 14,990.0), mean 2,045.00
   maxwin_tier=epic: share 0.0001% (1 in 1,499,000.0), mean 25,000.00
   maxwin_tier=super: share 0.0000% (1 in 280,393,638.7), mean 25,000.00
ante          RTP 96.7000%  0x 69.79%  MaxWin 1 in 286,469
   bonus_tier=bonus: share 1.4286% (1 in 70.0), mean 91.00
   bonus_tier=super: share 0.1776% (1 in 563.0), mean 245.00
   bonus_tier=epic: share 0.0334% (1 in 2,998.0), mean 2,045.00
   maxwin_tier=epic: share 0.0003% (1 in 299,800.0), mean 25,000.00
   maxwin_tier=super: share 0.0000% (1 in 23,197,322.9), mean 25,000.00
feature       RTP 96.7000%  0x 15.36%  MaxWin 1 in 527
   feature=heroic: share 51.2000% (1 in 2.0), mean 403.00
   feature=treasure_hunt: share 48.8000% (1 in 2.0), mean 567.96
   bonus_tier=bonus: share 0.6837% (1 in 146.3), mean 259.85
   bonus_tier=super: share 0.1952% (1 in 512.3), mean 720.01
   maxwin_feature=heroic: share 0.0996% (1 in 1,004.2), mean 25,000.00
   maxwin_feature=treasure_hunt: share 0.0903% (1 in 1,107.7), mean 25,000.00
buy3          RTP 96.7000%  0x 0.07%  MaxWin 1 in 7,948
   bonus_tier=bonus: share 97.4974% (1 in 1.0), mean 91.00
   bonus_tier=super: share 2.4001% (1 in 41.7), mean 245.00
   maxwin_tier=super: share 0.0021% (1 in 48,731.8), mean 25,000.00
   bonus_tier=epic: share 0.1026% (1 in 975.0), mean 2,045.00
   maxwin_tier=bonus: share 0.0105% (1 in 9,496.7), mean 25,000.00
buy4          RTP 96.7000%  0x 0.01%  MaxWin 1 in 922
   bonus_tier=super: share 97.4944% (1 in 1.0), mean 245.00
   bonus_tier=epic: share 2.5056% (1 in 39.9), mean 2,045.00
   maxwin_tier=epic: share 0.0251% (1 in 3,991.0), mean 25,000.00
   maxwin_tier=super: share 0.0834% (1 in 1,199.6), mean 25,000.00
random_bonus  RTP 96.7000%  0x 0.02%  MaxWin 1 in 626
   bonus_tier=super: share 26.9998% (1 in 3.7), mean 245.00
   bonus_tier=epic: share 13.0102% (1 in 7.7), mean 2,045.00
   bonus_tier=bonus: share 59.9899% (1 in 1.7), mean 91.00
   maxwin_tier=epic: share 0.1301% (1 in 768.6), mean 25,000.00
   maxwin_tier=super: share 0.0231% (1 in 4,331.8), mean 25,000.00
   maxwin_tier=bonus: share 0.0065% (1 in 15,434.7), mean 25,000.00
RTP of N random rounds, median of 100 repeats (p10, p90, p99)
base                     N=5:   13.0% (p10   0.0, p90   49.0, p99 4234.0)  N=20:   18.5% (p10   6.8, p90  188.8, p99 1637.7)  N=100:   44.0% (p10  13.6, p90  134.7, p99  959.5)  N=1000:   87.6% (p10  55.1, p90  148.2, p99  254.4)
ante                     N=5:    5.3% (p10   0.0, p90  164.0, p99 1726.7)  N=20:   11.2% (p10   3.2, p90  358.8, p99 4032.8)  N=100:   78.3% (p10  17.8, p90  187.4, p99  859.5)  N=1000:   79.9% (p10  53.5, p90  133.8, p99  891.1)
feature                  N=5:   76.8% (p10  31.8, p90  156.4, p99  266.6)  N=20:   84.4% (p10  54.2, p90  121.4, p99  292.8)  N=100:   90.2% (p10  74.5, p90  134.1, p99  235.9)  N=1000:   94.7% (p10  86.7, p90  106.4, p99  114.9)
  feature:heroic         N=5:   67.4% (p10  26.7, p90  156.9, p99  353.9)  N=20:   80.7% (p10  54.2, p90  128.0, p99  419.2)  N=100:   87.7% (p10  72.3, p90  148.1, p99  194.6)  N=1000:   96.5% (p10  87.2, p90  108.6, p99  116.3)
  feature:treasure_hunt  N=5:   76.4% (p10  32.3, p90  142.6, p99  183.0)  N=20:   87.8% (p10  64.3, p90  138.6, p99  303.5)  N=100:   92.0% (p10  76.5, p90  130.7, p99  207.6)  N=1000:   96.0% (p10  89.4, p90  106.2, p99  118.8)
buy3                     N=5:   69.7% (p10  28.2, p90  224.9, p99  589.9)  N=20:   87.0% (p10  56.6, p90  133.8, p99 1336.5)  N=100:   88.5% (p10  73.0, p90  119.1, p99  318.9)  N=1000:   94.2% (p10  87.9, p90  116.3, p99  146.5)
  buy3:bonus             N=5:   81.4% (p10  28.9, p90  174.3, p99  547.4)  N=20:   85.0% (p10  52.1, p90  140.5, p99  181.4)  N=100:   93.8% (p10  75.7, p90  113.3, p99  362.8)  N=1000:   94.4% (p10  88.7, p90  102.2, p99  127.2)
  buy3:super             N=5:   71.1% (p10  44.9, p90  128.3, p99 2017.0)  N=20:   77.1% (p10  64.3, p90  128.4, p99  563.6)  N=100:   85.7% (p10  69.0, p90  143.0, p99  224.0)  N=1000:   95.6% (p10  84.4, p90  114.4, p99  137.2)
  buy3:epic              N=5:   93.3% (p10  67.6, p90  116.9, p99  169.0)  N=20:   94.7% (p10  82.6, p90  110.7, p99  126.0)  N=100:   96.0% (p10  89.9, p90  102.6, p99  107.6)  N=1000:   96.8% (p10  94.8, p90   98.8, p99  100.3)
buy4                     N=5:   71.1% (p10  31.5, p90  158.2, p99  317.7)  N=20:   85.6% (p10  53.0, p90  140.6, p99  494.5)  N=100:   90.5% (p10  76.4, p90  151.3, p99  187.6)  N=1000:   96.0% (p10  85.3, p90  112.2, p99  121.5)
  buy4:super             N=5:   83.2% (p10  46.6, p90  175.9, p99  915.7)  N=20:   85.0% (p10  61.1, p90  130.7, p99  601.8)  N=100:   86.4% (p10  77.1, p90  139.6, p99  294.1)  N=1000:   93.2% (p10  85.5, p90  110.4, p99  141.1)
  buy4:epic              N=5:   82.7% (p10  59.6, p90  148.3, p99  335.5)  N=20:   89.2% (p10  74.1, p90  133.7, p99  202.5)  N=100:   95.8% (p10  82.9, p90  115.2, p99  137.4)  N=1000:   96.6% (p10  92.4, p90  101.5, p99  104.0)
random_bonus             N=5:   53.3% (p10  14.1, p90  186.3, p99  356.7)  N=20:   76.5% (p10  34.6, p90  138.6, p99  420.7)  N=100:   94.5% (p10  65.9, p90  158.2, p99  209.5)  N=1000:   95.8% (p10  83.9, p90  109.7, p99  119.4)
  random_bonus:super     N=5:   75.3% (p10  40.9, p90  146.5, p99  227.5)  N=20:   87.5% (p10  64.1, p90  133.2, p99  563.0)  N=100:   86.6% (p10  74.4, p90  113.1, p99  200.8)  N=1000:   97.8% (p10  87.4, p90  108.9, p99  143.8)
  random_bonus:epic      N=5:   84.2% (p10  60.0, p90  137.7, p99  324.2)  N=20:   87.7% (p10  73.5, p90  138.8, p99  199.8)  N=100:   93.8% (p10  81.5, p90  115.7, p99  143.3)  N=1000:   97.4% (p10  93.0, p90  103.8, p99  107.6)
  random_bonus:bonus     N=5:   87.7% (p10  49.5, p90  168.9, p99 5366.3)  N=20:   85.5% (p10  65.6, p90  129.4, p99  200.2)  N=100:   94.7% (p10  79.1, p90  113.3, p99  374.1)  N=1000:   94.8% (p10  89.3, p90  117.9, p99  127.9)
```


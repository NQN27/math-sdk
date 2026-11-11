# Boss Lines v3 – cấu hình LH8

Nguồn: `tuning/overrides/LH8.json` áp lên `game_config.py`. Bảng trọng số hiển thị dưới dạng **% của bảng**; số thô nằm trong file JSON.

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
| `action_order` | doc |
| `arrow_rule` | table |
| `bonus_min_total_win` | epic: 600 |
| `bonus_min_weapons_chance` | {} |
| `boss_drop_chance` | 0 |
| `boss_hp_offset` | {} |
| `chest_bags` | True |
| `chest_coin_min` | stage |
| `chest_display_names` | dong: green, bac: blue, vang: purple, do: red |
| `chest_order` | [dong, bac, vang] |
| `chest_power_immediate` | True |
| `chest_power_new_only` | True |
| `chest_rule` | v4 |
| `chest_sure_coin_tiers` | [] |
| `coin_excluded_values` | [6] |
| `power_reserve_cap` | 1 |
| `shuffle_rule` | doc |
| `stage_chest_weights` | **bonus**: **1**: dong: 92.2% · bac: 6.01% · vang: 1.8%<br>**2**: dong: 92.2% · bac: 6.01% · vang: 1.8% |
| `stage_coin_value_weights` | **bonus**: **1**: 0.2: 36.9% · 0.5: 26.9% · 1: 12.6% · 2: 6.66% · 3: 4.28% · 4: 3.12% · 5: 2.17% · 6: 1.78% · 8: 1.3% · 10: 1.02% · 12: 0.833% · 15: 0.652% · 20: 0.477% · 25: 0.373% · 30: 0.306% · 40: 0.224% · 50: 0.175% · 100: 0.0822% · 150: 0.0528% · 200: 0.0385% · 250: 0.0302% · 500: 0.0142% · 1000: 0.0066% · 25000: 4.1e-06%<br>**2**: 0.5: 42.2% · 1: 15.4% · 2: 9.78% · 3: 6.99% · 4: 5.5% · 5: 4.05% · 6: 3.48% · 8: 2.74% · 10: 2.28% · 12: 1.96% · 15: 1.63% · 20: 0.897% · 25: 0.746% · 30: 0.641% · 40: 0.505% · 50: 0.419% · 100: 0.236% · 150: 0.169% · 200: 0.133% · 250: 0.11% · 500: 0.0621% · 1000: 0.0349% · 25000: 6.7e-06%<br>**3**: 1: 49.3% · 2: 11.4% · 3: 8.44% · 4: 6.81% · 5: 5.11% · 6: 4.46% · 8: 3.6% · 10: 3.05% · 12: 2.66% · 15: 2.26% · 20: 0.663% · 25: 0.562% · 30: 0.491% · 40: 0.396% · 50: 0.336% · 100: 0.12% · 150: 0.089% · 200: 0.0719% · 250: 0.0609% · 500: 0.0364% · 1000: 0.0217% · 25000: 3.2e-06%<br>**4**: 5: 17.8% · 6: 16.3% · 8: 14.1% · 10: 12.6% · 12: 11.5% · 15: 10.3% · 20: 4.16% · 25: 3.66% · 30: 3.3% · 40: 2.8% · 50: 2.19% · 100: 0.413% · 150: 0.328% · 200: 0.279% · 250: 0.246% · 500: 0.0411% · 1000: 0.0205% · 25000: 0.00075%<br>**5**: 20: 24.4% · 25: 21.8% · 30: 19.9% · 40: 17.2% · 50: 11.6% · 100: 2.72% · 150: 1.11% · 200: 0.585% · 250: 0.357% · 500: 0.188% · 1000: 0.0939% · 25000: 0.0033%<br>**super**: **2**: 0.5: 42.5% · 1: 23.4% · 2: 10.1% · 3: 6.17% · 4: 4.36% · 5: 3.33% · 6: 2.67% · 8: 1.88% · 10: 1.44% · 12: 1.15% · 15: 0.879% · 20: 0.621% · 25: 0.474% · 30: 0.38% · 40: 0.268% · 50: 0.205% · 100: 0.0884% · 150: 0.0541% · 200: 0.0382% · 250: 0.0291% · 500: 0.0126% · 1000: 0.0054% · 25000: 6.7e-06%<br>**3**: 1: 47.5% · 2: 11.9% · 3: 8.23% · 4: 6.34% · 5: 5.17% · 6: 4.38% · 8: 3.37% · 10: 2.75% · 12: 2.33% · 15: 1.9% · 20: 1.47% · 25: 1.2% · 30: 1.01% · 40: 0.78% · 50: 0.637% · 100: 0.339% · 150: 0.234% · 200: 0.18% · 250: 0.147% · 500: 0.0784% · 1000: 0.0417% · 25000: 2.8e-06%<br>**4**: 5: 20.9% · 6: 19.1% · 8: 16.6% · 10: 14.8% · 12: 13.5% · 15: 12.1% · 20: 2.79% · 25: 0.191% · 30: 0.0215% · 40: 0.00068% · 50: 4.7e-05% · 100: 1e-08% · 25000: 0.00059%<br>**5**: 20: 24.4% · 25: 21.9% · 30: 20% · 40: 17.3% · 50: 15.5% · 100: 0.968% · 150: 0.0288% · 200: 0.0024% · 250: 0.00034% · 500: 8.4e-07% · 25000: 0.0017% |
| `stage_hp_range` | 0: [10, 20], 1: [15, 25], 2: [25, 40], 3: [40, 55], 4: [55, 75], 5: [75, 100], 6: [75, 100] |
| `stage_min_chest` | 0: dong, 1: dong, 2: dong, 3: bac, 4: vang, 5: vang, 6: vang |
| `stage_min_chest_count` | 1: 1, 2: 1, 3: 1, 4: 1, 5: 3, 6: 3 |
| `stage_min_coin` | 0: 0.2, 1: 0.2, 2: 0.5, 3: 1, 4: 5, 5: 20, 6: 20 |
| `symbol_damage` | L1: 1, L2: 1, L3: 1, L4: 1, H1: 2, H2: 2, H3: 3, H4: 3, H5: 4, W: 5 |
| `tier_hp_tilt` | super: 1, epic: 1 |
| `tier_stage_min_coin` | {} |
| `transform_skips_weapons` | False |
| `tumble_combine` | add |
| `tumble_multi` | True |
| `weapon_self_damage` | 5 |
| `wild_flash_needs_room` | True |
| `wild_skin_damage` | 5 |

Cờ mặc định liên quan (giữ nguyên game_config.py): `bonus_min_total_win` = epic: 600, `heroic_min_wild_or_weapon` = 5, `magnet_min_coins` = 2, `treasure_hunt_min_coin` = 1.

## 3. Bảng theo chế độ

Ô ghi *(chung)* = dùng giá trị chung (top-level) vì chế độ đó không có bảng riêng.

### `chain_block`

| Chế độ | Giá trị |
|---|---|
| Normal | 4: [2, 0.6], 5: [2, 0.6], 6: [2, 0.6], 3: [2, 0.5], 1: [2, 0.3] |
| Super | *(chung)* {} |
| Epic | *(chung)* {} |
| Heroic | *(chung)* {} |
| Treasure hunt | *(chung)* {} |

### `chest_bag_value_weights`

| Chế độ | Giá trị |
|---|---|
| Normal | 1: 50% · 2: 18.7% · 3: 9.94% · 4: 6.34% · 5: 4.48% · 6: 3.37% · 8: 2.15% · 10: 1.52% · 12: 1.14% · 15: 0.807% · 20: 0.516% · 25: 0.364% · 30: 0.274% · 40: 0.175% · 50: 0.123% · 100: 0.0419% · 150: 0.0223% · 200: 0.0142% · 250: 0.01% · 500: 0.0034% · 1000: 0.0012% · 25000: 0.0001% |
| Super | *(chung)* – |
| Epic | *(chung)* – |
| Heroic | *(chung)* – |
| Treasure hunt | *(chung)* – |

### `chest_gift_count_weights`

| Chế độ | Giá trị |
|---|---|
| Normal | **dong**: 1: 100%<br>**bac**: 2: 100%<br>**vang**: 3: 100%<br>**kimcuong**: 3: 100% |
| Super | **dong**: 1: 100%<br>**bac**: 2: 100%<br>**vang**: 3: 100%<br>**kimcuong**: 3: 100% |
| Epic | **dong**: 1: 100%<br>**bac**: 2: 100%<br>**vang**: 3: 100%<br>**kimcuong**: 3: 100% |
| Heroic | **dong**: 1: 100%<br>**bac**: 2: 100%<br>**vang**: 3: 100%<br>**kimcuong**: 3: 100% |
| Treasure hunt | *(chung)* **dong**: 1: 100%<br>**bac**: 2: 100%<br>**vang**: 3: 100%<br>**kimcuong**: 3: 100% |

### `chest_gift_multi_chance`

| Chế độ | Giá trị |
|---|---|
| Normal | dong: 0.0563524, bac: 0.0751366, vang: 0.0699696, do: 0.0932929 |
| Super | dong: 0.1, bac: 0.15, vang: 0.2, do: 0.2 |
| Epic | dong: 0.1, bac: 0.15, vang: 0.2, do: 0.2 |
| Heroic | dong: 0.1, bac: 0.15, vang: 0.2, do: 0.2 |
| Treasure hunt | *(chung)* {} |

### `chest_gift_power_chance`

| Chế độ | Giá trị |
|---|---|
| Normal | dong: 0.18, bac: 0.3, vang: 0.4, kimcuong: 0.45, do: 0.4 |
| Super | *(chung)* dong: 0.15, bac: 0.25, vang: 0.35, kimcuong: 0.45, do: 0.35 |
| Epic | dong: 0.1, bac: 0.2, vang: 0.45, kimcuong: 0.6, do: 0.45 |
| Heroic | *(chung)* dong: 0.15, bac: 0.25, vang: 0.35, kimcuong: 0.45, do: 0.35 |
| Treasure hunt | *(chung)* dong: 0.15, bac: 0.25, vang: 0.35, kimcuong: 0.45, do: 0.35 |

### `chest_multi_weights`

| Chế độ | Giá trị |
|---|---|
| Normal | 2: 58.3% · 3: 28.2% · 4: 8.47% · 5: 3.33% · 10: 1.67% |
| Super | *(chung)* 2: 50% · 3: 25% · 4: 12% · 5: 9% · 10: 4% |
| Epic | *(chung)* 2: 50% · 3: 25% · 4: 12% · 5: 9% · 10: 4% |
| Heroic | *(chung)* 2: 50% · 3: 25% · 4: 12% · 5: 9% · 10: 4% |
| Treasure hunt | *(chung)* 2: 50% · 3: 25% · 4: 12% · 5: 9% · 10: 4% |

### `chest_tier_bags`

| Chế độ | Giá trị |
|---|---|
| Normal | **dong**: 1: 30.8166, 2: 34.7577, 3: 30.3571, 4: 23.3738<br>**bac**: 5: 30.8166, 8: 29.8405, 10: 27.5463, 12: 21.2724, 15: 15.17<br>**vang**: 20: 35.8216, 25: 14.9159, 30: 8.22428, 40: 3.19996, 50: 1.41144<br>**do**: 100: 47.7621, 150: 20.0224, 200: 10.7158, 250: 6.53775, 500: 3.4747, 1000: 1.00096, 25000: 0.01 |
| Super | *(chung)* **dong**: 1: 40, 2: 30, 3: 18, 4: 12<br>**bac**: 5: 35, 8: 25, 10: 18, 12: 12, 15: 10<br>**vang**: 20: 35, 25: 25, 30: 18, 40: 12, 50: 10<br>**do**: 100: 40, 150: 25, 200: 15, 250: 10, 500: 7, 1000: 3, 25000: 0.01 |
| Epic | *(chung)* **dong**: 1: 40, 2: 30, 3: 18, 4: 12<br>**bac**: 5: 35, 8: 25, 10: 18, 12: 12, 15: 10<br>**vang**: 20: 35, 25: 25, 30: 18, 40: 12, 50: 10<br>**do**: 100: 40, 150: 25, 200: 15, 250: 10, 500: 7, 1000: 3, 25000: 0.01 |
| Heroic | *(chung)* **dong**: 1: 40, 2: 30, 3: 18, 4: 12<br>**bac**: 5: 35, 8: 25, 10: 18, 12: 12, 15: 10<br>**vang**: 20: 35, 25: 25, 30: 18, 40: 12, 50: 10<br>**do**: 100: 40, 150: 25, 200: 15, 250: 10, 500: 7, 1000: 3, 25000: 0.01 |
| Treasure hunt | *(chung)* **dong**: 1: 40, 2: 30, 3: 18, 4: 12<br>**bac**: 5: 35, 8: 25, 10: 18, 12: 12, 15: 10<br>**vang**: 20: 35, 25: 25, 30: 18, 40: 12, 50: 10<br>**do**: 100: 40, 150: 25, 200: 15, 250: 10, 500: 7, 1000: 3, 25000: 0.01 |

### `chest_tier_step_weights`

| Chế độ | Giá trị |
|---|---|
| Normal | [88, 8, 3.8, 0.2] |
| Super | [97, 2.6, 0.4] |
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

### `chest_upgrade_tier_weights`

| Chế độ | Giá trị |
|---|---|
| Normal | bac: 66.7% · vang: 33.3% |
| Super | bac: 66.7% · vang: 33.3% |
| Epic | *(chung)* – |
| Heroic | *(chung)* – |
| Treasure hunt | *(chung)* – |

### `clover_factor_weights`

| Chế độ | Giá trị |
|---|---|
| Normal | 2: 70.2% · 3: 15.1% · 4: 8.03% · 5: 4.01% · 10: 1.78% · 20: 0.888% |
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

### `destroy_weight_by_alive`

| Chế độ | Giá trị |
|---|---|
| Normal | 3: 1.6, 2: 1.2, 1: 0.7, 0: 0.3 |
| Super | *(chung)* {} |
| Epic | *(chung)* {} |
| Heroic | *(chung)* {} |
| Treasure hunt | *(chung)* {} |

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
| Super | 2: 55% · 3: 30% · 4: 12% · 5: 3% |
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
| Super | AR: 70% · BM: 10% · SW: 10% · LT: 10% |
| Epic | AR: 40% · BM: 20% · SW: 20% · LT: 20% |
| Heroic | W: 100% |
| Treasure hunt | *(chung)* W: 70% · AR: 10% · BM: 8% · SW: 8% · LT: 4% |

### `hp_cut_weights`

| Chế độ | Giá trị |
|---|---|
| Normal | 0: 100% |
| Super | 0: 70% · 5: 20% · 10: 10% |
| Epic | 0: 50% · 5: 25% · 10: 25% |
| Heroic | 0: 10% · 5: 20% · 10: 70% |
| Treasure hunt | *(chung)* 0: 100% |

### `last_hit_base`

| Chế độ | Giá trị |
|---|---|
| Normal | 0.005 |
| Super | *(chung)* 0 |
| Epic | *(chung)* 0 |
| Heroic | *(chung)* 0 |
| Treasure hunt | *(chung)* 0 |

### `last_hit_scale`

| Chế độ | Giá trị |
|---|---|
| Normal | 0.03 |
| Super | *(chung)* 0.002 |
| Epic | *(chung)* 0.002 |
| Heroic | *(chung)* 0.002 |
| Treasure hunt | *(chung)* 0.002 |

### `lit_wild_lines_only`

| Chế độ | Giá trị |
|---|---|
| Normal | cells |
| Super | cells |
| Epic | *(chung)* cells |
| Heroic | *(chung)* cells |
| Treasure hunt | *(chung)* cells |

### `power_pick_weights`

| Chế độ | Giá trị |
|---|---|
| Normal | shuffle: 10% · upgrade: 25.4% · transform: 25.4% · replace: 19.6% · destroy: 19.6% |
| Super | *(chung)* shuffle: 30% · upgrade: 20% · transform: 25% · replace: 15% · destroy: 10% |
| Epic | shuffle: 100% |
| Heroic | *(chung)* shuffle: 30% · upgrade: 20% · transform: 25% · replace: 15% · destroy: 10% |
| Treasure hunt | *(chung)* shuffle: 30% · upgrade: 20% · transform: 25% · replace: 15% · destroy: 10% |

### `shuffle_mult_weights`

| Chế độ | Giá trị |
|---|---|
| Normal | 2: 60% · 3: 25% · 4: 8% · 5: 5% · 10: 2% |
| Super | *(chung)* 2: 40% · 3: 25% · 4: 15% · 5: 12% · 10: 8% |
| Epic | *(chung)* 2: 40% · 3: 25% · 4: 15% · 5: 12% · 10: 8% |
| Heroic | *(chung)* 2: 40% · 3: 25% · 4: 15% · 5: 12% · 10: 8% |
| Treasure hunt | *(chung)* 2: 40% · 3: 25% · 4: 15% · 5: 12% · 10: 8% |

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
| Normal | coin: 95.9% · magnet: 0.73% · clover: 2.19% · golden: 0.156% · scatter: 1.04% |
| Super | coin: 96.1% · magnet: 0.679% · clover: 2.09% · golden: 0.119% · scatter: 1.04% |
| Epic | coin: 96.1% · magnet: 0.098% · clover: 2.5% · golden: 0.353% · scatter: 0.98% |
| Heroic | coin: 99.3% · magnet: 0.203% · clover: 0.507% |
| Treasure hunt | coin: 93.6% · magnet: 1.69% · clover: 2.5% · golden: 0.451% · scatter: 1.8% |

### `treasure_round_kind_mult`

| Chế độ | Giá trị |
|---|---|
| Normal | *(chung)* {} |
| Super | *(chung)* {} |
| Epic | *(chung)* {} |
| Heroic | *(chung)* {} |
| Treasure hunt | clover: [0, 1], golden: [0, 1], scatter: [1, 0.4], global: [1, 0.15] |

### `tumble_reset_scope`

| Chế độ | Giá trị |
|---|---|
| Normal | spin |
| Super | stage |
| Epic | bonus |
| Heroic | *(chung)* spin |
| Treasure hunt | *(chung)* spin |

### `weapon_lit_bias`

| Chế độ | Giá trị |
|---|---|
| Normal | 0.6 |
| Super | *(chung)* 0 |
| Epic | *(chung)* 0 |
| Heroic | *(chung)* 0 |
| Treasure hunt | *(chung)* 0 |

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

### `wild_flash_chance`

| Chế độ | Giá trị |
|---|---|
| Normal | 0.04 |
| Super | 0.08 |
| Epic | 0.1 |
| Heroic | 0.1 |
| Treasure hunt | *(chung)* 0.05 |

### `wild_lit_bias`

| Chế độ | Giá trị |
|---|---|
| Normal | 1 |
| Super | *(chung)* 0 |
| Epic | *(chung)* 0 |
| Heroic | *(chung)* 0 |
| Treasure hunt | *(chung)* 0 |

### `wild_mult_weights`

| Chế độ | Giá trị |
|---|---|
| Normal | 2: 40% · 3: 40% · 4: 20% |
| Super | 2: 35% · 3: 35% · 4: 20% · 5: 10% |
| Epic | 2: 30% · 3: 25% · 4: 20% · 5: 15% · 10: 10% |
| Heroic | 2: 45% · 3: 30% · 4: 15% · 5: 8% · 10: 2% |
| Treasure hunt | *(chung)* 2: 70% · 3: 20% · 4: 7% · 5: 3% |

### `wild_multi_weights`

| Chế độ | Giá trị |
|---|---|
| Normal | 1: 65.5% · 2: 17.2% · 3: 10.1% · 4: 4.21% · 5: 2.53% · 10: 0.476% |
| Super | 1: 60% · 2: 18% · 3: 12% · 4: 6% · 5: 4% |
| Epic | 1: 40% · 2: 25% · 3: 15% · 4: 10% · 5: 6% · 10: 4% |
| Heroic | 2: 90% · 3: 10% |
| Treasure hunt | *(chung)* 1: 90% · 2: 6% · 3: 3% · 5: 1% |

### `wild_power_drop_chance`

| Chế độ | Giá trị |
|---|---|
| Normal | 0 |
| Super | 0 |
| Epic | 0 |
| Heroic | 0 |
| Treasure hunt | *(chung)* 0 |

### `wild_skin_chance`

| Chế độ | Giá trị |
|---|---|
| Normal | 0.2 |
| Super | 0.2 |
| Epic | *(chung)* 0.4 |
| Heroic | *(chung)* 0.4 |
| Treasure hunt | *(chung)* 0.4 |

### `wild_skin_lit_bias`

| Chế độ | Giá trị |
|---|---|
| Normal | 1 |
| Super | *(chung)* 0 |
| Epic | *(chung)* 0 |
| Heroic | *(chung)* 0 |
| Treasure hunt | *(chung)* 0 |

## 4. Reel (gen_reels specs)

| Reel | Wild | Vũ khí | Scatter | Shape |
|---|---|---|---|---|
| BON_S1 | 1.7 | 1.9 | – | mặc định |
| BON_S2 | – | 3.3 | – | mặc định |
| BON_S3 | 1 | 4 | – | mặc định |
| BON_S4 | 0.4 | 4.3 | – | mặc định |
| BON_S5 | 0.4 | 4.3 | – | mặc định |

Reel theo chặng: **Super** 2→SUP_S2, 3→SUP_S3, 4→SUP_S4, 5→SUP_S5, 6→SUP_E; **Epic** 3→EPI_S3, 4→EPI_S4, 5→EPI_S5, 6→EPI_E

## 5. Số cố định (proposal)

| Chặng | HP | HP boss 3 |
|---|---|---|
| 0 | 10–20 | 10–20 |
| 1 | 15–25 | 15–25 |
| 2 | 25–40 | 25–40 |
| 3 | 40–55 | 40–55 |
| 4 | 55–75 | 55–75 |
| 5 | 75–100 | 75–100 |
| 6 | 75–100 | 75–100 |

HP trên là trước khi cắt: mỗi boss chặng 1-5 bị trừ thêm một lượng rút theo `hp_cut_weights` (mục 3).

Sát thương mỗi ô bị phá: L1 1, L2 1, L3 1, L4 1, H1 2, H2 2, H3 3, H4 3, H5 4, W 5.

## 6. Kết quả sau optimizer

```
fLH7        90.5  0.90    0     0.3     2.3     4.1     8.6    17.2    26.2    39.1    75.8    98.6   131.2   194.9   344.9   636.1  1029.7  1489.8  3557.2  93/96
fLH8        90.3  0.90    0     0.3     2.5     4.2     8.8    17.7    26.8    39.9    77.0   100.2   133.7   197.1   345.6   630.8  1025.8  1432.9  3211.9  93/96
fLH7 off: p5:-23% p99:+37% p99.5:+24%
fLH8 off: p5:-18% p99:+37% p99.5:+19%
fLH7: mean 90.5 MW 0 | wildev/spin 0.142 wildev/sess 1.00 | lines/sess 28.1 | src% lines 31 wildcoin 0 chest 42 treasure 27 | treasure paid 27 | chests/sess {'green': 2.88, 'blue': 0.71, 'purple': 0.07, 'red': 0.01}
fLH8: mean 90.3 MW 0 | wildev/spin 0.142 wildev/sess 1.00 | lines/sess 28.1 | src% lines 31 wildcoin 0 chest 42 treasure 27 | treasure paid 27 | chests/sess {'green': 2.88, 'blue': 0.71, 'purple': 0.07, 'red': 0.01}
fLH7 pass [49.65, 15.57, 3.95, 0.85, 0.23] {'lines': 28.1, 'chest': 37.9, 'treasure': 24.5}
fLH8 pass [49.65, 15.57, 3.95, 0.85, 0.23] {'lines': 28.1, 'chest': 38.2, 'treasure': 24.0}

[exited with code 0]
```


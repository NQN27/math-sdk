# Feature mode (cost 500) - chosen versions 2026-11-19 (not baked yet)
- Heroic = HR30 (tuning/overrides/HR30.json): mean 426.6 with 35% zero share, MaxWin 0.256% of Heroic spins.
- Treasure hunt = TR101 (tuning/overrides/TR101.json): mean 571.9, MaxWin 0.210% (1/476).
- feature_heroic_chance p = (571.9-483.5)/(571.9-426.6) = 0.608 -> combined mean 483.5 = 96.70% RTP.
- Combined: MaxWin 0.238% (1/420); zero share 21.3%; mean split Heroic 259.5 / Treasure hunt 224.0.
- Combined percentiles (x bet): p25 28.5, p30 70, p40 112, p50 152.5, p60 209, p70 289, p75 346, p80 430, p85 569, p90 825, p95 1556, p98 3653, p99 6407, p99.5 11999, p99.9 25000.
- To bake: heroic flags (heroic_chest_weights/hp, heroic_min_coin, chain_block heroic, HERO reel, line mult off), feature_zero_share heroic 0.35, feature_heroic_chance 0.608, all treasure_hunt flags of TR101.

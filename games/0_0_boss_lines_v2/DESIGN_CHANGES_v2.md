# Boss Lines — Đề xuất thay đổi cơ chế (v2)

Ghi lại nguyên văn ý tưởng của game designer (2026-09-30) để không bị quên.
**Chưa implement gì** — đây chỉ là spec nháp. Phần "Điểm cần làm rõ" ở cuối
là ghi chú của Claude, không phải của designer.

**Cập nhật lần 2 (cùng ngày):** designer bổ sung **mục 6** (lưới 6x5, last hit
boost, HP boss, bảng payout, luật trả thưởng, luật xoá biểu tượng). Mục 1–5 giữ
nguyên như bản đầu. Mục nào mới được đánh dấu **[MỚI]**.

## 1. Multi drop boss

- Multi drop từ boss được chia thành các loại rương:
  - Rương đồng: 1x; 2x; 3x; 4x
  - Rương bạc: 5x; 6x; 8x; 10x; 12x; 15x
  - Rương vàng: 20x; 25x; 30x; 40x; 50x
  - Rương kim cương: 100x; 150x; 200x; 250x
  - Rương cầu vồng: 500x; 1.000x; 1.500x; 2.000x; 2.500x; 5.000x; 10.000x; 20.000x
- Mỗi loại rương có tỷ lệ nhỏ khi mở **không drop multi** nhưng được **nâng cấp**
  lên rương cao hơn. Có thể nâng vượt cấp (vd bạc -> kim cương) nhưng chỉ được 1 lần.
- Rương chỉ được nâng tối đa lên rương kim cương. Từ kim cương không nâng tiếp.
- Rương kim cương có thể drop cả multi của rương cầu vồng (vd 1.000x).
- Rương cầu vồng chỉ rơi khi kill **boss cuối chặng 5**. Đồ hoạ hiện là rương
  kim cương, chuyển hoá thành rương cầu vồng sau khi kill.

## 2. Biểu tượng

- 4 biểu tượng trả thưởng nhỏ (trước là 5): L1, L2, L3, L4.
- 5 biểu tượng trả thưởng lớn (trước là 4): H1, H2, H3, H4, H5. H5 nên có đồ
  hoạ chi tiết và vượt trội hơn H1–H4.
- Wild xuất hiện ở tất cả các cột, bổ sung trả thưởng cho line có Wild liên tiếp.
- Power không xuất hiện ở cột đầu và cột cuối, chỉ ở các cột giữa.
- **Loại bỏ:** Mystery, Big symbol, Extra power (Extra wild giờ có thể ra cả
  Power), Alter. Global multi vẫn giữ như cũ nhưng chỉ thu thập được qua cơ chế Coin.
- **Bổ sung Coin:** kích hoạt cuối cùng (chi tiết ở mục 4).
- **Bổ sung Upgrade:** ngẫu nhiên 1–3 biểu tượng đổi thành H5 hoặc Wild.
- **Sửa Wild multi:** không còn tự nhân thưởng cho line mà trở thành một power
  kích hoạt sau. Khi kích hoạt, áp hệ số 2x; 3x; 5x; 10x; 20x; 50x; 100x cho
  toàn bộ các ô chứa 1 biểu tượng được chọn (L1–L4, H1–H5 và Wild).
  - Hệ số có hiệu lực đến khi ô biến mất do payout từ connect, hoặc khi sang
    vòng quay kế tiếp.
  - Nếu một line có nhiều ô mang hệ số thì **cộng** các hệ số trước khi payout cuối.
  - Damage được nhân hệ số theo từng ô.
- **Biểu tượng Súng thay thế Booster.** Hiển thị một con số = damage gây cho boss.
  Số này tính theo % Max HP của boss lớn nhất mà nó có thể damage hiện tại; roll
  theo 10%; 20%; ...; 100%, mỗi mức 10% cơ hội. Damage làm tròn số nguyên gần
  nhất, tối thiểu 5.
  - Súng ngắn: trừ HP boss trong cột.
  - Súng dài: trừ HP toàn bộ boss.

## 3. Cơ chế spin

- God Mode không gồm scatter, kể cả nếu trúng cơ chế Coin. (Đề xuất đổi tên.)
- Hidden Bonus đổi tên thành **Mega Bonus**.
- Tên gốc của Normal Bonus là **Bonus**.
- Mua Feature spin sẽ ngẫu nhiên trúng 1 trong 2 cơ chế (tỷ lệ tính sau):
  - **God Mode:** giữ cơ chế cũ, boss chặng 5 và không lên chặng tiếp.
  - **Full board coin** (cần tên hay hơn): cơ chế Coin áp dụng toàn bảng.
- Base spin và Ante spin đánh boss ở chặng 0; thắng sẽ vào Bonus hoặc upgrade Bonus.

## 4. Cơ chế Coin

- Kích hoạt bằng cách thu thập **Power Coin** khi nằm trong connect.
- Khi kích hoạt, toàn bộ ô đã từng biến mất trong lượt quay trở thành các biểu
  tượng đặc biệt của cơ chế này:
  - **Coin:** chứa multi giống drop boss nhưng chỉ 1x–1.000x (không bị loại bỏ
    multi nhỏ khi lên chặng như drop boss).
  - **Chest:** thu thập multi của toàn bộ coin (kể cả từ chest khác), làm tất cả
    các ô này trống và sẽ drop coin lại.
  - **Clover:** hệ số 2x; 3x; 4x; 5x; 10x; 20x. Nhân hệ số với 8 ô xung quanh (3x3).
    Nhân cả damage boss từ súng.
  - **Global multi:** hệ số 2–10x. Giữ đến hết session (hết vòng quay trong base,
    hoặc hết toàn bộ free spin trong bonus). Nhân với mọi payout line và coin kể
    từ khi có global multi (không áp dụng cho multi drop boss). Nhiều global
    multi thì cộng với nhau trước khi nhân.
  - **Scatter:** như scatter thường. Trong base, đủ 3+ scatter thì vào bonus như
    thường (tính gộp với scatter đang có trên bảng ở ô không áp dụng Coin). Trong
    bonus thì +1 spin cho mỗi scatter.
  - **Súng:** như mục 2. Damage không nhân với global multi.
- Đồ hoạ trong cơ chế Coin: các ô xuất hiện gần như đồng thời (độ trễ thấp).

## 5. Chặng boss

| Chặng | Là gì | Multi drop boss | Biểu tượng trả thưởng |
|---|---|---|---|
| 0 | Chặng của base spin và ante spin | Gồm multi của tất cả rương + bổ sung **0x**; đồ hoạ không thể hiện rương theo từng boss | Cả 3 boss HP cố định **20** |
| 1 | Bắt đầu của Bonus | Có tỷ lệ không ra rương; đảm bảo từ rương đồng trở lên | Giữ nguyên mọi biểu tượng cơ bản |
| 2 | Bắt đầu của Super Bonus, hoặc tiếp tục chặng 1 | Đảm bảo rương đồng trở lên | Loại L1 |
| 3 | Bắt đầu của Mega Bonus, hoặc tiếp tục chặng 2 | Đảm bảo rương bạc trở lên | Loại thêm L2 |
| 4 | Tiếp tục chặng 3 | Đảm bảo rương vàng trở lên | Loại thêm L3 |
| 5 | Chặng duy nhất của God Mode, hoặc tiếp tục chặng 4, hoặc vòng lặp sau khi diệt toàn bộ boss chặng 5 trong bonus | Đảm bảo rương kim cương trở lên | Loại thêm L4 |

Kết thúc chặng 0 (diệt toàn bộ boss): kích hoạt Bonus nếu có dưới 3 scatter.
Nếu vừa có 3+ scatter vừa diệt toàn bộ boss:
- 3 scatter -> Super Bonus (thay vì Bonus)
- 4 scatter -> Mega Bonus (thay vì Super Bonus)
- 5 scatter -> Maxwin ngay lập tức

## 6. Cơ chế cơ bản khác [MỚI]

- Lưới đổi từ 5x5 sang **6x5** (6 cột, 5 hàng). Boss 1 ở cột 1–2, boss 2 ở cột
  3–4, boss 3 ở cột 5–6.
- **Last hit boost:** cộng thêm tỷ lệ nếu spin hiện tại là spin cuối và không
  xuất hiện scatter nào. Công thức = tỷ lệ tính hiện tại **+ 3%**. Áp dụng cho
  cả súng ngắn, **không** tính súng dài.
- HP 3 boss ở từng chặng vẫn ngẫu nhiên và tăng dần, nhưng boss 2 **không còn**
  bắt buộc có HP lớn nhất trong 3 boss (do đổi sang 6 cột).
- **Payout đề xuất** (nếu đổi cơ chế sẽ chỉnh sau):

| Biểu tượng | 3 ô | 4 ô | 5 ô | 6 ô | Damage |
|---|---|---|---|---|---|
| L1 | 0.1 | 0.3 | 1 | 2 | 1 |
| L2 | 0.15 | 0.45 | 1.5 | 3 | 1 |
| L3 | 0.2 | 0.6 | 2 | 4 | 1 |
| L4 | 0.25 | 0.75 | 2.5 | 5 | 1 |
| H1 | 0.5 | 1.25 | 3.75 | 7.5 | 2 |
| H2 | 0.75 | 1.75 | 5 | 10 | 2 |
| H3 | 1 | 2.25 | 6.25 | 12.5 | 2 |
| H4 | 1.5 | 3 | 7.5 | 15 | 2 |
| H5 | 2 | 4 | 10 | 20 | 3 |
| Wild | (không có giá trị riêng trong bảng) | | | | |

  (Cột Damage là bảng dán bị vỡ dòng; tôi suy ra nhóm L=1, H1–H4=2, H5=3 —
  xem "Điểm cần làm rõ".)
- **Trả thưởng từ trái sang phải**, chỉ tính khả năng trả cao nhất trên từng
  line. Ví dụ Wild–Wild–Wild–H3–H4: (1) trả theo 3 Wild = 2.5x; (2) trả theo 4
  H3 (Wild thay thế) = 3x. Cách 2 cao hơn nên chỉ áp dụng cách 2.
- **Mega Bonus (Both Ways):** hai chiều trái->phải và phải->trái xét độc lập,
  mỗi chiều lấy khả năng trả cao nhất, rồi **cộng** hai chiều lại.
  - Ví dụ Wild–H4–Wild–Wild–H5: trái->phải cao nhất là 4 H4 = 5x; phải->trái cao
    nhất là 3 H5 = 2.5x; tổng = 7.5x.
  - Nếu hai chiều tương đương, vd H2–Wild–H2–H2–H2, vẫn theo nguyên tắc này:
    6x + 6x = 12x.
- **Luật xoá biểu tượng khi connect:** chỉ biểu tượng trả thưởng thường (L1–L4,
  H1–H5) khi có connect mới xoá **toàn bộ** biểu tượng giống nó trên bảng. Nếu
  Wild hoặc bất kỳ biểu tượng đặc biệt nào có connect thì chỉ xoá đúng ô được
  connect, không xoá các ô giống trên bảng. Súng và scatter **không phải power**,
  do đó cũng **không phải Wild**.

## Điểm cần làm rõ (ghi chú của Claude, chưa được designer xác nhận)

- Hiện game có **6 chặng** (Super bắt đầu ở chặng 2, Hidden ở chặng 3, vòng lặp
  ở chặng 6); spec mới có **chặng 0–5** và vòng lặp ở chặng 5. Cần xác nhận đây
  là đổi số chặng thật, không chỉ đổi cách đánh số. Ảnh hưởng: funnel, HP table,
  prune biểu tượng, và toàn bộ phần chest-tier Super đang tune dở.
- "Kích hoạt Bonus nếu có **dưới** 3 scatter" ở chặng 0 — có lẽ ý là "không có
  scatter / <3 scatter mà vẫn diệt hết boss"? Cần xác nhận điều kiện vào Bonus
  thường.
- 5 scatter -> Maxwin: cần quyết định rate mục tiêu (hiện Max Win đang tune
  1-in-26097 sessions).
- Bảng multi mới có rương cầu vồng tới 20.000x và kim cương bắt đầu từ 100x —
  khác hẳn 5 màu rương Super đang thử (đồng/bạc/vàng/bạch kim/kim cương). Đây
  thay thế thiết kế chest-tier hiện tại.
- Tỷ lệ "không drop nhưng nâng cấp rương", tỷ lệ Feature buy giữa God Mode và
  Full board coin, và hệ số/weights của Upgrade, Clover, Global multi: chưa có
  số, sẽ cần một vòng tune riêng.
- Câu Scatter trong mục 4 có ký tự thừa "k" ở cuối; đã bỏ khi chép lại.

### Ghi chú thêm cho mục 6 [MỚI]

- **Ví dụ trong mục 6 không khớp bảng payout.** Ví dụ Wild–Wild–Wild–H3–H4 nói
  4 H3 = 3x, nhưng bảng ghi H3 4 ô = 2.25 (H4 4 ô = 3). Ví dụ Both Ways nói 4 H4
  = 5x và 3 H5 = 2.5x, bảng ghi 3 và 2. Ví dụ H2 nói 5 ô = 6x, bảng ghi 5.
  Có vẻ ví dụ viết từ một bảng cũ. Cần chốt bảng nào là đúng trước khi tune.
- "3 Wild = 2.5x" cần một giá trị Wild riêng, nhưng dòng Wild trong bảng trống.
  Wild có bảng trả riêng hay chỉ là thay thế?
- Cột Damage của bảng bị vỡ khi dán; nhóm L=1 / H1–H4=2 / H5=3 là tôi suy ra.
  Cần xác nhận. Damage này là damage mỗi ô nổ, thay cho `flat_symbol_damage` hiện tại?
- Đổi sang lưới 6x5 ảnh hưởng nặng: paylines, reel strip (Normal/Super/Hidden
  đều đang 5 cột), tính lại RTP, toàn bộ tuning trước đó không còn dùng được.
  Cột 5–6 thuộc boss 3 nhưng Power vẫn không ở cột đầu/cuối (cột 1 và 6).
- Last hit +3% chỉ khi "spin cuối và không có scatter": trong spin-budget, "spin
  cuối" là spin cuối của ngân sách. Cần xác nhận đúng ý.

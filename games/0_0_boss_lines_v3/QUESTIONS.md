# Boss Lines v3: câu hỏi chờ trả lời

Nguồn: `Proposal_2026-10-06.docx` (bản lưu 01:34 ngày 2026-10-06, đã copy vào thư mục này).

Mỗi câu ghi kèm **mặc định đang code**. Đây là cách tôi tạm hiểu để code chạy được, và nó nằm sau một tham số trong
`game_config.py`, nên đổi lại không phải sửa logic. Bạn chỉ cần trả lời theo số câu. Câu nào đồng ý với mặc định
thì ghi "OK".

**Quyết định tôi tự đưa ra (bạn có thể đảo lại):** spec mới khác v2 quá nhiều (Hold and Spin, 35 dòng, Treasure,
vũ khí, rương có quà, Endless, số vòng quay cố định), nên tôi viết **game mới `0_0_boss_lines_v3`** theo đúng thứ tự
hành động mục 6. `0_0_boss_lines_v2` giữ nguyên, không sửa. Các cơ chế của v2 không có trong spec mới (HP người chơi,
spin budget, deadspin, chain-block...) không được mang sang.

## Đã chốt từ buổi QA trước (để đối chiếu)
- Ô hàng 3 cột 6 trong sơ đồ thứ tự là 25 (file mới đã sửa).
- Tên chế độ: Ante spin.
- Scatter chặn tối đa 5 khi sinh bảng: nếu 5 cột đầu đã có scatter thì cột 6 không có.
- Endless lần đầu HP 350–400; các lần sau chỉ cần HP ≥ boss Endless trước, không giới hạn trên.
- HP các chặng được phép chồng khoảng nhau.
- Wild gây damage 3 (ô gộp với H5 trong bảng).
- Scatter và vũ khí bị phá thì không trả thưởng, không gây damage. Vũ khí nổ: mỗi ô nó phá gây damage = damage của ô × hệ số vũ khí.
- Cung tên không có hệ số 1–10x.
- Upgrade: cả nhóm ô ra cùng một kết quả.
- Last hit dùng HP tối đa của boss.
- Scatter giữ trong Hold and Spin được tính vào điều kiện vào Bonus.
- Diệt boss chặng 0 chỉ nhận rương, không vào Bonus.

## Câu hỏi mới

### Trả thưởng
1. **Xu từ sự kiện Wild (Coin drop) có nhân Global multiplier không?** Mục 6 chỉ nói xu trong rương và Treasure
   nhân Global; Coin drop xảy ra ở bước (4), trước bước trả thưởng dòng.
   Mặc định: **có nhân** (`wild_coin_uses_global = True`).
2. **Nhiều Multiplier Wild trên cùng một dòng: cộng hay nhân?** (Hệ số Enhance thì spec ghi rõ là cộng.)
   Mặc định: **cộng** như Enhance (`wild_mult_combine = "add"`).
3. **Payout lẻ:** bảng trả thưởng có giá trị không chia hết 0.10 (0.15, 0.25, 0.45, 0.75, 1.25, 2.25, 3.75, 6.25,
   12.5). Khi xuất thư viện cho Stake, RGS kiểm tra payout là bội số 0.10 nên bước kiểm định dạng sẽ báo lỗi.
   Mục 7 nói không tự sửa bảng nên tôi chỉ báo. Hướng xử lý: làm tròn xuống tổng mỗi lượt về 0.10, hay đổi bảng?
   Mặc định: **chưa làm tròn**.

0. **Ô bị phá được lấp tại chỗ (không rơi xuống như cascade), đúng không?** Spec ghi "xuất hiện biểu tượng mới
   trên những ô bị phá huỷ". Hệ số Enhance, ô sáng nền và ô giữ của Hold and Spin đều gắn với **vị trí ô**, nên
   chỉ đúng nghĩa khi các ô không bị dịch chuyển.
   Mặc định: **lấp tại chỗ**, biểu tượng mới rút ngẫu nhiên theo reel của cột đó.

### Hold and Spin
4. **Hold and Spin nằm ở đâu trong thứ tự mục 6?** Mục 6 không liệt kê.
   Mặc định: chỉ xét **một lần, ngay sau bảng đầu tiên của vòng quay**, trước bước (1). Kích hoạt khi bảng đầu có
   ≥1 kết nối, với tỷ lệ `hold_spin_chance`.
5. **Ô được giữ:** tôi hiểu là mọi ô chứa biểu tượng đã kết nối ở bảng đầu, cộng mọi Wild, Scatter và vũ khí.
   Ô mới quay ra nếu trùng loại đó thì cũng được giữ. Các lượt quay lại chỉ đổi bảng, không trả thưởng hay gây
   damage riêng; sau khi dừng thì vào chuỗi bước (1)–(9) bình thường. Đúng không?
6. **Hold and Spin có trong Heroic spin không?** Mục 3 ghi "bất kì vòng quay nào".
   Mặc định: **có** (cùng tỷ lệ với base).

### Biểu tượng theo chặng và Endless
7. **Biểu tượng "Loại bỏ L1/L2…" là cộng dồn và gắn với chặng, không phụ thuộc lịch sử?** Ví dụ Super Bonus bắt
   đầu ở chặng 2 thì không có L1 ngay từ đầu; chặng 4 không có L1, L2, L3; Endless và chặng 5 không còn L nào.
   Mặc định: **đúng như vậy** (reel mỗi chặng không chứa các L đã loại).
8. **Boss Endless mới xuất hiện lúc nào sau khi diệt boss Endless cũ:** ngay trong vòng quay đó, hay vòng quay
   sau (như luật chuyển chặng)?
   Mặc định: **vòng quay sau**.
9. **Bước tăng HP boss Endless:** "≥ boss trước, không giới hạn" vẫn cần một quy tắc để sinh số.
   Mặc định: HP mới = HP cũ + một bội số của 5 ngẫu nhiên trong [0, 50] (`endless_hp_step_choices`).
10. **Heroic spin diệt hết boss chặng 5 thì sao?** (Không lên Endless.) Tôi hiểu là kích hoạt Treasure như mọi
    lần dọn chặng, rồi kết thúc vòng quay. Đúng không?

### Damage, Last hit, boss rơi đồ
11. **"Mỗi lần gây sát thương" để roll Last hit và roll boss rơi Wild/Power được tính theo đơn vị nào?** Bước (6)
    phá nhiều ô cùng lúc.
    Mặc định: **mỗi bước hành động roll 1 lần cho mỗi boss bị đánh** (một lượt phá kết nối, một vũ khí, một lần
    Destroy). Roll theo từng ô trước đây đã làm mean tăng 2–3 lần.
12. **Công thức Last hit:** spec chỉ nói "HP sau sát thương / HP tối đa càng thấp thì tỷ lệ càng cao".
    Mặc định: `chance = base + scale × (1 − HP_sau / HP_tối_đa)`, nhân 2 ở vòng quay Bonus cuối không có Scatter.
    `base`/`scale` là số tạm, sẽ tune sau.
13. **Destroy (bước 8):** các biểu tượng trả thưởng bị phá **có gây damage không?** Spec chỉ nói chúng không làm
    sáng nền cho Treasure. Mặc định: **có gây damage** (luật chung mục 5, hệ số 1x).
14. **Bom và Dao phá "biểu tượng trả thưởng": có tính Wild không?** (Sấm chớp ghi rõ "biểu tượng trả thưởng cơ
    bản", còn Bom và Dao không có chữ "cơ bản".) Mặc định: **có tính Wild** (Wild bị phá gây damage 3 × hệ số).
15. **Transform** ("2–5 ô bất kì, trừ Wild và Vũ khí"): **có được biến ô Scatter thành Wild không?**
    Mặc định: **không đụng Scatter** (tránh làm mất trigger Bonus).

### Rương
16. **Loại rương của mỗi boss:** gán lúc boss xuất hiện theo mức tối thiểu của chặng, có tỷ lệ ra loại cao hơn,
    cộng cơ hội nâng cấp một lần lúc mở. Đúng không? (Tỷ lệ là số tạm.)
17. **Rương ngoài Bonus chỉ có Đồng xu.** Vậy Đồng xu trong rương Đồng ở base là 1–3 xu, mỗi xu thuộc bảng Xu Đồng
    trở lên. Đúng không?
18. **Quà Power trong rương khi kho dự trữ loại đó đã đủ 3:** bỏ qua, hay đổi thành Đồng xu?
    Mặc định: **đổi thành Đồng xu** cùng cấp rương.

### Treasure
19. **Thứ tự Clover sau mỗi vòng Nam châm:** khi quay lại bước (1) rồi (2), chỉ Clover **mới xuất hiện** mới kích
    hoạt, hay mọi Clover kích hoạt lại? Mặc định: **chỉ Clover mới**.
20. **Clover nhân "ô có chứa hệ số thưởng xung quanh":** gồm Đồng xu và Nam châm, không gồm ô Global multiplier,
    đúng không? Mặc định: **xu + nam châm**.
21. **Global multiplier trong Treasure được cộng vào bộ đếm lúc nào?** Mặc định: lúc nó xuất hiện. Nó áp dụng
    cho trả thưởng của chính lần Treasure đó, và cho các trả thưởng sau trong Bonus.
22. **Scatter xuất hiện trong Treasure:** ở base thì tính vào số Scatter để vào Bonus; trong Bonus thì +1 vòng quay
    mỗi cái. Có giới hạn tối đa 5 Scatter và 1 Scatter mỗi cột như bảng thường không?
    Mặc định: **có giới hạn** (5 tổng, 1 mỗi cột).
23. **Ô sáng nền trong Bonus (không phải Epic):** sau khi Treasure dùng chúng thì bị xoá, hay giữ tiếp đến hết
    Bonus? Mặc định: **xoá sau khi Treasure chạy**. Epic thì luôn sáng toàn bộ.
24. **Treasure hunt "không đánh boss":** bảng 30 ô đều là biểu tượng Treasure. Mức xu tối thiểu là 1x (spec), còn
    Global multiplier xuất hiện thì vẫn nhân trả thưởng Treasure, đúng không? Scatter trong Treasure hunt đủ 3/4/5
    thì vào Bonus/Super/Epic.

### Chuyển chế độ
25. **Global multiplier thu được ở base spin (qua Treasure) có mang vào Bonus vừa trúng không?**
    Mặc định: **không**, Bonus bắt đầu với Global = 0x (hiển thị 1x).
26. **Vòng quay base trúng Bonus:** mặc định số Scatter tính ở bước tổng kết, gồm scatter trên bảng cuối cùng cộng
    scatter giữ trong Hold and Spin và scatter trong Treasure. Scatter bị Destroy phá ở base thì không tính. Đúng không?
27. **Tỷ lệ chia Feature spin** (Heroic / Treasure hunt) và mức "Ante tăng 5 lần tỷ lệ 3+ Scatter" sẽ được tune
    sau. Mặc định tạm: 50/50.

## Đề xuất gộp để giảm thời gian chạy (mục 7)
- **Sấm chớp** gần như một "kết nối giả": phá mọi ô của một biểu tượng. Có thể gộp với Bom/Dao thành một vũ khí
  nổ theo hình ngẫu nhiên (3x3 / hàng / cả biểu tượng).
- **Transform và Upgrade** đều tạo Wild. Có thể gộp thành Upgrade (một nhóm ô thành H5/Wild).
- **Replace** chạy lặp lại mỗi pass với điều kiện "2 trên 3 cột đầu", là bước tốn thời gian nhất trong chuỗi
  (1)–(6). Nếu bỏ Replace và chỉ giữ Destroy thì vẫn còn một Power "đổi bảng".
- **Hold and Spin ở base:** cộng với cascade làm số lượt xử lý mỗi spin tăng mạnh. Có thể chỉ giữ cho Epic Bonus
  (vốn đã luôn kích hoạt).

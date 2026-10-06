# Boss Lines v3: câu hỏi chờ trả lời

**Nguồn hiện tại:** `Proposal_KichBan1_2026-10-06.md` (bản "Kịch bản 1: Cơ chế Line" dán vào chat ngày 2026-10-06).
Bản trước là `Proposal_2026-10-06.docx` (01:34). File docx trên đĩa **chưa được cập nhật**, nên:
- Hình 35 dòng trả thưởng và sơ đồ thứ tự ô vẫn được test đọc từ docx cũ.
- Bảng chặng (HP, rương, xu) được test đọc từ bản .md mới.

Mỗi câu ghi kèm **mặc định đang code**. Mặc định nằm sau một cờ trong `game_config.py`, nên đổi lại không phải
sửa logic. Bạn chỉ cần trả lời theo số câu; câu nào đồng ý với mặc định thì ghi "OK".

**Quyết định tôi tự đưa ra (bạn có thể đảo lại):** game viết mới là `0_0_boss_lines_v3`. `0_0_boss_lines_v2` giữ
nguyên. Các cơ chế của v2 không có trong spec (HP người chơi, spin budget, deadspin, chain-block...) không được mang sang.

## A. Câu bản "Kịch bản 1" đã trả lời (đã cập nhật code)
- Q1: xu từ sự kiện Wild **có** nhân Global multiplier.
- Q5: không trả thưởng hay kích hoạt gì trong lúc Hold and Spin đang chạy.
- Q13: Destroy **được tính là phá huỷ**, nên gây damage. Không làm sáng nền.
- Q14: Bom và Dao phá **mọi biểu tượng** trong vùng (không chỉ biểu tượng trả thưởng). Xem câu mới N1.
- Q15: Transform không đụng Scatter **ngoài Bonus**; trong Bonus thì được. Destroy cũng vậy.
- Q19: Clover, Golden clover và Star sau khi kích hoạt thì làm trống ô và được lấp lại biểu tượng mới.
- Q22, Q24: Scatter từ Treasure cộng với Scatter thường để vào Bonus; Treasure hunt có Scatter để vào Bonus.
- Q23: ô sáng nền **giữ suốt Bonus**, không xoá sau khi Treasure chạy.
- Q25: vào Bonus thì Global multiplier và ô sáng nền được đặt lại, **trừ các ô chứa Scatter đã kích hoạt Bonus**
  (những ô này sáng sẵn khi bắt đầu Bonus).
- Q28: trong Bonus, ô sáng đang là Scatter thì vẫn giữ Scatter khi Treasure chạy.
- Epic: không còn ép bảng đầu phải có kết nối; Hold and Spin **luôn** kích hoạt khi bảng đầu có kết nối.

## B. Câu còn mở từ lần trước
0. **Ô bị phá được lấp tại chỗ (không rơi như cascade)?** Hệ số Enhance, ô sáng nền và ô giữ của Hold and Spin đều
   gắn với vị trí ô. Mặc định: **lấp tại chỗ**, rút ngẫu nhiên theo reel của cột đó.
2. **Nhiều Multiplier Wild trên cùng một dòng: cộng hay nhân?** Mặc định: **cộng** (như Enhance).
3. **Payout lẻ:** các giá trị 0.15, 0.25, 0.45, 0.75, 1.25, 2.25, 3.75, 6.25, 12.5 không chia hết 0.10, nên bước kiểm
   định dạng RGS của Stake sẽ báo lỗi. Làm tròn tổng mỗi lượt về 0.10, hay đổi bảng? Mặc định: **chưa làm tròn**.
4. **Hold and Spin nằm ở đâu trong thứ tự hành động?** Mặc định: xét **một lần, ngay sau bảng đầu tiên**, trước bước (1).
6. **Hold and Spin có trong Heroic spin không?** Mặc định: **có**.
7. **"Loại bỏ L1/L2…" là cộng dồn và gắn với chặng** (Super bắt đầu chặng 2 thì không có L1 ngay từ đầu)?
   Mặc định: **đúng vậy**.
8. **Boss Endless mới xuất hiện ngay trong vòng quay đó hay vòng quay sau?** Mặc định: **vòng quay sau**.
9. **Bước tăng HP boss Endless:** mặc định HP mới = HP cũ + bội số của 5 ngẫu nhiên trong [0, 50].
10. **Heroic spin diệt hết boss chặng 5:** kích hoạt Treasure rồi kết thúc. Đúng không?
11. **"Mỗi lần gây sát thương" để roll Last hit và rơi đồ là đơn vị nào?** Mặc định: **mỗi bước hành động roll 1 lần
    cho mỗi boss bị đánh** (một lượt phá kết nối, một vũ khí, một lần Destroy). Roll theo từng ô trước đây làm mean
    tăng 2–3 lần.
12. **Công thức Last hit:** mặc định `base + scale × (1 − HP_sau / HP_tối_đa)`, ×2 ở vòng quay Bonus cuối không có
    Scatter. `base`/`scale` là số tạm.
16. **Loại rương của mỗi boss:** gán lúc boss xuất hiện = mức tối thiểu của chặng, có tỷ lệ ra loại cao hơn, cộng cơ
    hội nâng cấp một lần lúc mở. Đúng không?
17. **Rương ngoài Bonus chỉ có xu:** rương Đồng ở base có 1–3 xu, mỗi xu từ bảng Xu Đồng trở lên. Đúng không?
18. **Quà Power trong rương khi kho loại đó đã đủ 3:** mặc định **đổi thành đồng xu** cùng cấp rương.
20. **Clover, Golden clover nhân "ô có chứa hệ số thưởng":** mặc định gồm **Đồng xu và Nam châm** (Star đã kích hoạt
    và rời bảng trước bước Clover).
21. **Global multiplier trong Treasure cộng vào bộ đếm lúc nào?** Mặc định: **lúc nó xuất hiện**, nên áp dụng cho
    chính lần Treasure đó.
26. **Số Scatter để vào Bonus ở base:** đếm trên bảng cuối, gồm Scatter giữ trong Hold and Spin và Scatter trong
    Treasure. Đúng không?
27. **Tỷ lệ chia Feature spin** (Heroic/Treasure hunt): mặc định tạm 50/50.

## C. Câu mới từ bản "Kịch bản 1"
N1. **Bom/Dao phá "các biểu tượng": gồm cả Scatter và vũ khí khác?** Vũ khí bị phá như vậy có còn được kích hoạt
    không? Mặc định: phá **mọi biểu tượng trừ Scatter ngoài Bonus**, cùng quy tắc giữ Scatter như Destroy và
    Transform. Vũ khí bị phá thì **không** kích hoạt.
N2. **Kiểm tra Maxwin "theo từng bước" trong Treasure:** Treasure chỉ cộng tiền ở bước (7). Mặc định: sau mỗi bước,
    nếu `bộ đếm hiện tại + tổng hệ số thưởng đang có × Global ≥ 25.000` thì trả Maxwin và dừng ngay. Một đồng xu đạt
    ≥ 25.000x (xu Maxwin) cũng dừng ngay.
N3. **Star sau khi kích hoạt:** giá trị của chính Star có được tính ở bước (7) không, hay ô Star chỉ được làm trống?
    Mặc định: **chỉ làm trống**; giá trị Star đã cộng vào xu và nam châm.
N4. **"Nam châm chỉ xuất hiện khi trên màn hình có ≥ 2 đồng xu":** có tính cả các đồng xu vừa xuất hiện trước nó
    trong cùng một loạt (theo thứ tự ô) không? Mặc định: **có tính**.
N5. **Treasure đầu Epic Bonus:** mức xu tối thiểu là của chặng 2 (1x), đúng không? Global multiplier thu được ở lần
    Treasure này có mang vào các vòng quay Epic không? Mặc định: **1x, và có mang vào** (Global giữ suốt Bonus).
N6. **"Không xuất hiện xu Đồng trong Epic":** áp dụng cho xu từ Wild, xu trong rương, xu và Star trong Treasure.
    Đúng không? Mặc định: **cả bốn đều tối thiểu 5x**.
N7. **Vòng quay base vừa diệt hết boss chặng 0 vừa đủ Scatter vào Bonus:** luật ô sáng nói "ô đã chứa Scatter kích
    hoạt Bonus" cũng biến thành biểu tượng Treasure. Nhưng câu về Scatter trong Treasure và luật "giữ ô sáng chứa
    Scatter kích hoạt Bonus" lại gợi ý các ô đó vẫn là Scatter. Mặc định: **Treasure ở base không đụng ô Scatter**;
    các ô đó mang trạng thái sáng vào Bonus, rồi thành biểu tượng Treasure ở lần Treasure đầu tiên trong Bonus.
N8. **Heroic spin "không xuất hiện Scatter để kích hoạt Bonus":** nghĩa là Heroic không có Scatter nào, hay có
    Scatter nhưng không tính? Mặc định: **không có Scatter**.
N9. **Paylines:** bản dán không có hình 35 dòng. Bạn xác nhận 35 dòng **không đổi** so với docx cũ và lưu lại file
    docx mới, để test đọc lại toàn bộ từ docx.
N10. **Thứ tự Treasure khi không có nam châm:** sau bước (3)–(5), ô Star/Clover đã kích hoạt bị làm trống. Chúng chỉ
     được lấp lại khi quay về bước (2), mà việc này chỉ xảy ra sau một nam châm. Không có nam châm thì các ô đó để
     trống đến bước (7). Đúng không?

## D. Cảnh báo cấu trúc (mục 7: báo những chỗ gây biến động lớn)
- **Treasure gần như phủ kín bảng:** mỗi kết nối phá mọi bản sao của biểu tượng, nên khi Treasure kích hoạt đã có
  khoảng 20+ ô sáng. Với xu tối thiểu 20x ở chặng 5/Endless, một lần Treasure ở đó có sàn khoảng vài trăm x, chưa nhân Global.
- **Global multiplier chỉ tăng trong suốt Bonus** và nhân trả thưởng dòng, rương, xu Wild và Treasure.
- **Rương Kim cương:** xu trong rương tối thiểu 100x, nhân Global.
- **Scatter trong Bonus:** mỗi spin lấp lại khoảng 32 ô, ô nào cũng có thể ra Scatter (+1 spin). Ở mật độ 1% mỗi spin
  tự cộng 1.38 spin, nên Bonus không bao giờ tự kết thúc. Reel Bonus hiện để 1 Scatter mỗi cột.

## E. Đề xuất gộp để giảm thời gian chạy (mục 7)
- **Sấm chớp** gần như một "kết nối giả" (phá mọi ô của một biểu tượng). Có thể gộp với Bom/Dao thành một vũ khí nổ
  theo hình ngẫu nhiên.
- **Transform và Upgrade** đều tạo Wild. Có thể gộp thành Upgrade.
- **Clover và Golden clover** chỉ khác phạm vi (3x3 / toàn bảng); có thể là một biểu tượng với hai mức.
- **Replace** chạy lặp mỗi pass với điều kiện "2 trên 3 cột đầu", là bước tốn thời gian nhất trong chuỗi (1)–(6).

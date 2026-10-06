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

## B. Trả lời ngày 2026-10-07 (đã áp dụng vào code)
- Q0: ô bị phá được **lấp tại chỗ**.
- Q2: nhiều Multiplier Wild trên một dòng thì **nhân** với nhau (2x và 5x thành 10x). Đã đổi code.
- Q4: Hold and Spin xét **một lần ngay sau bảng đầu**. Q6: **có** trong Heroic spin.
- Q7: biểu tượng bị loại **cộng dồn, theo chặng**.
- Q8: boss Endless mới xuất hiện ở **vòng quay sau**. Q9: HP mới = HP cũ + bội số của 5 trong [0, 50].
- Q10: Heroic dọn chặng 5 thì **Treasure rồi kết thúc**.
- Q11: Last hit và boss rơi đồ roll **mỗi bước hành động, mỗi boss**. Q12: giữ công thức tuyến tính, base/scale tune sau.
- Q16: loại rương **gán lúc boss xuất hiện**, có cơ hội nâng cấp một lần lúc mở.
- Q17: rương ngoài Bonus chỉ có xu, mỗi xu ≥ cấp rương.
- Q18: Power đã đủ 3 thì **không xuất hiện nữa** (rương/Wild/boss chọn loại khác còn chỗ). Khi cả 5 loại đều
  đầy thì quà thành đồng xu.
- Q20: Clover/Golden clover nhân **Đồng xu + Nam châm**. Q21: Global cộng **ngay khi xuất hiện**.
- Q26: số Scatter đếm **trên bảng cuối**. Q27: Feature spin chia Heroic/Treasure hunt tự tune trong khoảng
  **20–80%** (tạm 50/50).
- N1: Bom/Dao phá cả **Wild** và **Scatter trong Bonus**; ngoài Bonus giữ Scatter. Vũ khí bị phá thì không kích hoạt.
- N2: giá trị Treasure **cộng ngầm qua từng bước**, chỉ hiện ở bước 7; tổng ngầm chạm 25.000x thì dừng ngay.
- N3: Star kích hoạt xong **biến thành đồng xu** mang giá trị của nó. Đã đổi code.
- N5: Treasure đầu Epic dùng xu ≥ 1x, Global thu được **mang vào** các vòng quay Epic.
- N6: "không xu Đồng trong Epic" áp cho **cả 4 loại**: xu Wild, xu rương, xu Treasure, Star.
- N7: Treasure ở base **giữ ô Scatter**; các ô đó sáng sẵn khi vào Bonus.
- N8: Heroic spin **không có Scatter nào**. N9: 35 dòng **không đổi**.
- N10: Clover/Golden clover kích hoạt xong **ở lại trên ô**, không kích hoạt lại, không bị lấp. Đã đổi code.
  (Spec bước 2 ghi các ô này được làm trống rồi lấp lại; câu trả lời này thay cho đoạn đó.)

## B2. Mục tiêu tune (2026-10-07)
- RTP **96.7%** cho mọi chế độ: base 0.967x/spin, ante 2.901x/spin, buy3 96.7x, buy4 290.1x, Feature 483.5x.
- Feature: Heroic và Treasure hunt **không cần mean bằng nhau**; cân bằng bằng tỷ lệ ra p (20–80%) sao cho
  p × mean_Heroic + (1 − p) × mean_Treasure_hunt = 483.5x.
- Chờ duyệt: mean Bonus ≈ 68x / Super ≈ 226x / Epic 1.500x, tỷ lệ tier buy3 90/9/1 và buy4 95/5, Bonus chiếm
  30% RTP của base.

## C. Còn mở
3. **Payout lẻ** (0.15, 0.25, 1.25, 2.25…): bạn cho biết Stake mới không còn yêu cầu bội số 0.1. Bản SDK mới
   nhất của Stake trên GitHub (`utils/rgs_verification.py`) **vẫn kiểm tra** "Payout values must be in increments
   of 10", tức bội số 0.1x. Chưa làm tròn; cần xác nhận lại với Stake trước khi chạy bước kiểm tra định dạng.

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

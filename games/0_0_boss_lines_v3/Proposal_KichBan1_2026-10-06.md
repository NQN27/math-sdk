# Kịch bản 1: Cơ chế Line — LUẬT HỢP NHẤT

> Bản dán vào chat ngày 2026-10-06 (thay cho `Proposal_2026-10-06.docx` bản 01:34). Giữ nguyên văn.
> Bản dán không có hình 35 dòng trả thưởng (chỉ có số 1–35), nên paylines vẫn lấy theo file docx cũ.
> Bảng được chép lại dưới dạng bảng Markdown, nội dung không đổi.

## 1. Thông tin cơ bản
- Màn hình trò chơi gồm 30 ô trong khung 6x5 (6 cột và 5 hàng) kèm theo 3 boss nằm phía trên các cột được thể hiện qua sơ đồ sau (các ô được đánh số theo thứ tự ưu tiên):

| Boss 1 | | Boss 2 | | Boss 3 | |
|---|---|---|---|---|---|
| 1 | 2 | 4 | 7 | 11 | 16 |
| 3 | 5 | 8 | 12 | 17 | 21 |
| 6 | 9 | 13 | 18 | 22 | 25 |
| 10 | 14 | 19 | 23 | 26 | 28 |
| 15 | 20 | 24 | 27 | 29 | 30 |

- Dạng trả thưởng theo dòng (line) truyền thống gồm 35 dòng khác nhau. Các biểu tượng trả thưởng cơ bản khi kết nối sẽ được trả thưởng và phá huỷ tất cả các ô chứa biểu tượng đó trên màn hình. Trò chơi có cơ chế Hold and Spin.
- Cơ chế đánh boss theo chặng: Các biểu tượng khi phá huỷ sẽ gây sát thương (damage) cho boss cùng cột. Hỗ trợ đánh boss còn có Quyền năng (Power) thu thập và kích hoạt trong vòng quay.
- Các biểu tượng xuất hiện trong trò chơi: Biểu tượng trả thưởng cơ bản; Wild; Scatter; Vũ khí.
- Các chế độ vòng quay: Vòng quay cơ bản (Base spin); Vòng quay tăng cường (Ante spin); Vòng quay anh dũng (Heroic spin); Săn kho báu (Treasure hunt); Chế độ Thưởng (Bonus): Bao gồm Bonus, Super Bonus, Epic Bonus.
- Chiến thắng tối đa (Maxwin) của trò chơi là 25.000 lần cược cơ bản (Base bet).

## 2. Biểu tượng trong trò chơi
- Wild là biểu tượng trả thưởng đặc biệt có khả năng thay thế các biểu tượng trả thưởng cơ bản. Mỗi Wild khi kết nối có cơ hội kích hoạt một trong số các sự kiện (event) sau:
  - Wild nhân thưởng (Multiplier Wild): Xuất hiện hệ số đặc biệt trên Wild được kết nối để nhân với trả thưởng theo dòng. Hệ số ngẫu nhiên có thể là: 2x, 3x, 4x, 5x, 10x.
  - Rơi đồng xu (Coin drop): Xuất hiện đồng xu kèm hệ số thưởng ngẫu nhiên bao gồm: Xu Đồng (0.2x, 0.5x, 1x, 2x, 3x, 4x); Xu Bạc (5x, 6x, 8x 10x, 12x, 15x); Xu Vàng (20x, 25x, 30x, 40x, 50x); Xu Kim cương (100x, 150x, 200x, 250x, 500x, 1.000x); Xu Maxwin (25.000x).
  - Quyền năng (Power): Thu thập một Power ngẫu nhiên và được kích hoạt sau.
- Biểu tượng trả thưởng cơ bản: Bao gồm các biểu tượng trả thưởng theo bảng như sau:

| Biểu tượng | 3 biểu tượng | 4 biểu tượng | 5 biểu tượng | 6 biểu tượng | Sát thương |
|---|---|---|---|---|---|
| L1 | 0.1 | 0.3 | 1 | 2 | 1 |
| L2 | 0.15 | 0.45 | 1.5 | 3 | (gộp: 1) |
| L3 | 0.2 | 0.6 | 2 | 4 | (gộp: 1) |
| L4 | 0.25 | 0.75 | 2.5 | 5 | (gộp: 1) |
| H1 | 0.5 | 1.25 | 3.75 | 7.5 | 2 |
| H2 | 0.75 | 1.75 | 5 | 10 | (gộp: 2) |
| H3 | 1 | 2.25 | 6.25 | 12.5 | (gộp: 2) |
| H4 | 1.5 | 3 | 7.5 | 15 | (gộp: 2) |
| H5 | 2 | 4 | 10 | 20 | 3 |
| Wild | - | - | - | 25 | (gộp: 3) |

- Scatter là biểu tượng để kích hoạt chế độ Bonus hoặc cộng thêm vòng quay miễn phí trong chế độ Bonus. Tối đa 5 Scatter xuất hiện trên màn hình với mỗi cột xuất hiện tối đa 1 Scatter.
- Vũ khí là biểu tượng hỗ trợ trong việc đánh boss. Các loại vũ khí bao gồm:
  - Cung tên (Arrow): Gây sát thương cho boss cùng cột.
  - Bom (Bomb): Phá huỷ các biểu tượng trong phạm vi 3x3.
  - Dao (Sword): Phá huỷ các biểu tượng cùng hàng.
  - Sấm chớp (Lightning): Phá huỷ các ô chứa 1 biểu tượng trả thưởng cơ bản ngẫu nhiên không kết nối được chọn.

## 3. Cơ chế trả thưởng theo dòng và Hold and Spin
- Cơ chế trả thưởng theo dòng dựa trên sự liên tục các biểu tượng trả thưởng theo chiều từ trái sang phải. Khoản trả thưởng theo dòng dựa theo bảng trả thưởng và nhân với các loại hệ số trả thưởng (nếu có).
- Các biểu tượng trả thưởng cơ bản khi kết nối sẽ làm phá huỷ toàn bộ các ô chứa biểu tượng tương tự trên màn hình (dù có kết nối hay không).
- Wild khi kết nối chỉ phá huỷ Wild đó, không ảnh hưởng đến các Wild khác trên màn hình.
- Scatter và Vũ khí không có chức năng trả thưởng và gây sát thương khi bị phá huỷ.
- Những ô chứa biểu tượng bị phá huỷ sẽ tiếp tục xuất hiện biểu tượng mới.
- Giữ và quay lại (Hold and Spin) là cơ chế đặc biệt kích hoạt ngẫu nhiên tại mỗi đầu vòng quay bất kì có biểu tượng trả thưởng được kết nối. Khi kích hoạt, toàn bộ các ô chứa biểu tượng trùng với biểu tượng được kết nối trên màn hình, Wild, Scatter và Vũ khí được giữ nguyên, những ô còn lại được quay lại nhằm xuất hiện biểu tượng mới. Việc quay lại kết thúc khi lượt quay đó không xuất hiện ô được giữ lại hoặc toàn bộ ô trên màn hình đã được giữ lại.
- Trò chơi bao gồm 35 dòng trả thưởng như sau: (hình 1–35, không có trong bản dán)

## 4. Chế độ vòng quay và mua tính năng

| Chế độ | Loại | Tính năng |
|---|---|---|
| Cơ bản | Cơ bản (Base spin) | - Bao gồm các tính năng thông thường trong trò chơi.<br>- Đánh boss ở chặng 0. |
| Cơ bản | Tăng cường (Ante spin) | - Tính năng tương tự vòng quay cơ bản.<br>- Tăng gấp 5 lần tỷ lệ xuất hiện 3 scatter trở lên trên màn hình. |
| Feature spin | Anh dũng (Heroic spin) | - Đánh boss ở chặng 5 và không chuyển lên chặng Endless.<br>- Đảm bảo ít nhất 5 Wild hoặc Vũ khí (có thể lẫn lộn) xuất hiện trên màn hình. Sự kiện chắc chắn được kích hoạt khi Wild được kết nối.<br>- Không xuất hiện Scatter để kích hoạt Bonus. |
| Feature spin | Săn kho báu (Treasure hunt) | - Không đánh boss nhưng có xuất hiện Scatter để kích hoạt Bonus.<br>- Toàn bộ các ô trên màn hình biến thành các biểu tượng trong tính năng kho báu. Đồng xu đảm bảo tối thiểu 1x. |
| Thưởng | Bonus | - Kích hoạt khi màn hình có 3 Scatter.<br>- Bắt đầu trò chơi ở Chặng 1 với 6 vòng quay miễn phí.<br>- Mỗi scatter thu thập trong chế độ được thêm 1 vòng quay miễn phí.<br>- Một số tiến độ trò chơi không bị đặt lại trong Bonus. |
| Thưởng | Super Bonus | - Kích hoạt khi màn hình có 4 Scatter.<br>- Bắt đầu trò chơi ở Chặng 2 với 7 vòng quay miễn phí. Tính năng bao gồm của cả Bonus.<br>- Đảm bảo ít nhất 3 Wild hoặc Vũ khí (có thể lẫn lộn) xuất hiện trong đầu mỗi vòng quay. |
| Thưởng | Epic Bonus | - Kích hoạt khi màn hình có 5 Scatter.<br>- Bắt đầu trò chơi ở Chặng 3 với 8 vòng quay miễn phí. Tính năng bao gồm của cả Super Bonus. Toàn bộ ô trên màn hình được làm sáng nền cho mục đích kích hoạt Treasure. Kích hoạt Treasure ngay khi bắt đầu như khi tiêu diệt toàn bộ boss chặng 2.<br>- Không xuất hiện xu Đồng trong quá trình quay vòng quay miễn phí (không tính khi kích hoạt Treasure đầu Epic Bonus).<br>- Đảm bảo luôn kích hoạt Hold and Spin khi thỏa điều kiện kết nối. |

- Ante spin: Trả 3 lần cược cơ bản để kích hoạt tăng khả năng ra 3 Scatter trở lên.
- Feature spin: Trả 500 lần cược cơ bản để được ngẫu nhiên: Heroic spin hoặc Treasure hunt.
- 3+ scatter: Trả 100 lần cược cơ bản để được tối thiểu 3 Scatter trên màn hình.
- 4+ scatter: Trả 300 lần cược cơ bản để được tối thiểu 4 Scatter trên màn hình.

## 5. Cơ chế đánh boss
- Cơ chế đánh boss trải qua từng chặng. Tổng cộng 7 chặng xuất hiện trong trò chơi như sau:

| Chặng | HP Từng Boss | Biểu tượng | Đảm bảo tối thiểu: Rương | Đảm bảo tối thiểu: Xu |
|---|---|---|---|---|
| 0 | 25 | Đầy đủ | Đồng | 0.2x |
| 1 | 30 - 40 | Đầy đủ | Đồng | 0.2x |
| 2 | 35 - 50 | Loại bỏ L1 | Đồng | 1x |
| 3 | 45 - 65 | Loại bỏ L2 | Bạc | 1x |
| 4 | 65 - 90 | Loại bỏ L3 | Vàng | 5x |
| 5 | 85 - 120 | Loại bỏ L4 | Kim cương | 20x |
| Endless | 350 - 400 | - | Kim cương | 20x |

  Ghi chú (ô gộp cột cuối):
  - Rương đồng chứa ít nhất 1 lượt quà.
  - Rương bạc chứa ít nhất 2 lượt quà.
  - Rương vàng trở lên chứa cả 3 lượt quà, trong đó có ít nhất 1 đồng xu.
  - Đồng xu trong rương tối thiểu phải cùng cấp với rương đang chứa.
  - Mỗi rương có cơ hội nâng cấp rương cao hơn, có thể nâng vượt cấp nhưng chỉ nâng được một lần.
  - Xu tối thiểu của bảng này không áp dụng cho xu trong rương.
- Ở chặng 0 đến chặng 5, Boss 1 nằm trên cột 1 và 2. Boss 2 nằm trên cột 3 và 4. Boss 3 nằm trên cột 5 và 6. Với chặng Endless, chỉ có duy nhất 1 boss trải dài trên cả 6 cột màn hình. Không có boss trong loại vòng quay Treasure hunt.
- Mỗi boss được gán với lượng máu (HP) cụ thể là bội số của 5 và bị tiêu diệt khi HP rơi về 0. Sau khi tiêu diệt toàn bộ boss trong 1 chặng (không áp dụng cho chặng 0 và Feature spin) thì chuyển lên chặng cao hơn khi qua vòng quay mới. Nếu tiêu diệt boss ở chặng Endless thì sẽ tiếp tục trong chặng này với boss mới có HP cao hơn hoặc bằng boss Endless trước đó.
- Mỗi boss gắn liền với một loại rương và khi tiêu diệt sẽ mở rương đó. Mỗi rương chứa lượt quà ngẫu nhiên gồm Đồng xu hoặc Power (áp dụng cho vòng quay sau). Tối đa 3 lượt quà xuất hiện ở mỗi rương. Nếu không trong chế độ Bonus thì rương chỉ có thể chứa Đồng xu.
- Các biểu tượng trả thưởng khi bị phá huỷ sẽ chuyển hóa thành sát thương tấn công lên boss trên cùng cột. Mỗi biểu tượng trả thưởng sẽ gây sát thương riêng lẻ và áp dụng duy nhất cho boss cùng cột. Chỉ số sát thương dựa theo bảng trả thưởng và chỉ nhân với hệ số sát thương từ Vũ khí.
- Vũ khí (ngoại trừ Cung tên) không gây sát thương trực tiếp cho boss mà có chức năng phá huỷ biểu tượng, từ đó gây sát thương gián tiếp. Mỗi loại Vũ khí chứa hệ số sát thương: 1x, 2x, 3x, 4x, 5x, 6x, 7x, 8x, 9x, 10x và nhân với chỉ số sát thương của các biểu tượng mà Vũ khí đó phá huỷ.
- Cung tên gây sát thương cho Boss ngẫu nhiên dựa vào HP tối đa của boss cùng cột ở chặng đó với cách tính là: Sát thương = 3 + HP tối đa x Hệ số hiệu chỉnh ngẫu nhiên (0.05x, 0.1x, 0.15x, 0.2x, 0.25x, 0.3x, 0.35x, 0.4x, 0.45x, 0.5x). Trong chặng Endless, sát thương của cung tên theo công thức bị chia 3 trước khi áp dụng. Chỉ số sát thương được làm tròn đến số nguyên gần nhất.
- Tính năng Đòn chí mạng (Last hit) cho phép mỗi khi gây sát thương có khả năng tiêu diệt boss ngay lập tức. Tỷ lệ HP sau khi gây sát thương trên HP tối đa càng thấp thì tỷ lệ kích hoạt tính năng càng cao và được tăng cường gấp đôi tỷ lệ nếu trong vòng quay cuối cùng (không có Scatter) của chế độ Bonus.
- Mỗi boss khi bị gây sát thương có tỷ lệ nhỏ rơi Wild thay thế cho biểu tượng trả thưởng cơ bản ngẫu nhiên trên các cột trải dài của boss hoặc Power được thu thập ngay.
- Các Power trong trò chơi bao gồm:

| Power | Tính năng |
|---|---|
| Thay thế (Replace) | Toàn bộ ô chứa biểu tượng trả thưởng cơ bản không xuất hiện ở tối thiểu 2 trên 3 cột đầu tiên được chuyển thành biểu tượng ngẫu nhiên khác với biểu tượng ban đầu trong mỗi ô. |
| Cải tiến (Enhance) | Chọn 1 biểu tượng trả thưởng cơ bản ngẫu nhiên trên màn hình. Toàn bộ các ô chứa biểu tượng này áp dụng hệ số ngẫu nhiên (2x, 3x, 4x, 5x, 10x, 15x, 20x, 25x, 50x, 100x). Nếu trên một dòng gồm nhiều ô chứa hệ số loại này thì các hệ số được cộng với nhau trước khi nhân với mức trả thưởng dòng. |
| Nâng cấp (Upgrade) | Các ô chứa 1 biểu tượng trả thưởng cơ bản ngẫu nhiên trên màn hình đều được chuyển thành 1 trong hai loại biểu tượng sau: H5 hoặc Wild. |
| Biến đổi (Transform) | Chuyển 2 - 5 ô bất kì (ngoại trừ Wild, Vũ khí và Scatter khi không trong chế độ Bonus) trên màn hình thành Wild. |
| Phá huỷ (Destroy) | Toàn bộ các biểu tượng trên màn hình (ngoại trừ Wild và Scatter khi không trong chế độ Bonus) đều bị phá huỷ. |

- Các biểu tượng chuyển hoá bởi Power (ngoại trừ Destroy) không được tính là bị phá huỷ.
- Sau khi toàn bộ boss trong chặng bị tiêu diệt và vòng quay không còn hành động nào diễn ra thì kích hoạt Tính năng Kho báu (Treasure). Khi này, những ô đã chứa Scatter kích hoạt chế độ Bonus (không tính Scatter trong Bonus) hoặc biểu tượng trả thưởng cơ bản đã bị phá huỷ (không tính do bị phá huỷ do Destroy, Vũ khí) trở thành một trong các biểu tượng ngẫu nhiên sau:
  - Đồng xu (Coin): Giới hạn theo hệ số thưởng đồng xu tối thiểu quy định từng chặng.
  - Nam châm (Magnet): Thu thập toàn bộ các hệ số từ đồng xu và nam châm khác trên màn hình. Các ô bị thu thập sẽ tiếp tục xuất hiện lại các biểu tượng.
  - Cỏ bốn lá (Clover): Chứa hệ số 2x, 3x, 4x, 5x, 10x, 20x. Hệ số này nhân với các ô có chứa hệ số thưởng xung quanh trong phạm vi 3x3.
  - Cỏ bốn lá vàng (Golden clover): Tương tự Clover nhưng hệ số nhân với các ô chứa hệ số thưởng trên toàn màn hình.
  - Ngôi sao (Star): Chứa hệ số thưởng tương tự như hệ số thưởng của đồng xu, giới hạn theo hệ số thưởng đồng xu tối thiểu quy định từng chặng. Khi kích hoạt, hệ số thưởng từ Star sẽ cộng vào hệ số thưởng của từng Đồng xu và Nam châm trên màn hình.
  - Hệ số toàn cục (Global multiplier): Chứa hệ số 2x, 3x, 4x, 5x, 6x, 7x, 8x, 9x, 10x. Áp dụng cho trả thưởng dòng và trả thưởng Treasure. Hệ số toàn cục ban đầu là 0x (nhưng tính theo mục đích trả thưởng là 1x). Hệ số toàn cục mới được thu thập sẽ cộng vào hệ số toàn cục hiện có.
  - Scatter: Tương tự như Scatter thông thường. Trong chế độ quay không Bonus, Scatter từ tính năng Treasure được tính kết hợp với các Scatter ở các ô không trong tính năng Treasure cho mục đích kích hoạt Bonus. Những ô trong chế độ quay trong Bonus trước khi kích hoạt tính năng Treasure mà là Scatter thì sẽ tiếp tục là Scatter mà không trở thành biểu tượng khác.

## 6. Thứ tự hành động và quy tắc trả thưởng
- Các định nghĩa trong trò chơi:
  - Dự trữ: Trạng thái thu thập Power nhưng chưa được kích hoạt.
  - Cược cơ bản: Mức cược gốc của vòng quay cơ bản (không tính mua tính năng).
- Tại bất kì thời điểm nào trong vòng quay:
  - Mỗi loại Power chỉ có thể dự trữ tối đa 3 cái. Nếu một loại Power đã được dự trữ đủ số tối đa nhưng chưa kích hoạt thì Wild sẽ không xảy ra sự kiện thu thập Power loại đó.
  - Tính năng Last hit kiểm tra khả năng kích hoạt mỗi lần gây sát thương và được tính độc lập theo từng boss, khi kích hoạt không ảnh hưởng đến các boss còn lại. Mỗi boss khi bị gây sát thương có tỷ lệ nhỏ rơi Wild thay thế cho biểu tượng trả thưởng cơ bản ngẫu nhiên trên các cột trải dài của boss hoặc Power được thu thập ngay.
  - Các biểu tượng trả thưởng kết nối xuất hiện viền sáng (hoặc làm nổi bật). Những ô thỏa mãn điều kiện Treasure được làm sáng nền.
  - Nếu kích hoạt Hold and Spin thì các ô giữ lại có thêm viền khung. Không trả thưởng hay kích hoạt bất kì gì trong khi chế độ Hold and Spin đang diễn ra.
  - Khoản trả thưởng từ dòng, boss và Treasure được nhân với cược cơ bản trước khi cộng vào bộ đếm trả thưởng.
  - Khi bộ đếm trả thưởng vòng quay kết hợp bộ đếm trả thưởng toàn cục đạt hoặc vượt mức 25.000 lần cược cơ bản thì chuyển sang tổng kết vòng quay ngay lập tức. Với Treasure và rương, kiểm tra điều kiện này theo từng bước và chuyển sang tổng kết vòng quay nếu đạt hoặc vượt mức Maxwin dù tính năng còn có thể tiếp tục.
  - Đồng xu khi được nhân với Global multiplier và thay đổi hệ số thưởng thì cập nhật loại đồng xu theo hệ số thưởng mới sau khi thay đổi (Dưới 5x là xu Đồng; Từ 5x đến dưới 20x là xu Bạc; Từ 20x đến dưới 100x là xu Vàng; Từ 100x đến dưới 25.000x là xu Kim cương; Từ 25.000x trở lên là xu Maxwin). Khi có đồng xu Maxwin trên màn hình thì chuyển sang tổng kết vòng quay với các hiệu ứng từ Nice win đến Maxwin.
  - Nếu xuất hiện Power khi mở rương trong Bonus mà không còn vòng quay nữa thì mặc nhiên tiếp tục cộng thêm 1 vòng quay miễn phí để quay thêm 1 lần nữa.
  - Trong Treasure, nam châm chỉ xuất hiện khi trên màn hình có ít nhất 2 ô là đồng xu trong tính năng này. Đảm bảo ít nhất 1 ô là đồng xu nếu là loạt xuất hiện biểu tượng đầu tiên khi kích hoạt tính năng, ngoại trừ khi tất cả các ô sáng nền đều là các Scatter trong chế độ không Bonus.
- Thứ tự các sự kiện trong vòng quay diễn ra như sau (nếu không diễn ra thì bỏ qua):
  1. Scatter trong Bonus kích hoạt cộng lượt quay đồng thời và làm tối các biểu tượng này.
  2. Power Replace được kích hoạt 1 lần nếu trên màn hình có biểu tượng trả thưởng cơ bản thoả mãn điều kiện thay thế. Nếu có thể kích hoạt được lần nữa thì sẽ kích hoạt tiếp.
  3. Các Power như sau lần lượt được kích hoạt: Enhance, Upgrade, Transform. Nếu dự trữ nhiều power cùng loại thì được kích hoạt lần lượt trước khi chuyển sang Power tiếp theo.
  4. Các biểu tượng Wild được kết nối kích hoạt sự kiện (nếu có) theo thứ tự ô. Các đồng xu rơi từ sự kiện này trước khi được thu thập sẽ nhân với Global multiplier và cộng vào bộ đếm trả thưởng vòng quay.
  5. Các biểu tượng trả thưởng kết nối theo dòng được kích hoạt đồng thời và cộng lại để trả thưởng. Khoản trả thưởng lần lượt được nhân với tổng hệ số từ Enhance, hệ số từ Wild nhân thưởng và cuối cùng là với Global multiplier. Hệ số từ Enhance trong ô biến mất khi ô bị phá huỷ (hệ số giữ nguyên khi chuyển biểu tượng do Upgrade, Transform hay Replace). Sau đó cộng khoản trả thưởng vào bộ đếm trả thưởng vòng quay.
  6. Toàn bộ biểu tượng trả thưởng cơ bản trên màn hình trùng với những biểu tượng được kết nối, Wild được kết nối bị phá huỷ và gây sát thương. Scatter trong Bonus đã bất hoạt cũng sẽ bị phá huỷ đồng thời. Xuất hiện biểu tượng mới trên những ô bị phá huỷ và quay lại bước (1). Sau chu trình quay lại mà từ bước (1) đến bước (6) không diễn ra hành động thì chuyển qua bước (7).
  7. Kích hoạt các Vũ khí lần lượt theo thứ tự ô. Sau khi toàn bộ Vũ khí đã kích hoạt, xuất hiện các biểu tượng mới trên những ô bị phá huỷ và quay lại bước (1). Sau chu trình quay lại mà từ bước (1) đến bước (7) không diễn ra hành động thì chuyển qua bước (8).
  8. Power Destroy được kích hoạt 1 lần và quay lại bước (1). Sau chu trình quay lại mà từ bước (1) đến bước (8) không diễn ra hành động thì chuyển qua bước (9).
  9. Kích hoạt rương từ boss đã tiêu diệt và thu thập quà theo thứ tự từ trái sang phải, đồng xu trước khi được thu thập sẽ nhân với Global multiplier và cộng vào bộ đếm trả thưởng vòng quay. Nếu toàn bộ boss trong chặng bị tiêu diệt thì kích hoạt Treasure và sau đó tổng kết toàn bộ vòng quay.
- Thứ tự các sự kiện trong tính năng Treasure thực hiện như sau:
  1. Xuất hiện các biểu tượng trong Treasure trên những ô được làm sáng nền.
  2. Xuất hiện các biểu tượng trong Treasure mới trên những ô làm trống bởi nam châm hoặc các biểu tượng Star, Clover và Golden Clover đã được kích hoạt.
  3. Kích hoạt Star theo thứ tự ô. Hệ số thưởng được cộng theo thứ tự ô.
  4. Kích hoạt Clover theo thứ tự ô. Hệ số nhân áp dụng đồng thời.
  5. Kích hoạt Golden clover theo thứ tự ô. Hệ số nhân lần lượt theo thứ tự ô.
  6. Nam châm thu thập các hệ số thưởng từ những ô khác có chứa hệ số thưởng (hệ số khi mới xuất hiện của mỗi nam châm là 0x). Nếu có nhiều nam châm thì ưu tiên kích hoạt nam châm theo thứ tự ô và quay về bước (2) trước khi kích hoạt nam châm tiếp theo.
  7. Thu thập toàn bộ các hệ số thưởng trên màn hình từ Treasure và nhân với hệ số Global multiplier sau đó cộng vào bộ đếm trả thưởng vòng quay và kết thúc tính năng.
- Tổng kết vòng quay thực hiện như sau:
  - Dựa vào bộ đếm trả thưởng vòng quay thực hiện theo thứ tự sau (chỉ chuyển đến bước tiếp theo sau khi đã thực hiện hiệu ứng của bước trước):
    (1) Nếu bộ đếm trả thưởng vòng quay đạt mốc 20 lần cược cơ bản trở lên thì xuất hiện hiệu ứng Nice win.
    (2) Nếu bộ đếm trả thưởng vòng quay đạt mốc 50 lần cược cơ bản trở lên thì xuất hiện hiệu ứng Big win.
    (3) Nếu bộ đếm trả thưởng vòng quay đạt mốc 100 lần cược cơ bản trở lên thì xuất hiện hiệu ứng Super win.
    (4) Nếu bộ đếm trả thưởng vòng quay đạt mốc 500 lần cược cơ bản trở lên thì xuất hiện hiệu ứng Mega win.
    (5) Nếu bộ đếm trả thưởng vòng quay đạt mốc 25.000 lần cược cơ bản trở lên thì xuất hiện hiệu ứng Maxwin.
  - Nếu vòng quay thuộc chế độ Bonus thì giữ nguyên tiến độ về Chặng, HP Boss, Global multiplier, các ô làm sáng nền và bộ đếm trả thưởng toàn cục cho đến khi kết thúc. Bộ đếm trả thưởng toàn cục được cập nhật cộng thêm bộ đếm trả thưởng vòng quay và bộ đếm trả thưởng vòng quay được đặt lại. Khi kết thúc chế độ Bonus, xuất hiện hiệu ứng Total win nhằm tổng kết bộ đếm trả thưởng toàn cục (ngoại trừ khi trong Bonus đã kích hoạt hiệu ứng Maxwin).
  - Nếu vòng quay không thuộc chế độ Bonus thì kiểm tra số Scatter trên màn hình, đủ số lượng theo yêu cầu thì kích hoạt loại Bonus tương ứng, giữ nguyên tiến độ về bộ đếm trả thưởng toàn cục (bộ đếm trả thưởng vòng quay trong chế độ không Bonus trở thành bộ đếm vòng quay toàn cục). Đặt lại Global multiplier và các ô làm sáng nền ngoại trừ các ô chứa Scatter kích hoạt chế độ Bonus.

## 7. Lưu ý
- Các rương cấp bậc càng cao thì khả năng xuất hiện đồng xu trong lượt quà càng thấp.
- Cột 4, 5 và 6 có tỷ lệ xuất hiện nhiều Cung tên hơn một chút để đảm bảo khả năng tiêu diệt boss và tỷ lệ tiêu diệt boss cuối cùng trong chặng của cả 3 boss cũng xấp xỉ bằng nhau.
- Không xuất hiện thêm Vũ khí kể từ khi toàn bộ boss trong chặng bị tiêu diệt và Cung tên trong các cột có boss đã bị tiêu diệt.
- Mục về bảng trả thưởng và HP của boss là cố định, không chỉnh sửa. Nếu có chỉnh sửa thì phải hỏi ý kiến trước, đề xuất bộ số mới và được duyệt qua. Các mục về tỷ lệ phân bổ hệ số, biểu tượng,... cho phép sửa tùy ý nhưng phải báo nếu việc sửa gây biến động lớn.
- Lưu ý và cảnh báo những mâu thuẫn hoặc chỗ tối nghĩa cần làm rõ trong luật.
- Đề xuất thêm những cách có thể làm gộp lại, loại bỏ tính năng trùng lặp hoặc gần giống nhau để giảm thời gian chạy cho một lần quay mà có thể không làm ảnh hưởng đến cảm giác chơi.

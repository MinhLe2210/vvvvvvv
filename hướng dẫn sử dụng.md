Hướng dẫn sử dụng

1. CSV Batch

- Chuẩn bị file CSV có header và một cột chứa nội dung bài viết. Mặc định app đọc cột `content`; nếu file dùng tên cột khác, sửa ô "Tên cột content".
- Prompt bước 1 dùng để trả về `result places` và `label`. Prompt này nằm trực tiếp trên UI, không lấy từ key `Location` trong `cms_prompt.json`.
- Prompt bước 2 được chia theo từng tab label để dễ chỉnh. App chỉ chạy prompt bước 2 khi `result places = true`.
- Kết quả trả về đúng 4 cột: `content`, `result places`, `label`, `final result`.
- Cột `label` hiển thị nhãn tiếng Việt tương ứng với một trong các topic: Known, Alert, Social Order, SAR, Accident, Complaint, Security, Child, Fiction, SanitationPollution, Cybersecurity, Movement, Other.
- Sau khi chạy, có thể xem bảng kết quả trên UI hoặc tải file CSV kết quả.

2. Custom Prompt Lab

- Dùng để thử nhanh một prompt riêng với schema mong muốn.
- Chọn schema, nhập system prompt, nhập user content, rồi bấm "Run prompt".

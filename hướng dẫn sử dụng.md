Hướng dẫn sử dụng

1. CSV Batch

- Chuẩn bị file CSV có header và cột `content`. App tự đọc cột này, không cần nhập tên cột.
- Nếu muốn test nhanh prompt bước 1 theo tỉnh/thành, nhập danh sách vào ô `Places override`. Khi có override, `result places` chỉ trả `true` nếu nội dung khớp một trong các địa điểm đó.
- Mặc định app chạy tất cả dòng trong CSV. Chỉ nhập giới hạn số dòng khi muốn test nhanh một phần file.
- Prompt bước 1 dùng để trả về `result places` và `label`. Prompt này nằm trực tiếp trên UI, không lấy từ key `Location` trong `cms_prompt.json`.
- Prompt bước 2 được chia theo từng tab label để dễ chỉnh. App chỉ chạy prompt bước 2 khi `result places = true`.
- Kết quả trả về đúng 4 cột: `content`, `result places`, `label`, `final result`.
- Cột `label` hiển thị nhãn tiếng Việt tương ứng với một trong các topic: Known, Alert, Social Order, SAR, Accident, Complaint, Security, Child, Fiction, SanitationPollution, Cybersecurity, Movement, Other.
- Sau khi chạy, có thể xem bảng kết quả trên UI hoặc bấm `Download CSV kết quả` để tải file CSV kết quả.
- Có thể bấm `Download CSV prompts đã sửa` để tải bộ prompt đang chỉnh trên UI, gồm prompt bước 1, places override và các prompt bước 2 theo label.

2. Custom Prompt Lab

- Dùng để thử nhanh một prompt riêng với schema mong muốn.
- Chọn schema, nhập system prompt, nhập user content, rồi bấm "Run prompt".

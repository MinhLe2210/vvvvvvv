Hướng dẫn sử dụng:

1. Location Prompt:

1.1 Field_override

Nếu có places_override → dùng places_override, còn nếu không có thì sẽ dùng Event_id như trong hệ thống.
Ví dụ prompt default của event có:
"Hồ Hoàn Kiếm, Phường Hàng Trống, Quận Hoàn Kiếm"
Nhưng bạn muốn test nhanh với địa điểm khác mà không sửa file JSON, thì nhập vào places_override:
"Cầu Giấy, Mỹ Đình, Nam Từ Liêm"
1.2 Event ID
- Đổi event ID theo yêu cầu địa điểm

1.3 Content
- truyền vào bài viết để chạy thử prompt đã chỉnh sửa phía trên

2. Custom prompt Lab
2.1 Schema
- Để default là RawText không cần thay đổi
  
2.2 System Prompt
- Điền vào prompt muốn tinh chỉnh

2.3 User content
- Điền vào nội dung bài viết.
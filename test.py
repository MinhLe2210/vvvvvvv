import requests

URL = "http://127.0.0.1:25001/v1/cms-validation"

headers = {"Content-Type": "application/json"}
content = "Công an TP.HCM đề nghị truy tố ca sĩ Chi Dân về tội tổ chức sử dụng tr.ái ph.ép chất c.ấm 👇👇"
# content = "China: nổ nhà máy pháo hoa khiến cho 21 người thiêt mạng"
# content = "lũ quét ở huế  "
# content = "khẩn cấp cháy nhà ở bình dương"
res = requests.post(
    URL,
    headers=headers,
    json={
        "content": content,
        "event_id": "47c89263-1248-4c56-8a0b-b213a7fdd5c4",
        "title": "",
        "description": "",
        "display_name": "",
        "request_id": "abc"
    },
)
print(res.json())


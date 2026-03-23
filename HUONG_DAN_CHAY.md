# Hướng dẫn chạy Parking LPR Service

## 1. Cài đặt
```bash
pip install -r requirements.txt
```

## 2. Chạy server
```bash
python main.py
```

## 3. Gọi API nhận diện biển số

### Cách 1: Dùng script test có sẵn (nhanh)
Mở terminal **khác**, chạy:
```bash
python test_api.py test-images/image8.jpg
```
Thay `image8.jpg` bằng tên ảnh bất kỳ trong thư mục `test-images/`.

### Cách 2: Gọi API trực tiếp (dùng thật)

**Upload file ảnh:**
```
POST http://localhost:8000/api/v1/lpr/recognize
Content-Type: multipart/form-data
Body: file = <file ảnh>
```

**Gửi ảnh Base64:**
```
POST http://localhost:8000/api/v1/lpr/recognize-base64
Content-Type: application/json
Body: { "image_base64": "data:image/jpeg;base64,..." }
```

## 4. Kết quả trả về (JSON)
```json
{
  "success": true,
  "plate_number": "51F88686",
  "message": "Xe 51F88686 vào.",
  "status": "in",
  "entry_time": "2026-03-23T08:10:26",
  "exit_time": null,
  "fee": 0.0,
  "duration_hours": 0.0
}
```
- Lần đầu gửi ảnh → xe **vào** (`status: "in"`)
- Gửi lại cùng biển số → xe **ra** (`status: "out"`) kèm phí tính theo giờ.

# 🚀 Hướng Dẫn Chạy Smart Parking (2 Terminal Mode)

Hệ thống đã được thiết kế lại theo ý bạn: **Gọn nhẹ nhưng vẫn chuẩn kiến trúc**.

### 1. Terminal 1: Backend Hub (Core + LPR)
```powershell
.\venv\Scripts\activate
python main.py
```
*   **Hệ thống sẽ khởi chạy:**
    *   **API Hub (Cổng 8000)**: Xử lý cả Business Logic và AI (LPR).
    *   Tự động gọi `GET /capture` sang camera (điện thoại) khi có yêu cầu.
*   *Lưu ý:* Nếu camera điện thoại offline, LPR sẽ tự động lấy ảnh trong `tests/image` làm mẫu để test.

### 2. Terminal 2: Test Interface (Mock HW)
```powershell
.\venv\Scripts\activate
python tests/mock_hw.py
```

---
## 🛠 Các lệnh Test (Trong Terminal 2):
*   **Bấm 1**: Xe VÀO. (Core gọi LPR chụp ảnh -> AI đọc biển số -> Lưu DB).
*   **Bấm 2**: Xe RA. (Core gọi LPR -> Tính tiền dựa trên phí đã cấu hình).
*   **Bấm 3/4**: Giả lập tình trạng Slot 1 (Đầu cảm biến IR của ESP32).
*   **Bấm 5**: Xác nhận thanh toán xong (Để mở barrier cổng ra).

## 📡 Tài liệu API:
- **Swagger UI**: http://localhost:8000/docs
- **Base URL**: `http://localhost:8000/api/v1`

---

## 🔍 Lệnh gọi API Test (Dùng cURL hoặc PowerShell):

### 1. Nhận diện từ Camera (Gọi là chụp luôn)
**cURL:**
```bash
curl -X POST http://localhost:8000/api/v1/recognize/camera
```
**PowerShell:**
```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/recognize/camera"
```

### 2. Nhận diện từ file ảnh Local
**cURL (Theo tên file trong thư mục `tests/image`):**
```bash
curl -X POST http://localhost:8000/api/v1/recognize/local \
     -H "Content-Type: application/json" \
     -d '{"file_name": "1.png"}'
```
**PowerShell:**
```powershell
$body = @{ file_name = "1.png" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/recognize/local" -ContentType "application/json" -Body $body
```

### 3. Xem danh sách các phiên (Sessions) đã nhận diện
**cURL:**
```bash
curl -X GET http://localhost:8000/api/v1/recognize/sessions
```
**PowerShell:**
```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/api/v1/recognize/sessions" | ConvertTo-Json -Depth 5
```

### 4. Xóa sạch lịch sử Sessions
**cURL:**
```bash
curl -X DELETE http://localhost:8000/api/v1/recognize/sessions
```

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/recognize/camera" | ConvertTo-Json -Depth 2


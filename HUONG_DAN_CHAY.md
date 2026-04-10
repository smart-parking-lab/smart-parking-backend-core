# Hướng dẫn chạy Smart Parking — LPR Backend

## 1. Chuẩn bị

- Python 3.11+ (khớp `Dockerfile`).
- Tạo virtualenv và cài dependency:

```powershell
cd E:\HocTap\AI\Doan\smart-parking-backend-core
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

- Copy cấu hình: tạo file `.env` ở thư mục gốc project (đã có trong `.gitignore`). Tham khảo các biến trong `src/app/core/config.py`:
  - `CAMERA_URL`, `CAMERA_ROTATE_DEG`
  - `DATABASE_URL`, Cloudinary (nếu dùng)
  - `SERVER_HOST`, `SERVER_PORT` (mặc định local thường `127.0.0.1` và `8000`)

**Base URL API local:** `http://<SERVER_HOST>:<SERVER_PORT>/api/v1`  
Ví dụ mặc định: `http://127.0.0.1:8000/api/v1`

Swagger: `http://127.0.0.1:8000/docs` (đổi port nếu bạn đổi `SERVER_PORT`).

---

## 2. Chạy backend trên máy (development)

```powershell
.\venv\Scripts\activate
python main.py
```

Log sẽ in địa chỉ API theo `SERVER_HOST` / `SERVER_PORT` trong `.env`.

---

## 3. Camera: hai kiểu cấu hình

### 3.1. Backend và camera cùng mạng LAN (chạy local)

Trong `.env` trỏ thẳng sang app camera (điện thoại), ví dụ:

```env
CAMERA_URL=http://192.168.1.41:8080/shot.jpg
```

Không cần proxy/ngrok.

### 3.2. Backend trên cloud (Render) — bắt buộc qua proxy + ngrok

Server trên internet **không** vào được IP dạng `192.168.x.x`. Cách làm:

1. Trên **một máy trong LAN** (cùng Wi‑Fi với camera): chạy **camera proxy** — nó lấy ảnh từ camera rồi phục vụ cổng local.
2. Chạy **ngrok** để mở HTTPS công khai vào cổng đó.
3. Trên **Render**, đặt biến môi trường `CAMERA_URL` = URL ngrok + `/shot.jpg`.

**Vì sao proxy dùng cổng 8090 còn camera dùng 8080?**  
8080 là cổng **app camera**; 8090 là cổng **proxy trên PC bạn** (tránh trùng cổng). `ngrok` tunnel vào cổng proxy (8090), proxy mới gọi `192.168.x.x:8080`.

### Chạy proxy (terminal 1)

```powershell
.\venv\Scripts\activate
python scripts/camera_proxy.py
```

Proxy đọc `.env`: `CAMERA_UPSTREAM_URL` (URL thật của camera), `CAMERA_PROXY_PORT` (mặc định `8090`).

### Chạy ngrok (terminal 2)

```powershell
ngrok http 8090
```

(Đổi `8090` nếu bạn đổi `CAMERA_PROXY_PORT`.)

### Lấy URL HTTPS đầy đủ

- Kéo rộng cửa sổ terminal để thấy hết dòng **Forwarding**, hoặc
- Mở trình duyệt: [http://127.0.0.1:4040](http://127.0.0.1:4040), hoặc
- PowerShell:

```powershell
(Invoke-RestMethod "http://127.0.0.1:4040/api/tunnels").tunnels |
  Where-Object { $_.proto -eq "https" } |
  Select-Object -ExpandProperty public_url
```

URL có dạng: `https://<subdomain>.ngrok-free.app` hoặc `https://<subdomain>.ngrok-free.dev`.

### Render — biến môi trường

Trong **Dashboard → Service → Environment**, thêm (hoặc sửa):

| Key | Giá trị ví dụ |
|-----|----------------|
| `CAMERA_URL` | `https://<subdomain>.ngrok-free.dev/shot.jpg` |

**Bắt buộc** có `/shot.jpg` ở cuối. Lưu → chờ deploy xong.

Mỗi lần tắt/mở lại ngrok (gói miễn phí), subdomain thường **đổi** → cần cập nhật lại `CAMERA_URL` trên Render và deploy lại.

### Kiểm tra nhanh

1. Trình duyệt mở: `https://<subdomain>.../shot.jpg` — thấy ảnh là proxy + ngrok ổn.
2. Gọi API Render (sau khi deploy):

```powershell
Invoke-RestMethod -Method Post -Uri "https://<ten-service>.onrender.com/api/v1/recognize/camera" | ConvertTo-Json -Depth 5
```

Giữ **proxy** và **ngrok** chạy trên máy khi test; tắt một trong hai thì URL không còn ảnh.

---

## 4. Deploy Docker / Render (port)

- Container lắng nghe theo biến `PORT` của Render; project dùng `SERVER_PORT=${PORT:-10000}` trong `CMD` Dockerfile.
- Trên Render không dùng file `.env` trong repo — khai báo biến trong **Environment** (giống `CAMERA_URL`, `DATABASE_URL`, v.v.).

---

## 5. Gọi API thử (PowerShell)

Đổi `8000` theo `SERVER_PORT` trong `.env` nếu khác.

### Nhận diện từ camera

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/recognize/camera"
```

### Nhận diện từ ảnh local (JSON)

```powershell
$body = @{ file_name = "1.png" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/recognize/local" `
  -ContentType "application/json" -Body $body
```

### Danh sách sessions

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/v1/recognize/sessions" | ConvertTo-Json -Depth 5
```

### Xóa sessions

```powershell
Invoke-RestMethod -Method Delete -Uri "http://127.0.0.1:8000/api/v1/recognize/sessions"
```

---

## 6. Cấu hình Cloudinary (tùy chọn)

Khi có đủ 3 biến, ảnh chụp sẽ được upload lên Cloudinary và API trả về URL dạng `https://res.cloudinary.com/...`. Nếu thiếu biến, backend vẫn chạy và lưu file vào `storage/captures/` (log cảnh báo “fallback local”).

### Bước 1 — Tạo tài khoản và lấy khóa

1. Vào [Cloudinary](https://cloudinary.com/) → đăng ký / đăng nhập.
2. Vào **Dashboard** (Programmable Media).
3. Ở **Account Details** bạn sẽ thấy:
   - **Cloud name** — ví dụ `dxxxxxxx`
   - **API Key** — dãy số
   - **API Secret** — bí mật (chỉ dùng server-side, không đưa vào frontend)

### Bước 2 — Ghi vào `.env` (máy dev)

Trong thư mục gốc project, thêm hoặc sửa:

```env
CLOUDINARY_CLOUD_NAME=dxxxxxxx
CLOUDINARY_API_KEY=123456789012345
CLOUDINARY_API_SECRET=your_api_secret_here
```

Lưu file → chạy lại `python main.py`. Gọi API nhận diện; trong log nên thấy dòng kiểu `☁️ Đã upload ảnh Cloudinary: https://...` thay vì cảnh báo thiếu cấu hình.

### Bước 3 — Thêm trên Render (production)

1. **Dashboard** → service `smart-parking-backend-core` → **Environment**.
2. **Add Environment Variable** (hoặc Edit), thêm **3 biến** với **cùng tên** như trên và giá trị từ Dashboard Cloudinary.
3. **Save** → chờ deploy xong.

Render **không** đọc file `.env` trong repo; biến chỉ có tác dụng khi khai báo ở đây.

### Kiểm tra

- Sau một request nhận diện có lưu ảnh: vào Cloudinary **Media Library** — thư mục `captures` (hoặc tên `folder` trong code) sẽ có ảnh mới.
- Nếu vẫn lưu local: kiểm tra đúng chính tả tên biến, không thừa dấu cách, và đã redeploy sau khi sửa env.

---

## 7. cURL (tùy chọn)

```bash
curl -X POST http://127.0.0.1:8000/api/v1/recognize/camera
```

```bash
curl -X POST http://127.0.0.1:8000/api/v1/recognize/local \
  -H "Content-Type: application/json" \
  -d "{\"file_name\": \"1.png\"}"
```

---

## 8. Bảo mật

- Không commit file `.env` (đã ignore).
- Không chia sẻ public: khóa Supabase, Cloudinary, chuỗi kết nối database.

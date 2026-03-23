import requests
import json
import sys

image_path = "test-images/image8.jpg"
if len(sys.argv) > 1:
    image_path = sys.argv[1]

url = "http://localhost:8000/api/v1/lpr/recognize"

print(f"Đang nhận diện biển số từ ảnh: {image_path}")
print("-" * 50)

try:
    with open(image_path, "rb") as f:
        files = {"file": (image_path, f, "image/jpeg")}
        response = requests.post(url, files=files)

    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Lỗi: {e}")

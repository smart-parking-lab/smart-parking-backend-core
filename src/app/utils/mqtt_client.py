import paho.mqtt.client as mqtt
import json
import time
import logging
import os
import asyncio
import threading
from dotenv import load_dotenv
from app.service.parking_service import handle_lpr
from app.utils.camera import capture_image_from_camera

load_dotenv()

logger = logging.getLogger("mqtt_client")

# Cấu hình MQTT từ .env
MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT"))
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID")

# Topic phải khớp 100% với ESP32 (arduino_hardware.ino)
TOPIC_SENSOR = os.getenv("TOPIC_SENSOR")


class MQTTClient:

    def __init__(self, on_gate_event=None):
        """
        Args:
            on_gate_event: Callback khi phát hiện xe tại cổng.
                           Signature: on_gate_event(gate: str, status: str)
                           gate = "GATE_IN" | "GATE_OUT"
                           status = "CO_XE" | "TRONG"
        """
        self._on_gate_event = on_gate_event
        self._client = mqtt.Client(client_id=MQTT_CLIENT_ID)
        self._client.on_connect = self._handle_connect
        self._client.on_message = self._handle_message
        self._client.on_disconnect = self._handle_disconnect
        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def _handle_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"✅ MQTT đã kết nối broker ({MQTT_BROKER}:{MQTT_PORT})")
            client.subscribe(TOPIC_SENSOR, qos=1)
            logger.info(f"🎧 Đang lắng nghe topic: {TOPIC_SENSOR}")
            self._is_connected = True
        else:
            logger.error(f"❌ MQTT kết nối thất bại, mã lỗi: {rc}")

    def _handle_disconnect(self, client, userdata, rc):
        self._is_connected = False
        if rc != 0:
            logger.warning(f"⚠️ MQTT mất kết nối bất ngờ (rc={rc}), đang thử kết nối lại...")

    def _handle_message(self, client, userdata, msg):
        """Xử lý message từ ESP32 trên topic sensor."""
        try:
            payload = msg.payload.decode("utf-8")
            logger.info(f"📩 MQTT nhận: topic={msg.topic} | payload={payload}")

            data = json.loads(payload)
            sensor = data.get("sensor", "")
            status = data.get("status", "")
            
            # Khi GATE_IN hoặc GATE_OUT phát hiện có xe → gọi handle_lpr
            if sensor in ("GATE_IN", "GATE_OUT") and status == "CO_XE":
                logger.info(f"🚨 Phát hiện xe tại {sensor} - kích hoạt LPR!")
                # Gọi callback cũ nếu có
                if self._on_gate_event:
                    self._on_gate_event(sensor, status)
                # Gọi handle_lpr trong thread riêng (vì MQTT callback là sync)
                threading.Thread(
                    target=self._trigger_lpr,
                    args=(sensor,),
                    daemon=True
                ).start()
        except json.JSONDecodeError:
            logger.error("⚠️ Message không phải JSON hợp lệ")
        except Exception as e:
            logger.error(f"❌ Lỗi xử lý MQTT message: {e}")

    def _trigger_lpr(self, gate: str):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def _run():
                image_bytes, filename, content_type = await capture_image_from_camera(gate)
                result = await handle_lpr(image_bytes, filename, content_type)
                logger.info(f"✅ LPR hoàn tất tại {gate}: {result}")

            loop.run_until_complete(_run())
        except Exception as e:
            logger.error(f"❌ Lỗi khi trigger LPR tại {gate}: {e}")
        finally:
            loop.close()

    def connect(self):
        """Kết nối tới MQTT broker và bắt đầu vòng lặp nền."""
        try:
            self._client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            self._client.loop_start()
            logger.info("🔄 MQTT loop đã khởi động (background thread)")
        except Exception as e:
            logger.error(f"❌ Không thể kết nối MQTT: {e}")

    def disconnect(self):
        """Ngắt kết nối MQTT."""
        self._client.loop_stop()
        self._client.disconnect()
        self._is_connected = False
        logger.info("🔌 Đã ngắt kết nối MQTT")

mqtt_client = MQTTClient()
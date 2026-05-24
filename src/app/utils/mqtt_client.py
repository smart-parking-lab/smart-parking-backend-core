import paho.mqtt.client as mqtt
import json
import time
import logging
import os
import asyncio
import threading
from dotenv import load_dotenv

from app.schemas.invoices import InvoicePay
from app.schemas.parking_slots import ParkingSlotStatusUpdate
from app.utils.supabase import SessionLocal
from app.utils.http_client import get_sync_client

load_dotenv()

logger = logging.getLogger("mqtt_client")

# Cấu hình MQTT từ .env
MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT"))
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID")

TOPIC_SENSOR = os.getenv("TOPIC_SENSOR")
TOPIC_CONTROL = os.getenv("TOPIC_CONTROL")

class MQTTClient:

    def __init__(self, on_gate_event=None):
        self._on_gate_event = on_gate_event
        self._client = mqtt.Client(client_id=MQTT_CLIENT_ID)
        self._client.on_connect = self._handle_connect
        self._client.on_message = self._handle_message
        self._client.on_disconnect = self._handle_disconnect
        self._is_connected = False
        self.loop = None

    def set_loop(self, loop):
        self.loop = loop

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def _handle_connect(self, client, userdata, flags, rc):
        if rc == 0:
            msg = f"✅ MQTT đã kết nối broker ({MQTT_BROKER}:{MQTT_PORT})"
            logger.info(msg)
            print(msg)
            client.subscribe([
                (TOPIC_SENSOR, 1),
                (TOPIC_CONTROL, 1)
            ])
            self._is_connected = True
        else:
            logger.error(f"❌ MQTT kết nối thất bại, mã lỗi: {rc}")

    def _handle_disconnect(self, client, userdata, rc):
        self._is_connected = False
        if rc != 0:
            logger.warning(f"⚠️ MQTT mất kết nối bất ngờ (rc={rc}), đang thử kết nối lại...")

    def _handle_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8")
            msg_log = f"📩 Nhận tin nhắn | Topic: {msg.topic} | Payload: {payload}"
            print(msg_log)
            logger.info(msg_log)

            data = json.loads(payload)

            if msg.topic == TOPIC_SENSOR:
                self._handle_sensor(data)

            elif msg.topic == TOPIC_CONTROL:
                self._handle_control(data)

        except Exception as e:
            logger.error(f"❌ Lỗi xử lý message: {e}")


    def _handle_sensor(self, data: dict):
        sensor = data.get("sensor", "")
        status = data.get("status", "")

        if sensor in ("SLOT_1", "SLOT_2"):
            logger.info(f"🚨 Xe tại {sensor}")
            if self.loop:
                asyncio.run_coroutine_threadsafe(self._async_update_slot_status(sensor, status), self.loop)
            else:
                logger.error("❌ MQTTClient loop not set!")
        if sensor in ("GATE_IN", "GATE_OUT"):
            if status == "CO_XE":
                logger.info(f"🚨 Phát hiện xe tại {sensor}, đang gọi LPR...")
                print(f"🚀 Trigger LPR cho {sensor}...")
                if self.loop:
                    asyncio.run_coroutine_threadsafe(self._async_handle_vehicle_gate_event(sensor, status), self.loop)
                else:
                    logger.error("❌ MQTTClient loop not set!")
            else:
                logger.info(f"ℹ️ {sensor}: {status} (Bỏ qua LPR)")

    #gate
    async def _async_handle_vehicle_gate_event(self, sensor: str, status: str):
        client = get_sync_client()
        try:
            from app.services.parking_sessions_services import create_parking_session, update_parking_session
            
            try:
                res = client.post("/recognize/camera", timeout=100.0)
                res.raise_for_status()
            except Exception as http_err:
                error_msg = f"❌ Lỗi gọi LPR Service ({sensor}): {http_err}"
                print(error_msg)
                logger.error(error_msg)
                return

            if res.status_code == 200:
                result = res.json()
                plate = result.get("plate")
                image_url = result.get("image_url")
                
                if not plate:
                    logger.warning(f"⚠️ LPR không nhận diện được biển số tại {sensor}")
                    return

                async with SessionLocal() as db:
                    if sensor == "GATE_IN":
                        await create_parking_session(db, plate, image_url)
                    else:
                        await update_parking_session(db, plate, image_url)    
                
                print(f"✅ Đã xử lý {sensor} cho xe: {plate}")
        except Exception as e:
            logger.error(f"❌ Lỗi hệ thống khi xử lý gate event {sensor}: {e}")
            print(f"❌ Lỗi: {e}")
    #slot
    async def _async_update_slot_status(self, sensor: str, status: str):
        try:
            from app.services.parking_slots_services import update_parking_slot_status
            SLOT_MAPPING = {
                "SLOT_1": "0eb4585f-eef0-40d3-8303-e1baa87bf7ba",
                "SLOT_2": "1d8f4bc3-2c87-4051-ba44-45f96a17b676"
            }

            slot_id = SLOT_MAPPING.get(sensor)
            if not slot_id:
                logger.warning(f"⚠️ Không tìm thấy slot cho {sensor}")
                return

            new_status = "occupied" if status == "CO_XE" else "empty"

            payload = ParkingSlotStatusUpdate(
                id=slot_id,
                status=new_status
            )

            async with SessionLocal() as db:
                result = await update_parking_slot_status(db, payload)

            msg = f"✅ Updated {sensor} → {new_status}"
            print(msg)
            logger.info(msg)

        except Exception as e:
            error_msg = f"❌ Lỗi update slot {sensor}: {e}"
            print(error_msg)
            logger.error(error_msg)
    
    #payment
    def _handle_control(self, data: dict):
        target = data.get("target", "")
        status = data.get("status", "")
        payment_method = data.get("payment_method", "")
        invoice = data.get("invoice", "")
        if status in ("SUCCESS", "FAIL"):
            if self.loop:
                asyncio.run_coroutine_threadsafe(self._async_update_invoice_status(status, payment_method, invoice), self.loop)
            else:
                logger.error("❌ MQTTClient loop not set!")

    async def _async_update_invoice_status(self, status: str, payment_method: str, invoice: str):
        try:
            from app.services.invoices_services import pay_invoice
            if status == "SUCCESS":
                payload = InvoicePay(
                    id=invoice,
                    payment_method=payment_method,
                )
                async with SessionLocal() as db:
                    result = await pay_invoice(db, payload)
                logger.info(f"✅ Updated invoice {invoice} → {status}")
            else:
                logger.info(f"❌ Updated invoice {invoice} → {status}")
        except Exception as e:
            logger.error(f"❌ Lỗi update invoice {invoice}: {e}")


    def send_payment_start(self, session: str, invoice: str, cost: str):
        self._publish_control({
            "target": "PAYMENT",
            "status": "START",
            "session": session,
            "invoice": invoice,
            "cost": cost
        })


    def open_servo(self, target: str):
        self._publish_control({
            "target": target,
            "command": "OPEN"
        })
        
    def _publish_control(self, message: dict):
        """Gửi message bất kỳ lên TOPIC_CONTROL"""
        try:
            if not self._is_connected:
                logger.warning("⚠️ MQTT chưa kết nối")
                return

            payload = json.dumps(message)
            result = self._client.publish(TOPIC_CONTROL, payload, qos=1)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"📤 Sent to {TOPIC_CONTROL}: {payload}")
            else:
                logger.error(f"❌ Publish thất bại, rc={result.rc}")

        except Exception as e:
            logger.error(f"❌ Lỗi khi publish: {e}")
        
    
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
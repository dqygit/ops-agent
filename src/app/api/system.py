from fastapi import APIRouter
import serial.tools.list_ports

from app.api.schemas import SerialPortView

router = APIRouter()

@router.get("/api/system/serial-ports", response_model=list[SerialPortView])
def list_serial_ports() -> list[SerialPortView]:
    """
    Get a list of available serial ports in the system.
    """
    ports = serial.tools.list_ports.comports()
    result = []
    for port in ports:
        result.append(
            SerialPortView(
                device=port.device,
                description=port.description,
                hwid=port.hwid,
                name=port.name,
                vid=port.vid,
                pid=port.pid,
                serial_number=port.serial_number,
                location=port.location,
                manufacturer=port.manufacturer,
                product=port.product,
                interface=port.interface,
            )
        )
    return result

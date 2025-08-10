print("starting dogger v1.0")

from zoneinfo import ZoneInfo
from datetime import datetime
import time
import serial
import gpiod
# import threading

# varaibles
TIMEZONE = "Europe/Belgrade"
SLEEP = False
SLEEP_END = 21 # in hours
SLEEP_START = 10
RING_NUMBER = "+38164*******"
MAX_RING_TIME = 10 # in seconds, or None
STEP_DELAYS = 1 # in minutes
PIR_SENSOR_PIN = 16
PIR_ACTIVATION_DELAY = 1 # in seconds
# LED_PIN = 20

timezone = ZoneInfo(TIMEZONE)

def getCurrentTime():
    return datetime.now(tz=timezone)

def secondsUntil(targetHour) -> float:
    now = getCurrentTime()
    startTarget = now.replace(hour=targetHour, minute=0, second=0, microsecond=0)

    if now >= startTarget:
        startTarget = startTarget.replace(day=now.day + 1)
    
    return (startTarget - now).total_seconds()

def sleepUntil(targetHour):
    seconds = secondsUntil(targetHour)
    if seconds > 0:
        log(f"Sleeping until {targetHour}:00")
        time.sleep(seconds)

def log(message):
    currentTime = getCurrentTime().strftime("%d.%m.%Y. %H:%M:%S")
    print(f"[{currentTime}] {message}")

# GPIO
chip = gpiod.Chip("/dev/gpiochip0")

pinConfig = {
    LED_PIN: gpiod.LineSettings(
        direction=gpiod.line.Direction.OUTPUT,
        output_value=gpiod.line.Value.INACTIVE
    ),
    PIR_SENSOR_PIN: gpiod.LineSettings(
        direction=gpiod.line.Direction.INPUT
    )
}

lines = chip.request_lines(pinConfig, consumer="dogger")

# activity LED
# blinkEvent = threading.Event()

# def ledBlink():
#     while blinkEvent.is_set():
#         lines.set_value(LED_PIN, gpiod.line.Value.ACTIVE)
#         time.sleep(1)
#         lines.set_value(LED_PIN, gpiod.line.Value.INACTIVE)
#         time.sleep(1)

#     lines.set_value(LED_PIN, gpiod.line.Value.INACTIVE)

# ledThread = threading.Thread(target=ledBlink, daemon=True)

# def startBlink():
#     blinkEvent.set()
#     if not ledThread.is_alive():
#         ledThread.start()

# def stopBlink():
#     blinkEvent.clear()
#     ledThread.join()

# initialize modem
modemAvailable = True

try:
    modem = serial.Serial(
        "/dev/ttyUSB0", 
        115200, 
        timeout=2,
    )

    if modem.is_open:
        log("Successfully connected to modem")
        modem.reset_input_buffer()
        modem.reset_output_buffer()
    else:
        log("Failed connecting to modem")
        modemAvailable = False
        modem = None
except serial.SerialException as e:
    log(f"Error initializing modem: {e}")
    modemAvailable = False
    modem = None

modemReady = False
def checkStatus():
    modem.write(b"AT\r\n")
    response = modem.readline().decode("utf-8", errors="ignore").strip()
    if response == "OK":
        global modemReady
        modemReady = True

        # disable stupid features (only modem, Huawei E153 propriatery)
        modem.write(b"AT^U2DIAG=0\r\n")
        
        log("Modem is ready")

def ring():
    modem.write(f"ATD{RING_NUMBER};\r\n".encode("utf-8"))

def hangup():
    modem.write(b"AT+CHUP\r\n")

try:
    while True:
        try:
            if SLEEP:
                now = getCurrentTime()
                if time(SLEEP_START, 0) <= now < time(SLEEP_END, 0):
                    # stopBlink()
                    sleepUntil(time(SLEEP_END, 0))
            
            # startBlink()
            
            if lines.get_value(PIR_SENSOR_PIN) == gpiod.line.Value.ACTIVE:
                log("Motion detected")
                # TODO: insert dog scaring frequency here maybe

                if modemAvailable:
                    if not modemReady:
                        checkStatus()
                    
                    if modemReady:
                        log("Making call")
                        ring()

                        if MAX_RING_TIME is not None:
                            time.sleep(MAX_RING_TIME)
                            hangup()
                            log("Call ended")
                    else:
                        log("Modem is not ready yet, cannot make a call")
                
                log(f"Sleeping for {STEP_DELAYS} minutes")
                time.sleep(STEP_DELAYS * 60)
            
            time.sleep(PIR_ACTIVATION_DELAY)
        except Exception as e:
            log(f"An error had occurred in main loop: {e}")
finally:
    if modemAvailable:
        modem.close()
    lines.release()
    chip.close()
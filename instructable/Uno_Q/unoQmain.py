from arduino.app_utils import App
import time

def loop():
    # Ne fait RIEN, juste garde l'app vivante pour STM32
    time.sleep(1)

App.run(user_loop=loop)
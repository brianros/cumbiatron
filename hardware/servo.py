# hardware/servo.py

import machine
import utime
import uasyncio as asyncio

class Servo:
    def __init__(self, pin, min_angle=60, max_angle=120, reversed=False):
        self.pwm = machine.PWM(machine.Pin(pin))
        self.pwm.freq(50)
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.reversed = reversed
        self.min_duty = 3000 + (min_angle - 60) * (4000 / 60)
        self.max_duty = 3000 + (max_angle - 60) * (4000 / 60)
        self.offset = 0
        self.current_angle = 90

    async def set_angle(self, angle):
        self.current_angle = angle
        adjusted_angle = max(self.min_angle, min(self.max_angle, angle - self.offset))
        if self.reversed:
            adjusted_angle = self.max_angle - (adjusted_angle - self.min_angle)
        duty = int(self.min_duty + (self.max_duty - self.min_duty) * (adjusted_angle - self.min_angle) / (self.max_angle - self.min_angle))
        self.pwm.duty_u16(duty)
        await asyncio.sleep_ms(30)  # Wait for the servo to reach the position
        self.disable()

    def get_actual_angle(self):
        actual_angle = max(self.min_angle, min(self.max_angle, self.current_angle - self.offset))
        return self.max_angle - (actual_angle - self.min_angle) if self.reversed else actual_angle

    def disable(self):
        self.pwm.duty_u16(0)

    def set_offset(self, offset):
        if -30 <= offset <= 30:
            self.offset = offset
        else:
            raise ValueError("Offset must be between -30 and 30.")

    async def center(self):
        await self.set_angle(90)

# Example usage
if __name__ == "__main__":
    async def test_servo():
        servo = Servo(0)  # Assuming servo is connected to pin 0
        await servo.center()
        print("Servo centered")
        await asyncio.sleep(1)
        await servo.set_angle(45)
        print("Servo at 45 degrees")
        await asyncio.sleep(1)
        await servo.set_angle(135)
        print("Servo at 135 degrees")
        await asyncio.sleep(1)
        servo.disable()
        print("Servo disabled")

    asyncio.run(test_servo())

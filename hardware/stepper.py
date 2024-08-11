# hardware/stepper.py

import machine
import utime
import uasyncio as asyncio

class StepperMotor:
    def __init__(self, enable_pin, mode0_pin, step_pin, dir_pin, mode1_pin, mode2_pin):
        self.ENABLE_PIN = machine.Pin(enable_pin, machine.Pin.OUT)
        self.MODE0_PIN = machine.Pin(mode0_pin, machine.Pin.OUT)
        self.STEP_PIN = machine.Pin(step_pin, machine.Pin.OUT)
        self.DIR_PIN = machine.Pin(dir_pin, machine.Pin.OUT)
        self.MODE1_PIN = machine.Pin(mode1_pin, machine.Pin.OUT)
        self.MODE2_PIN = machine.Pin(mode2_pin, machine.Pin.OUT)

        # Set 1/16 microstepping mode
        self.MODE0_PIN.value(1)
        self.MODE1_PIN.value(1)
        self.MODE2_PIN.value(0)

        self.disable()  # Start with the motor disabled
        self.current_position = 0

    def enable(self):
        self.ENABLE_PIN.value(0)  # Enable the driver (active low)

    def disable(self):
        self.ENABLE_PIN.value(1)  # Disable the driver

    def set_direction(self, clockwise=True):
        self.DIR_PIN.value(1 if clockwise else 0)

    async def step(self, steps, delay_us=100):  # delay in microseconds
        self.enable()  # Enable the motor before stepping
        for _ in range(steps):
            self.STEP_PIN.value(1)
            await asyncio.sleep_us(delay_us)
            self.STEP_PIN.value(0)
            await asyncio.sleep_us(delay_us)
        self.disable()  # Disable the motor after stepping

    async def move_steps(self, steps, clockwise=True):
        self.set_direction(clockwise)
        await self.step(abs(steps))
        self.current_position += steps if clockwise else -steps
        print(f"Moved {steps} steps {'clockwise' if clockwise else 'counter-clockwise'}")
        print(f"Current position: {self.current_position}")

    async def move_to_position(self, target_position):
        steps_to_move = target_position - self.current_position
        await self.move_steps(abs(steps_to_move), steps_to_move > 0)

    def get_current_position(self):
        return self.current_position

    async def home(self, home_switch_pin):
        home_switch = machine.Pin(home_switch_pin, machine.Pin.IN, machine.Pin.PULL_UP)
        
        # Move left until home switch is triggered
        while home_switch.value() == 1:
            await self.move_steps(1, clockwise=False)
        
        # Reset position to 0
        self.current_position = 0
        print("Homing completed. Current position set to 0.")

# Example usage
if __name__ == "__main__":
    async def test_stepper():
        # Adjust these pin numbers according to your actual connections
        stepper = StepperMotor(enable_pin=10, mode0_pin=11, step_pin=12, dir_pin=13, mode1_pin=14, mode2_pin=15)
        
        # Assuming the home switch is connected to pin 16
        await stepper.home(home_switch_pin=16)
        
        await stepper.move_steps(1000)  # Move 1000 steps clockwise
        await asyncio.sleep(1)
        await stepper.move_steps(500, clockwise=False)  # Move 500 steps counter-clockwise
        await asyncio.sleep(1)
        await stepper.move_to_position(750)  # Move to absolute position 750
        
        print(f"Final position: {stepper.get_current_position()}")

    asyncio.run(test_stepper())

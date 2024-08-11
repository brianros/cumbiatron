# cart/cumbiatron_cart.py

import uasyncio as asyncio
from machine import Pin
from hardware.servo import Servo
from hardware.stepper import StepperMotor

class CumbiatronCart:
    def __init__(self, servo_pins, stepper_pins, home_switch_pin, end_switch_pin):
        self.servos = [Servo(pin) for pin in servo_pins]
        self.stepper = StepperMotor(*stepper_pins)
        self.home_switch = Pin(home_switch_pin, Pin.IN, Pin.PULL_UP)
        self.end_switch = Pin(end_switch_pin, Pin.IN, Pin.PULL_UP)
        self.is_homing = False
        self.switch_activated = asyncio.Event()

        # Set up interrupts for both switches
        self.home_switch.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=self.switch_handler)
        self.end_switch.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=self.switch_handler)

        # Servo configuration
        self.servo_orientations = [1, 1, 1, 1, -1, -1, -1]  # 1 for left-trigger, -1 for right-trigger
        self.servo_key_types = ['w', 'w', 'w', 'w', 'b', 'b', 'b']  # 'w' for white keys, 'b' for black keys
        self.servo_states = [0] * 7  # 0 for center, -1 for left note, 1 for right note

    def switch_handler(self, pin):
        if not self.is_homing and (pin.value() == 0):  # Switch activated (assuming active low)
            self.stepper.emergency_stop()
            self.switch_activated.set()

    async def initialize(self):
        await self.center_all_servos()
        await await asyncio.sleep_ms(500) #Wait for servos to stabilize
        await self.home()
        

    async def home(self):
        self.is_homing = True
        self.switch_activated.clear()

        # Move left until home switch is activated
        while self.home_switch.value() == 1:
            self.stepper.step_left()
            await asyncio.sleep_ms(1)

        # Move right to clear the home switch
        while self.home_switch.value() == 0:
            self.stepper.step_right()
            await asyncio.sleep_ms(1)

        # Wait for the switch to be activated again
        while self.home_switch.value() == 1:
            self.stepper.step_left()
            await asyncio.sleep_ms(1)

        self.stepper.reset_position()
        self.is_homing = False

    async def center_all_servos(self):
        await asyncio.gather(*[servo.center() for servo in self.servos])
        self.servo_states = [0] * 7

    async def move_to_position(self, position):
        self.switch_activated.clear()
        await self.stepper.move_to_position(position)
        if self.switch_activated.is_set():
            print("Warning: Movement interrupted by switch activation")

    async def play_note(self, servo_index, is_left_note):
        if servo_index < 0 or servo_index >= len(self.servos):
            raise ValueError("Invalid servo index")

        orientation = self.servo_orientations[servo_index]
        current_state = self.servo_states[servo_index]

        # Determine the direction to turn
        if (is_left_note and orientation == 1) or (not is_left_note and orientation == -1):
            target_state = -1
            angle = -45  # Adjust this value as needed
        else:
            target_state = 1
            angle = 45  # Adjust this value as needed

        # Only move if we're not already in the correct position
        if current_state != target_state:
            await self.servos[servo_index].set_angle(angle)
            self.servo_states[servo_index] = target_state

    async def release_note(self, servo_index):
        if servo_index < 0 or servo_index >= len(self.servos):
            raise ValueError("Invalid servo index")

        if self.servo_states[servo_index] != 0:
            await self.servos[servo_index].center()
            self.servo_states[servo_index] = 0

    def get_current_position(self):
        return self.stepper.get_current_position()

    def get_servo_key_type(self, servo_index):
        return self.servo_key_types[servo_index]

# Example usage
if __name__ == "__main__":
    async def test_cumbiatron():
        # Example pin configurations - adjust as needed
        servo_pins = [0, 1, 2, 3, 4, 5, 6]
        stepper_pins = [10, 11, 12, 13, 14, 15]
        home_switch_pin = 16
        end_switch_pin = 17

        cart = CumbiatronCart(servo_pins, stepper_pins, home_switch_pin, end_switch_pin)
        await cart.initialize()

        # Example: Play a white key note (left note on servo 0)
        await cart.move_to_position(100)
        await cart.play_note(0, True)

        # Example: Play a black key note (right note on servo 4)
        await cart.move_to_position(200)
        await cart.play_note(4, False)

        # Release all notes
        for i in range(7):
            await cart.release_note(i)

        print(f"Current position: {cart.get_current_position()}")

    asyncio.run(test_cumbiatron())
# cart/cumbiatron_cart.py

import uasyncio as asyncio
from hardware.servo import Servo
from hardware.stepper import StepperMotor

class CumbiatronCart:
    def __init__(self, servo_pins, stepper_pins, home_switch_pin):
        self.servos = [Servo(pin) for pin in servo_pins]
        self.stepper = StepperMotor(*stepper_pins)
        self.home_switch_pin = home_switch_pin

    async def initialize(self):
        # Home the cart and center all servos
        await self.stepper.home(self.home_switch_pin)
        await asyncio.gather(*[servo.center() for servo in self.servos])

    async def move_to_position(self, position):
        await self.stepper.move_to_position(position)

    async def play_chord(self, servo_angles):
        # Assume servo_angles is a list of angles corresponding to each servo
        await asyncio.gather(*[self.servos[i].set_angle(angle) for i, angle in enumerate(servo_angles)])

    async def play_note(self, position, servo_index, angle):
        await self.move_to_position(position)
        await self.servos[servo_index].set_angle(angle)

    def get_current_position(self):
        return self.stepper.get_current_position()

# Example usage
if __name__ == "__main__":
    async def test_cumbiatron():
        # Example pin configurations - adjust as needed
        servo_pins = [0, 1, 2, 3, 4, 5, 6]
        stepper_pins = [10, 11, 12, 13, 14, 15]
        home_switch_pin = 16

        cart = CumbiatronCart(servo_pins, stepper_pins, home_switch_pin)
        await cart.initialize()

        # Example: Play a chord
        await cart.play_chord([90, 45, 120, 90, 90, 90, 90])

        # Example: Play a single note
        await cart.play_note(500, 2, 60)

        print(f"Current position: {cart.get_current_position()}")

    asyncio.run(test_cumbiatron())

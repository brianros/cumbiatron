# music/music_interpreter.py

import mido
from typing import List, Tuple

class MusicInterpreter:
    def __init__(self, cart):
        self.cart = cart
        self.note_mapping = self._create_note_mapping()

    def _create_note_mapping(self) -> dict:
        # Map MIDI note numbers to (position, servo_index) tuples
        # This is a simplified mapping and should be adjusted based on your specific setup
        return {
            60: (0, 0),    # C4
            62: (100, 0),  # D4
            64: (200, 1),  # E4
            65: (300, 1),  # F4
            67: (400, 2),  # G4
            69: (500, 2),  # A4
            71: (600, 3),  # B4
            72: (700, 3),  # C5
            # Add more mappings as needed
        }

    async def play_midi_file(self, midi_file_path: str):
        midi_file = mido.MidiFile(midi_file_path)
        
        for msg in midi_file.play():
            if msg.type == 'note_on' and msg.velocity > 0:
                await self._play_note(msg.note)
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                await self._release_note(msg.note)

    async def _play_note(self, note: int):
        if note in self.note_mapping:
            position, servo_index = self.note_mapping[note]
            await self.cart.play_note(position, servo_index, 45)  # Adjust angle as needed
            print(f"Playing note {note} at position {position} with servo {servo_index}")
        else:
            print(f"Note {note} not in mapping")

    async def _release_note(self, note: int):
        if note in self.note_mapping:
            _, servo_index = self.note_mapping[note]
            await self.cart.servos[servo_index].set_angle(90)  # Return to neutral position
            print(f"Releasing note {note}")

    async def play_chord(self, notes: List[int]):
        positions_and_servos = [self.note_mapping.get(note) for note in notes if note in self.note_mapping]
        if positions_and_servos:
            avg_position = sum(pos for pos, _ in positions_and_servos) // len(positions_and_servos)
            await self.cart.move_to_position(avg_position)
            
            servo_angles = [90] * len(self.cart.servos)  # Start with all servos at neutral
            for _, servo_index in positions_and_servos:
                servo_angles[servo_index] = 45  # Adjust angle as needed
            
            await self.cart.play_chord(servo_angles)
            print(f"Playing chord: {notes}")
        else:
            print("No playable notes in the chord")

# Example usage
if __name__ == "__main__":
    import asyncio
    from cart.cumbiatron_cart import CumbiatronCart

    async def test_music_interpreter():
        # Example pin configurations - adjust as needed
        servo_pins = [0, 1, 2, 3, 4, 5, 6]
        stepper_pins = [10, 11, 12, 13, 14, 15]
        home_switch_pin = 16

        cart = CumbiatronCart(servo_pins, stepper_pins, home_switch_pin)
        await cart.initialize()

        interpreter = MusicInterpreter(cart)

        # Test playing individual notes
        await interpreter.play_midi_file('path_to_your_midi_file.mid')

        # Test playing a chord
        await interpreter.play_chord([60, 64, 67])  # C major chord

    asyncio.run(test_music_interpreter())
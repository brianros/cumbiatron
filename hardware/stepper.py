from machine import Pin, PWM, Timer
import utime
import math

class StepperMotorController:
    MICROSTEP_MODES = {1: (0, 0, 0), 2: (1, 0, 0), 4: (0, 1, 0), 8: (1, 1, 0), 16: (0, 0, 1), 32: (1, 0, 1)}

    def __init__(self, step_pin, dir_pin, enable_pin, mode_pins, limit_switch_pin):
        self.step_pin = Pin(step_pin, Pin.OUT)
        self.dir_pin = Pin(dir_pin, Pin.OUT)
        self.enable_pin = Pin(enable_pin, Pin.OUT)
        self.mode_pins = [Pin(pin, Pin.OUT) for pin in mode_pins]
        self.limit_switch = Pin(limit_switch_pin, Pin.IN, Pin.PULL_UP)
        
        self.position = 0
        self.direction = 1  # 1 for clockwise, -1 for counterclockwise
        self.current_microstep = 1
        
        # Initialize PWM for step pin
        self.pwm = PWM(self.step_pin)
        self.pwm.duty_u16(0)  # Start with PWM off
        
        # Initialize timer for position tracking
        self.timer = Timer()
        self.pulse_count = 0
        
    def set_direction(self, direction):
        self.direction = 1 if direction > 0 else -1
        self.dir_pin.value(self.direction > 0)
        
    def enable(self):
        self.enable_pin.value(0)  # Assuming active low enable
            
    def disable(self):
        self.enable_pin.value(1)  # Assuming active low enable
            
    def set_microstep_mode(self, microstep):
        if microstep not in self.MICROSTEP_MODES:
            raise ValueError(f"Invalid microstep value. Choose from {list(self.MICROSTEP_MODES.keys())}")
        
        for pin, value in zip(self.mode_pins, self.MICROSTEP_MODES[microstep]):
            pin.value(value)
        self.current_microstep = microstep
            
    def _pulse_counter(self, timer):
        self.pulse_count += 1
        
    def _calculate_pwm_parameters(self, freq):
        clock_freq = 125_000_000
        for div in range(1, 256):
            wrap = clock_freq // (freq * div)
            if 1 <= wrap <= 65535:
                return div, int(wrap)
        return None
        
    def _set_speed(self, steps_per_second):
        # Adjust frequency for microstepping
        adjusted_freq = steps_per_second * self.current_microstep
        
        # Ensure minimum frequency of 10 Hz
        adjusted_freq = max(adjusted_freq, 10)
        
        pwm_params = self._calculate_pwm_parameters(adjusted_freq)
        if pwm_params is None:
            raise ValueError(f"Unable to achieve frequency of {adjusted_freq} Hz")
        
        self.pwm.freq(int(adjusted_freq))
        self.pwm.duty_u16(32768)  # 50% duty cycle

    def _stop_motor(self):
        self.pwm.duty_u16(0)
        self.timer.deinit()
        self.disable()
        
    def move_for_time(self, direction, steps_per_second, duration_ms, microstep=None):
        if microstep is not None:
            self.set_microstep_mode(microstep)
        
        self.set_direction(direction)
        self._set_speed(steps_per_second)
        
        # Setup pulse counting
        self.pulse_count = 0
        self.timer.init(freq=self.pwm.freq()*2, mode=Timer.PERIODIC, callback=self._pulse_counter)
        
        self.enable()  # Ensure motor is enabled before movement
        
        try:
            # Move for the specified duration or until limit switch is triggered
            start_time = utime.ticks_ms()
            while (utime.ticks_diff(utime.ticks_ms(), start_time) < duration_ms) and self.limit_switch.value():
                utime.sleep_ms(1)
        except KeyboardInterrupt:
            print("Movement interrupted by user.")
        finally:
            # Stop PWM and timer
            self.pwm.duty_u16(0)
            self.timer.deinit()
            self.disable()
        
        # Update position
        actual_steps = self.pulse_count / self.current_microstep
        self.position += self.direction * actual_steps
        
        return actual_steps
    
    def move_with_variable_speed(self, direction, speed_profile, duration_ms, microstep=None):
        if microstep is not None:
            self.set_microstep_mode(microstep)
        
        self.set_direction(direction)
        
        # Setup pulse counting
        self.pulse_count = 0
        self.timer.init(freq=1000, mode=Timer.PERIODIC, callback=self._pulse_counter)
        
        self.enable()  # Ensure motor is enabled before movement
        
        try:
            start_time = utime.ticks_ms()
            while (utime.ticks_diff(utime.ticks_ms(), start_time) < duration_ms) and self.limit_switch.value():
                elapsed_time = utime.ticks_diff(utime.ticks_ms(), start_time)
                current_speed = speed_profile(elapsed_time, duration_ms)
                self._set_speed(current_speed)
                utime.sleep_ms(10)  # Small delay to allow for speed changes
        except KeyboardInterrupt:
            print("Movement interrupted by user.")
        finally:
            # Stop PWM and timer
            self.pwm.duty_u16(0)
            self.timer.deinit()
            self.disable()
        
        # Update position
        actual_steps = self.pulse_count / self.current_microstep
        self.position += self.direction * actual_steps
        
        return actual_steps

    def get_position(self):
        return self.position

def run_tests(motor):
    print("Starting StepperMotorController tests...")
    
    try:
        # Test 1: Constant speed
        print("\nTest 1: Constant Speed")
        speed = 200  # steps per second
        duration = 2000  # milliseconds
        print(f"Speed: {speed} steps/second")
        print(f"Duration: {duration} ms")
        print(f"Expected steps: {speed * (duration / 1000)}")
        
        steps = motor.move_for_time(1, speed, duration, microstep=16)
        
        print(f"Actual steps moved: {steps}")
        print(f"Actual speed: {steps / (duration / 1000):.2f} steps/second")
        
        # Test 2: Acceleration
        print("\nTest 2: Acceleration")
        start_speed = 100  # steps per second
        end_speed = 400  # steps per second
        duration = 3000  # milliseconds
        print(f"Start speed: {start_speed} steps/second")
        print(f"End speed: {end_speed} steps/second")
        print(f"Duration: {duration} ms")
        print(f"Acceleration: {(end_speed - start_speed) / (duration / 1000):.2f} steps/second²")
        
        def accelerate(t, total_t):
            return start_speed + ((end_speed - start_speed) * t / total_t)
        
        steps = motor.move_with_variable_speed(1, accelerate, duration, microstep=16)
        
        print(f"Actual steps moved: {steps}")
        print(f"Average speed: {steps / (duration / 1000):.2f} steps/second")
        
        # Test 3: Deceleration
        print("\nTest 3: Deceleration")
        start_speed = 400  # steps per second
        end_speed = 100  # steps per second
        duration = 3000  # milliseconds
        print(f"Start speed: {start_speed} steps/second")
        print(f"End speed: {end_speed} steps/second")
        print(f"Duration: {duration} ms")
        print(f"Deceleration: {(end_speed - start_speed) / (duration / 1000):.2f} steps/second²")
        
        def decelerate(t, total_t):
            return start_speed + ((end_speed - start_speed) * t / total_t)
        
        steps = motor.move_with_variable_speed(-1, decelerate, duration, microstep=16)
        
        print(f"Actual steps moved: {steps}")
        print(f"Average speed: {steps / (duration / 1000):.2f} steps/second")
        
        # Test 4: Sinusoidal speed profile
        print("\nTest 4: Sinusoidal Speed Profile")
        base_speed = 250  # steps per second
        amplitude = 150  # steps per second
        duration = 5000  # milliseconds
        print(f"Base speed: {base_speed} steps/second")
        print(f"Amplitude: ±{amplitude} steps/second")
        print(f"Duration: {duration} ms")
        print(f"Frequency: 0.2 Hz (1 full sine wave over 5 seconds)")
        
        def sine_wave(t, total_t):
            return base_speed + amplitude * math.sin(2 * math.pi * t / total_t)
        
        steps = motor.move_with_variable_speed(1, sine_wave, duration, microstep=16)
        
        print(f"Actual steps moved: {steps}")
        print(f"Average speed: {steps / (duration / 1000):.2f} steps/second")
        
        # Test 5: Microstepping Accuracy
        print("\nTest 5: Microstepping Accuracy")
        test_steps = 200
        speed = 100  # steps per second

        for microstep in sorted(motor.MICROSTEP_MODES.keys()):
            print(f"\nTesting {microstep}-microstep mode:")
            motor.set_microstep_mode(microstep)
            
            # Move clockwise
            print("  Moving clockwise...")
            start_pos = motor.get_position()
            steps_cw = motor.move_for_time(1, speed, (test_steps / speed) * 1000)
            end_pos = motor.get_position()
            
            print(f"    Requested steps: {test_steps}")
            print(f"    Actual steps: {steps_cw}")
            print(f"    Position change: {end_pos - start_pos}")
            print(f"    Speed: {steps_cw / ((test_steps / speed)):.2f} steps/second")
            
            utime.sleep_ms(1000)  # Pause between movements
            
            # Move counterclockwise
            print("  Moving counterclockwise...")
            start_pos = motor.get_position()
            steps_ccw = motor.move_for_time(-1, speed, (test_steps / speed) * 1000)
            end_pos = motor.get_position()
            
            print(f"    Requested steps: {test_steps}")
            print(f"    Actual steps: {steps_ccw}")
            print(f"    Position change: {start_pos - end_pos}")
            print(f"    Speed: {steps_ccw / ((test_steps / speed)):.2f} steps/second")
            
            utime.sleep_ms(1000)  # Pause between microstep modes

    except KeyboardInterrupt:
        print("\nTests interrupted by user.")
    finally:
        motor.disable()
        print("\nMotor disabled. Tests completed or interrupted.")

# Create motor instance and run tests
motor = StepperMotorController(step_pin=12, dir_pin=13, enable_pin=10, mode_pins=[11, 14, 15], limit_switch_pin=16)
run_tests(motor)
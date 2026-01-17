# Go1 MQTT Controller Library - Custom Dances & Movements Guide

A comprehensive guide for configuring and using the Go1 MQTT library to create custom dances and movements.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites & Installation](#prerequisites--installation)
3. [System Architecture](#system-architecture)
4. [Configuration Guide](#configuration-guide)
5. [Core Concepts](#core-concepts)
6. [Usage Guide](#usage-guide)
7. [Creating Custom Movements](#creating-custom-movements)
8. [Creating Custom Dances](#creating-custom-dances)
9. [API Reference](#api-reference)
10. [Examples](#examples)
11. [Troubleshooting](#troubleshooting)

---

## Overview

This library provides a Python interface to control the Go1 robot through MQTT (Message Queuing Telemetry Transport). It allows you to:

- Control robot movement (forward, backward, strafe, turn)
- Change robot modes (stand, walk, etc.)
- Control LED colors
- Monitor battery and sensor status
- Create complex movement sequences and dances

### Key Components

- **Go1MQTT** (`client.py`): Main MQTT client for robot communication
- **Go1State** (`state.py`): Complete state representation of the robot
- **Topics** (`topics.py`): MQTT topic definitions for pub/sub messaging
- **MQTTConfig**: Configuration dataclass for connection settings

---

## Prerequisites & Installation

### Requirements

- Python 3.7+
- Network connection to the Go1 robot (WiFi or Ethernet)
- `paho-mqtt` library for MQTT communication
- `numpy` for efficient numerical operations

### Installation

1. **Clone or download the go1pylib package**:
   ```bash
   cd /path/to/Robot_Rave_Hackathon/go1pylib
   ```

2. **Install dependencies**:
   ```bash
   pip install paho-mqtt numpy
   ```

3. **Install the package** (optional, for use in other projects):
   ```bash
   pip install -e .
   ```

### Network Setup

Before using the library, ensure your computer can communicate with the Go1 robot:

1. Connect to the Go1's WiFi network (default: `Go1` or similar)
2. Verify connectivity:
   ```bash
   ping 192.168.12.1
   ```
3. If unsuccessful, check the robot's IP address in its settings

---

## System Architecture

### MQTT Communication Flow

```
Your Python Script
       ↓
  Go1MQTT Client
       ↓
  MQTT Broker (on Go1)
       ↓
  Go1 Robot Hardware
```

### Message Flow for Movement

1. You call `update_speed()` to set movement values
2. You call `send_movement_command()` to send the command
3. MQTT publishes to `controller/stick` topic
4. Go1 receives and executes the movement
5. Robot state updates are published back on subscription topics

### File Descriptions

| File | Purpose |
|------|---------|
| `client.py` | Main Go1MQTT class - handles connection, movement, LED control |
| `state.py` | Data structures for robot state (battery, position, sensors) |
| `topics.py` | MQTT topic definitions and validation helpers |

---

## Configuration Guide

### Basic Configuration

The `MQTTConfig` dataclass holds all configuration settings:

```python
from go1pylib.mqtt.client import MQTTConfig

# Default configuration (works for most cases)
config = MQTTConfig()

# Custom configuration
config = MQTTConfig(
    host="192.168.12.1",      # Robot IP address
    port=1883,                 # MQTT broker port
    keepalive=60,              # Connection keepalive in seconds
    client_id="my_controller"  # Unique client identifier
)
```

### Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `host` | `192.168.12.1` | IP address of the Go1 robot |
| `port` | `1883` | MQTT broker port on the robot |
| `keepalive` | `60` | Seconds before connection timeout |
| `client_id` | Random 6-char hex | Unique identifier for this client |
| `protocol` | `MQTTv311` | MQTT protocol version |

### Advanced Configuration

```python
from go1pylib.mqtt.client import Go1MQTT

mqtt_options = {
    "host": "192.168.12.1",
    "port": 1883,
    "keepalive": 60,
    "client_id": "dance_controller_v1"
}

mqtt_client = Go1MQTT(go1_controller, mqtt_options=mqtt_options)
```

### Changing Network Settings

If your robot uses a different IP address or network:

```python
# Example: Robot on different network
mqtt_options = {
    "host": "192.168.0.100",  # Custom IP
    "port": 1883,
    "client_id": "custom_network_controller"
}

mqtt_client = Go1MQTT(go1, mqtt_options=mqtt_options)
```

---

## Core Concepts

### Movement Values

All movement commands use **normalized values between -1.0 and 1.0**:

- **-1.0**: Maximum in one direction (e.g., full left)
- **0.0**: Stopped/neutral
- **1.0**: Maximum in opposite direction (e.g., full right)

#### Movement Axes Explained

```
update_speed(left_right, turn_left_right, look_up_down, backward_forward)
                ↓               ↓                ↓              ↓
         Strafe movement   Rotation      Body tilt       Forward/back
         -1 (left) to      -1 (left) to  -1 (down) to   -1 (back) to
         1 (right)         1 (right)     1 (up)         1 (forward)
         [Stand mode]      [All modes]    [Stand mode]   [All modes]
```

#### Visual Examples

**Forward movement:**
```python
mqtt_client.update_speed(0.0, 0.0, 0.0, 1.0)  # Full forward
mqtt_client.update_speed(0.0, 0.0, 0.0, 0.5)  # Half speed forward
```

**Turning:**
```python
mqtt_client.update_speed(0.0, 1.0, 0.0, 0.0)  # Full right turn
mqtt_client.update_speed(0.0, -0.5, 0.0, 0.0) # Half left turn
```

**Strafing (side movement):**
```python
mqtt_client.update_speed(0.5, 0.0, 0.0, 0.0)  # Move right
mqtt_client.update_speed(-1.0, 0.0, 0.0, 0.0) # Full left
```

**Complex movement:**
```python
mqtt_client.update_speed(0.3, 0.5, 0.0, 0.8)  # Right strafe, right turn, forward
```

### Robot Modes

The `Go1Mode` enum defines robot operating modes:

```python
from go1pylib.go1 import Go1Mode

# Available modes
Go1Mode.IDLE       # Robot at rest
Go1Mode.STAND      # Standing position (can use look_up_down)
Go1Mode.WALK       # Walking gait
Go1Mode.TROT       # Trotting gait (faster)
Go1Mode.DANCE      # Dance mode (for choreography)
Go1Mode.AMBLE      # Ambling gait (slower)
```

**Mode Selection Tips:**
- Use `STAND` for precise movements and choreography
- Use `WALK` for normal movement
- Use `TROT` for faster movement
- Use `DANCE` for synchronized choreographed movements
- Use `IDLE` to park the robot safely

### MQTT Topics

**Subscription Topics** (receive data from robot):
- `bms/state`: Battery Management System status
- `firmware/version`: Robot firmware version

**Publishing Topics** (send commands to robot):
- `controller/stick`: Movement commands (primary)
- `controller/action`: Mode change commands
- `programming/code`: LED and special commands

---

## Usage Guide

### Basic Setup

```python
from go1pylib.mqtt.client import Go1MQTT, MQTTConfig
from go1pylib.go1 import Go1, Go1Mode
import asyncio

# Create main Go1 controller
go1 = Go1()

# Configure MQTT
mqtt_config = {
    "host": "192.168.12.1",
    "port": 1883
}

# Initialize MQTT client
mqtt_client = Go1MQTT(go1, mqtt_options=mqtt_config)

# Connect to robot
mqtt_client.connect()

# Subscribe to status topics
mqtt_client.subscribe()

print("Connected to Go1 robot!")
```

### Sending Movement Commands

```python
import asyncio

# Set movement speeds
mqtt_client.update_speed(
    left_right=0.0,           # No left/right movement
    turn_left_right=0.0,      # No rotation
    look_up_down=0.0,         # No body tilt
    backward_forward=1.0      # Full forward
)

# Send movement for 2 seconds
await mqtt_client.send_movement_command(duration_ms=2000)

# Stop robot
mqtt_client.update_speed(0.0, 0.0, 0.0, 0.0)
await mqtt_client.send_movement_command(duration_ms=100)
```

### Changing Modes

```python
from go1pylib.go1 import Go1Mode
import asyncio

# Change to standing mode
mqtt_client.send_mode_command(Go1Mode.STAND)
await asyncio.sleep(1)  # Wait for mode change

# Change to walk mode
mqtt_client.send_mode_command(Go1Mode.WALK)
await asyncio.sleep(1)

# Change to dance mode
mqtt_client.send_mode_command(Go1Mode.DANCE)
await asyncio.sleep(1)
```

### Controlling LEDs

```python
# Set LED to red
mqtt_client.send_led_command(r=255, g=0, b=0)

# Set LED to green
mqtt_client.send_led_command(r=0, g=255, b=0)

# Set LED to blue
mqtt_client.send_led_command(r=0, g=0, b=255)

# Set LED to white
mqtt_client.send_led_command(r=255, g=255, b=255)

# Set LED to custom color (purple)
mqtt_client.send_led_command(r=255, g=0, b=255)

# Turn off LED
mqtt_client.send_led_command(r=0, g=0, b=0)
```

### Monitoring Robot State

```python
# Get current robot state
state = mqtt_client.get_state()

# Check connection status
print(f"MQTT Connected: {state.mqtt_connected}")

# Check battery information
print(f"Battery SOC: {state.bms.soc}%")
print(f"Battery Voltage: {state.bms.voltage}V")
print(f"Battery Current: {state.bms.current}A")
print(f"Battery Temperature: {state.bms.temps}")
print(f"Charge Cycles: {state.bms.cycle}")

# Check robot information
print(f"Robot State: {state.robot.state}")
print(f"Robot Mode: {state.robot.mode}")
print(f"Robot Gait Type: {state.robot.gait_type}")
print(f"Hardware Version: {state.robot.version.hardware}")
print(f"Software Version: {state.robot.version.software}")

# Check distance warnings (obstacle detection)
print(f"Front distance: {state.robot.distance_warning.front}m")
print(f"Back distance: {state.robot.distance_warning.back}m")
print(f"Left distance: {state.robot.distance_warning.left}m")
print(f"Right distance: {state.robot.distance_warning.right}m")

# Check temperatures
print(f"Motor temperatures: {state.robot.temps}")
```

---

## Creating Custom Movements

### Simple Movement Patterns

```python
import asyncio
from go1pylib.mqtt.client import Go1MQTT

async def move_forward(mqtt_client, duration_ms=1000, speed=1.0):
    """Move robot forward."""
    mqtt_client.update_speed(0.0, 0.0, 0.0, speed)
    await mqtt_client.send_movement_command(duration_ms)
    mqtt_client.update_speed(0.0, 0.0, 0.0, 0.0)
    await mqtt_client.send_movement_command(100)

async def move_backward(mqtt_client, duration_ms=1000, speed=0.5):
    """Move robot backward."""
    mqtt_client.update_speed(0.0, 0.0, 0.0, -speed)
    await mqtt_client.send_movement_command(duration_ms)
    mqtt_client.update_speed(0.0, 0.0, 0.0, 0.0)
    await mqtt_client.send_movement_command(100)

async def turn_left(mqtt_client, duration_ms=1000, speed=0.7):
    """Turn robot left."""
    mqtt_client.update_speed(0.0, -speed, 0.0, 0.0)
    await mqtt_client.send_movement_command(duration_ms)
    mqtt_client.update_speed(0.0, 0.0, 0.0, 0.0)
    await mqtt_client.send_movement_command(100)

async def turn_right(mqtt_client, duration_ms=1000, speed=0.7):
    """Turn robot right."""
    mqtt_client.update_speed(0.0, speed, 0.0, 0.0)
    await mqtt_client.send_movement_command(duration_ms)
    mqtt_client.update_speed(0.0, 0.0, 0.0, 0.0)
    await mqtt_client.send_movement_command(100)

async def strafe_left(mqtt_client, duration_ms=1000, speed=0.6):
    """Move robot left (strafe)."""
    mqtt_client.update_speed(-speed, 0.0, 0.0, 0.0)
    await mqtt_client.send_movement_command(duration_ms)
    mqtt_client.update_speed(0.0, 0.0, 0.0, 0.0)
    await mqtt_client.send_movement_command(100)

async def strafe_right(mqtt_client, duration_ms=1000, speed=0.6):
    """Move robot right (strafe)."""
    mqtt_client.update_speed(speed, 0.0, 0.0, 0.0)
    await mqtt_client.send_movement_command(duration_ms)
    mqtt_client.update_speed(0.0, 0.0, 0.0, 0.0)
    await mqtt_client.send_movement_command(100)

# Usage example
async def test_movements(mqtt_client):
    await move_forward(mqtt_client, 1000)
    await asyncio.sleep(0.5)
    await turn_right(mqtt_client, 500)
    await asyncio.sleep(0.5)
    await strafe_left(mqtt_client, 800)
```

### Complex Movement Sequences

```python
async def square_pattern(mqtt_client):
    """Make robot walk in a square."""
    side_length = 2000  # milliseconds
    
    # Forward
    await move_forward(mqtt_client, side_length, 0.8)
    await asyncio.sleep(0.2)
    
    # Right turn
    await turn_right(mqtt_client, 1000, 0.8)
    await asyncio.sleep(0.2)
    
    # Forward
    await move_forward(mqtt_client, side_length, 0.8)
    await asyncio.sleep(0.2)
    
    # Right turn
    await turn_right(mqtt_client, 1000, 0.8)
    await asyncio.sleep(0.2)
    
    # Forward
    await move_forward(mqtt_client, side_length, 0.8)
    await asyncio.sleep(0.2)
    
    # Right turn
    await turn_right(mqtt_client, 1000, 0.8)
    await asyncio.sleep(0.2)
    
    # Forward
    await move_forward(mqtt_client, side_length, 0.8)
    await asyncio.sleep(0.2)
    
    # Final right turn to face original direction
    await turn_right(mqtt_client, 1000, 0.8)

async def zigzag_pattern(mqtt_client):
    """Make robot move in zigzag pattern."""
    for i in range(4):
        # Move forward
        await move_forward(mqtt_client, 1500, 0.7)
        await asyncio.sleep(0.2)
        
        # Strafe left
        await strafe_left(mqtt_client, 1000, 0.5)
        await asyncio.sleep(0.2)
        
        # Move forward
        await move_forward(mqtt_client, 1500, 0.7)
        await asyncio.sleep(0.2)
        
        # Strafe right
        await strafe_right(mqtt_client, 1000, 0.5)
        await asyncio.sleep(0.2)

async def circular_motion(mqtt_client, duration_ms=5000):
    """Make robot move in circular pattern."""
    mqtt_client.update_speed(0.5, 0.5, 0.0, 0.7)  # Forward and slight turn
    await mqtt_client.send_movement_command(duration_ms)
    mqtt_client.update_speed(0.0, 0.0, 0.0, 0.0)
    await mqtt_client.send_movement_command(100)

async def diagonal_movement(mqtt_client, duration_ms=2000):
    """Move diagonally (strafe + forward)."""
    mqtt_client.update_speed(0.7, 0.0, 0.0, 0.7)  # Right and forward
    await mqtt_client.send_movement_command(duration_ms)
    mqtt_client.update_speed(0.0, 0.0, 0.0, 0.0)
    await mqtt_client.send_movement_command(100)
```

---

## Creating Custom Dances

### Basic Dance Structure

```python
import asyncio
from go1pylib.mqtt.client import Go1MQTT
from go1pylib.go1 import Go1, Go1Mode

async def simple_dance(mqtt_client):
    """A simple dance sequence."""
    
    # Switch to stand mode for better balance during dance
    mqtt_client.send_mode_command(Go1Mode.STAND)
    await asyncio.sleep(1)
    
    # Set LED to dance color
    mqtt_client.send_led_command(255, 0, 255)  # Magenta
    
    # Dance sequence
    for _ in range(3):
        # Sway left
        mqtt_client.update_speed(-0.5, 0.0, 0.3, 0.0)
        await mqtt_client.send_movement_command(500)
        
        # Sway right
        mqtt_client.update_speed(0.5, 0.0, -0.3, 0.0)
        await mqtt_client.send_movement_command(500)
    
    # Stop dancing
    mqtt_client.update_speed(0.0, 0.0, 0.0, 0.0)
    await mqtt_client.send_movement_command(100)
    
    # Turn off LED
    mqtt_client.send_led_command(0, 0, 0)
```

### Intermediate Dance: Spinning

```python
async def spinning_dance(mqtt_client):
    """Make robot spin and dance."""
    
    mqtt_client.send_mode_command(Go1Mode.DANCE)
    await asyncio.sleep(1)
    
    # Color cycling
    colors = [
        (255, 0, 0),      # Red
        (0, 255, 0),      # Green
        (0, 0, 255),      # Blue
        (255, 255, 0),    # Yellow
    ]
    
    for i in range(4):
        # Set color
        r, g, b = colors[i % len(colors)]
        mqtt_client.send_led_command(r, g, b)
        
        # Spin
        mqtt_client.update_speed(0.0, 1.0, 0.0, 0.3)
        await mqtt_client.send_movement_command(1000)
        
        await asyncio.sleep(0.1)
    
    # Stop
    mqtt_client.update_speed(0.0, 0.0, 0.0, 0.0)
    await mqtt_client.send_movement_command(100)
    mqtt_client.send_led_command(0, 0, 0)
```

### Advanced Dance: Choreographed Routine

```python
async def choreographed_dance(mqtt_client):
    """Complex choreographed dance with multiple moves."""
    
    mqtt_client.send_mode_command(Go1Mode.DANCE)
    await asyncio.sleep(1)
    
    # Section 1: Side-to-side motion
    mqtt_client.send_led_command(255, 0, 0)  # Red
    for _ in range(4):
        mqtt_client.update_speed(-0.7, 0.0, 0.2, 0.2)
        await mqtt_client.send_movement_command(400)
        
        mqtt_client.update_speed(0.7, 0.0, -0.2, 0.2)
        await mqtt_client.send_movement_command(400)
    
    await asyncio.sleep(0.2)
    
    # Section 2: Spinning
    mqtt_client.send_led_command(0, 255, 0)  # Green
    for _ in range(2):
        mqtt_client.update_speed(0.0, 1.0, 0.0, 0.0)
        await mqtt_client.send_movement_command(1000)
        
        mqtt_client.update_speed(0.0, -1.0, 0.0, 0.0)
        await mqtt_client.send_movement_command(1000)
    
    await asyncio.sleep(0.2)
    
    # Section 3: Forward and backward with rotation
    mqtt_client.send_led_command(0, 0, 255)  # Blue
    for _ in range(3):
        mqtt_client.update_speed(0.0, 0.5, 0.0, 0.8)
        await mqtt_client.send_movement_command(600)
        
        mqtt_client.update_speed(0.0, -0.5, 0.0, -0.8)
        await mqtt_client.send_movement_command(600)
    
    # Final pose
    mqtt_client.send_led_command(255, 255, 0)  # Yellow
    mqtt_client.update_speed(0.0, 0.0, 0.5, 0.0)
    await mqtt_client.send_movement_command(500)
    
    # Cooldown
    mqtt_client.update_speed(0.0, 0.0, 0.0, 0.0)
    await mqtt_client.send_movement_command(200)
    mqtt_client.send_led_command(0, 0, 0)
```

### Music-Synchronized Dance

```python
class MusicSyncedDance:
    """Dance synchronized to music beats."""
    
    def __init__(self, mqtt_client, bpm=120):
        self.mqtt_client = mqtt_client
        self.bpm = bpm
        self.beat_duration = 60.0 / bpm  # seconds per beat
    
    async def dance_to_beat(self, num_beats, move_func):
        """Execute move_func on each beat."""
        for beat in range(num_beats):
            await move_func()
            await asyncio.sleep(self.beat_duration)
    
    async def simple_beat_dance(self):
        """Simple dance on beat."""
        self.mqtt_client.send_mode_command(Go1Mode.DANCE)
        await asyncio.sleep(1)
        
        # Define beat moves
        async def beat_move():
            self.mqtt_client.update_speed(0.5, 0.5, 0.0, 0.3)
            await self.mqtt_client.send_movement_command(
                int(self.beat_duration * 1000 * 0.8)
            )
            
            self.mqtt_client.update_speed(-0.5, -0.5, 0.0, 0.3)
            await self.mqtt_client.send_movement_command(
                int(self.beat_duration * 1000 * 0.2)
            )
        
        # Dance for 32 beats (2 bars at 120 BPM)
        await self.dance_to_beat(32, beat_move)
        
        # Stop
        self.mqtt_client.update_speed(0.0, 0.0, 0.0, 0.0)
        await self.mqtt_client.send_movement_command(200)

# Usage
async def main():
    mqtt_client = Go1MQTT(go1)
    mqtt_client.connect()
    
    dancer = MusicSyncedDance(mqtt_client, bpm=120)
    await dancer.simple_beat_dance()
    
    mqtt_client.disconnect()
```

### Creating a Reusable Dance Library

```python
from enum import Enum
import asyncio

class DanceStyle(str, Enum):
    """Available dance styles."""
    SIMPLE = "simple"
    SPINNING = "spinning"
    CHOREOGRAPHED = "choreographed"
    FUNKY = "funky"

class DanceLibrary:
    """Library of pre-programmed dances."""
    
    @staticmethod
    async def execute_dance(mqtt_client, style: DanceStyle, loop_count=1, speed=1.0):
        """Execute a dance by style."""
        
        if style == DanceStyle.SIMPLE:
            for _ in range(loop_count):
                await simple_dance(mqtt_client)
                await asyncio.sleep(0.5)
        
        elif style == DanceStyle.SPINNING:
            for _ in range(loop_count):
                await spinning_dance(mqtt_client)
                await asyncio.sleep(0.5)
        
        elif style == DanceStyle.CHOREOGRAPHED:
            for _ in range(loop_count):
                await choreographed_dance(mqtt_client)
                await asyncio.sleep(0.5)
        
        elif style == DanceStyle.FUNKY:
            for _ in range(loop_count):
                await funky_dance(mqtt_client, speed)
                await asyncio.sleep(0.5)

async def funky_dance(mqtt_client, speed=1.0):
    """Funky robot dance."""
    mqtt_client.send_mode_command(Go1Mode.DANCE)
    await asyncio.sleep(1)
    
    # Pattern 1: Bouncing
    for i in range(8):
        mqtt_client.send_led_command(
            int(255 * (i % 2)),
            int(128 * ((i + 1) % 2)),
            int(200)
        )
        mqtt_client.update_speed(0, 0, 0.5 if i % 2 else -0.5, 0.3)
        await mqtt_client.send_movement_command(int(250 / speed))
    
    # Pattern 2: Spinning with movement
    for i in range(4):
        mqtt_client.send_led_command(255, int(128 * (i % 2)), 0)
        mqtt_client.update_speed(0, 1.0 if i % 2 else -1.0, 0, 0.5)
        await mqtt_client.send_movement_command(int(500 / speed))
    
    # Stop and finalize
    mqtt_client.update_speed(0, 0, 0, 0)
    await mqtt_client.send_movement_command(100)
    mqtt_client.send_led_command(0, 0, 0)
```

---

## API Reference

### Go1MQTT Class

#### Constructor
```python
Go1MQTT(go1, mqtt_options=None)
```
Initialize MQTT client for Go1 communication.

**Parameters:**
- `go1`: Go1 controller instance
- `mqtt_options` (dict, optional): MQTT configuration options

#### Methods

**connect()**
```python
mqtt_client.connect() -> None
```
Establish connection to MQTT broker on the Go1 robot.

**subscribe()**
```python
mqtt_client.subscribe() -> None
```
Subscribe to robot status topics (bms/state, firmware/version).

**disconnect()**
```python
mqtt_client.disconnect() -> None
```
Cleanly disconnect from the MQTT broker.

**update_speed(left_right, turn_left_right, look_up_down, backward_forward)**
```python
mqtt_client.update_speed(0.5, 0.0, 0.0, 1.0) -> None
```
Update movement speed values.

**Parameters:**
- `left_right` (float): Left/right movement (-1.0 to 1.0)
- `turn_left_right` (float): Rotation (-1.0 to 1.0)
- `look_up_down` (float): Body tilt (-1.0 to 1.0, stand mode only)
- `backward_forward` (float): Forward/backward movement (-1.0 to 1.0)

**send_movement_command(duration_ms)**
```python
await mqtt_client.send_movement_command(2000) -> None
```
Send movement command for specified duration.

**Parameters:**
- `duration_ms` (int): Duration in milliseconds

**send_led_command(r, g, b)**
```python
mqtt_client.send_led_command(255, 0, 0) -> None
```
Send LED color command.

**Parameters:**
- `r` (int): Red value (0-255)
- `g` (int): Green value (0-255)
- `b` (int): Blue value (0-255)

**send_mode_command(mode)**
```python
mqtt_client.send_mode_command(Go1Mode.DANCE) -> None
```
Send mode change command.

**Parameters:**
- `mode` (Go1Mode): Target mode

**get_state()**
```python
state = mqtt_client.get_state() -> Go1State
```
Get current robot state.

**Returns:**
- `Go1State`: Current complete robot state

### Go1State Class

```python
@dataclass
class Go1State:
    mqtt_connected: bool          # Connection status
    manager_on: bool              # Manager status
    controller_on: bool           # Controller status
    bms: BMSState                 # Battery info
    robot: RobotState             # Robot state
```

#### Methods

**to_dict()**
```python
state_dict = state.to_dict() -> dict
```
Convert state to dictionary representation.

**from_dict(data)**
```python
state = Go1State.from_dict(data) -> Go1State
```
Create Go1State from dictionary.

### BMSState Class

```python
@dataclass
class BMSState:
    version: str                  # BMS firmware version
    status: int                   # BMS status code
    soc: float                    # State of charge (0-100%)
    current: float                # Battery current (A)
    cycle: int                    # Charge cycles
    temps: List[float]            # Cell temperatures (°C)
    voltage: float                # Total voltage (V)
    cell_voltages: List[float]    # Individual cell voltages
```

### RobotState Class

```python
@dataclass
class RobotState:
    sn: SerialNumber              # Serial number info
    version: Version              # Hardware/software version
    temps: List[float]            # Motor temperatures
    mode: int                     # Current mode
    gait_type: int                # Current gait type
    obstacles: List[int]          # Obstacle detection
    state: str                    # Robot state string
    distance_warning: DistanceWarning  # Distance sensor data
```

---

## Examples

### Complete Example: Simple Controller

```python
#!/usr/bin/env python3
"""
Simple Go1 Robot Controller
Controls the Go1 robot with basic movements.
"""

import asyncio
from go1pylib.mqtt.client import Go1MQTT, MQTTConfig
from go1pylib.go1 import Go1, Go1Mode

class Go1Controller:
    def __init__(self, robot_ip="192.168.12.1"):
        self.go1 = Go1()
        
        mqtt_config = {
            "host": robot_ip,
            "port": 1883
        }
        
        self.mqtt = Go1MQTT(self.go1, mqtt_options=mqtt_config)
    
    async def connect(self):
        """Connect to robot."""
        print("Connecting to Go1 robot...")
        self.mqtt.connect()
        self.mqtt.subscribe()
        print("Connected!")
    
    async def disconnect(self):
        """Disconnect from robot."""
        self.mqtt.disconnect()
        print("Disconnected")
    
    async def dance(self):
        """Execute dance routine."""
        print("Starting dance...")
        
        # Set mode
        self.mqtt.send_mode_command(Go1Mode.DANCE)
        await asyncio.sleep(1)
        
        # Dance sequence
        self.mqtt.send_led_command(255, 0, 0)  # Red
        
        for i in range(4):
            # Sway
            self.mqtt.update_speed(0.7 if i % 2 else -0.7, 0.0, 0.0, 0.3)
            await self.mqtt.send_movement_command(500)
            
            # Spin
            self.mqtt.update_speed(0.0, 1.0 if i % 2 else -1.0, 0.0, 0.0)
            await self.mqtt.send_movement_command(500)
        
        # Stop
        self.mqtt.update_speed(0.0, 0.0, 0.0, 0.0)
        await self.mqtt.send_movement_command(100)
        self.mqtt.send_led_command(0, 0, 0)
        
        print("Dance complete!")
    
    async def check_battery(self):
        """Check battery status."""
        state = self.mqtt.get_state()
        print(f"Battery: {state.bms.soc}%")
        print(f"Voltage: {state.bms.voltage}V")
        print(f"Current: {state.bms.current}A")
    
    async def test_movement(self):
        """Test basic movement."""
        print("Testing movement...")
        
        self.mqtt.send_mode_command(Go1Mode.WALK)
        await asyncio.sleep(1)
        
        # Forward
        self.mqtt.update_speed(0, 0, 0, 0.5)
        await self.mqtt.send_movement_command(1000)
        
        # Turn
        self.mqtt.update_speed(0, 0.5, 0, 0)
        await self.mqtt.send_movement_command(500)
        
        # Stop
        self.mqtt.update_speed(0, 0, 0, 0)
        await self.mqtt.send_movement_command(100)
        
        print("Movement test complete!")

async def main():
    controller = Go1Controller()
    
    try:
        await controller.connect()
        await controller.check_battery()
        await controller.test_movement()
        await controller.dance()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await controller.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

### Complete Example: Dance Sequence Manager

```python
#!/usr/bin/env python3
"""
Go1 Dance Sequence Manager
Manage and execute complex dance choreography.
"""

import asyncio
from go1pylib.mqtt.client import Go1MQTT
from go1pylib.go1 import Go1, Go1Mode
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Movement:
    """Represents a single movement."""
    left_right: float
    turn_left_right: float
    look_up_down: float
    backward_forward: float
    duration_ms: int
    led_color: Tuple[int, int, int] = (0, 0, 0)

class DanceSequence:
    """A sequence of movements forming a dance."""
    
    def __init__(self, name: str):
        self.name = name
        self.movements: List[Movement] = []
    
    def add_movement(self, movement: Movement):
        """Add movement to sequence."""
        self.movements.append(movement)
    
    def add_movements(self, movements: List[Movement]):
        """Add multiple movements to sequence."""
        self.movements.extend(movements)
    
    async def execute(self, mqtt_client: Go1MQTT):
        """Execute the dance sequence."""
        print(f"Executing: {self.name}")
        
        mqtt_client.send_mode_command(Go1Mode.DANCE)
        await asyncio.sleep(1)
        
        for movement in self.movements:
            # Set LED
            if movement.led_color != (0, 0, 0):
                mqtt_client.send_led_command(*movement.led_color)
            
            # Execute movement
            mqtt_client.update_speed(
                movement.left_right,
                movement.turn_left_right,
                movement.look_up_down,
                movement.backward_forward
            )
            await mqtt_client.send_movement_command(movement.duration_ms)
        
        # Stop and turn off LED
        mqtt_client.update_speed(0, 0, 0, 0)
        await mqtt_client.send_movement_command(100)
        mqtt_client.send_led_command(0, 0, 0)
        
        print(f"Completed: {self.name}")

# Define dances
def create_simple_dance() -> DanceSequence:
    """Create a simple dance."""
    dance = DanceSequence("Simple Dance")
    
    # Sway left
    dance.add_movement(Movement(-0.5, 0, 0, 0.3, 500, (255, 0, 0)))
    # Sway right
    dance.add_movement(Movement(0.5, 0, 0, 0.3, 500, (0, 255, 0)))
    # Spin
    dance.add_movement(Movement(0, 1.0, 0, 0, 1000, (0, 0, 255)))
    
    return dance

def create_complex_dance() -> DanceSequence:
    """Create a more complex dance."""
    dance = DanceSequence("Complex Dance")
    
    # Section 1: Side to side
    for i in range(4):
        color = (255, 0, 0) if i % 2 else (0, 255, 0)
        dance.add_movement(Movement(-0.7, 0, 0.2, 0.2, 400, color))
        dance.add_movement(Movement(0.7, 0, -0.2, 0.2, 400, color))
    
    # Section 2: Spinning
    dance.add_movement(Movement(0, 1.0, 0, 0, 1000, (0, 0, 255)))
    dance.add_movement(Movement(0, -1.0, 0, 0, 1000, (0, 0, 255)))
    
    return dance

async def main():
    go1 = Go1()
    mqtt = Go1MQTT(go1, mqtt_options={"host": "192.168.12.1"})
    
    try:
        mqtt.connect()
        
        # Execute simple dance
        dance1 = create_simple_dance()
        await dance1.execute(mqtt)
        
        await asyncio.sleep(2)
        
        # Execute complex dance
        dance2 = create_complex_dance()
        await dance2.execute(mqtt)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        mqtt.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Troubleshooting

### Connection Issues

**Problem: "Connection timeout" error**

**Solution:**
1. Verify robot is powered on
2. Check WiFi connection to robot
3. Ping the robot: `ping 192.168.12.1`
4. Check robot IP address in settings
5. Restart MQTT broker on robot

```bash
# Test connectivity
ping 192.168.12.1

# Test MQTT port
nc -zv 192.168.12.1 1883
```

### Movement Issues

**Problem: Robot not responding to movement commands**

**Solutions:**
1. Check if mode is set to WALK or DANCE (not IDLE)
2. Verify connection status: `mqtt_client.get_state().mqtt_connected`
3. Check error logs for MQTT publishing failures
4. Ensure values are between -1.0 and 1.0
5. Try sending a simple test command:

```python
mqtt_client.update_speed(1.0, 0.0, 0.0, 0.0)  # Full right strafe
await mqtt_client.send_movement_command(500)
```

### State Issues

**Problem: Robot state not updating**

**Solutions:**
1. Subscribe to topics: `mqtt_client.subscribe()`
2. Check MQTT broker logs on robot
3. Verify network stability
4. Restart the MQTT connection

### Performance Issues

**Problem: Slow or laggy movements**

**Solutions:**
1. Reduce `publish_frequency` (currently 0.1s)
2. Decrease command duration_ms values
3. Reduce network congestion
4. Check robot CPU usage via SSH

```python
# Modify publish frequency
mqtt_client.publish_frequency = 0.05  # 50ms
```

### Debugging

**Enable debug logging:**

```python
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('go1pylib.mqtt.client')
logger.setLevel(logging.DEBUG)
```

**Check robot SSH connection:**

```bash
ssh unitree@192.168.12.1
# Default password: 123
```

**View MQTT topics on broker:**

```bash
# From robot SSH
mosquitto_sub -h 192.168.12.1 -t '#'
```

---

## Tips & Best Practices

1. **Always stop movements cleanly**: Send zero speed before disconnecting
2. **Check battery before long sequences**: Battery depletion affects performance
3. **Use asyncio for smooth transitions**: Avoid blocking operations
4. **Test movements at low speeds first**: Increase speed once working
5. **Monitor connection stability**: Log connection events in production
6. **Keep movement sequences under 10 seconds**: Longer sequences may timeout
7. **Use appropriate modes**: Different modes have different capabilities
8. **Handle exceptions gracefully**: Always disconnect in finally blocks
9. **Document your dance choreography**: Comment timing and moves
10. **Test on different network conditions**: WiFi strength affects performance

### Performance Optimization

- **Reduce motion command frequency**: Combine multiple small movements into one
- **Use efficient color changes**: Batch LED commands with movements
- **Monitor battery**: Execute dances when battery is above 20%
- **Test timing locally**: Use logging to measure actual vs expected timing
- **Profile your dances**: Measure execution time for long sequences

---

## Contributing

To contribute improvements:

1. Test your code thoroughly with the actual Go1 robot
2. Document new features with examples
3. Follow the existing code style (Python PEP 8)
4. Add type hints to functions
5. Include error handling

---

## Support & Resources

For issues or questions:

1. Check the Troubleshooting section
2. Review the examples
3. Check MQTT connection: `ping 192.168.12.1`
4. View debug logs with logging enabled
5. Consult Unitree Go1 documentation
6. Join the Go1 robotics community forums

---

**Last Updated**: January 17, 2026
**Library Version**: 1.0.0
**Compatible with**: Unitree Go1 (all variants)
**Python Version**: 3.7+

import asyncio
import logging
import shutil
import subprocess
import time
from typing import Awaitable, Callable, List, Tuple, NamedTuple

from go1pylib.go1 import Go1, Go1Mode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Music clip settings (Uptown Funk first 60s)
SONG_TITLE = "Uptown Funk"
SONG_CLIP_PATH = "Robot_Rave_Hackathon/go1pylib/examples/assets/uptown_funk_60s.wav"
SONG_CLIP_START_OFFSET = "00:00"
SONG_CLIP_DURATION_S = 60
SONG_TEMPO_BPM = 117.45  # From beat_detection.ipynb analysis

# Calculate beat timing
BEAT_DURATION_MS = int((60.0 / SONG_TEMPO_BPM) * 1000)  # milliseconds per beat
TWO_BEAT_DURATION_MS = BEAT_DURATION_MS * 2  # Typical move length

# Set True to auto-play the clip via ffplay (if available).
AUTO_PLAY = False

# Define Move as a NamedTuple with proper typing
class Move(NamedTuple):
    """Represents a single move with description."""
    func: Callable[..., Awaitable[None]]
    description: str


async def maybe_start_music() -> None:
    """Prompt the user (or auto-play) to start the music clip."""
    if AUTO_PLAY:
        if shutil.which("ffplay") is None:
            logger.warning("AUTO_PLAY=True but ffplay not found; start music manually.")
        else:
            logger.info("Auto-playing clip with ffplay: %s", SONG_CLIP_PATH)
            subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit", SONG_CLIP_PATH],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            await asyncio.sleep(0.5)
            return

    logger.info("Start the music clip now: %s (%ss from %s)", SONG_TITLE, SONG_CLIP_DURATION_S, SONG_CLIP_START_OFFSET)
    for count in range(3, 0, -1):
        logger.info("Starting in %d...", count)
        await asyncio.sleep(1)


def build_sequence(pattern: List[Move], count: int) -> List[Move]:
    """Repeat a move pattern until a specific count is reached.
    
    Args:
        pattern: List of moves to repeat
        count: Number of moves to generate
        
    Returns:
        List of moves (repeated pattern truncated to count)
    """
    sequence: List[Move] = []
    while len(sequence) < count:
        sequence.extend(pattern)
    return sequence[:count]


async def perform_block(
    dog: Go1,
    label: str,
    moves: List[Move],
    intensity: float,
    duration_ms: int,
    pause_s: float
) -> None:
    """Run a labeled block of moves with error handling.
    
    Args:
        dog: Go1 robot instance
        label: Name/description of this block
        moves: List of Move objects to execute
        intensity: Speed multiplier (0.0 to 1.0)
        duration_ms: Duration for each move in milliseconds
        pause_s: Pause between moves in seconds
        
    Raises:
        RuntimeError: If connection is lost during execution
    """
    logger.info("Block: %s (intensity: %.0f%%)", label, intensity * 100)
    
    for i, move in enumerate(moves):
        # Check connection status
        if not dog.mqtt.connected:
            logger.error("Lost connection during block '%s' at move %d/%d", 
                        label, i + 1, len(moves))
            raise RuntimeError("MQTT connection lost during dance")

        logger.info("  [%d/%d] %s", i + 1, len(moves), move.description)
        
        try:
            # Call the move function with parameters
            await move.func(speed=intensity, duration_ms=duration_ms)
            await asyncio.sleep(pause_s)
        except Exception as e:
            logger.error("Error executing move '%s': %s", move.description, str(e))
            raise


async def main():
    """
    Custom dance routine based on dance.py, timed to a 60s clip with tempo reference.
    
    This routine:
    1. Connects to the Go1 robot
    2. Checks battery level
    3. Sets stand mode for choreography
    4. Executes a 4-part dance with music
    5. Safely returns to walk mode
    """
    dog = None
    try:
        # Initialize robot
        logger.info("Initializing Go1 robot...")
        dog = Go1()

        # Connect to robot
        logger.info("Connecting to MQTT broker at 192.168.12.1:1883...")
        dog.init()

        # Wait for connection with proper timeout handling
        timeout = 10
        start_time = time.time()
        while not dog.mqtt.connected:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                logger.error("Connection timeout after %.1f seconds", elapsed)
                raise ConnectionError(f"Failed to connect within {timeout}s")
            logger.debug("Waiting for connection... %.1fs", elapsed)
            await asyncio.sleep(0.1)

        logger.info("Connected to robot!")

        # Check battery level
        state = dog.mqtt.get_state()
        battery_soc = state.bms.soc
        logger.info("Battery level: %.1f%%", battery_soc)
        
        if battery_soc < 20:
            logger.warning("Battery low (%.1f%%). Dance may be interrupted.", battery_soc)
        
        if battery_soc < 10:
            logger.error("Battery critically low (%.1f%%). Aborting dance.", battery_soc)
            return

        # Initial wait for robot to stabilize
        logger.info("Stabilizing robot...")
        await asyncio.sleep(2)

        # Set to stand mode for choreography
        logger.info("Setting stand mode for choreography...")
        dog.set_mode(Go1Mode.STAND)
        await asyncio.sleep(3)  # Increased wait for mode change

        try:
            await maybe_start_music()

            # Calculate timings based on BPM
            # At 117.45 BPM: 1 beat = ~510ms, 2 beats = ~1020ms
            move_duration_ms = TWO_BEAT_DURATION_MS  # Align with beat structure
            pause_s = 0.2  # 200ms pause for recovery

            logger.info("Dance timing: %dms per move (%.2f beats), %dms pause",
                       move_duration_ms, move_duration_ms / BEAT_DURATION_MS, int(pause_s * 1000))

            # Define base movement patterns
            base_pattern: List[Move] = [
                Move(dog.look_up, "Look up"),
                Move(dog.look_down, "Look down"),
                Move(dog.lean_left, "Lean left"),
                Move(dog.lean_right, "Lean right"),
                Move(dog.twist_left, "Twist left"),
                Move(dog.twist_right, "Twist right"),
            ]

            bounce_pattern: List[Move] = [
                Move(dog.extend_up, "Extend up"),
                Move(dog.squat_down, "Squat down"),
            ]

            # Build dance sections with proper move counts
            warmup_moves = build_sequence(base_pattern, 10)
            verse_moves = build_sequence(base_pattern + bounce_pattern, 15)
            chorus_moves = build_sequence(bounce_pattern + base_pattern + bounce_pattern, 15)
            finale_moves = build_sequence(base_pattern + bounce_pattern, 10)

            # Calculate estimated timing
            total_moves = len(warmup_moves) + len(verse_moves) + len(chorus_moves) + len(finale_moves)
            estimated_duration = total_moves * (move_duration_ms / 1000.0 + pause_s)
            logger.info("Routine will execute %d moves in approximately %.1fs",
                       total_moves, estimated_duration)

            # Execute dance blocks
            logger.info("Starting dance routine!")
            
            await perform_block(dog, "Warmup (50% intensity)", warmup_moves, 0.5, 
                              move_duration_ms, pause_s)
            await dog.reset_body()
            await asyncio.sleep(0.5)

            await perform_block(dog, "Verse (70% intensity)", verse_moves, 0.7, 
                              move_duration_ms, pause_s)
            await dog.reset_body()
            await asyncio.sleep(0.5)

            await perform_block(dog, "Chorus (90% intensity)", chorus_moves, 0.9, 
                              move_duration_ms, pause_s)
            await dog.reset_body()
            await asyncio.sleep(0.5)

            await perform_block(dog, "Finale (100% intensity)", finale_moves, 1.0, 
                              move_duration_ms, pause_s)
            await dog.reset_body()
            await asyncio.sleep(1)

            # Return to walk mode
            logger.info("Returning to walk mode...")
            dog.set_mode(Go1Mode.WALK)
            await asyncio.sleep(2)

            logger.info("✓ Custom dance routine completed successfully!")

        except Exception as e:
            logger.error("✗ Error during dance sequence: %s", str(e))
            import traceback
            traceback.print_exc()
        finally:
            # Always ensure we reset the body and stop movement
            try:
                if dog and dog.mqtt.connected:
                    logger.info("Resetting robot to neutral position...")
                    await dog.reset_body()
            except Exception as e:
                logger.warning("Error during reset: %s", str(e))

    except Exception as e:
        logger.error("✗ Error initializing robot: %s", str(e))
        import traceback
        traceback.print_exc()
    finally:
        # Disconnect cleanly
        if dog is not None:
            try:
                logger.info("Disconnecting from robot...")
                dog.mqtt.disconnect()
                logger.info("Disconnection complete")
            except Exception as e:
                logger.warning("Error during disconnection: %s", str(e))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")

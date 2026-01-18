import asyncio
import logging
import shutil
import subprocess
import time
from pathlib import Path
from typing import Awaitable, Callable, List, Tuple, NamedTuple
import librosa
import IPython.display as ipd

from go1pylib.go1 import Go1, Go1Mode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# AUDIO AND BEAT CONFIGURATION
# ============================================================================

# Audio file paths and metadata
BASE_DIR = Path(__file__).resolve().parent
SONG_CLIP_PATH = str(BASE_DIR / "up_town_funk.wav")
SONG_TITLE = "Uptown Funk"
SONG_CLIP_START_OFFSET = "0:00"
SONG_CLIP_DURATION_S = 270  # Full clip duration in seconds

# Load audio and extract tempo/beat information
try:
    if not Path(SONG_CLIP_PATH).is_file():
        logger.warning(f"Audio file not found: {SONG_CLIP_PATH}. Using default values.")
        y, sr = None, None
        beat_frames = []
        tempo, beat_times = 117, [0.0]
    else:
        y, sr = librosa.load(SONG_CLIP_PATH)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        if tempo <= 0:
            tempo = 117  # Default fallback
        if len(beat_times) == 0:
            beat_times = [0.0]
except Exception as e:
    logger.warning(f"Error loading audio file: {e}. Using default values.")
    y, sr = None, None
    beat_frames = []
    tempo, beat_times = 117, [0.0]

# Create click track to hear beats with audio
if y is not None and len(beat_frames) > 0:
    clicks = librosa.clicks(frames=beat_frames, sr=sr, length=len(y))
    y_with_clicks = y + clicks * 0.5
    ipd.Audio(y_with_clicks, rate=sr)
else:
    logger.warning("Skipping audio playback - audio file not loaded")
print(f"Tempo: {tempo} BPM")
print(f"Beat times (seconds): {beat_times}")

# Calculate beat timing constants
BEAT_DURATION_MS = int((60 / tempo) * 1000)  # Duration of one beat in milliseconds
TWO_BEAT_DURATION_MS = BEAT_DURATION_MS * 2  # Duration of two beats

logger.info(f"Calculated Beat Duration: {BEAT_DURATION_MS}ms per beat ({tempo} BPM)")

# Set True to auto-play the clip via ffplay (if available).
AUTO_PLAY = False

# Define Move as a NamedTuple with proper typing
class Move(NamedTuple):
    """Represents a single move with description."""
    func: Callable[..., Awaitable[None]]
    description: str


# ============================================================================
# BEAT-TO-MODE MAPPING SYSTEM
# ============================================================================

class BeatModeMapper:
    """Maps beat ranges to robot modes for synchronized choreography."""
    
    def __init__(self, beat_times: List[float], tempo: float):
        """
        Initialize the beat-to-mode mapper.
        
        Args:
            beat_times: List of beat times in seconds from librosa
            tempo: Tempo in BPM
        """
        self.beat_times = beat_times
        self.tempo = tempo
        self.beat_duration_s = 60 / tempo
        
    def get_mode_for_beat_range(self, start_beat: int, end_beat: int) -> Go1Mode:
        """
        Get the appropriate mode for a beat range.
        
        Args:
            start_beat: Starting beat index
            end_beat: Ending beat index
            
        Returns:
            Go1Mode appropriate for this beat range
        """
        beat_range = end_beat - start_beat
        
        # Beat ranges mapped to modes
        if beat_range <= 2:
            return Go1Mode.STAND  # Short bursts stay in stand mode
        elif beat_range <= 4:
            return Go1Mode.DANCE1  # Medium phrases use dance1
        elif beat_range <= 8:
            return Go1Mode.DANCE2  # Longer phrases use dance2
        else:
            return Go1Mode.STAND  # Default fallback
            
    def get_beat_time_range(self, start_beat: int, end_beat: int) -> Tuple[float, float]:
        """
        Get the time range in seconds for a beat range.
        
        Args:
            start_beat: Starting beat index
            end_beat: Ending beat index (exclusive)
            
        Returns:
            Tuple of (start_time_seconds, end_time_seconds)
            
        Raises:
            ValueError: If beat range is invalid
        """
        if start_beat < 0 or end_beat < 0:
            raise ValueError(f"Beat indices cannot be negative: start={start_beat}, end={end_beat}")
        if start_beat >= len(self.beat_times):
            logger.warning(f"Start beat {start_beat} exceeds available beats {len(self.beat_times)}")
            start_beat = len(self.beat_times) - 1
        if end_beat > len(self.beat_times):
            logger.warning(f"End beat {end_beat} exceeds available beats {len(self.beat_times)}")
            end_beat = len(self.beat_times)
        
        start_time = self.beat_times[start_beat] if start_beat < len(self.beat_times) else self.beat_times[-1]
        end_time = self.beat_times[end_beat - 1] if (end_beat - 1) < len(self.beat_times) else self.beat_times[-1]
        return (start_time, end_time)
    
    def get_total_beats(self) -> int:
        """Get the total number of detected beats."""
        return len(self.beat_times)


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
    pause_s: float,
    mode: Go1Mode = Go1Mode.STAND
) -> None:
    """Run a labeled block of moves with error handling and mode control.
    
    Args:
        dog: Go1 robot instance
        label: Name/description of this block
        moves: List of Move objects to execute
        intensity: Speed multiplier (0.0 to 1.0)
        duration_ms: Duration for each move in milliseconds
        pause_s: Pause between moves in seconds
        mode: Go1Mode to set before executing moves
        
    Raises:
        RuntimeError: If connection is lost during execution
    """
    logger.info("Block: %s (intensity: %.0f%%, mode: %s)", label, intensity * 100, mode.value)
    
    # Set mode for this block
    dog.set_mode(mode)
    await asyncio.sleep(1)  # Allow mode transition time
    
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
    3. Initializes beat-to-mode mapper
    4. Executes a 4-part dance with music synchronized to beats
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
        state_timeout = 10
        state_start_time = time.time()
        state = dog.mqtt.get_state()
        while not state:
            state_elapsed = time.time() - state_start_time
            if state_elapsed > state_timeout:
                logger.error("State connection timeout after %.1f seconds", state_elapsed)
                raise ConnectionError(f"Failed to get state within {state_timeout}s")
            logger.debug("Waiting for state connection... %.1fs", state_elapsed)
            await asyncio.sleep(0.1) 
            state = dog.mqtt.get_state()
        if not state or not getattr(state, "bms", None):
            logger.error("Robot state missing BMS data; aborting dance.")
            return
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

        # Initialize beat-to-mode mapper
        logger.info("Initializing beat-to-mode mapper...")
        beat_mapper = BeatModeMapper(beat_times, tempo)
        total_beats = beat_mapper.get_total_beats()
        logger.info(f"Using {total_beats} detected beats for choreography")
        
        # Calculate dynamic beat ranges based on song length
        # Divide the song into 4 sections proportionally
        section_size = total_beats // 4
        warmup_start, warmup_end = 0, min(section_size, total_beats)
        verse_start, verse_end = warmup_end, min(warmup_end + section_size, total_beats)
        chorus_start, chorus_end = verse_end, min(verse_end + section_size, total_beats)
        finale_start, finale_end = chorus_end, total_beats
        
        logger.info(f"Beat sections: Warmup[{warmup_start}-{warmup_end}] Verse[{verse_start}-{verse_end}] Chorus[{chorus_start}-{chorus_end}] Finale[{finale_start}-{finale_end}]")

        # Set to stand mode for choreography
        logger.info("Setting initial stand mode for choreography...")
        dog.set_mode(Go1Mode.STAND)
        await asyncio.sleep(3)  # Increased wait for mode change

        try:
            await maybe_start_music()

            # Calculate timings based on BPM
            # At detected tempo: align moves with beat structure
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

            # ========================================================================
            # BEAT-SYNCHRONIZED DANCE EXECUTION
            # ========================================================================
            
            # Execute dance blocks with beat-mapped modes
            logger.info("Starting beat-synchronized dance routine!")
            
            # Warmup section: first quarter, uses STAND mode for stability
            warmup_mode = beat_mapper.get_mode_for_beat_range(warmup_start, warmup_end)
            warmup_start_s, warmup_end_s = beat_mapper.get_beat_time_range(warmup_start, warmup_end)
            logger.info(f"Warmup section: beats {warmup_start}-{warmup_end} ({warmup_start_s:.2f}s - {warmup_end_s:.2f}s), mode: {warmup_mode.value}")
            await perform_block(dog, "Warmup (50% intensity)", warmup_moves, 0.5, 
                              move_duration_ms, pause_s, mode=warmup_mode)
            await dog.reset_body()
            await asyncio.sleep(0.5)

            # Verse section: second quarter, uses DANCE1 for dynamic movement
            verse_mode = beat_mapper.get_mode_for_beat_range(verse_start, verse_end)
            verse_start_s, verse_end_s = beat_mapper.get_beat_time_range(verse_start, verse_end)
            logger.info(f"Verse section: beats {verse_start}-{verse_end} ({verse_start_s:.2f}s - {verse_end_s:.2f}s), mode: {verse_mode.value}")
            await perform_block(dog, "Verse (70% intensity)", verse_moves, 0.7, 
                              move_duration_ms, pause_s, mode=verse_mode)
            await dog.reset_body()
            await asyncio.sleep(0.5)

            # Chorus section: third quarter, uses DANCE2 for complex choreography
            chorus_mode = beat_mapper.get_mode_for_beat_range(chorus_start, chorus_end)
            chorus_start_s, chorus_end_s = beat_mapper.get_beat_time_range(chorus_start, chorus_end)
            logger.info(f"Chorus section: beats {chorus_start}-{chorus_end} ({chorus_start_s:.2f}s - {chorus_end_s:.2f}s), mode: {chorus_mode.value}")
            await perform_block(dog, "Chorus (90% intensity)", chorus_moves, 0.9, 
                              move_duration_ms, pause_s, mode=chorus_mode)
            await dog.reset_body()
            await asyncio.sleep(0.5)

            # Finale section: final quarter, maximal expression
            finale_mode = beat_mapper.get_mode_for_beat_range(finale_start, finale_end)
            finale_start_s, finale_end_s = beat_mapper.get_beat_time_range(finale_start, finale_end)
            logger.info(f"Finale section: beats {finale_start}-{finale_end} ({finale_start_s:.2f}s - {finale_end_s:.2f}s), mode: {finale_mode.value}")
            await perform_block(dog, "Finale (100% intensity)", finale_moves, 1.0, 
                              move_duration_ms, pause_s, mode=finale_mode)
            await dog.reset_body()
            await asyncio.sleep(1)

            # Return to walk mode
            logger.info("Returning to walk mode...")
            dog.set_mode(Go1Mode.WALK)
            await asyncio.sleep(2)

            logger.info("✓ Custom beat-synchronized dance routine completed successfully!")

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

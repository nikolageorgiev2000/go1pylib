"""
Real-time beat-synced head bobbing script.
Captures audio from microphone and makes the robot bob its head in sync with detected beats.
"""

import asyncio
import time
import numpy as np
import librosa
import sounddevice as sd
from collections import deque

DRY_RUN = False  # Set to False to actually control the robot

if not DRY_RUN:
    from go1pylib import Go1, Go1Mode


# Configuration
SAMPLE_RATE = 22050  # Hz
BUFFER_DURATION = 5  # seconds of audio to analyze for beat detection
CHUNK_DURATION = 0.1  # seconds per update (smaller for more responsive detection)
START_BPM = 120  # Initial guess for tempo
TIGHTNESS = 100  # Tempo stability (100 = default)
MIN_BEAT_INTERVAL = 0  # Minimum seconds between beats (prevents double triggers)

# Movement configuration
BOB_SPEED = 1.0  # Movement speed
BEATS_PER_BOB = 4  # How many beats to wait between each bob (1 = bob on every beat, 2 = every other beat, etc.)
BOB_DURATION_RATIO = 0.8  # What fraction of the beat period to use for bobbing (0.8 = 80% of beat duration)

buffer_size = int(SAMPLE_RATE * BUFFER_DURATION)
chunk_size = int(SAMPLE_RATE * CHUNK_DURATION)


class RealtimeBeatDetector:
    """Detects beats in real-time audio stream with phase tracking"""
    
    def __init__(self):
        self.audio_buffer = np.zeros(buffer_size)
        self.last_bpm = START_BPM
        self.last_beat_time = 0
        self.onset_env = None
        
        # Beat tracking for phase prediction
        self.beat_times = deque(maxlen=8)  # Keep last 8 beat times
        self.beat_period = 60.0 / START_BPM  # Time between beats in seconds
        self.next_predicted_beat = None
        self.prediction_tolerance = 0.15  # seconds - window for accepting predicted beat
        
    def process_chunk(self, audio_chunk):
        """Process audio chunk and detect if a beat occurred"""
        # Roll buffer and add new chunk
        self.audio_buffer = np.roll(self.audio_buffer, -len(audio_chunk))
        self.audio_buffer[-len(audio_chunk):] = audio_chunk.flatten()
        
        current_time = time.time()
        
        # Check if we're expecting a predicted beat
        predicted_beat = False
        if self.next_predicted_beat is not None:
            time_to_predicted = self.next_predicted_beat - current_time
            
            # If we're within tolerance of predicted beat, trigger it
            if abs(time_to_predicted) < self.prediction_tolerance:
                predicted_beat = True
        
        # Compute onset strength envelope
        self.onset_env = librosa.onset.onset_strength(
            y=self.audio_buffer, 
            sr=SAMPLE_RATE
        )
        
        # Detect beats in the onset envelope
        beat_frames = librosa.onset.onset_detect(
            onset_envelope=self.onset_env,
            sr=SAMPLE_RATE,
            backtrack=False
        )
        
        # Check if there's a recent beat (in the last chunk)
        onset_beat = False
        if len(beat_frames) > 0:
            # Convert frames to time
            beat_times = librosa.frames_to_time(beat_frames, sr=SAMPLE_RATE)
            
            # Check for beats in the most recent portion
            recent_beats = beat_times[beat_times > (BUFFER_DURATION - CHUNK_DURATION * 2)]
            
            if len(recent_beats) > 0:
                # Prevent triggering too frequently
                if current_time - self.last_beat_time > MIN_BEAT_INTERVAL:
                    onset_beat = True
        
        # Trigger beat if either onset detected OR prediction says it's time
        if onset_beat or predicted_beat:
            self.last_beat_time = current_time
            self.beat_times.append(current_time)
            
            # Update beat period based on recent beats
            if len(self.beat_times) >= 2:
                # Calculate average period from recent beats
                intervals = []
                for i in range(1, len(self.beat_times)):
                    intervals.append(self.beat_times[i] - self.beat_times[i-1])
                self.beat_period = np.mean(intervals)
            
            # Predict next beat
            self.next_predicted_beat = current_time + self.beat_period
            
            beat_type = "predicted" if predicted_beat and not onset_beat else "detected"
            return True, beat_type
        
        return False, None
    
    def get_bpm(self):
        """Get current BPM estimate"""
        try:
            tempo, _ = librosa.beat.beat_track(
                y=self.audio_buffer,
                sr=SAMPLE_RATE,
                start_bpm=self.last_bpm,
                tightness=TIGHTNESS
            )
            bpm = tempo.item() if isinstance(tempo, np.ndarray) else float(tempo)
            
            # Keep BPM in reasonable range
            while bpm < 80:
                bpm *= 2
            while bpm > 200:
                bpm /= 2
            
            self.last_bpm = bpm
            return bpm
        except Exception:
            return self.last_bpm


async def head_bob(dog, bob_duration_ms):
    """Execute a quick head bob"""
    if not DRY_RUN:
        # Quick down and up motion - split duration into thirds
        single_move_ms = bob_duration_ms // 3
        await dog.look_down(speed=BOB_SPEED, duration_ms=single_move_ms)
        await asyncio.sleep(single_move_ms / 1000 / 2)
        await dog.look_up(speed=BOB_SPEED, duration_ms=single_move_ms)
        await asyncio.sleep(single_move_ms / 1000 / 2)
    else:
        # Simulate bob in dry run
        await asyncio.sleep(bob_duration_ms / 1000)


async def audio_processing_loop(detector, dog):
    """Main loop for processing audio and controlling robot"""
    beat_count = 0
    bob_count = 0
    bpm_update_interval = 20  # Update BPM estimate every N chunks
    chunk_count = 0
    
    print("Listening for beats...")
    print("Make some rhythmic sounds or play music!")
    print(f"Bobbing every {BEATS_PER_BOB} beat(s), using {BOB_DURATION_RATIO*100:.0f}% of beat duration")
    print("Press Ctrl+C to stop.\n")
    
    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, 
                           blocksize=chunk_size) as stream:
            while True:
                # Read audio chunk
                audio_chunk, _ = stream.read(chunk_size)
                
                # Process chunk and check for beat
                beat_detected, beat_type = detector.process_chunk(audio_chunk)
                
                if beat_detected:
                    beat_count += 1
                    beat_period_ms = detector.beat_period * 1000
                    type_str = f"[{beat_type}]" if beat_type else ""
                    
                    # Only bob every Nth beat
                    if beat_count % BEATS_PER_BOB == 0:
                        bob_count += 1
                        # Calculate bob duration based on beat period and number of beats to span
                        bob_duration_ms = int(detector.beat_period * BEATS_PER_BOB * BOB_DURATION_RATIO * 1000)
                        print(f"🎵 Beat {beat_count} {type_str} | Bob #{bob_count} | Duration: {bob_duration_ms}ms")
                        
                        # Trigger head bob (non-blocking)
                        asyncio.create_task(head_bob(dog, bob_duration_ms))
                    else:
                        print(f"   Beat {beat_count} {type_str} | Period: {beat_period_ms:.0f}ms (skipping bob)")
                
                # Periodically update BPM estimate
                chunk_count += 1
                if chunk_count % bpm_update_interval == 0:
                    bpm = detector.get_bpm()
                    measured_bpm = 60.0 / detector.beat_period if detector.beat_period > 0 else 0
                    print(f"   Librosa BPM: {bpm:.1f} | Measured BPM: {measured_bpm:.1f}")
                
                # Small sleep to prevent CPU overload
                await asyncio.sleep(0.01)
                
    except KeyboardInterrupt:
        print("\nStopped by user")


async def main():
    dog = None
    
    if not DRY_RUN:
        # Initialize robot
        print("Connecting to robot...")
        dog = Go1()
        dog.init()
        
        # Wait for connection
        start_time = time.time()
        while not dog.mqtt.connected and (time.time() - start_time < 10):
            await asyncio.sleep(0.1)
        
        if not dog.mqtt.connected:
            print("Failed to connect to robot")
            return
        
        print("Connected to robot!")
        
        # Set to stand mode
        dog.set_mode(Go1Mode.STAND)
        await asyncio.sleep(2)
    else:
        print("\n*** DRY RUN MODE - No robot connection ***\n")
    
    # Initialize beat detector
    detector = RealtimeBeatDetector()
    
    print("Starting real-time beat detection and head bobbing...")
    print("Warming up audio buffer...")
    await asyncio.sleep(BUFFER_DURATION)
    
    try:
        # Start audio processing loop
        await audio_processing_loop(detector, dog)
    finally:
        if not DRY_RUN and dog:
            print("\nResetting robot...")
            await dog.reset_body()
            dog.set_mode(Go1Mode.WALK)
            dog.mqtt.disconnect()
        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())

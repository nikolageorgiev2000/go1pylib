"""
Simple beat-synced dance routine.
Runs a sequence of small moves in sync with music beats.
"""

import asyncio
import time
import librosa
import sounddevice as sd
from dance_moves import DANCE_MOVES, MOVE_SEQUENCE, run_move

DRY_RUN = True  # Set to False to actually control the robot
BEATS_PER_MOVE = 2  # Number of beats between each move

if not DRY_RUN:
    from go1pylib import Go1, Go1Mode


async def main():
    # Load and analyze music
    print("Loading music file...")
    audio_file = "beat_routine/up_town_funk.wav"
    y, sr = librosa.load(audio_file)
    
    print("Detecting beats...")
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    
    print(f"Tempo: {tempo[0]:.1f} BPM")
    print(f"Detected {len(beat_times)} beats")
    
    dog = None
    # Calculate move duration based on tempo and beats per move
    # Duration = (beats / BPM) * 60 seconds
    move_duration_s = (BEATS_PER_MOVE / tempo[0]) * 60
    print(f"Move duration: {move_duration_s}s (fills {BEATS_PER_MOVE} beats)")
    
    
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
            print("Failed to connect")
            return
        
        print("Connected!")
        
        # Set to stand mode
        dog.set_mode(Go1Mode.STAND)
        await asyncio.sleep(2)
    else:
        print("\n*** DRY RUN MODE - No robot connection ***\n")
    
    print("Starting in...")
    for i in [3, 2, 1]:
        print(i)
        await asyncio.sleep(1)
    
    # Play music in separate thread
    print(f"Playing music and dancing every {BEATS_PER_MOVE} beats!")
    sd.play(y, sr)

    start_time = time.time()
    move_index = 0

    try:
        for i, beat_time in enumerate(beat_times):
            # Only process every Nth beat
            if i % BEATS_PER_MOVE != 0:
                continue

            # Wait until this beat time
            current_time = time.time() - start_time
            wait_time = beat_time - current_time

            if wait_time > 0:
                await asyncio.sleep(wait_time)

            # Run move
            move_name = MOVE_SEQUENCE[move_index % len(MOVE_SEQUENCE)]
            move = DANCE_MOVES[move_name]
            move_index += 1
            print(f"Move on beat {i} at {beat_time:.2f}s: {move.name}")
            print("  → Move START")
            await run_move(dog, move, move_duration_s, dry_run=DRY_RUN)
            print("  → Move END")
    
    except KeyboardInterrupt:
        print("\nStopped by user")
    finally:
        sd.stop()
        if not DRY_RUN and dog:
            await dog.reset_body()
            dog.set_mode(Go1Mode.WALK)
            dog.mqtt.disconnect()
        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
from go1pylib import Go1, Go1Mode

async def main():
    robot = Go1()
    robot.init()  # Connect to the robot

    # Set to WALK mode and move forward
    robot.set_mode(Go1Mode.WALK)
    await robot.go_forward(speed=0.3, duration_ms=1000)

    # Check battery status
    battery_level = robot.get_battery_level()
    print(f"Battery Level: {battery_level}%")

    # Stop and disconnect
    robot.set_mode(Go1Mode.STAND_DOWN)
    robot.disconnect()

asyncio.run(main())
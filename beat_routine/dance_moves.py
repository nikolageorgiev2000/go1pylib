from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, List, Optional
import asyncio


@dataclass(frozen=True)
class DanceStep:
    name: str
    runner: Callable[["Go1", float], Awaitable[None]]
    turn_rate: float = 0.0


@dataclass
class TurnState:
    balance: float = 0.0


@dataclass(frozen=True)
class DanceMove:
    name: str
    steps: List[DanceStep]
    description: str

    async def run(
        self,
        dog: "Go1",
        duration_s: float,
        turn_state: Optional[TurnState] = None,
    ) -> None:
        if duration_s <= 0 or not self.steps:
            return
        step_duration_ms = (duration_s * 1000.0) / len(self.steps)
        step_duration_s = step_duration_ms / 1000.0
        for step in self.steps:
            await step.runner(dog, step_duration_ms)
            if turn_state is not None and step.turn_rate != 0.0:
                turn_state.balance += step.turn_rate * step_duration_s


def _speed_step(name: str, method_name: str, speed: float) -> DanceStep:
    async def _run(dog: "Go1", duration_ms: float) -> None:
        method = getattr(dog, method_name)
        await method(speed=speed, duration_ms=duration_ms)

    return DanceStep(name=name, runner=_run)


def _pose_step(name: str, lean: float, twist: float, look: float, extend: float) -> DanceStep:
    async def _run(dog: "Go1", duration_ms: float) -> None:
        await dog.pose(
            lean=lean,
            twist=twist,
            look=look,
            extend=extend,
            duration_ms=duration_ms,
        )

    return DanceStep(name=name, runner=_run)


def _turn_step(name: str, direction: str, speed: float) -> DanceStep:
    async def _run(dog: "Go1", duration_ms: float) -> None:
        if direction == "left":
            await dog.turn_left(speed=speed, duration_ms=duration_ms)
        else:
            await dog.turn_right(speed=speed, duration_ms=duration_ms)

    turn_rate = speed if direction == "right" else -speed
    return DanceStep(name=name, runner=_run, turn_rate=turn_rate)


def _wait_step(name: str) -> DanceStep:
    async def _run(dog: "Go1", duration_ms: float) -> None:
        await dog.wait(duration_ms)

    return DanceStep(name=name, runner=_run)


DANCE_MOVES: Dict[str, DanceMove] = {
    "head_bob": DanceMove(
        name="head_bob",
        description="Simple down/up head bob.",
        steps=[
            _speed_step("look_down", "look_down", 0.6),
            _speed_step("look_up", "look_up", 0.6),
        ],
    ),
    "side_sway": DanceMove(
        name="side_sway",
        description="Lean left, then right.",
        steps=[
            _speed_step("lean_left", "lean_left", 0.5),
            _speed_step("lean_right", "lean_right", 0.5),
        ],
    ),
    "twist": DanceMove(
        name="twist",
        description="Twist left, then right.",
        steps=[
            _speed_step("twist_left", "twist_left", 0.5),
            _speed_step("twist_right", "twist_right", 0.5),
        ],
    ),
    "bounce": DanceMove(
        name="bounce",
        description="Extend up, then squat down.",
        steps=[
            _speed_step("extend_up", "extend_up", 0.5),
            _speed_step("squat_down", "squat_down", 0.5),
        ],
    ),
    "look_and_twist": DanceMove(
        name="look_and_twist",
        description="Mix head tilt and torso twist.",
        steps=[
            _speed_step("look_down", "look_down", 0.5),
            _speed_step("twist_left", "twist_left", 0.4),
            _speed_step("look_up", "look_up", 0.5),
            _speed_step("twist_right", "twist_right", 0.4),
        ],
    ),
    "body_wave": DanceMove(
        name="body_wave",
        description="Alternating lean/twist/look/extend poses.",
        steps=[
            _pose_step("pose_left_down", lean=-0.3, twist=-0.2, look=0.2, extend=0.2),
            _pose_step("pose_right_up", lean=0.3, twist=0.2, look=-0.2, extend=0.2),
            _pose_step("pose_left_up", lean=-0.3, twist=-0.2, look=-0.2, extend=0.2),
            _pose_step("pose_right_down", lean=0.3, twist=0.2, look=0.2, extend=0.2),
        ],
    ),
    "pause": DanceMove(
        name="pause",
        description="Hold still for a beat.",
        steps=[_wait_step("wait")],
    ),
    "turn_left": DanceMove(
        name="turn_left",
        description="Turn left in place.",
        steps=[_turn_step("turn_left", "left", 0.4)],
    ),
    "turn_right": DanceMove(
        name="turn_right",
        description="Turn right in place.",
        steps=[_turn_step("turn_right", "right", 0.4)],
    ),
    "turn_left_right": DanceMove(
        name="turn_left_right",
        description="Turn left, then right to return to heading.",
        steps=[
            _turn_step("turn_left", "left", 0.4),
            _turn_step("turn_right", "right", 0.4),
        ],
    ),
}

MOVE_SEQUENCE = [
    "head_bob",
    "side_sway",
    "twist",
    "bounce",
    "look_and_twist",
    "body_wave",
]


async def balance_turn(
    dog: "Go1",
    turn_state: TurnState,
    balance_speed: float,
    dry_run: bool,
) -> None:
    if balance_speed <= 0:
        return
    if abs(turn_state.balance) <= 1e-6:
        return
    duration_s = abs(turn_state.balance) / balance_speed
    if duration_s <= 0:
        return
    if dry_run:
        await asyncio.sleep(duration_s)
        turn_state.balance = 0.0
        return
    if turn_state.balance > 0:
        await dog.turn_left(speed=balance_speed, duration_ms=duration_s * 1000.0)
    else:
        await dog.turn_right(speed=balance_speed, duration_ms=duration_s * 1000.0)
    turn_state.balance = 0.0


async def run_move(
    dog: "Go1",
    move: DanceMove,
    duration_s: float,
    dry_run: bool,
    turn_state: Optional[TurnState] = None,
    auto_balance_turns: bool = False,
    balance_speed: float = 0.4,
) -> None:
    if duration_s <= 0:
        return
    if dry_run:
        step_duration_s = duration_s / len(move.steps) if move.steps else duration_s
        for step in move.steps:
            await asyncio.sleep(step_duration_s)
            if turn_state is not None and step.turn_rate != 0.0:
                turn_state.balance += step.turn_rate * step_duration_s
        if auto_balance_turns and turn_state is not None:
            await balance_turn(dog, turn_state, balance_speed, dry_run=True)
        return
    await move.run(dog, duration_s, turn_state=turn_state)
    if auto_balance_turns and turn_state is not None:
        await balance_turn(dog, turn_state, balance_speed, dry_run=False)

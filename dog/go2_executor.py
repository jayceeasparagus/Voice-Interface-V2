import argparse
import math
import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.obstacles_avoid.obstacles_avoid_client import ObstaclesAvoidClient
from unitree_sdk2py.go2.sport.sport_client import SportClient
from transport.commands import ALLOWED_COMMANDS


IFACE = "ethrobot"

WALK_SPEED_MPS = 0.2
WALK_DURATION_S = 5.0
LATERAL_SPEED_MPS = 0.15
LATERAL_DURATION_S = 3.0
ROTATE_SPEED_RADPS = 0.4
ROTATE_CORRECTION = 1.2
ROTATE_DURATION_S = 2.4
TURN_AROUND_DURATION_S = 9.4
MOVE_COMMAND_HZ = 20.0
OBSTACLE_ENABLE_TIMEOUT_S = 5.0

MIN_DISTANCE_M = 0.2
MAX_DISTANCE_M = 2.0
MIN_ROTATION_DEG = 10.0
MAX_ROTATION_DEG = 180.0

def initialize_channel():
    ChannelFactoryInitialize(0, IFACE)


def make_sport_client():
    client = SportClient()
    client.SetTimeout(3.0)
    client.Init()
    return client


def make_obstacle_client():
    client = ObstaclesAvoidClient()
    client.SetTimeout(3.0)
    client.Init()
    return client


def stop_sport(sport_client):
    try:
        print("Sport StopMove:", sport_client.StopMove())
    except Exception as exc:
        print("Warning: SportClient StopMove failed:", exc)

    try:
        print("Sport zero Move:", sport_client.Move(0.0, 0.0, 0.0))
    except Exception as exc:
        print("Warning: SportClient zero Move failed:", exc)


def stop_obstacle(obstacle_client):
    try:
        print("Obstacle zero Move:", obstacle_client.Move(0.0, 0.0, 0.0))
    except Exception as exc:
        print("Warning: obstacle zero Move failed:", exc)


def enable_classic_walk(sport_client):
    print("ClassicWalk:", sport_client.ClassicWalk(True))
    time.sleep(0.5)


def enable_obstacle_api(obstacle_client):
    switch = obstacle_client.SwitchGet()
    print("SwitchGet before:", switch)
    deadline = time.monotonic() + OBSTACLE_ENABLE_TIMEOUT_S

    while not switch[1]:
        if time.monotonic() >= deadline:
            raise RuntimeError("Timed out enabling obstacle API")
        print("SwitchSet:", obstacle_client.SwitchSet(True))
        time.sleep(0.1)
        switch = obstacle_client.SwitchGet()

    print("SwitchGet after:", switch)
    print("UseRemoteCommandFromApi true:", obstacle_client.UseRemoteCommandFromApi(True))


def release_obstacle_api(obstacle_client):
    stop_obstacle(obstacle_client)
    try:
        print("UseRemoteCommandFromApi false:", obstacle_client.UseRemoteCommandFromApi(False))
    except Exception as exc:
        print("Warning: disabling obstacle remote API failed:", exc)


def repeated_obstacle_move(obstacle_client, vx, vy, vyaw, duration_s):
    period_s = 1.0 / MOVE_COMMAND_HZ
    end_time = time.monotonic() + duration_s

    while time.monotonic() < end_time:
        obstacle_client.Move(vx, vy, vyaw)
        time.sleep(period_s)


def clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def walk_duration_from_distance(distance_m, speed_mps):
    distance_m = clamp(float(distance_m), MIN_DISTANCE_M, MAX_DISTANCE_M)
    return distance_m / abs(speed_mps)


def rotate_duration_from_degrees(degrees):
    degrees = clamp(float(degrees), MIN_ROTATION_DEG, MAX_ROTATION_DEG)
    radians = math.radians(degrees)
    return (radians / abs(ROTATE_SPEED_RADPS)) * ROTATE_CORRECTION


class Go2Executor:
    def __init__(self):
        print("Initializing Go2 channel on", IFACE)
        initialize_channel()
        print("Channel ready.")
        self.sport_client = make_sport_client()
        self.obstacle_client = make_obstacle_client()

    def execute(self, command, distance_m=None, degrees=None):
        if command not in ALLOWED_COMMANDS:
            raise ValueError("Invalid Go2 command: {}".format(command))

        if command == "check":
            return "OK check obstacle_switch={}".format(self.obstacle_client.SwitchGet())

        if command == "stop":
            stop_obstacle(self.obstacle_client)
            stop_sport(self.sport_client)
            return "OK stop"

        if command == "release":
            release_obstacle_api(self.obstacle_client)
            stop_sport(self.sport_client)
            return "OK release"

        if command == "stand":
            print("StandUp:", self.sport_client.StandUp())
            return "OK stand"

        if command == "sit":
            print("Sit:", self.sport_client.Sit())
            return "OK sit"

        if command == "stand_down":
            print("StandDown:", self.sport_client.StandDown())
            return "OK stand_down"

        if command == "recover":
            print("RecoveryStand:", self.sport_client.RecoveryStand())
            return "OK recover"

        if command == "walk_forward":
            duration_s = WALK_DURATION_S
            if distance_m is not None:
                duration_s = walk_duration_from_distance(distance_m, WALK_SPEED_MPS)
            self.walk(vx=WALK_SPEED_MPS, vy=0.0, vyaw=0.0, duration_s=duration_s)
            return "OK walk_forward"

        if command == "walk_backward":
            duration_s = WALK_DURATION_S
            if distance_m is not None:
                duration_s = walk_duration_from_distance(distance_m, WALK_SPEED_MPS)
            self.walk(vx=-WALK_SPEED_MPS, vy=0.0, vyaw=0.0, duration_s=duration_s)
            return "OK walk_backward"

        if command == "walk_left":
            duration_s = LATERAL_DURATION_S
            if distance_m is not None:
                duration_s = walk_duration_from_distance(distance_m, LATERAL_SPEED_MPS)
            self.walk(vx=0.0, vy=LATERAL_SPEED_MPS, vyaw=0.0, duration_s=duration_s)
            return "OK walk_left"

        if command == "walk_right":
            duration_s = LATERAL_DURATION_S
            if distance_m is not None:
                duration_s = walk_duration_from_distance(distance_m, LATERAL_SPEED_MPS)
            self.walk(vx=0.0, vy=-LATERAL_SPEED_MPS, vyaw=0.0, duration_s=duration_s)
            return "OK walk_right"

        if command == "rotate_left":
            duration_s = ROTATE_DURATION_S
            if degrees is not None:
                duration_s = rotate_duration_from_degrees(degrees)
            self.walk(vx=0.0, vy=0.0, vyaw=ROTATE_SPEED_RADPS, duration_s=duration_s)
            return "OK rotate_left"

        if command == "rotate_right":
            duration_s = ROTATE_DURATION_S
            if degrees is not None:
                duration_s = rotate_duration_from_degrees(degrees)
            self.walk(vx=0.0, vy=0.0, vyaw=-ROTATE_SPEED_RADPS, duration_s=duration_s)
            return "OK rotate_right"

        if command == "turn_around":
            duration_s = TURN_AROUND_DURATION_S
            if degrees is not None:
                duration_s = rotate_duration_from_degrees(degrees)
            self.walk(vx=0.0, vy=0.0, vyaw=ROTATE_SPEED_RADPS, duration_s=duration_s)
            return "OK turn_around"

        return "ERROR unhandled {}".format(command)

    def walk(self, vx, vy, vyaw, duration_s):
        enable_classic_walk(self.sport_client)

        try:
            enable_obstacle_api(self.obstacle_client)
            repeated_obstacle_move(
                self.obstacle_client,
                vx=vx,
                vy=vy,
                vyaw=vyaw,
                duration_s=duration_s,
            )
        finally:
            release_obstacle_api(self.obstacle_client)
            stop_sport(self.sport_client)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=sorted(ALLOWED_COMMANDS))
    parser.add_argument("--distance-m", type=float, default=None)
    parser.add_argument("--degrees", type=float, default=None)
    args = parser.parse_args()

    executor = Go2Executor()
    print(executor.execute(
        args.command,
        distance_m=args.distance_m,
        degrees=args.degrees,
    ))


if __name__ == "__main__":
    main()

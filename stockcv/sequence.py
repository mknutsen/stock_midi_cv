from time import sleep, time
from math import floor
from threading import Lock, Thread
from time import sleep, time
from typing import Callable, Dict, List

from mido import Message

from flask_entry import (
    _BASE_KEYWORD,
    _DEBUG,
    _KEYWORD_LIST,
    _MAX_VALUE,
    _RATE_KEYWORD,
    _SKEW_KEYWORD,
    StockMidiCvException,
)
from helpers import _MILLISECONDS_PER_SECOND, get_time_ms, Value


class NoTimeException(StockMidiCvException):
    """time is not set yet"""


class InvalidSequenceProgress(StockMidiCvException):
    """must be a float between 0 and 1 for the %"""


class Clock:
    """A thread that controls a specific value over MIDI CC at a given rate
    This rate is computed in real time based on the tics that come in as input.
    """

    def __init__(self, sequence_length, tics_per_step, channel, cc, step_fn) -> None:
        print("abc123 init")
        self.sequence_length = sequence_length
        self.lock = Lock()
        self.step_index = 0
        self.tic_index = 0
        self.channel = channel
        self.cc = cc
        self.tics_ms = []
        self.step_fn: Callable[
            [None],
        ] = step_fn
        self.tics_per_step = Value(min=0.01, max=1000, initialized_value=tics_per_step)
        self.thread = Thread(target=self.time, args=())
        self.thread.start()

    def tic(self):
        time_ms = get_time_ms()
        with self.lock:
            self.tics_ms.append(time_ms)
            self.tic_index = self.tic_index + 1

    @property
    def ms_per_tick(self):
        # print("abc123 entering ms per tic")
        with self.lock:
            recent_tics = self.tics_ms[-4:]

        def _yeild_pairs(arr):
            for i in range(0, len(arr) - 1):
                yield arr[i], arr[i + 1]

        if len(recent_tics) >= 1:
            time_delta_list = [
                (time_b - time_a) for time_a, time_b in _yeild_pairs(recent_tics)
            ]
            # print(
            #     f"{time_delta_list} - sum: {sum(time_delta_list)} - len {len(time_delta_list)} - ret {sum(time_delta_list) / len(time_delta_list)}"
            # )

            return sum(time_delta_list) / len(time_delta_list)
        else:
            raise NoTimeException()

    @property
    def time_since_last_tic(self):
        with self.lock:
            return time() - self.tics_ms[-1]

    @property
    def sequence_progress(self):
        """
        Returns:
            Where we are in the sequence 0 - 1.0. 0 being at the very beginning and 1.0 being at the very end
        """
        num_tics = self.tic_index + self.time_since_last_tic / self.ms_per_tick
        num_steps = num_tics / self.tics_per_step
        percent = num_steps / self.sequence_length
        print(f"sequence progress: tics: {num_tics} steps:{num_steps} perct: {percent}")
        return percent

    @property
    def tic_index(self):
        return self._tic_index

    @tic_index.setter
    def tic_index(self, value):
        self._tic_index = value
        if self._tic_index > self.sequence_length:
            self._tic_index = 0

    def time(self):
        print("abc123 time init")
        # get past the beginning when no time
        while True:
            try:
                print(self.ms_per_tick)
                break
            except NoTimeException:
                pass

        while True:
            # call the function to update the value
            self.step_fn(self.sequence_progress)
            # sleep until the next update is due
            sleep_duration_msec: float = self.tics_per_step * self.ms_per_tick
            sleep_duration_sec: float = sleep_duration_msec * _MILLISECONDS_PER_SECOND
            sleep(sleep_duration_sec)


class SequenceState:
    """abstract class to be implemented with _step"""

    def __init__(self, sequence: List[float], port, tics_per_step, channel, cc) -> None:
        def step_fn(sequence_percent_progress: float):
            self._step(sequence_percent_progress)

        self.port = port
        self.sequence = sequence
        self.clock = Clock(
            sequence_length=len(sequence),
            tics_per_step=tics_per_step,
            channel=channel,
            cc=cc,
            step_fn=step_fn,
        )
        self.alter_table: Dict[str, Value] = {
            word: Value(
                initialized_value=(_MAX_VALUE / 2), max_value=_MAX_VALUE, min_value=0
            )
            for word in _KEYWORD_LIST
        }
        # set a listener here and on each action if there is a listener it will be called
        self.alter_action_table = {}

    def set_sequence(self, sequence: List[float]):
        self.sequence = sequence
        self.clock.sequence_length = self.sequence_length

    @property
    def sequence_length(self):
        return len(self.sequence)

    def alter(self, key, value):
        print(f"altering: key {key}  {value}")
        self.alter_table[key] = value
        if key in self.alter_action_table:
            print("calling action {key} with {value}")
            # call action listener
            self.alter_action_table[key](value)
        else:
            print(f"not calling any action for {key}")

    def _step(self, sequence_percent_progress: float):
        """Abstract"""
        raise NotImplementedError


class AveragingSequenceState(SequenceState):
    def __init__(self, sequence: List[float], port, tics_per_step, channel, cc) -> None:
        super().__init__(sequence, port, tics_per_step, channel, cc)

        def _alter_tics_per_step(value):
            self.clock.tics_per_step = value

        self.alter_action_table[_RATE_KEYWORD] = _alter_tics_per_step

    def _step(self, sequence_percent_progress: float):
        if sequence_percent_progress > 1 or sequence_percent_progress < 0:
            raise InvalidSequenceProgress()

        # rounding down to the nearest step
        step_index = floor(sequence_percent_progress * self.sequence_length)
        raw_step_value = self.sequence[step_index]

        # getting relevant data out of the alter table
        rate_value = self.alter_table[_RATE_KEYWORD]
        base_value = self.alter_table[_BASE_KEYWORD]
        skew_value = self.alter_table[_SKEW_KEYWORD]
        skewed_skew_value = Value(
            min_value=0.5, max_value=1.5, initialized_percent=skew_value.value_percent
        )
        # computing step by skewing raw value
        computed_step = raw_step_value * skewed_skew_value
        # normalize step to be between 0 and max value
        normalized_value: Value = Value(
            max_value=_MAX_VALUE,
            min_value=base_value.value,
            initialized_percent=computed_step,
        )
        message = Message(
            type="control_change",
            channel=self.channel,
            control=self.cc,
            value=normalized_value,
        )
        self.tics_per_step = rate_value
        if not _DEBUG:
            self.port.send(message)
        else:
            print("not sending bc debug -", message)

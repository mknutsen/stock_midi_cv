from mido import Message
from typing import Dict
from threading import Lock
from helpers import Value
from time import time, sleep
from PyQt5 import QtWidgets
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from threading import Thread
from flask_entry import (
    main as flask_entry_point,
    _KEYWORD_LIST,
    _BASE_KEYWORD,
    _MAX_VALUE,
    _SKEW_KEYWORD,
    _RATE_KEYWORD,
    _DEBUG,
)

class NoTimeException(Exception):
    """time is not set yet"""

class CvSequence:
    def __init__(self, port, sequence, tics_per_step, channel, cc) -> None:
        print("abc123 init")
        self.lock = Lock()
        self.step_index = 0
        self.tic_index = 0
        self.port = port
        self.sequence = sequence
        self.sequence_length = len(sequence)
        self.channel = channel
        self.cc = cc
        self.tics = []
        self.tics_per_step = tics_per_step
        self.alter_table: Dict[str, Value] = {
            word: Value(initialized_value=0, max_value=_MAX_VALUE, min_value=0)
            for word in _KEYWORD_LIST
        }
        self.thread = Thread(target=self.time, args=())
        self.thread.start()

    @property
    def ms_per_tick(self):
        print("abc123 entering ms per tic")
        with self.lock:
            recent_tics = self.tics[-4:]
        def _yeild_pairs(arr):
            for i in range(0, len(arr) - 1):
                yield (arr[i], arr[i+1])
        if len(recent_tics) >= 1:
            time_delta_list = [(time_b - time_a) for time_a, time_b in _yeild_pairs(recent_tics)]
            print(f"{time_delta_list} - sum: {sum(time_delta_list)} - len {len(time_delta_list)} - ret {sum(time_delta_list) / len(time_delta_list)}")

            return (sum(time_delta_list) / len(time_delta_list))
        else:
            raise NoTimeException()

        

    def time(self):
        print("abc123 time!!!")
        # old_tick_len = len(self.tics)
        while True:
            try:
                print(self.ms_per_tick)
            except NoTimeException:
                pass
            sleep(5)


    def alter(self, name, value):
        self.alter_table[name].value = int(value)

    def _increment_step_index(self):
        # print("next_step", self.step_index)
        self.step_index += 1
        if self.step_index >= self.sequence_length:
            print("----LOOP-------")
            self.step_index = 0

    def tick(self):
        with self.lock:
            self.ticks.append(time())
            self.tic_index += 1
            tic_index = self.tic_index
            tics_per_step = self.tics_per_step 
        
        if tic_index >= tics_per_step:
            self._step()
            with self.lock:
                self.tic_index = 0

    def _step(self):
        # print("step")
        raw_step_value = self.sequence[self.step_index]
        rate_value = self.alter_table[_RATE_KEYWORD]
        # length_value = self.alter_table[_LENGTH_KEYWORD]
        # range_value = self.alter_table[_RANGE_KEYWORD]
        base_value = self.alter_table[_BASE_KEYWORD]
        skew_value = self.alter_table[_SKEW_KEYWORD]
        skewed_skew_value = Value(
            min_value=0.5, max_value=1.5, initialized_percent=skew_value.value_percent
        )
        computed_step = raw_step_value * skewed_skew_value
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
        print(f"{'not sending' if _DEBUG else 'sending'}", message)
        self._increment_step_index()

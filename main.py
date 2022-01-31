from mido import Message, open_input, get_input_names, get_output_names
from yfinance import download as stock_price_download
from typing import List, Callable
from pandas import DataFrame
from threading import Thread, Lock
from math import floor

ticker: str = "AAPL"
start_date: str = "2016-01-01"
end_date: str = "2018-01-01"
steps = 16
mix = 1

output_port_name: str = "FH-2"
input_port_name: str = "Arturia BeatStep Pro Arturia BeatStepPro"

data: DataFrame = stock_price_download(ticker, start_date, end_date)
stock_data = None

for label, content in data.items():
    if label == "Open":
        stock_data = content

num_entries: int = len(stock_data)
step_factor: int = floor(num_entries / steps)
port_out = None
port_in = None

step_values: List[float] = [
    stock_data[index] for index in range(0, num_entries, step_factor)
]
sorted_values: List[float] = [
    stock_data[index] for index in range(0, num_entries, step_factor)
]
sorted_values.sort()

min_value: float = sorted_values[-1]
max_value: float = sorted_values[0]
min_max_gap: float = max_value - min_value

normalized_data: List[float] = [
    ((step - min_value) / min_max_gap) for step in step_values
]

mixed_data: List[float] = [
    ((normalized - raw) * mix) + raw
    for raw, normalized in zip(step_values, normalized_data)
]


class Clock:
    def __init__(self, callback_fn) -> None:
        self.callback_fn: Callable[[], None] = callback_fn
        pass

    def tic(self) -> None:
        self.callback_fn()


def input_loop(port_name: str, clock: Clock) -> None:
    print("input loop")
    try:
        port = open_input(port_name)
    except:
        print("input failed")
        print(get_input_names())
        raise
    print("up and running")
    for message in port:
        if message.type != "clock":
            # print(message.type, message)
            continue
        clock.tic()


class CvSequence:
    def __init__(self, port, sequence, tics_per_step, channel, cc) -> None:
        self.lock = Lock()
        self.step_index = 0
        self.tic_index = 0
        self.port = port
        self.sequence = sequence
        self.sequence_length = len(sequence)
        self.channel = channel
        self.cc = cc
        self.tics_per_step = tics_per_step

    def _increment_step_index(self):
        # print("next_step", self.step_index)
        self.step_index += 1
        if self.step_index >= self.sequence_length:
            self.step_index = 0
    
    def tick(self):
        with self.lock:
            self.tic_index += 1
            if self.tic_index >= self.tics_per_step:
                self.tic_index = 0
                self._step()

    def _step(self):
        # print("step")
        normalized_value: int = floor(127 * normalized_data[self.step_index])
        message = Message(
            type="control_change",
            channel=self.channel,
            control=self.cc,
            value=normalized_value,
        )
        # self.port.send(message)
        print(message)
        self._increment_step_index()


sequence = CvSequence(port= None, sequence=normalized_data, tics_per_step = 16, channel = 0, cc = 20)

def clock_tic_callback() -> None:
    # print("clock tick callback")
    sequence.tick()


clock = Clock(clock_tic_callback)
input_thread = Thread(target=input_loop, args=(input_port_name, clock))
input_thread.start()

while True:
    pass

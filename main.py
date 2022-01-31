from mido import Message, open_input, get_input_names, get_output_names, open_output
from yfinance import download as stock_price_download
from typing import List, Callable
from pandas import DataFrame
from threading import Thread, Lock
from math import floor

ticker: str = "AAPL"
start_date: str = "2016-01-01"
end_date: str = "2018-01-01"
steps = 128
mix = 1

output_port_name: str = "mio"
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

min_value: float = sorted_values[0]
max_value: float = sorted_values[-1]
min_max_gap: float = max_value - min_value

normalized_data: List[float] = [
    (step - min_value) / min_max_gap for step in step_values
]

print(step_values[0:10])
print(normalized_data[0:10])

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
            print("----LOOP-------")
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
        self.port.send(message)
        print(message)
        self._increment_step_index()

try:
    port_out = open_output(output_port_name)
except:
    print(get_output_names())
    raise

sequence = CvSequence(port= port_out, sequence=normalized_data, tics_per_step = 4, channel = 2, cc = 22)

def clock_tic_callback() -> None:
    # print("clock tick callback")
    sequence.tick()


clock = Clock(clock_tic_callback)
input_thread = Thread(target=input_loop, args=(input_port_name, clock))
input_thread.start()

from PyQt5 import QtWidgets
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
import sys  # We need sys so that we can pass argv to QApplication
import os

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.graphWidget = pg.PlotWidget()
        self.setCentralWidget(self.graphWidget)
        x = [i for i in range(len(stock_data))]
        y = stock_data
        # plot data: x, y values
        self.graphWidget.plot(x, y)

app = QtWidgets.QApplication(sys.argv)
main = MainWindow()
main.show()
sys.exit(app.exec_())

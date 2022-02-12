from re import M
from mido import Message, open_input, get_input_names, get_output_names, open_output
from yfinance import download as stock_price_download
from typing import List, Callable, Optional, Dict
from pandas import DataFrame
from threading import Thread, Lock
from math import floor
from helpers import Clock, Value
import logging
from flask_entry import (
    main as flask_entry_point,
    _KEYWORD_LIST,
    _RANGE_KEYWORD,
    _LENGTH_KEYWORD,
    _BASE_KEYWORD,
    _MAX_VALUE,
    _SKEW_KEYWORD,
    _RATE_KEYWORD,
)

_DEBUG = True
ticker: str = "PTON"
start_date: str = "2020-01-01"
end_date: str = "2022-01-01"
steps = Value(max_value=1024, min_value=8, initialized_value=32)

channel = 2
cc = 22
tics_per_step = Value(max_value=1024, min_value=1, initialized_value=8)
SEQUENCE = None

output_port_name: str = "mio"
input_port_name: str = "Arturia BeatStep Pro Arturia BeatStepPro"
stock_data = None


def math():
    global stock_data
    df: DataFrame = stock_price_download(ticker, start_date, end_date)
    df = df["Open"]

    num_entries: int = len(df)
    step_factor: int = floor(num_entries / steps.value)
    # NOTE: if the goal is to get 32 final steps, the floor causes the actual number you get to be slightly higher (ex.: ~34)

    filtered_df = df.iloc[::step_factor]

    min_value: float = df.min()
    max_value: float = df.max()
    value_range: float = max_value - min_value

    normalized_df = (filtered_df - min_value) / value_range

    # mixed_data: List[float] = [
    #     ((normalized - raw) * mix) + raw
    #     for raw, normalized in zip(step_values, normalized_data)
    # ]

    return normalized_df.tolist()


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
        if message.type == "clock":
            clock.tic()
        else:
            # thru port hack
            # print("input loop sending", message)
            clock.tic(message)


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
        self.alter_table: Dict[str, Value] = {
            word: Value(initialized_value=0, max_value=_MAX_VALUE, min_value=0)
            for word in _KEYWORD_LIST
        }

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
            self.tic_index += 1
            if self.tic_index >= self.tics_per_step:
                self.tic_index = 0
                self._step()

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
        computed_step = base_value.value_percent + raw_step_value * skewed_skew_value
        normalized_value: Value = Value(
            max_value=_MAX_VALUE, min_value=0, initialized_percent=computed_step
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


def data_callback(name, value):
    global SEQUENCE
    SEQUENCE.alter(name, value)


def main():
    global SEQUENCE
    logging.basicConfig(filename="example.log", encoding="utf-8", level=logging.DEBUG)
    if not _DEBUG:
        try:
            port_out = open_output(output_port_name)
        except:
            print(get_output_names())
            raise
    else:
        port_out = None

    normalized_sequence_data = math()
    SEQUENCE = CvSequence(
        port=port_out,
        sequence=normalized_sequence_data,
        tics_per_step=tics_per_step,
        channel=channel,
        cc=cc,
    )

    def clock_tic_callback(message: Optional[Message] = None) -> None:
        if not message:
            sequence.tick()
        else:
            # print("clock tick callback", message)
            if not _DEBUG:
                port_out.send(message)

    flask_entry_point(callback=data_callback)
    # clock = Clock(clock_tic_callback)
    # input_thread = Thread(target=input_loop, args=(input_port_name, clock))
    # input_thread.start()


if __name__ == "__main__":
    main()

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
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec_())

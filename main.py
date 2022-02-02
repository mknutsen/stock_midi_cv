from mido import Message, open_input, get_input_names, get_output_names, open_output
from yfinance import download as stock_price_download
from typing import List, Callable, Optional
from pandas import DataFrame
from threading import Thread, Lock
from math import floor

ticker: str = "PTON"
start_date: str = "2020-01-01"
end_date: str = "2022-01-01"
steps = 32
mix = 1

channel = 2
cc = 22
tics_per_step = 8

output_port_name: str = "mio"
input_port_name: str = "Arturia BeatStep Pro Arturia BeatStepPro"
stock_data = None

def math():
    global stock_data
    df: DataFrame = stock_price_download(ticker, start_date, end_date)
    df = df['Open']

    num_entries: int = len(df)
    step_factor: int = floor(num_entries / steps) 
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


class Clock:
    def __init__(self, callback_fn) -> None:
        self.callback_fn: Callable[[Optional[Message]], None] = callback_fn
        pass

    def tic(self, message: Optional[Message] = None) -> None:
        self.callback_fn(message)

    def message(self, message: Message) -> None:
        self.callback_fn(message)


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
        normalized_value: int = floor(127 * self.sequence[self.step_index])
        message = Message(
            type="control_change",
            channel=self.channel,
            control=self.cc,
            value=normalized_value,
        )
        self.port.send(message)
        print(message)
        self._increment_step_index()


def main():
    try:
        port_out = open_output(output_port_name)
    except:
        print(get_output_names())
        raise

    normalized_sequence_data = math()
    sequence = CvSequence(port= port_out, sequence=normalized_sequence_data, tics_per_step = tics_per_step, channel = channel, cc = cc)

    def clock_tic_callback(message: Optional[Message] = None) -> None:
        if not message:
            sequence.tick()
        else:
            # print("clock tick callback", message)
            port_out.send(message)


    clock = Clock(clock_tic_callback)
    input_thread = Thread(target=input_loop, args=(input_port_name, clock))
    input_thread.start()

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
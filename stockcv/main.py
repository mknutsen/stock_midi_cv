from mido import Message, open_input, get_input_names, get_output_names, open_output
from yfinance import download as stock_price_download
from typing import List, Callable, Optional, Dict
from pandas import DataFrame
from threading import Thread, Lock
from math import floor
from helpers import Clock, Value, MainWindow
import logging
import sys
import os

from PyQt5 import QtWidgets
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from flask_entry import (
    main as flask_entry_point,
    _KEYWORD_LIST,
    _RANGE_KEYWORD,
    _LENGTH_KEYWORD,
    _BASE_KEYWORD,
    _MAX_VALUE,
    _SKEW_KEYWORD,
    _RATE_KEYWORD,
    _DEBUG,
)
from sequence import CvSequence

GLOBAL_TICKER: str = "PTON"
GLOBAL_START_DATE: str = "2020-01-01"
GLOBAL_END_DATE: str = "2022-01-01"
GLOBAL_NUM_STEPS = Value(max_value=1024, min_value=8, initialized_value=32)

channel = 2
cc = 22
tics_per_step = Value(max_value=1024, min_value=1, initialized_value=8)
SEQUENCE = None

output_port_name: str = "mio"
input_port_name: str = "Arturia BeatStep Pro Arturia BeatStepPro"
GLOBAL_STOCK_DATA = None


def math():
    global GLOBAL_STOCK_DATA, GLOBAL_TICKER, GLOBAL_START_DATE, GLOBAL_END_DATE
    df: DataFrame = stock_price_download(GLOBAL_TICKER, GLOBAL_START_DATE, GLOBAL_END_DATE)
    df = df["Open"]
    GLOBAL_STOCK_DATA = df
    num_entries: int = len(df)

    if not num_entries:
        print("empty stock info")
        return []

    step_factor: int = floor(num_entries / GLOBAL_NUM_STEPS.value)
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
    logging.debug("input loop")
    if not _DEBUG:
        try:
            port = open_input(port_name)
        except:
            logging.debug("input failed")
            logging.debug(get_input_names())
            raise
        logging.debug("up and running")
        for message in port:
            if message.type == "clock":
                clock.tic()
            else:
                # thru port hack
                # logging.debug("input loop sending", message)
                clock.tic(message)
    else:
        logging.debug("input loop is nto running because of debug mode")


def data_callback(name, value):
    global SEQUENCE, GLOBAL_STOCK_DATA, GLOBAL_TICKER, GLOBAL_START_DATE, GLOBAL_END_DATE
    if name == "ticker":
        print("ticker", name, value)
        GLOBAL_TICKER = value
        SEQUENCE.set_sequence(math())
    else:
        SEQUENCE.alter(name, value)


def run_graph():
    global GLOBAL_STOCK_DATA
    logging.debug(f"abc123 running graph {GLOBAL_STOCK_DATA}")
    app = QtWidgets.QApplication(sys.argv)
    mw = MainWindow(GLOBAL_STOCK_DATA)
    mw.show()


def main():
    global SEQUENCE
    if not _DEBUG:
        try:
            port_out = open_output(output_port_name)
        except:
            logging.debug(get_output_names())
            raise
    else:
        port_out = None

    def clock_tic_callback(message: Optional[Message] = None) -> None:
        global SEQUENCE
        if not message:
            SEQUENCE.tick()

        if not _DEBUG:
            port_out.send(message)

    normalized_sequence_data = math()
    SEQUENCE = CvSequence(
        port=port_out,
        sequence=normalized_sequence_data,
        tics_per_step=tics_per_step,
        channel=channel,
        cc=cc,
    )

    clock = Clock(clock_tic_callback)
    input_thread = Thread(target=input_loop, args=(input_port_name, clock))
    input_thread.start()
    flask_thread = Thread(target=flask_entry_point, args=(data_callback,))
    flask_thread.start()
    # app = QtWidgets.QApplication(sys.argv)
    # mw = MainWindow(GLOBAL_STOCK_DATA)
    # mw.show()
    # sys.exit(app.exec_())
    # flask_entry_point(callback=data_callback)


if __name__ == "__main__":
    logging.basicConfig(filename="example.log", encoding="utf-8", level=logging.DEBUG)
    main()

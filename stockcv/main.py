import logging
import sys
from math import floor
from threading import Thread
from typing import List, Optional

from mido import get_input_names, get_output_names, open_input, open_output
from mido.ports import BaseOutput as Port
from pandas import DataFrame
from PyQt5 import QtWidgets
from yfinance import download as stock_price_download

from flask_entry import _DEBUG, main as flask_entry_point
from helpers import MainWindow, Value
from sequence import AveragingSequenceState, Clock, SequenceState

GLOBAL_OUTPUT_PORT: Optional[Port] = None
GLOBAL_SEQUENCE: Optional[SequenceState] = None
GLOBAL_STOCK_DATA_AS_STEPS: Optional[List[float]] = None
GLOBAL_TICKER: str = "PTON"
GLOBAL_START_DATE: str = "2020-01-01"
GLOBAL_END_DATE: str = "2022-01-01"
GLOBAL_NUM_STEPS = Value(max_value=1024, min_value=8, initialized_value=32)

channel = 2
cc = 22
tics_per_step = Value(max_value=1024, min_value=1, initialized_value=8)

output_port_name: str = "mio"
input_port_name: str = "Arturia BeatStep Pro Arturia BeatStepPro"
GLOBAL_STOCK_DATA = None
GLOBAL_THRU = True  # is a thru port


def math():
    global GLOBAL_STOCK_DATA, GLOBAL_TICKER, GLOBAL_START_DATE, GLOBAL_END_DATE, GLOBAL_STOCK_DATA_AS_STEPS
    df: DataFrame = stock_price_download(
        GLOBAL_TICKER, GLOBAL_START_DATE, GLOBAL_END_DATE
    )
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

    GLOBAL_STOCK_DATA_AS_STEPS = normalized_df.tolist()
    return normalized_df.tolist()


def input_loop(port_name: str) -> None:
    global GLOBAL_OUTPUT_PORT, GLOBAL_THRU, GLOBAL_SEQUENCE
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
                GLOBAL_SEQUENCE.clock.tic()
            if GLOBAL_THRU and GLOBAL_OUTPUT_PORT:
                GLOBAL_OUTPUT_PORT.send(message)
    else:
        logging.debug("input loop is not running because of debug mode")


def data_callback(name, value):
    global GLOBAL_CLOCK, GLOBAL_STOCK_DATA, GLOBAL_TICKER, GLOBAL_START_DATE, GLOBAL_END_DATE
    if name == "ticker":
        print("ticker", name, value)
        GLOBAL_TICKER = value
        math()  # sets global
        GLOBAL_SEQUENCE.set_sequence(GLOBAL_STOCK_DATA_AS_STEPS)
    else:
        GLOBAL_SEQUENCE.alter(name, value)


def run_graph():
    global GLOBAL_STOCK_DATA
    logging.debug(f"abc123 running graph {GLOBAL_STOCK_DATA}")
    app = QtWidgets.QApplication(sys.argv)
    mw = MainWindow(GLOBAL_STOCK_DATA)
    mw.show()


def main():
    global GLOBAL_OUTPUT_PORT, GLOBAL_SEQUENCE
    if not _DEBUG:
        try:
            GLOBAL_OUTPUT_PORT = open_output(output_port_name)
        except:
            logging.debug(get_output_names())
            raise

    normalized_sequence_data = math()

    GLOBAL_SEQUENCE = AveragingSequenceState(
        tics_per_step=tics_per_step,
        channel=channel,
        cc=cc,
        sequence=normalized_sequence_data,
        port=GLOBAL_OUTPUT_PORT,
    )

    input_thread = Thread(target=input_loop, args=(input_port_name,))
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

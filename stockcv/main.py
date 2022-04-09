import logging
from threading import Thread
from typing import List, Optional

from mido import get_input_names, get_output_names, open_input, open_output, Message
from mido.ports import BaseOutput as Port

from flask_entry import _DEBUG, main as flask_entry_point

GLOBAL_OUTPUT_PORT: Optional[Port] = None

output_port_name: str = "mio"
input_port_name: str = "Arturia BeatStep Pro Arturia BeatStepPro"
GLOBAL_THRU = True  # is a thru port


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
            if message.type == "control_change":
                # only reroute things in our mapping table
                cc = GLOBAL_MAPPING_TABLE.get(message.control, message.control)
                out_msg = Message(
                    type=message.type,
                    channel=message.channel,
                    control=cc,
                    value=message.value,
                )

                print(out_msg)
                GLOBAL_OUTPUT_PORT.send(out_msg)
    else:
        logging.debug("input loop is not running because of debug mode")


def data_callback(key, value):
    """just send to output based on mapping"""
    global GLOBAL_MAPPING_TABLE, GLOBAL_OUTPUT_PORT


GLOBAL_MAPPING_TABLE = dict()


def mapping_callback(key, value):
    global GLOBAL_MAPPING_TABLE
    print(f"mapping callback key {key} value {value}")
    GLOBAL_MAPPING_TABLE[key] = value


def main():
    global GLOBAL_OUTPUT_PORT
    if not _DEBUG:
        try:
            GLOBAL_OUTPUT_PORT = open_output(output_port_name)
        except:
            logging.debug(get_output_names())
            raise

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

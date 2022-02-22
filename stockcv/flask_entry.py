from flask import Flask, request, send_from_directory
from pystache import Renderer
from os import makedirs
from shutil import rmtree
from pathlib import Path


class StockMidiCvException(Exception):
    """ExceptionClass"""


class FlaskException(StockMidiCvException):
    """This is what happens when flask fails"""


file_path = Path(__file__) / ".."
static_web_folder_name = "static_web"
dashboard_file_name = "dashboard"

_DEBUG = True
static_web_folder_path = file_path / static_web_folder_name
static_web_folder_path_str = static_web_folder_path.resolve()
dashboard_file_path = static_web_folder_path / (dashboard_file_name + ".html")
dashboard_file_path_str = dashboard_file_path.resolve()

_MAX_VALUE = 100
_RATE_KEYWORD = "rate"
_LENGTH_KEYWORD = "length"
_RANGE_KEYWORD = "range"
_BASE_KEYWORD = "base"
_SKEW_KEYWORD = "skew"
_KEYWORD_LIST = [
    _RATE_KEYWORD,
    _LENGTH_KEYWORD,
    _RANGE_KEYWORD,
    _BASE_KEYWORD,
    _SKEW_KEYWORD,
]

rmtree(static_web_folder_path_str)
makedirs(static_web_folder_path_str)
input_template = """
Hello world dashboard

<FORM id="form">

    {{#names}}
    {{name}}
    <input type="range" name="{{name}}" min="0" max="{{max_value}}" value="50" class="slider" id="{{name}}">
    {{/names}}
</FORM>
<form>
  <input type="textbox" id="stock_box">
  <input type="button" id="stock_button">
</form>
<script>
  (function () {
    var xhr = new XMLHttpRequest();
    document.getElementById("stock_button").addEventListener('click', () => {
      console.log("button pressed: " + document.getElementById("stock_box").value);
      xhr.open("POST", '/result', true);
      xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
      xhr.send("name=ticker&value=" + document.getElementById("stock_box").value);
    });
    {{#names}}
    document.getElementById("{{name}}").addEventListener('click', () => {
      console.log("abc123 event {{name}}");
      console.log(event);
      xhr.open("POST", '/result', true);

      //Send the proper header information along with the request
      xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");

      console.log(document.getElementById("{{name}}").value)
      xhr.send("name={{name}}&value=" + document.getElementById("{{name}}").value);
    });
    {{/names}}
  })();
</script>
"""

input_dict = {"names": [{"name": element} for element in _KEYWORD_LIST]}
input_dict["max_value"] = _MAX_VALUE
renderer = Renderer()

with open(dashboard_file_path_str, "w") as file:
    file.write(renderer.render(input_template, input_dict))

GLOBAL_DATA_CALLBACK = None
app = Flask(__name__, static_url_path="", static_folder=static_web_folder_path_str)


def main(callback=None):
    global GLOBAL_DATA_CALLBACK
    if callback:
        GLOBAL_DATA_CALLBACK = callback
    app.run(host="localhost", port=5000)


@app.route("/stock", methods=["GET", "POST"])
def parse_stock():
    print("abc123 in stock parse", request)
    return "ak"


@app.route("/result", methods=["GET", "POST"])
def parse_request():
    global GLOBAL_DATA_CALLBACK
    data = request.data  # data is empty
    data_source_name = request.form.get("name", "")
    data_value = request.form.get("value", "")
    print(
        "abc123 hsdaf0dishfpiadsjh",
        data,
        data_source_name,
        data_value,
        request,
        request.data,
    )
    # print("in here abc123", data, type(data), request.form)
    if GLOBAL_DATA_CALLBACK:
        if not (data_source_name and data_value):
            raise FlaskException()
        GLOBAL_DATA_CALLBACK(data_source_name, data_value)
    # print("data dict: ", data.__dict__)
    return "ak"
    # need posted data here


if __name__ == "__main__":
    main()

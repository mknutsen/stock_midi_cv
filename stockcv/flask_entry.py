from flask import Flask, request, send_from_directory
from pystache import Renderer
from os import makedirs
from shutil import rmtree
from pathlib import Path


class FlaskException(Exception):
    """This is what happens when flask fails"""


file_path = Path(__file__) / ".."
static_web_folder_name = "static_web"
dashboard_file_name = "dashboard"

static_web_folder_path = file_path / static_web_folder_name
static_web_folder_path_str = static_web_folder_path.resolve()
dashboard_file_path = static_web_folder_path / (dashboard_file_name + ".html")
dashboard_file_path_str = dashboard_file_path.resolve()


_RATE_KEYWORD = "RATE"
_LENGTH_KEYWORD = "length"
_RANGE_KEYWORD = "range"
_BASE_KEYWORD = "base"
_KEYWORD_LIST = [_RATE_KEYWORD, _LENGTH_KEYWORD, _RANGE_KEYWORD, _BASE_KEYWORD]

rmtree(static_web_folder_path_str)
makedirs(static_web_folder_path_str)
input_template = """
Hello world dashboard

<FORM action="/result" method="post" id="form">

    {{#names}}
    {{name}}
    <input type="range" name="{{name}}" min="0" max="100" value="50" class="slider" id="{{name}}">
    {{/names}}
  <INPUT type="submit" name="Send">
</FORM>
<script>
  (function () {
    var xhr = new XMLHttpRequest();
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


@app.route("/result", methods=["GET", "POST"])
def parse_request():
    global GLOBAL_DATA_CALLBACK
    data = request.data  # data is empty
    data_source_name = request.form.get("name", "")
    data_value = request.form.get("value", "")
    print("in here abc123", data, type(data), request.form)
    if GLOBAL_DATA_CALLBACK:
        if not (data_source_name and data_value):
            raise FlaskException()
        GLOBAL_DATA_CALLBACK(data_source_name, data_value)
    # print("data dict: ", data.__dict__)
    return "ak"
    # need posted data here


if __name__ == "__main__":
    main()

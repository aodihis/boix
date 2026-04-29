from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route("/actions/elements/save", methods=["POST"])
def save_element():
    print(f"[Craft Stub] POST /actions/elements/save body={request.get_json(silent=True)}")
    return jsonify({"success": True, "id": 1})

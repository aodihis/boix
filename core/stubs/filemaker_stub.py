from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route("/fmrest/vLatest/databases/<db>/sessions", methods=["POST"])
def create_session(db: str):
    print(f"[FM Stub] POST /sessions db={db} body={request.get_json(silent=True)}")
    return jsonify({"response": {"token": "stub-token-abc123"}, "messages": [{"code": "0", "message": "OK"}]})


@app.route("/fmrest/vLatest/databases/<db>/layouts/<layout>/records", methods=["POST"])
def create_record(db: str, layout: str):
    print(f"[FM Stub] POST /records db={db} layout={layout} body={request.get_json(silent=True)}")
    return jsonify({"response": {"recordId": "1", "modId": "0"}, "messages": [{"code": "0", "message": "OK"}]})


@app.route("/fmrest/vLatest/databases/<db>/sessions/<token>", methods=["DELETE"])
def delete_session(db: str, token: str):
    print(f"[FM Stub] DELETE /sessions db={db} token={token}")
    return jsonify({"response": {}, "messages": [{"code": "0", "message": "OK"}]})

import logging
from argparse import ArgumentParser

from daggerml import Dml
from flask import Flask, jsonify, render_template, request, url_for

from dml_ui.app.util import get_dag_info, get_node_info
from dml_ui.cloudwatch import CloudWatchLogs

logger = logging.getLogger(__name__)
app = Flask(__name__)


def get_dropdowns(dml, repo, branch, dag_id):
    dropdowns = {"repos": {x["name"]: url_for("main", repo=x["name"]) for x in dml("repo", "list")}}
    if repo is not None:
        dropdowns["branches"] = {x: url_for("main", repo=repo, branch=x) for x in dml("branch", "list")}
    if branch is not None:
        tmp = {x["name"]: x["id"] for x in dml("dag", "list")}
        dropdowns["dags"] = {k: url_for("main", repo=repo, branch=branch, dag_id=v) for k, v in tmp.items()}
    return dropdowns


cloudwatch_logs = CloudWatchLogs()

@app.route("/")
def main():
    dml = Dml()
    repo = request.args.get("repo")
    branch = request.args.get("branch")
    dag_id = request.args.get("dag_id")
    node_id = request.args.get("node_id")
    dropdowns = get_dropdowns(dml, repo, branch, dag_id)
    if dag_id is None:
        return render_template("index.html", dropdowns=dropdowns)
    if node_id is None:
        print("running dag_id", dag_id)
        data = get_dag_info(dml, dag_id)
        data.pop("argv", None)
        data.update(data.pop("result", {}))
        log_streams = data.pop("log_streams", {})
        print("yyyyyyyyyyyyyyyyyyyyy")
        print(f"AAA... {log_streams = }")
        dag_data = data.pop("dag_data")
        for node in dag_data["nodes"]:
            node["link"] = url_for(
                "main",
                repo=repo,
                branch=branch,
                dag_id=dag_id,
                node_id=node["id"] or "",
            )
            if node["node_type"] in ["import", "fn"]:
                node["parent_link"] = url_for("main", repo=repo, branch=branch, dag_id=node["parent"])
                if node["node_type"] == "fn":
                    node["sublist"] = [
                        [
                            x,
                            url_for(
                                "main",
                                repo=repo,
                                branch=branch,
                                dag_id=dag_id,
                                node_id=x,
                            ),
                        ]
                        for x in node["sublist"]
                    ]
        return render_template("dag.html", dropdowns=dropdowns, data=dag_data, log_streams=log_streams, **data)
    data = get_node_info(dml, dag_id, node_id)
    return render_template(
        "node.html",
        dropdowns=dropdowns,
        dag_id=dag_id,
        dag_link=url_for("main", repo=repo, branch=branch, dag_id=dag_id),
        node_id=node_id,
        **data,
    )

@app.route("/logs", methods=["GET"])
def get_logs():
    """
    Fetch logs for a specific DAG with pagination.

    Query Parameters:
    - stream: The log stream name to fetch (e.g. stdout, stderr)
    - next_token: Token for pagination
    - limit: Maximum number of log events to return
    """
    dml = Dml()
    dag_id = request.args.get("dag_id")
    stream = request.args.get("stream_name")
    next_token = request.args.get("next_token")
    print(f"{stream = }")
    limit = request.args.get("limit", 100, type=int)
    # Get the dag info to find the log stream details
    dag_info = get_dag_info(dml, dag_id)
    log_streams = dag_info.get("log_streams", {})
    print(f"get_logs: {log_streams = }")
    # If the stream name doesn't exist in the log_streams, return an error
    if stream not in log_streams:
        return jsonify({
            "error": f"Log stream {stream} not found for DAG {dag_id}",
            "available_streams": list(log_streams.keys())
        }), 401
    # Get the log stream details
    stream_details = log_streams[stream]
    log_group = stream_details["log_group"]
    log_stream = stream_details["log_stream"]
    # Get the logs from CloudWatch
    logs = cloudwatch_logs.get_log_events(
        log_group_name=log_group,
        log_stream_name=log_stream,
        next_token=next_token,
        limit=min(limit, 1000),  # Limit to 1000 events max
        start_from_head=True
    )
    return jsonify(logs)

@app.route("/idx")
def idx():
    dml = Dml()
    repo = request.args.get("repo")
    branch = request.args.get("branch")
    dropdowns = get_dropdowns(dml, repo, branch, None)
    return render_template("indexes.html", dropdowns=dropdowns)

@app.route("/kill-indexes", methods=["POST"])
def kill_idx():
    dml = Dml()
    repo = request.args.get("repo")
    branch = request.args.get("branch")
    body = request.form.getlist("del-idx", type=str)
    for idx in body:
        dml("index", "delete", idx)
    idxs = dml("index", "list")
    for idx in idxs:
        idx["dag_link"] = url_for("main", repo=repo, branch=branch, dag_id=idx["dag"])
    return jsonify({"deleted": len(body), "indexes": idxs})


def run():
    parser = ArgumentParser()
    parser.add_argument("-p", "--port", type=int, default=5000)
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    args = parser.parse_args()
    logger.setLevel(logging.DEBUG)
    app.run(debug=args.debug, port=args.port)

if __name__ == "__main__":
    app.run(debug=True, port=5000)

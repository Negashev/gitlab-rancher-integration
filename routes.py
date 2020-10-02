import os
import yaml
import base64
import jsonpatch
from flask import current_app as app, request, jsonify
from models import db, Workload

IGNORE_NAMESPACE = os.getenv("IGNORE_NAMESPACE", "default,gitlab-managed-apps,gri,cattle-prometheus,cattle-system,ingress-nginx,kube-node-lease,kube-public,kube-system,security-scan,istio-system,knative-serving,knative-eventing,longhorn-system").split(",")
ADD_IGNORE_NAMESPACE = os.getenv("ADD_IGNORE_NAMESPACE", "")

IGNORE_NAMESPACE = IGNORE_NAMESPACE + ',' + ADD_IGNORE_NAMESPACE

@app.route('/healthz', methods=['GET'])
def healthz():
    return jsonify({"response": "OK"})

@app.route('/autostop/workloads', methods=['POST'])
def workload_records():
    request_info = request.get_json()
    ownerReferences = request_info['request']["object"]['metadata']["ownerReferences"]
    # ignored Namespaces
    if request_info['request']["namespace"] in IGNORE_NAMESPACE:
        return admission_response(True, "Workload in ignore namespaces")
    for i in ownerReferences:
        if i['kind'] in ['StatefulSet', 'ReplicaSet']:
            name = i['name']
            if i['kind'] =='ReplicaSet':
                name = i['name'].rpartition('-')[0]
            workload = Workload(
                workload=name,
                workload_type=i['kind'],
                namespace=request_info['request']["namespace"],
            )
            db.session.add(workload)  # Adds new Workload record to database
            try:
                db.session.commit()  # Commits all changes
            except:
                db.session.rollback()
            return admission_response(True, "Workload append to autostop queue")
        elif i['kind'] == 'DaemonSet':
            return admission_response(False, "DaemonSet not allowed for you on this cluster")
        else:
            return admission_response(True, "Nothing happend for autostop")


def admission_response(allowed, message):
    return jsonify({"response": {"allowed": allowed, "status": {"message": message}}})


@app.route('/mutate/workloads', methods=['POST'])
def deployment_webhook_mutate():
    request_info = request.get_json()
    if request_info['request']["namespace"] in IGNORE_NAMESPACE:
        return admission_response(True, "Workload in ignore namespaces")
    print(yaml.dump(request_info, allow_unicode=True, default_flow_style=False))
    return admission_response_patch(True, "Adding allow label", json_patch = jsonpatch.JsonPatch([{"op": "add", "path": "/metadata/labels/allow", "value": "yes"}]))



def admission_response_patch(allowed, message, json_patch):
    base64_patch = base64.b64encode(json_patch.to_string().encode("utf-8")).decode("utf-8")
    return jsonify({"response": {"allowed": allowed,
                                 "status": {"message": message},
                                 "patchType": "JSONPatch",
                                 "patch": base64_patch}})
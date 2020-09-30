import os
import yaml
from flask import current_app as app, request, jsonify
from models import db, Workload

IGNORE_NAMESPACE = os.getenv("IGNORE_NAMESPACE", "default,gitlab-managed-apps,gri,cattle-prometheus,cattle-system,ingress-nginx,kube-node-lease,kube-public,kube-system,security-scan,istio-system").split(",")

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
                print(i)
                name = i['name'].rpartition('-')[0]
                print(name)
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
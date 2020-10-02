import os
import re
import yaml
import base64
import copy
import jsonpatch
from flask import current_app as app, request, jsonify
from models import db, Workload

IGNORE_NAMESPACE = os.getenv("IGNORE_NAMESPACE", "default,gitlab-managed-apps,gri,cattle-prometheus,cattle-system,ingress-nginx,kube-node-lease,kube-public,kube-system,security-scan,istio-system,knative-serving,knative-eventing,longhorn-system").split(",")
ADD_IGNORE_NAMESPACE = os.getenv("ADD_IGNORE_NAMESPACE", "").split(",")

DEFAULT_CPU = os.getenv("DEFAULT_CPU", "50m")
DEFAULT_MEMORY = os.getenv("DEFAULT_MEMORY", "128Mi")

IGNORE_NAMESPACE = IGNORE_NAMESPACE + ADD_IGNORE_NAMESPACE

projects_regexp = re.compile(r"-([0-9]{1,})-[\s\S-]{1,24}$")

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


def resources_mutation(container):
    mutate = False
    try:
        requests =  container['resources']['requests']
    except KeyError:
        mutate = True
        container['resources']['requests'] = {}
    try:
        cpu =  container['resources']['requests']['cpu']
    except KeyError:
        mutate = True
        container['resources']['requests']['cpu'] = DEFAULT_CPU
    try:
        memory =  container['resources']['requests']['memory']
    except KeyError:
        mutate = True
        container['resources']['requests']['memory'] = DEFAULT_MEMORY
    return container, mutate


@app.route('/mutate/workloads', methods=['POST'])
def deployment_webhook_mutate():
    request_info = request.get_json()
    if request_info['request']["namespace"] in IGNORE_NAMESPACE:
        return admission_response(True, "Workload in ignore namespaces")

    mutate = False

    # apply resources mutation to containers
    spec = request.json["request"]["object"]
    modified_spec = copy.deepcopy(spec)
    for i in range(len(modified_spec["spec"]['template']['spec']['containers'])):
        container = modified_spec["spec"]['template']['spec']['containers'][i]
        modified_spec["spec"]['template']['spec']['containers'][i], mutate = resources_mutation(container)

    # apply resources mutation to initContainers which may not exist
    try:
        for i in range(len(modified_spec["spec"]['template']['spec']['initContainers'])):
            container = modified_spec["spec"]['template']['spec']['initContainers'][i]

            modified_spec["spec"]['template']['spec']['initContainers'][i], mutate = resources_mutation(container)
    except KeyError:
        pass

    if mutate:
        patch = jsonpatch.JsonPatch.from_diff(spec, modified_spec)
        return admission_response_patch(True, "Adding resources for containers", json_patch = patch)
    else:
        return admission_response(True, "Workload is not mutate")



def admission_response_patch(allowed, message, json_patch):
    base64_patch = base64.b64encode(json_patch.to_string().encode("utf-8")).decode("utf-8")
    return jsonify({"response": {"allowed": allowed,
                                 "status": {"message": message},
                                 "patchType": "JSONPatch",
                                 "patch": base64_patch}})



@app.route('/mutate/namespaces', methods=['POST'])
def namespaces_webhook_mutate():
    request_info = request.get_json()
    if request_info['request']["namespace"] in IGNORE_NAMESPACE:
        return admission_response(True, "namespace is ignore")
    print('mutate', request_info['request']["namespace"])
    spec = request.json["request"]["object"]
    modified_spec = copy.deepcopy(spec)
    if 'field.cattle.io/projectId' not in modified_spec['metadata']['annotations']:
        this_regexp = projects_regexp
        if 'labels' in modified_spec['metadata'] and 'app.gitlab.com/env' in modified_spec['metadata']['labels']:
            this_regexp = re.compile(r"-([0-9]{1,})-(ENV)$".replace('ENV', modified_spec['metadata']['labels']['app.gitlab.com/env']))
        result_project = this_regexp.search(request_info['request']["namespace"])
        print(result_project)
    return admission_response(True, "Workload is not mutate")
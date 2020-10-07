import os
import re
import yaml
import base64
import copy
import jsonpatch
import time
import gitlab
import rancher
from flask import current_app as app, request, jsonify
from models import db, Workload

IGNORE_NAMESPACE = os.getenv("IGNORE_NAMESPACE", "default,gitlab-managed-apps,gri,cattle-prometheus,cattle-system,ingress-nginx,kube-node-lease,kube-public,kube-system,security-scan,istio-system,knative-serving,knative-eventing,longhorn-system").split(",")
ADD_IGNORE_NAMESPACE = os.getenv("ADD_IGNORE_NAMESPACE", "").split(",")
IGNORE_NAMESPACE = IGNORE_NAMESPACE + ADD_IGNORE_NAMESPACE

DEFAULT_CPU = os.getenv("DEFAULT_CPU", "50m")
DEFAULT_MEMORY = os.getenv("DEFAULT_MEMORY", "128Mi")

RANCHER_PREFIX_PROJECT_NAME = os.getenv('RANCHER_PREFIX_PROJECT_NAME', 'Project')

GL = gitlab.Gitlab(
    os.getenv('GITLAB_URL', 'https://gitlab.company.com'),
    private_token=os.getenv('GITLAB_TOKEN', 'GITLAB_TOKEN')
)

projects_regexp = re.compile(r"-([0-9]{1,})-[\s\S-]{1,24}$")

RANCHER_ACCESS_KEY = os.getenv('RANCHER_ACCESS_KEY', 'RANCHER_ACCESS_KEY')
RANCHER_SECRET_KEY = os.getenv('RANCHER_SECRET_KEY', 'RANCHER_SECRET_KEY')
RANCHER_URL = os.getenv('RANCHER_URL', 'https://rancher.company.com/v3')
RANCHER_SSL_VERIFY = bool(int(os.getenv('RANCHER_SSL_VERIFY', '1')))
RANCHER_CLUSTER_ID = os.getenv('RANCHER_CLUSTER_ID', 'c-xxxxx')
RANCHER_DEFAULT_PROJECT_ID = os.getenv('RANCHER_DEFAULT_PROJECT_ID', 'p-yyyyy')
RANCHER_PROJECT_PSP = os.getenv('RANCHER_PROJECT_PSP', None)

rancher_client = rancher.Client(
    url=RANCHER_URL, 
    access_key=RANCHER_ACCESS_KEY, 
    secret_key=RANCHER_SECRET_KEY, 
    verify=RANCHER_SSL_VERIFY
)

@app.route('/healthz', methods=['GET'])
def healthz():
    return jsonify({"response": "OK"})

@app.route('/autostop/workloads', methods=['POST'])
def workload_records():
    request_info = request.get_json()
    # ignored Namespaces
    if request_info['request']["namespace"] in IGNORE_NAMESPACE:
        return admission_response(True, "Workload in ignore namespaces")
    try:
        ownerReferences = request_info['request']["object"]['metadata']["ownerReferences"]
    except:
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


def resources_mutation(container):
    mutate = False
    try:
        _ = container['resources']['requests']
    except KeyError:
        mutate = True
        container['resources']['requests'] = {}
    try:
        _ = container['resources']['requests']['cpu']
    except KeyError:
        mutate = True
        container['resources']['requests']['cpu'] = DEFAULT_CPU
    try:
        _ = container['resources']['requests']['memory']
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
    try:
        for i in range(len(modified_spec["spec"]['template']['spec']['containers'])):
            container = modified_spec["spec"]['template']['spec']['containers'][i]
            modified_spec["spec"]['template']['spec']['containers'][i], mutate = resources_mutation(container)
    except KeyError as e:
        print('skip', e, request_info['request']["namespace"])

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


def find_or_create_rancher_project(project_name):
    global rancher_client
    # find project
    for i in rancher_client.list_project(name=project_name, clusterId=RANCHER_CLUSTER_ID):
        return i
    # or create project
    project = rancher_client.create_project(name=project_name, clusterId=RANCHER_CLUSTER_ID)
    if RANCHER_PROJECT_PSP is not None:
        time.sleep(2)
        project.setpodsecuritypolicytemplate(podSecurityPolicyTemplateId=RANCHER_PROJECT_PSP)
    return project

def get_rancher_project_from_ns_name(this_regexp, namespace):
    result_project = this_regexp.search(namespace)
    if result_project:
        project_id = int(result_project.group(1))
        project = GL.projects.get(project_id)
        project_name = f"{RANCHER_PREFIX_PROJECT_NAME} {project.path_with_namespace} ({project_id})"
        rancher_project_object = find_or_create_rancher_project(project_name)
        rancher_project_id = rancher_project_object['id']
    else:
        rancher_project_id = RANCHER_DEFAULT_PROJECT_ID
    print(rancher_project_id)
    return rancher_project_id

def get_regexp_with_gitlab_metadata(metadata):
    this_regexp = projects_regexp
    if 'labels' in metadata and 'app.gitlab.com/env' in metadata['labels']:
        # better regexp for get gitalb project id from namespace name
        this_regexp = re.compile(r"-([0-9]{1,})-(ENV)$".replace('ENV',metadata['labels']['app.gitlab.com/env']))
    return this_regexp

@app.route('/mutate/namespaces', methods=['POST'])
def namespaces_webhook_mutate():
    request_info = request.get_json()
    if request_info['request']["name"] in IGNORE_NAMESPACE:
        return admission_response(True, "namespace is ignore")
    print('mutate', request_info['request']["name"])
    spec = request.json["request"]["object"]
    modified_spec = copy.deepcopy(spec)
    this_regexp = projects_regexp
    # check that annotations exists
    print("check that annotations exists")
    if 'annotations' not in modified_spec['metadata'] or 'annotations' in modified_spec['metadata'] and 'field.cattle.io/projectId' not in modified_spec['metadata']['annotations']:
        # try find gitlab keys for sync
        print("try find gitlab keys for sync")
        this_regexp = get_regexp_with_gitlab_metadata(modified_spec['metadata'])
        rancher_project_id = get_rancher_project_from_ns_name(this_regexp, request_info['request']["name"])
        # if annotations not exist
        if 'annotations' not in modified_spec['metadata']:
            modified_spec['metadata']['annotations'] = {}
        # set rancher project
        modified_spec['metadata']['annotations']['field.cattle.io/projectId'] = rancher_project_id
        # bind namespace to rancher project (help for delete all NS in Rancher projects)
        modified_spec['metadata']['annotations']['field.cattle.io/creatorId'] = 'gitlab-rancher-integration'
        patch = jsonpatch.JsonPatch.from_diff(spec, modified_spec)
        return admission_response_patch(True, f"Namespace move to project {rancher_project_id}", json_patch = patch)
    return admission_response(True, "Namespace is not mutate")
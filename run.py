from gevent import monkey
monkey.patch_all()

import yaml
from flask import Flask, request, jsonify

admission_controller = Flask(__name__)

@admission_controller.route('/autostop/workloads', methods=['POST'])
def deployment_webhook():
    request_info = request.get_json()
    print(yaml.dump(request_info, allow_unicode=True, default_flow_style=False))
    return admission_response(True, "Workload append to autostop queue")

def admission_response(allowed, message):
    return jsonify({"response": {"allowed": allowed, "status": {"message": message}}})

if __name__ == '__main__':
    admission_controller.run(host='0.0.0.0', port=443, ssl_context=("/etc/webhook/certs/server.crt", "/etc/webhook/certs/server.key"))
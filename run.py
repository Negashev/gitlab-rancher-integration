from gevent import monkey
monkey.patch_all()

from __init__ import create_app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=443, ssl_context=("/etc/webhook/certs/server.crt", "/etc/webhook/certs/server.key"))
import os
import dramatiq
from kubernetes import client, config
from __init__ import create_app
from models import db, Workload

brokerService = os.getenv("DRAMATIQ_BROKER")
config.load_incluster_config()

apps_v1 = client.AppsV1Api()

app = create_app()


if brokerService.startswith('redis'):
    from dramatiq.brokers.redis import RedisBroker
    redis_broker = RedisBroker(url=brokerService)
    dramatiq.set_broker(redis_broker)
else:
    from dramatiq.brokers.rabbitmq import RabbitmqBroker
    rabbitmq_broker = RabbitmqBroker(url=brokerService)
    dramatiq.set_broker(rabbitmq_broker)


@dramatiq.actor
def stop_workload(id, workload, workload_type, namespace):
    if workload_type == 'ReplicaSet':
        resp = apps_v1.list_namespaced_deployment(namespace=namespace)
        for i in resp.items:
            if i.metadata.name == workload:
                i.spec.replicas = 0        
                apps_v1.patch_namespaced_deployment(
                    name=workload,
                    namespace=namespace,
                    body=i)
    elif workload_type == 'StatefulSet':
        resp = apps_v1.list_namespaced_stateful_set(namespace=namespace)
        for i in resp.items:
            if i.metadata.name == workload:
                i.spec.replicas = 0        
                apps_v1.patch_namespaced_stateful_set(
                    name=workload,
                    namespace=namespace,
                    body=i)
    with app.app_context():
        deleted_objects = Workload.__table__.delete().where(Workload.id==id)
        db.session.execute(deleted_objects)
        db.session.commit()
from datetime import datetime, timedelta
from __init__ import create_app
from models import db, Workload
from tasks import stop_workload

app = create_app()

with app.app_context():
    data = db.session.query(Workload.id, Workload.workload, Workload.workload_type, Workload.namespace).filter(Workload.created < datetime.utcnow() - timedelta(hours=1)).all()
    for workload in data:
        stop_workload.send(workload.id, workload.workload, workload.workload_type, workload.namespace)
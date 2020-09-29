"""Data models."""
from datetime import datetime

from __init__ import db


class Workload(db.Model):
    """Data model for workloads."""

    __tablename__ = 'workloads'
    
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    workload = db.Column(
        db.String(253), #https://unofficial-kubernetes.readthedocs.io/en/latest/concepts/overview/working-with-objects/names/#:~:text=Names%20are%20used%20to%20refer,resources%20have%20more%20specific%20restrictions.
        index=True,
        nullable=False
    )
    workload_type = db.Column(
        db.String(253),
        index=True,
        nullable=False
    )
    namespace = db.Column(
        db.String(253), #https://unofficial-kubernetes.readthedocs.io/en/latest/concepts/overview/working-with-objects/names/#:~:text=By%20convention%2C%20the%20names%20of,precise%20syntax%20rules%20for%20names.
        index=True,
        nullable=False
    )
    created = db.Column(
        db.DateTime,
        index=True,
        nullable=False,
        default=datetime.utcnow
    )
    
    __table_args__ = (db.UniqueConstraint('workload', 'workload_type', 'namespace', name='workload_namespace'),
                        )
    

    def __repr__(self):
        return '<{} {}.{}>'.format(self.workload_type, self.workload, self.namespace)
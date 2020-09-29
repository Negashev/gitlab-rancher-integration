# gitlab rancher integration (gri)
---
This helm repo integrate gitlab group/users (AutoDevOps) with rancher projects/users (Kubernetes)

---

### installation

1. install postgresql (for store workloads for kill) and redis (for kill workloads in background)
2. generate server.key,server.crt (for secret gitlab-rancher-integration-webhook-certs) and caBundle (for .Values.caBundle)

    - clone repo
    - run alpine with mount repo `docker run -ti --rm -v ./gitlab-rancher-integration:/data -w /data alpine`
    - in alpine install `apk add --update bash openssl gettext`
    - bash gen_certs.sh
    - add `certs/admission-webhook-key.pem` and `certs/admission-webhook-crt.pem` to kubernetes secret `gitlab-rancher-integration-webhook-certs` (.Values.caCertsSecret)
    - copy `CA_BUNDLE` to .Values.caBundle
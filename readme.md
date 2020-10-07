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
3. deploy helm with values

    ```
    caBundle=LS0t..................
    env.DRAMATIQ_BROKER=redis://queue:6379
    env.GITLAB_TOKEN=access token admin account
    env.GITLAB_URL=https://gitlab.company.com
    env.RANCHER_ACCESS_KEY=token-xxxxx
    env.RANCHER_CLUSTER_ID=c-xxxxx
    env.RANCHER_DEFAULT_PROJECT_ID=p-yyyyy
    env.RANCHER_PROJECT_PSP=restricted
    env.RANCHER_SECRET_KEY=LongLongToken
    env.RANCHER_SSL_VERIFY=0 # or 1
    env.RANCHER_URL=https://rancher.company.com/v3
    env.SQLALCHEMY_DATABASE_URI=postgresql://postgres:password@database/gri
    ```
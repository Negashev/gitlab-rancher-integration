# gitlab rancher integration (gri)

This helm repo integrate gitlab auth to rancher and gitlab group/users (AutoDevOps) with rancher projects/users (Kubernetes)

---

Thanks for [sandstorm](https://sandstorm.de/de/blog/post/making-rancher-2-and-gitlab-oauth-authentication-work-together.html)

---

## installation

1. deploy helm with values

    ```
    env:
      GITLAB_URL=https://gitlab.company.com
      RANCHER_URL=https://rancher.company.com
      GITLAB_HOOK_TOKEN: "" secret token for gitlab system hook
      RANCHER_CLUSTER_ID: c-m-xxxxxxxx # cluster id for integration gitlab groups and subgroups
      CATTLE_ACCESS_KEY: "" # access key for cluster from rancher
      CATTLE_SECRET_KEY: "" # secret key for cluster from rancher
    ingress:
    annotations:
        cert-manager.io/issuer: rancher
        kubernetes.io/tls-acme: 'true'
    enabled: true
    hosts:
        - host: gitlab-rancher-integration.company.com
    tls:
        - hosts:
            - gitlab-rancher-integration.company.com
        secretName: tls-gitlab-rancher-integration
    ```

2. create gitlab admin application https://gitlab.company.com/admin/applications

```
    name: Rancher
    Redirect URI: https://rancher.company.com/verify-auth
    Scopes: read_api
```

3. Go to Rancher Authentication Provider choose Github
```
    - select Github enterprise: https://gitlab-rancher-integration.company.com
    - paste Client ID and Client Secret from step 2
```
4. Go to giltab system hooks and create hook to `gitlab-rancher-integration.company.com/create-rancher-project-for-gitlab-group`
5. Install jspolicy from https://charts.loft.sh to k8s from `RANCHER_CLUSTER_ID` with env 
```
GITLAB_HOOK_TOKEN - secret token for gitlab system hook
GITLAB_RANCHER_INTEGRATION - http url gitlab rancher sever auth
GITLAB_HOST gitab host url
GITLAB_TOKEN gitlab token (read all groups)
```
6. Install crd JsPolicy from ./jspolicy (you can do it with fleet)

## troubleshooting

    Groups not show in new UI (rancher v2.6.5) use https://rancher.company.com/g to work with "Projects access" and "Assign Global Roles To Group"
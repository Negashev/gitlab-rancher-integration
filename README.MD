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


## troubleshooting

    Groups not show in new UI (rancher v2.6.5) use https://rancher.company.com/g to work with "Projects access" and "Assign Global Roles To Group"
# gitlab rancher integration (gri)

This helm repo integrate gitlab auth to rancher and gitlab group/users (AutoDevOps) with rancher projects/users (Kubernetes)

---

Thanks for [sandstorm](https://sandstorm.de/de/blog/post/making-rancher-2-and-gitlab-oauth-authentication-work-together.html)

---

### installation

1. deploy helm with values

    ```
    env.GITLAB_URL=https://gitlab.company.com
    env.RANCHER_URL=https://rancher.company.com
    ```
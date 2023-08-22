import requests
import json
gri = 'https://gitlab-rancher-integration.company'
xgt = 'X-Gitlab-Token'
gg = 'https://gitlab.company'
gt = 'PRIVATE-TOKEN'
r = requests.get(f'{gg}/api/v4/groups?per_page=100', headers={"PRIVATE-TOKEN": gt})
for i in r.json():
    print(i['id'])
    data = requests.post(f'{gri}/create-rancher-project-for-gitlab-group', 
                  headers={"X-Gitlab-Token": xgt},
                  data=json.dumps({
                      "event_name": "group_create",
                      "full_path": i["full_path"],
                      "group_id": i['id']
                        })
                )
    print(data.status_code)
    print(data.text)
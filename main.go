package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strconv"
	"strings"

	"github.com/drexedam/gravatar"
	"github.com/julienschmidt/httprouter"
	"github.com/tidwall/gjson"
	"github.com/urfave/negroni"
	"github.com/xanzy/go-gitlab"
)

func getEnv(key, fallback string) string {
    if value, ok := os.LookupEnv(key); ok {
        return value
    }
    return fallback
}

// /////////////// MAIN
func main() {
	router := httprouter.New()
	router.GET("/", home)
	router.GET("/login/oauth/authorize", oauthAuthorize)
	router.POST("/login/oauth/access_token", oauthAccessToken)
	router.GET("/api/v3/user", apiV3User)
	router.GET("/api/v3/user/:id", apiV3UserId)
	router.GET("/api/v3/teams/:id", apiV3TeamsId)
	router.GET("/api/v3/search/users", apiV3SearchUsers)
	router.POST("/create-rancher-project-for-gitlab-group", createRancherProjectForGitlabGroup)
	router.GET("/get-project-for-group", getProjectIdForGroup)
	n := negroni.Classic() // Includes some default middlewares
	n.UseHandler(router)
  
	fmt.Println("Listening to 0.0.0.0:8888")
	if err := http.ListenAndServe("0.0.0.0:8888", n); err != nil {
		panic(err)
	}
}

// /////////////// API
func home(w http.ResponseWriter, req *http.Request, ps httprouter.Params) {
	fmt.Fprintf(w, "ok\n")
}

type CreateRancherProject struct {
	Type        string `json:"type"`
	Name        string `json:"name"`
	Annotations struct {} `json:"annotations"`
	Labels struct {Group string `json:"group"`} `json:"labels"`
	ClusterID                     string `json:"clusterId"`
	ContainerDefaultResourceLimit struct {} `json:"containerDefaultResourceLimit"`
	ResourceQuota struct {} `json:"resourceQuota"`
	NamespaceDefaultResourceQuota struct {} `json:"namespaceDefaultResourceQuota"`
}

type AddGroupToProject struct {
	Type             string `json:"type"`
	RoleTemplateID   string `json:"roleTemplateId"`
	GroupPrincipalID string `json:"groupPrincipalId"`
	ProjectID        string `json:"projectId"`
}

func getProjectIdForGroup(w http.ResponseWriter, req *http.Request, ps httprouter.Params) {
	gitlabToken := req.Header.Get("X-Gitlab-Token")
	if gitlabToken != os.Getenv("GITLAB_HOOK_TOKEN") {
		fmt.Fprintf(w, "")
		return
	}
	groupId := req.Header.Get("Group-Id")

	request, err := http.NewRequest("GET", os.Getenv("RANCHER_URL") + "/v1/management.cattle.io.project/" + os.Getenv("RANCHER_CLUSTER_ID"), nil)
	if err != nil {
		panic(err)
	}

	request.SetBasicAuth(os.Getenv("CATTLE_ACCESS_KEY"), os.Getenv("CATTLE_SECRET_KEY"))
	request.Header.Set("Accept", "application/json")
	request.Header.Set("Content-Type", "application/json")

	response, err := http.DefaultClient.Do(request)
	if err != nil {
		panic(err)
	}
	defer response.Body.Close()
	
	// new request for add group to rancher project
	resBody, err := io.ReadAll(response.Body)
	if err != nil {
		panic(err)
	}
	stringResBody := string(resBody)
	rancherProjectId := gjson.Get(stringResBody, "data.#(metadata.labels.group==" + groupId + ").id").String()
	// set default project if group not found
	if rancherProjectId == "" {
		rancherProjectId = gjson.Get(stringResBody, "data.#(spec.displayName=='Default').id").String()
	}
	fmt.Fprintf(w, strings.Replace(rancherProjectId, "/", ":", 1))
}

func createRancherProjectForGitlabGroup(w http.ResponseWriter, req *http.Request, ps httprouter.Params) {
	gitlabToken := req.Header.Get("X-Gitlab-Token")
	if gitlabToken != os.Getenv("GITLAB_HOOK_TOKEN") {
		fmt.Fprintf(w, "ok\n")
		return
	}
	// load json
	reqBody, err := io.ReadAll(req.Body)
	if err != nil {
		panic(err)
	}
	stringReqBody := string(reqBody) 

	eventName := gjson.Get(stringReqBody, "event_name")

	if eventName.String() != "group_create" {
		fmt.Fprintf(w, "ok\n")
		return
	}

	rb := &CreateRancherProject{}
	rb.Name = gjson.Get(stringReqBody, "full_path").String()
	rb.ClusterID = os.Getenv("RANCHER_CLUSTER_ID")
	rb.Labels.Group = gjson.Get(stringReqBody, "group_id").String()
	jsonDataProject, err := json.Marshal(rb)
	if err != nil {
		panic(err)
	}
	request, err := http.NewRequest("POST", os.Getenv("RANCHER_URL") + "/v3/projects",  bytes.NewBuffer(jsonDataProject))
	if err != nil {
		panic(err)
	}

	request.SetBasicAuth(os.Getenv("CATTLE_ACCESS_KEY"), os.Getenv("CATTLE_SECRET_KEY"))
	request.Header.Set("Accept", "application/json")
	request.Header.Set("Content-Type", "application/json")

	response, err := http.DefaultClient.Do(request)
	if err != nil {
		panic(err)
	}
	defer response.Body.Close()
	
	// new request for add group to rancher project
	resBody, err := io.ReadAll(response.Body)
	if err != nil {
		panic(err)
	}
	stringResBody := string(resBody) 
	agp := &AddGroupToProject{}
	agp.ProjectID = gjson.Get(stringResBody, "id").String()
	agp.GroupPrincipalID = "github_team://" + gjson.Get(stringReqBody, "group_id").String()
	agp.RoleTemplateID = "read-only"
	agp.Type = "projectroletemplatebinding"
	jsonDataProject, err = json.Marshal(agp)
	if err != nil {
		panic(err)
	}
	request, err = http.NewRequest("POST", os.Getenv("RANCHER_URL") + "/v3/projectroletemplatebindings",  bytes.NewBuffer(jsonDataProject))
	if err != nil {
		panic(err)
	}
	request.SetBasicAuth(os.Getenv("CATTLE_ACCESS_KEY"), os.Getenv("CATTLE_SECRET_KEY"))
	request.Header.Set("Accept", "application/json")
	request.Header.Set("Content-Type", "application/json")

	response, err = http.DefaultClient.Do(request)
	if err != nil {
		panic(err)
	}
	defer response.Body.Close()

	fmt.Fprintf(w, "ok\n")
}

func oauthAuthorize(w http.ResponseWriter, req *http.Request, ps httprouter.Params) {
	v := req.URL.Query()
	v.Add("response_type", "code")
	v.Add("scope",getEnv("GITLAB_SCOPE", "read_api"))
	target := os.Getenv("GITLAB_URL") + "/oauth/authorize?" + v.Encode()
	http.Redirect(w, req, target, http.StatusTemporaryRedirect)
}

func oauthAccessToken(w http.ResponseWriter, req *http.Request, ps httprouter.Params) {
	v := req.URL.Query()
	v.Add("grant_type", "authorization_code")
	v.Add("redirect_uri", os.Getenv("RANCHER_URL")+"/verify-auth")

	target := os.Getenv("GITLAB_URL") + "/oauth/token?" + v.Encode()
	http.Redirect(w, req, target, http.StatusTemporaryRedirect)
}

func apiV3User(w http.ResponseWriter, req *http.Request, ps httprouter.Params) {
	gitlabClient := createGitlabClient(req)
	gitlabUser, _, err := gitlabClient.Users.CurrentUser()
	if err != nil {
		panic(err)
	}

	githubAccount := convertGitlabUserToAccount(gitlabUser)

	jsonStr, _ := json.Marshal(githubAccount)
	w.Write(jsonStr)
}

func apiV3UserId(w http.ResponseWriter, req *http.Request, ps httprouter.Params) {
	// Workaround to deal with routing library
	if ps.ByName("id") == "orgs" {
		apiV3UserOrgs(w, req, ps)
		return
	}
	if ps.ByName("id") == "teams" {
		apiV3UserTeams(w, req, ps)
		return
	}

	gitlabClient := createGitlabClient(req)

	id, _ := strconv.Atoi(ps.ByName("id"))
	// user
	gitlabUser, _, err := gitlabClient.Users.GetUser(id, gitlab.GetUsersOptions{WithCustomAttributes: gitlab.Bool(false)})
	if err != nil {
		panic(err)
	}

	githubAccount := convertGitlabUserToAccount(gitlabUser)
	jsonStr, _ := json.Marshal(githubAccount)
	w.Write(jsonStr)
}

func apiV3UserOrgs(w http.ResponseWriter, req *http.Request, ps httprouter.Params) {
	result := make([]string, 0)

	jsonStr, _ := json.Marshal(result)
	w.Write(jsonStr)
}

func apiV3UserTeams(w http.ResponseWriter, req *http.Request, ps httprouter.Params) {
	gitlabClient := createGitlabClient(req)
	allAvailable := false

	result := make([]Team, 0, 0)

	listGroupsOptions := &gitlab.ListGroupsOptions{
		ListOptions: gitlab.ListOptions{},
		// here, we only want to search for groups WHICH WE ARE MEMBER OF!!!
		AllAvailable: &allAvailable,
	}
	for {
		gitlabGroups, resp, err := gitlabClient.Groups.ListGroups(listGroupsOptions)
		if err != nil {
			panic(err)
		}

		for _, gitlabGroup := range gitlabGroups {
			team := convertGitlabGroupToTeam(gitlabGroup)
			result = append(result, *team)
		}

		// Exit the loop when we've seen all pages.
		if resp.CurrentPage >= resp.TotalPages {
			break
		}

		// Update the page number to get the next page.
		listGroupsOptions.ListOptions.Page = resp.NextPage

	}
	jsonStr, _ := json.Marshal(result)
	w.Write(jsonStr)
}

func apiV3TeamsId(w http.ResponseWriter, req *http.Request, ps httprouter.Params) {

	gitlabClient := createGitlabClient(req)

	id, _ := strconv.Atoi(ps.ByName("id"))

	gitlabGroup, _, err := gitlabClient.Groups.GetGroup(id, &gitlab.GetGroupOptions{ListOptions: gitlab.ListOptions{Page: 1, PerPage: 50}, WithCustomAttributes: gitlab.Bool(false), WithProjects: gitlab.Bool(false)})
	if err != nil {
		panic(err)
	}
	team := convertGitlabGroupToTeam(gitlabGroup)

	jsonStr, _ := json.Marshal(team)
	w.Write(jsonStr)
}

type searchResult struct {
	Items []*Account `json:"items"`
}

func apiV3SearchUsers(w http.ResponseWriter, req *http.Request, ps httprouter.Params) {
	query := req.URL.Query().Get("q")
	gitlabClient := createGitlabClient(req)

	searchResult := &searchResult{
		Items: make([]*Account, 0),
	}

	shouldSearchUsers := true
	shouldSearchOrgs := true
	if strings.Contains(query, "type:org") {
		shouldSearchUsers = false
		shouldSearchOrgs = true
		query = strings.ReplaceAll(query, "type:org", "")
	}

	if shouldSearchOrgs {
		allAvailable := true
		gitlabGroups, _, err := gitlabClient.Groups.ListGroups(&gitlab.ListGroupsOptions{
			Search: &query,
			// we want to find ALL groups (which are not fully private)
			AllAvailable: &allAvailable,
		})
		if err != nil {
			panic(err)
		}
		for _, gitlabGroup := range gitlabGroups {
			githubOrg := convertGitlabGroupToAccount(gitlabGroup)
			searchResult.Items = append(searchResult.Items, githubOrg)
		}
	}

	if shouldSearchUsers {
		gitlabUsers, _, err := gitlabClient.Users.ListUsers(&gitlab.ListUsersOptions{
			Search: &query,
		})
		if err != nil {
			panic(err)
		}
		for _, gitlabUser := range gitlabUsers {
			githubAccount := convertGitlabUserToAccount(gitlabUser)
			searchResult.Items = append(searchResult.Items, githubAccount)
		}
	}

	jsonStr, _ := json.Marshal(searchResult)
	w.Write(jsonStr)
}

///////////////// HELPERS

// https://docs.github.com/en/free-pro-team@latest/rest/reference/users#get-the-authenticated-user
// copied from https://github.com/rancher/rancher/blob/2506427ba7bd31edf12f7110b7fdb8b2defe8eb3/pkg/auth/providers/github/github_account.go#L12
type Account struct {
	ID        int    `json:"id,omitempty"`
	Login     string `json:"login,omitempty"`
	Name      string `json:"name,omitempty"`
	AvatarURL string `json:"avatar_url,omitempty"`
	HTMLURL   string `json:"html_url,omitempty"`
	// "Type" must be "user", "team", oder "org"
	Type string `json:"type,omitempty"`
}

// Team defines properties a team on github has
type Team struct {
	ID           int                    `json:"id,omitempty"`
	Organization map[string]interface{} `json:"organization,omitempty"`
	Name         string                 `json:"name,omitempty"`
	Slug         string                 `json:"slug,omitempty"`
}

func createGitlabClient(req *http.Request) *gitlab.Client {
	authorizationHeader := req.Header.Get("Authorization")
	t := strings.Split(authorizationHeader, " ")
	token := t[1]
	gitlabClient, err := gitlab.NewOAuthClient(token, gitlab.WithBaseURL(os.Getenv("GITLAB_URL")+"/api/v4"))
	if err != nil {
		panic(err)
	}
	return gitlabClient
}

func convertGitlabUserToAccount(gitlabUser *gitlab.User) *Account {
	AvatarURL := ""
	if gitlabUser.AvatarURL == "" {
		AvatarURL = gravatar.New(gitlabUser.Username).Default(gravatar.Retro).AvatarURL()
	} else {
		AvatarURL = gitlabUser.AvatarURL
	}
	return &Account{
		ID:        gitlabUser.ID,
		Login:     gitlabUser.Username,
		Name:      gitlabUser.Name,
		AvatarURL: AvatarURL,
		HTMLURL:   "",
		Type:      "user",
	}
}

func convertGitlabGroupToAccount(gitlabGroup *gitlab.Group) *Account {
	AvatarURL := ""
	if gitlabGroup.AvatarURL == "" {
		AvatarURL = gravatar.New(gitlabGroup.FullPath).Default(gravatar.Retro).AvatarURL()
	} else {
		AvatarURL = gitlabGroup.AvatarURL
	}
	return &Account{
		ID:        gitlabGroup.ID,
		Login:     gitlabGroup.Path,
		Name:      gitlabGroup.FullPath,
		AvatarURL: AvatarURL,
		HTMLURL:   "",
		Type:      "team",
	}
}

func convertGitlabGroupToTeam(gitlabGroup *gitlab.Group) *Team {
	org := make(map[string]interface{})
	org["login"] = gitlabGroup.FullPath
	if gitlabGroup.AvatarURL == "" {
		org["avatar_url"] = gravatar.New(gitlabGroup.FullPath).Default(gravatar.Retro).AvatarURL()
	} else {
		org["avatar_url"] = gitlabGroup.AvatarURL
	}

	return &Team{
		ID:           gitlabGroup.ID,
		Organization: org,
		Name:         gitlabGroup.FullPath,
		Slug:         gitlabGroup.Path,
	}
}

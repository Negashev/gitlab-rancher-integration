FROM golang:alpine

# Get the TLS CA certificates, they're not provided by busybox.
RUN apk --no-cache add ca-certificates && update-ca-certificates

# Copy the single source file to the app directory
WORKDIR /go/src/app
COPY . .

# Install depenancies
RUN go get -d

# Build the app
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-w -s" .

# Switch to a small base image
FROM scratch

ENV RANCHER_URL=https://rancher.company.com
ENV GITLAB_URL=https://gitlab.company.com
# Copy the binary over from the deploy container
COPY --from=0 /go/src/app/gitlab-rancher-integration /usr/bin/gitlab-rancher-integration

# Get the TLS CA certificates from the build container, they're not provided by busybox.

COPY --from=0 /etc/ssl/certs /etc/ssl/certs

ENTRYPOINT ["/usr/bin/gitlab-rancher-integration"]
#!/bin/bash

set -o errexit
set -o nounset
set -o pipefail

# fork https://github.com/giantswarm/grumpy/blob/instance_migration/gen_certs.sh
# CREATE THE PRIVATE KEY FOR OUR CUSTOM CA
openssl genrsa -out certs/ca.key 2048

# GENERATE A CA CERT WITH THE PRIVATE KEY
openssl req -new -x509 -key certs/ca.key -out certs/ca.crt -config certs/admission-webhook_config.txt

# CREATE THE PRIVATE KEY FOR OUR ADMINSSION WEBHOOK SERVER
openssl genrsa -out certs/admission-webhook-key.pem 2048

# CREATE A CSR FROM THE CONFIGURATION FILE AND OUR PRIVATE KEY
openssl req -new -key certs/admission-webhook-key.pem -subj "/CN=gri.gri.svc" -out admission-webhook.csr -config certs/admission-webhook_config.txt

# CREATE THE CERT SIGNING THE CSR WITH THE CA CREATED BEFORE
openssl x509 -req -in admission-webhook.csr -CA certs/ca.crt -CAkey certs/ca.key -CAcreateserial -out certs/admission-webhook-crt.pem

# export data
echo ---------------------------------------------------
echo Your data
echo ---------------------------------------------------
export CA_BUNDLE=$(cat certs/ca.crt | base64 | tr -d '\n')
echo CA_BUNDLE: ${CA_BUNDLE}
echo file key.pem: certs/admission-webhook-key.pem
echo file cert.pem: certs/admission-webhook-crt.pem
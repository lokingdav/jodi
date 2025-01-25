#!/bin/bash

cmd=$1
cmds=('configure' 'create' 'destroy')

case "$cmd" in
    configure)
        ./scripts/generate-ssh-keys.sh
        ./scripts/configure-aws-cli.sh
        terraform init
        ;;
    create)
        terraform apply -auto-approve
        ;;
    destroy)
        terraform destroy -auto-approve
        rm -rf hosts.yml
        ;;
    *)
        echo "Usage: $0 {${cmds[*]}}"
        exit 1
        ;;
esac
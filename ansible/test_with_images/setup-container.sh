#!/usr/bin/env bash
# https://dev.to/pencillr/test-ansible-playbooks-using-docker-ci0
# How this works:
# 1) Create a temp dir, create temp ssh rsa key
# 2) Build dockerfile, run the container (which runs ssh service), get the ip addr
# 3) Create an inventory file with the ip address, and the private rsa key
# 4) run your ansible playbook of choice
# 5) cleanup /tmp and the containers
set -euo pipefail

identifier="$(< /dev/urandom tr -dc 'a-z0-9' | fold -w 5 | head -n 1)" ||:
NAME="compute-node-sim-${identifier}"
base_dir="$(dirname "$(readlink -f "$0")")"

function cleanup() {
    container_id=$(docker inspect --format="{{.Id}}" "${NAME}" ||:)
    if [[ -n "${container_id}" ]]; then
        echo "Cleaning up container ${NAME}"
        docker rm --force "${container_id}"
    fi
    if [[ -n "${TEMP_DIR:-}" && -d "${TEMP_DIR:-}" ]]; then
        echo "Cleaning up tepdir ${TEMP_DIR}"
        rm -rf "${TEMP_DIR}"
    fi
}

function setup_tempdir() {
    TEMP_DIR=$(mktemp --directory "/tmp/${NAME}".XXXXXXXX)
    export TEMP_DIR
}

function create_temporary_ssh_id() {
    ssh-keygen -b 2048 -t rsa -C "${USER}@email.com" -f "${TEMP_DIR}/id_rsa" -N ""
    chmod 600 "${TEMP_DIR}/id_rsa"
    chmod 644 "${TEMP_DIR}/id_rsa.pub"
}

function start_container() {
    docker build --tag "compute-node-sim" \
        --build-arg USER \
        --file "${base_dir}/Dockerfile" \
        "${TEMP_DIR}"
    docker run -d -P --name "${NAME}" "compute-node-sim"
    CONTAINER_ADDR=$(docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "${NAME}")
    export CONTAINER_ADDR
}

function setup_test_inventory() {
    TEMP_INVENTORY_FILE="${TEMP_DIR}/hosts"

    cat > "${TEMP_INVENTORY_FILE}" << EOL
[myhosts]
${CONTAINER_ADDR}:22
[myhosts:vars]
ansible_ssh_private_key_file=${TEMP_DIR}/id_rsa
ansible_ssh_common_args="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
EOL
    export TEMP_INVENTORY_FILE
}

function run_ansible_playbook() {
    ANSIBLE_CONFIG="${base_dir}/ansible.cfg"
    # More 'v in -v (verbose) adds more verbosity'
    echo "Running test-playbook.yaml playbook"
    ansible-playbook -i "${TEMP_INVENTORY_FILE}" -v "${base_dir}/test-playbook.yaml"
    echo "Running machine-setup.yml playbook"
    ansible-playbook -i "${TEMP_INVENTORY_FILE}" -vv "${base_dir}/machine-setup.yaml"
}

setup_tempdir
trap cleanup EXIT
trap cleanup ERR
create_temporary_ssh_id
start_container
setup_test_inventory
run_ansible_playbook

#!/usr/bin/env bash
export WORKON_HOME='/home/fumao-zhou/.localhost/virtualenvs'
source /home/fumao-zhou/.local/bin/virtualenvwrapper.sh
while true
do
    cd /home/fumao-zhou/PycharmProject/select-proxy/
    workon script
    python3 buy_ocean_sun.py
#    workon ansible
#    cd ansible_task/playbook_apollo_ocean_sun
#    ansible-playbook deploy_squid.yml
#    ansible-playbook deploy_squid.yml --limit @./deploy_squid.retry
#    ansible-playbook deploy_squid.yml --limit @./deploy_squid.retry
done

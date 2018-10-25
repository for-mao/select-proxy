#! /bin/bash
export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh

workon script
nohup python3 ss_process_delete_vps.py >> logs/delete_vps.out &
nohup python3 ss_process_stop_container.py >> logs/stop_container.out &
nohup python3 ss_process_test_hoovers.py >> logs/test_hoovers.out &
nohup python3 ss_process_start_container.py >> logs/start_container.out &
nohup python3 ss_process_create_compose.py >> logs/create_compose.out &
nohup python3 ss_process_collection_vps.py >> logs/collection_vps.out &
nohup python3 ss_process_buy_vps.py >> logs/buy_vps.out &

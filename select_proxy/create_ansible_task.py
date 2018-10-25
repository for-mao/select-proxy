from os import path
from shutil import copytree
from shutil import rmtree
from typing import List

from jinja2 import Template


def create_ansible_task(task_name: str,
                        ips: List,
                        cent_os_ips: List = '',
                        task_template: str='squid') -> str:
    base_dir = path.abspath(path.join(__file__, path.pardir, path.pardir))
    # copy folder playbook-squid-template -> playbook-task_name
    folder = path.join(base_dir,
                       'ansible_task', 'playbook_{}'.format(task_name))
    if path.exists(folder):
        rmtree(folder)
    copytree(path.join(base_dir, 'docs',
                       'playbook-{}-template'.format(task_template)), folder)
    # create hosts
    with open(path.join(base_dir, 'docs', 'hosts_template')) as t:
        t_hosts = Template(t.read())
    with open(path.join(folder, 'hosts'), 'w') as f:
        f.write(t_hosts.render(task_name=task_name, ips=ips,
                               cent_os_ips=cent_os_ips))

    # create playbook
    with open(path.join(base_dir, 'docs',
                        'playbook_{}_template'.format(task_template))) as t:
        t_playbook = Template(t.read())
    with open(path.join(
            folder, 'deploy_{}.yml'.format(task_template)
    ), 'w') as f:
        f.write(t_playbook.render(task_name=task_name))

    return path.join(folder, 'deploy_squid.yml')


if __name__ == '__main__':
    pass

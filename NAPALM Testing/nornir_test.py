from nornir import InitNornir
from nornir.core import configuration
#from nornir.core.inventory import Group
from nornir_utils.plugins.tasks.files import write_file
import pathlib
from nornir_netmiko.tasks import netmiko_send_config
from nornir_utils.plugins.functions import print_result
from nornir_napalm.plugins.tasks import napalm_get,napalm_configure
from nornir_utils.plugins.tasks.data import load_yaml
from nornir_jinja2.plugins.tasks import template_file
import yaml,re

nr = InitNornir(config_file="config.yaml")
backupDir = "Config Backup"
globalVar = yaml.safe_load(pathlib.Path('./Global Vars/global.yaml').read_text())

def init_napalm(task):
    task.run(task=netmiko_send_config,config_file="init_napalm.txt")

def pull_info(task):
    #task.run(task=napalm_get, getters=['get_facts','get_interfaces'])
    task.run(task=napalm_get, getters=['get_interfaces_ip'])
    

def backup_config(task):
    config_result = task.run(task=napalm_get, getters=['config'])
    running_config = config_result.result['config']['running']
    pathlib.Path(backupDir).mkdir(exist_ok=True)
    task.run(task=write_file,content=running_config,filename=f'{backupDir}/{task.host}.txt')

def replace_config(task):
    task.run(task=napalm_configure,filename=f'{backupDir}/{task.host}.txt', replace=True)

etx = chr(3)

def replace_ntp_napalm(task):

    config = task.run(task=napalm_get, getters=['config'])
    showrun = config.result["config"]["running"]
    pattern = re.compile("^ntp server ([^!]+)", flags=re.I | re.M)
    ntp_template = task.run(name="Building Jinja Config",task=template_file,template="ntp.j2",path="./templates",globalVar=globalVar)
    template_to_load = ntp_template.result
    newconfig = re.sub(pattern, template_to_load, showrun)
    final_config= newconfig.replace("^C",etx)
    task.run(task=napalm_configure,configuration=final_config,replace=True)

def add_ntp_netmiko(task):
    ntp_template = task.run(name="Building Jinja Config",task=template_file,template="ntp.j2",path="./templates",globalVar=globalVar)
    ntp_config = ntp_template.result
    config_list = ntp_config.splitlines()
    config_list.append("do wr")
    task.run(task=netmiko_send_config,config_commands=config_list)

def add_logging_netmiko(task):
    logging_template = task.run(name="Building Jinja Config",task=template_file,template="logging.j2",path="./templates",globalVar=globalVar)
    logging_config = logging_template.result
    config_list = logging_config.splitlines()
    config_list.append("do wr")
    task.run(task=netmiko_send_config,config_commands=config_list)

def get_mgt_int(task):
    res = task.run(task=napalm_get, getters=["get_interfaces_ip"])
    interfaces = res.result['get_interfaces_ip']
    hostIP = task.host.hostname
    for intf,ipv4addr in interfaces.items():
        tmp = ipv4addr['ipv4']
        for ipaddr, prefix in tmp.items():
            if ipaddr == hostIP:
                mgmtInft = intf
    print(mgmtInft)
    return mgmtInft


results = nr.run(task=get_mgt_int)
#results = nr.run(task=backup_config)
print_result(results)



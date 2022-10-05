#!/usr/bin/python3

# Modules
from unittest import result
import netmiko
import signal
import json
import sys
import newvlanfunctions

# Remove error messages
signal.signal(signal.SIGPIPE, signal.SIG_DFL) # IOError: Broken pipe
signal.signal(signal.SIGINT, signal.SIG_DFL) #Keyboardinterrupt: Ctrl-C

# Exceptions
netmiko_exceptions = (netmiko.exceptions.NetmikoAuthenticationException)

# Dictionary
with open('vlan-dict.json') as dev_file:
    devices = json.load(dev_file)

# Functions
def check_vlan_existance(USERNAME, PASSWORD, VLAN, forti):
    # Kontrollerar om VLAN finns i switch och gate. Skriptet stängs ned om VLANet finns.
    for device in devices:
        try:
            print('~'*79)
            print('Checking if VLAN exists in cisco-catalyst.')
            connection = netmiko.ConnectHandler(**device['cisco-catalyst'], username=USERNAME, password=PASSWORD)
            vlancore = (connection.send_command(f'show vlan id {VLAN}'))
            print(vlancore)
            connection.disconnect()
            print('~'*79)
            print('Checking if VLAN exists in fortinet-fortigate.')
            connection = netmiko.ConnectHandler(**device['fortinet-fortigate'], fast_cli='true', username=USERNAME, password=PASSWORD)
            vlangate = (connection.send_config_set(forti, cmd_verify=False)[70:-19])
            print(vlangate)
            connection.disconnect()
        except netmiko_exceptions as e:
            print ('Login failed to', device, e)
    if "not found in current VLAN database" not in vlancore or "entry is not found in table" not in vlangate:
        print('~'*79)
        print('VLAN already exists in at least 1 device, terminating script.')
        sys.exit()    

def create_vlan_cisco(USERNAME, PASSWORD, change_number, cvlan, VLAN, addtrunk1, secondarytrunk, addtrunk2):
    # Creates VLAN in Catalyst and adds it to trunk towards firewall.
    # Netmiko expects a value which is not returned, fixed with cmd_verify=False in connection.send_config_set 
    for device in devices:
        try:
            print('~'*79)
            print('Creating VLAN in cisco-catalyst.')
            connection = netmiko.ConnectHandler(**device['cisco-catalyst'], username=USERNAME, password=PASSWORD)
            (connection.send_command(f'send log Changed issued by script cisco-configure-all with change-number: {change_number}'))
            connection.send_config_set(cvlan, cmd_verify=False)
            print(connection.send_command(f'show vlan id {VLAN}'))
            connection.send_config_set(addtrunk1, cmd_verify=False)
            print('~'*79)
            print('Verifying VLAN is added to interface Port-channel 1')
            print(connection.send_command('show interface Port-channel1 trunk'))
            print('~'*79)
            if secondarytrunk == True:
                connection.send_config_set(addtrunk2, cmd_verify=False)
                print('Verifying VLAN is added to interface GigabitEthernet 0/3')
                print(connection.send_command('show interfaces gigabitEthernet 0/3 trunk'))
                print('~'*79)
            connection.disconnect()
        except netmiko_exceptions as e:
            print ('Login failed to', device, e)

def create_vlan_fortigate(USERNAME, PASSWORD, fortigatevlan, fortivlan2, enable_dns_fortigate):
    # Creates VLAN in fortinet-fortigate
    for device in devices:
        try:
            print('~'*79)
            print('Creating VLAN in fortinet-fortigate and enabling DNS on interface.')
            connection = netmiko.ConnectHandler(**device['fortinet-fortigate'], username=USERNAME, password=PASSWORD, fast_cli='True')
            connection.send_config_set(fortigatevlan, cmd_verify=False)
            print(connection.send_config_set(fortivlan2)[:-17]) 
            connection.send_config_set(enable_dns_fortigate, cmd_verify=False)
            connection.disconnect()
        except netmiko_exceptions as e:
            print ('Login failed to', device, e)

def template_vlan_fortigate(VLAN, fortigateip, fortigatesubnet, VLANNAME):
     return(f"""
config vdom
edit root
config system interface
edit VLAN-{VLAN}
set vdom "root"
set ip {fortigateip} {fortigatesubnet}
set allowaccess ping
set description "{VLANNAME}"
set device-identification enable
set role lan
set interface "lag1"
set vlanid "{VLAN}"
next
end
""")

def add_vlan_trunk_gi03(VLAN): 
    return(f"""
interface GigabitEthernet0/3
switchport trunk allowed vlan add {VLAN}
""")

def add_vlan_trunk_po1(VLAN): 
    return (f"""
interface Port-channel1
switchport trunk allowed vlan add {VLAN}
""")

def create_vlan(VLAN, VLANNAME): 
    return (f"""
vlan {VLAN}
name {VLANNAME}
""")

def forti(fortivlan):
    return (f"""
config vdom
edit root
show system interface VLAN-{fortivlan}
""")

def forti2(fortivlan2):
    return (f"""
show system interface VLAN-{fortivlan2}
""")

def enable_dns_interface(vlan):
    return (f"""
config system dns-server
edit edit VLAN-{vlan}
set dnsfilter-profile DNS-PROFIL
next
end
""")

def main():
    #Login
    USERNAME, PASSWORD = newvlanfunctions.get_credentials()
    VLAN = input('Input VLAN number: ')
    VLANNAME = input('VLAN NAME: ')
    secondarytrunk =  newvlanfunctions.yes_or_no('Add VLAN towards secondarytrunk? y/n')
    change_number = input('Add change number: ')

    fortivlan = forti(VLAN)
    fortivlan2 = forti2(VLAN)
    check_vlan_existance(USERNAME, PASSWORD, VLAN, fortivlan)
    cvlan = create_vlan(VLAN, VLANNAME)
    addtrunk1 = add_vlan_trunk_po1(VLAN)
    addtrunk2 = add_vlan_trunk_gi03(VLAN)
    create_vlan_cisco(USERNAME, PASSWORD, change_number, cvlan, VLAN, addtrunk1, secondarytrunk, addtrunk2)
    
    testipv4 = input('Enter IP-address to be used by Fortigate interface: ')
    rentestipv4 = newvlanfunctions.ipv4(testipv4)
    if rentestipv4['Valid'] == True: 
        fortigateip = rentestipv4['Output']
    while rentestipv4['Valid'] == False:
        print('Wrong format, try again')
        testipv4 = input('IP-address: ')
        rentestipv4 = newvlanfunctions.ipv4(testipv4)
        fortigateip = rentestipv4['Output']
    print('IP-address to be used by Fortigate: ', fortigateip)

    print('~'*79)
    testsubnet = input('Subnet mask for network (255.255.x.x): ')
    rentsubnet = newvlanfunctions.ipv4(testsubnet)
    if rentsubnet['Valid'] == True: 
        fortigatesubnet = rentsubnet['Output']
    while rentsubnet['Valid'] == False:
        print('Wrong format, try again')
        testsubnet = input('Subnet mask for network (255.255.x.x): ')
        rentsubnet = newvlanfunctions.ipv4(testsubnet)
        fortigatesubnet = rentsubnet['Output']
    print('Subnet mask to be used by Fortigate: ', fortigatesubnet)

    fortigatevlan = template_vlan_fortigate(VLAN, fortigateip, fortigatesubnet, VLANNAME)
    enable_dns_fortigate = enable_dns_interface(VLAN)
    create_vlan_fortigate(USERNAME, PASSWORD, fortigatevlan, fortivlan2, enable_dns_fortigate)

    print('~'*79)
    print('Script complete.')
if __name__ == '__main__':
    main()

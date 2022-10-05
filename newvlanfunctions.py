# Funktion för loginsnurra med getpass...och lite annat

# Moduler
from getpass import getpass
import ipaddress

# Login
def get_credentials():
	username = input('Username: ')
	password = None
	while not password:
		password = getpass()
		password_verify = getpass('Retype your password: ')
		if password != password_verify:
			print('Not identical, try again.')
			password = None
	return username, password

def yes_or_no(question):
    reply = str(input(question+' (y/n): ')).lower().strip()
    if reply[0] == 'y':
        return True
    if reply[0] == 'n':
        return False
    else:
        return yes_or_no("Uhhhh... please enter ")

def ipv4(ip):
    result = {
        'Valid' : False,
        'Output' : ''
    }

    ip = ip.replace(',', '.')
    octets = ip.split(".")
    if len(octets) != 4:
        return result
    for octet in octets:
        if not isinstance(int(octet), int):
            return result
        if int(octet) < 0 or int(octet) > 255:
            return result
    result['Valid'] = True
    result['Output'] = ip
    return result
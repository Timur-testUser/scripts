import paramiko

def get_ip_from_mac(cisco_devices, mac_address, username, password):
    ip_addresses = []
    for host in cisco_devices:
        try:
            # Устанавливаем SSH-соединение
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=host,
                username=username,
                password=password
            )

            # Выполняем команду на устройстве
            command = f"show ip arp | include {mac_address}"
            stdin, stdout, stderr = ssh.exec_command(command)
            output = stdout.read().decode()

            # Ищем IP-адрес в выводе
            for line in output.splitlines():
                if mac_address in line:
                    parts = line.split()
                    ip_addresses.append(parts[1])  

            ssh.close()
        except Exception as e:
            print(f"Ошибка при подключении к {host}: {e}")

    return ip_addresses

def main():
    # IP-адреса устройств Cisco
    cisco_devices = ['10.51.0.27', '10.51.0.31', '10.51.0.65', '10.51.0.71']
    
    # Логин и пароль
    username = ''
    password = ''

    mac_address = input("Введите MAC-адрес: ")
    ip_addresses = get_ip_from_mac(cisco_devices, mac_address, username, password)

    print("\nНайденные IP-адреса:")
    for ip in ip_addresses:
        print(ip)

if __name__ == "__main__":
    main()

import sys
import os
import logging
import time
import subprocess
from datetime import date
import zipfile
import paramiko
from scp import SCPClient

# Конфигурация
CONFIG = {
    'today': f"{date.today():%d-%m-%Y}",
    'ssh_user': "lanors",
    'ssh_password': "2530orsK",
    'tftp_server': "192.168.156.2",
    'script_path': os.path.dirname(os.path.abspath(sys.argv[0])),
    'switch_list_file': "switch.txt",
    'log_dir': "logs",
    'archive_dir': 'D:\\switch-backup\\archives\\',
    'current_configs_dir': 'D:\\switch-backup\\currents',
    'log_level': logging.INFO,
    'timeout': 30,
    'ssh_port': 22
}

# Настройка логирования
def setup_logging():
    log_file = os.path.join(CONFIG['script_path'], CONFIG['log_dir'], f"{CONFIG['today']}-swlog.txt")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    logger = logging.getLogger("SwitchBackup")
    logger.setLevel(CONFIG['log_level'])
    
    formatter = logging.Formatter("%(asctime)s — %(name)s — %(levelname)s — %(message)s")
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logging()

def ping(host):
    try:
        process = subprocess.Popen(["ping", "-n", "1", host], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE,
                                  creationflags=subprocess.CREATE_NO_WINDOW)
        streamdata = process.communicate()[0]
        return b'Reply from ' + host.encode() not in streamdata
    except Exception as e:
        logger.error(f"Ping error for {host}: {str(e)}")
        return 1

def get_switch_type(host):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=host, 
                   port=CONFIG['ssh_port'], 
                   username=CONFIG['ssh_user'], 
                   password=CONFIG['ssh_password'],
                   timeout=CONFIG['timeout'])
        
        stdin, stdout, stderr = ssh.exec_command("show version", timeout=10)
        output = stdout.read().decode().lower()
        
        if 'dgs' in output:
            return 4  # D-Link DGS
        elif 'hp' in output or 'hpe' in output or 'aruba' in output:
            return 5  # HP/Aruba
        elif 'snr' in output:
            return 0  # SNR
        elif 'd-link' in output:
            return 1  # D-Link
        
        return "unknown"
        
    except Exception as e:
        logger.error(f"SSH error detecting switch type for {host}: {str(e)}")
        return "failed"
    finally:
        try:
            ssh.close()
        except:
            pass

def backup_switch_config(host, switch_type):
    ssh = None
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=host, 
                   port=CONFIG['ssh_port'], 
                   username=CONFIG['ssh_user'], 
                   password=CONFIG['ssh_password'],
                   timeout=CONFIG['timeout'])
        
        # Для передачи файлов по SCP
        scp = SCPClient(ssh.get_transport())
        
        if switch_type == 0:  # SNR
            # Сохраняем конфиг локально на коммутаторе
            stdin, stdout, stderr = ssh.exec_command("wr", timeout=CONFIG['timeout'])
            output = stdout.read().decode()
            
            # Копируем конфиг через SCP
            local_path = f"{host}.cfg"
            scp.get("running-config", local_path=local_path)
            
        elif switch_type == 1:  # D-Link
            stdin, stdout, stderr = ssh.exec_command("save", timeout=CONFIG['timeout'])
            output = stdout.read().decode()
            
            # Для D-Link может потребоваться дополнительная обработка
            local_path = f"{host}.cfg"
            scp.get("config.cfg", local_path=local_path)
            
        elif switch_type == 4:  # DGS-1210
            stdin, stdout, stderr = ssh.exec_command("save", timeout=CONFIG['timeout'])
            output = stdout.read().decode()
            
            local_path = f"{host}.cfg"
            scp.get("config.cfg", local_path=local_path)
            
        elif switch_type == 5:  # HP
            stdin, stdout, stderr = ssh.exec_command("save force", timeout=CONFIG['timeout'])
            output = stdout.read().decode()
            
            local_path = f"{host}.cfg"
            scp.get("config.cfg", local_path=local_path)
            
        else:
            logger.error(f"Unsupported switch type {switch_type} for {host}")
            return False
        
        # Перемещаем файл в папку с текущими конфигурациями
        if os.path.exists(local_path):
            os.rename(local_path, os.path.join(CONFIG['current_configs_dir'], os.path.basename(local_path)))
        
        logger.info(f"Successfully backed up {host} (type: {switch_type})")
        return True
        
    except Exception as e:
        logger.error(f"SSH error backing up {host}: {str(e)}")
        return False
    finally:
        try:
            scp.close()
        except:
            pass
        try:
            ssh.close()
        except:
            pass

def archive_current_configs():
    try:
        os.makedirs(CONFIG['archive_dir'], exist_ok=True)
        os.makedirs(CONFIG['current_configs_dir'], exist_ok=True)
        
        config_files = os.listdir(CONFIG['current_configs_dir'])
        if not config_files:
            logger.info("No config files to archive")
            return
            
        archive_path = os.path.join(CONFIG['archive_dir'], f"{CONFIG['today']}-sw.zip")
        
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file in config_files:
                try:
                    file_path = os.path.join(CONFIG['current_configs_dir'], file)
                    zf.write(file_path, arcname=file)
                except Exception as e:
                    logger.error(f"Error adding {file} to archive: {str(e)}")
        
        logger.info(f"Created archive {archive_path}")
        
        # Очистка директории с текущими конфигурациями
        for file in config_files:
            try:
                os.remove(os.path.join(CONFIG['current_configs_dir'], file))
            except Exception as e:
                logger.error(f"Error deleting {file}: {str(e)}")
                
    except Exception as e:
        logger.error(f"Archive error: {str(e)}")

def main():
    logger.info("Starting switch backup process")
    
    # Архивируем текущие конфигурации
    archive_current_configs()
    
    # Читаем список коммутаторов
    switch_list_path = os.path.join(CONFIG['script_path'], CONFIG['switch_list_file'])
    try:
        with open(switch_list_path, 'r') as f:
            switches = [line.strip() for line in f if line.strip()]
    except Exception as e:
        logger.error(f"Error reading switch list: {str(e)}")
        return
        
    if not switches:
        logger.warning("No switches found in the list")
        return
        
    # Обрабатываем каждый коммутатор
    for switch_ip in switches:
        try:
            logger.info(f"Processing switch: {switch_ip}")
            
            if ping(switch_ip):
                logger.warning(f"{switch_ip} is down!")
                continue
                
            logger.info(f"{switch_ip} is up")
            switch_type = get_switch_type(switch_ip)
            
            if switch_type == "failed":
                logger.error(f"Failed to determine type for {switch_ip}")
                continue
                
            logger.info(f"{switch_ip} type: {switch_type}")
            backup_switch_config(switch_ip, switch_type)
            
        except Exception as e:
            logger.error(f"Error processing {switch_ip}: {str(e)}")
            
    logger.info("Backup process completed")

if __name__ == "__main__":
    main()

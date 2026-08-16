import ftplib
import re

FTP_HOST = "87.228.52.244"
FTP_USER = "motor_ftp"
FTP_PASS = "{Y8T^C$c}hD4QSz["

try:
    ftp = ftplib.FTP()
    ftp.connect(FTP_HOST, 21, timeout=10)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.set_pasv(True)
    
    # MODX config
    with open("motor_config.php", "wb") as f:
        try:
            ftp.retrbinary("RETR home/motor_ftp/public_html/core/config/config.inc.php", f.write)
            print("Downloaded core/config/config.inc.php")
        except Exception as e:
            print("Could not download config:", e)
            
    ftp.quit()
    
    try:
        with open("motor_config.php", "r", encoding="utf-8") as f:
            content = f.read()
            db_info = re.findall(r"\$(?:database|database_user|database_password|database_server|dbase|database_dsn|table_prefix).*?=.*?;", content)
            print("Database configuration found:")
            for line in db_info:
                print(line.strip())
    except Exception as e:
        print("File read error", e)
        
except Exception as e:
    print(f"FTP Error: {e}")

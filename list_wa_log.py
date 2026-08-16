import ftplib
import io
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("==================================================================")
print("  🔍 СПИСОК ФАЙЛОВ В WA-LOG НА FTP")
print("==================================================================")

ftp = ftplib.FTP("regiontehsnab.ru", timeout=10)
ftp.login("regiontehsnab_ftp", "UidI@?AB2s3TO4FQ")
ftp.set_pasv(True)

items = []
ftp.dir("/public_html/wa-log", items.append)
print("Contents of /public_html/wa-log:")
for it in items:
    print("  ", it)

# Read error.log if present
try:
    buf = io.BytesIO()
    ftp.retrbinary("RETR /public_html/wa-log/error.log", buf.write)
    print("\n--- error.log (last 20 lines) ---")
    txt = buf.getvalue().decode('utf-8', errors='ignore')
    for line in txt.split('\n')[-20:]:
        print(line)
except Exception as e:
    print("Err reading error.log:", e)

ftp.quit()

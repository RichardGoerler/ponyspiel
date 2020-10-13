import requests
import time
from pathlib import Path
import subprocess
import sys

if __name__ == '__main__':
    print('Updating...')
    time.sleep(2)     # Waiting because this is called from the exe that this is replacing. Making sure the exe has closed before it is replaced
    remote_exe_url = 'https://github.com/RichardGoerler/ponyspiel/raw/master/dist/pony_gui.exe'
    r = requests.get(remote_exe_url, allow_redirects=True)
    p = Path('./pony_gui.exe')
    p.unlink()
    time.sleep(2)
    with open(p, 'wb') as f:
        f.write(r.content)
    time.sleep(2)
    print('Restarting')
    # _ = subprocess.run([], executable='./pony_gui.exe')
    _ = subprocess.run([str(p.absolute())])

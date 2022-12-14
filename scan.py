import urllib
from urllib import request
import time
import ipaddress
import threading
import requests
import json
from waiting import wait
from alive_progress import alive_bar
from bs4 import BeautifulSoup
import queue
import ssl
import config
import warnings
import platform
import subprocess
import socket
from fp.fp import FreeProxy
from requests.adapters import HTTPAdapter
import platform

warnings.filterwarnings("ignore")

tasks = queue.Queue()

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class FrontingAdapter(HTTPAdapter):
    """"Transport adapter" that allows us to use SSLv3."""

    def __init__(self, fronted_domain=None, **kwargs):
        self.fronted_domain = fronted_domain
        super(FrontingAdapter, self).__init__(**kwargs)

    def send(self, request, **kwargs):
        connection_pool_kwargs = self.poolmanager.connection_pool_kw
        if self.fronted_domain:
            connection_pool_kwargs["assert_hostname"] = self.fronted_domain
        elif "assert_hostname" in connection_pool_kwargs:
            connection_pool_kwargs.pop("assert_hostname", None)
        return super(FrontingAdapter, self).send(request, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        server_hostname = None
        if self.fronted_domain:
            server_hostname = self.fronted_domain
        super(FrontingAdapter, self).init_poolmanager(server_hostname=server_hostname, *args, **kwargs)

def ping(host):
    """
    Returns True if host (str) responds to a ping request.
    Remember that a host may not respond to a ping (ICMP) request even if the host name is valid.
    """

    # Option for the number of packets as a function of
    param = '-n' if platform.system().lower()=='windows' else '-c'

    # Building the command. Ex: "ping -c 1 google.com"
    command = ['ping', param, '1', host]

    return subprocess.call(command, stdout=subprocess.DEVNULL) == 0

def FileHandler():
    global tasks
    while True:
        if not tasks.empty():
            task = str(tasks.get()).split(';')
            with open(str(task[1]), 'a+') as out:
                out.write(str(task[0]) + '\n')
                out.close()
            tasks.task_done()
        else:
            time.sleep(2)

def update_script(code):
    if code == 1:
        file_list = requests.get('https://raw.githubusercontent.com/SuspectWorkers/cf_scan_443/main/file_list.txt', verify=False).text
        for a in file_list.split('\n'):
            rep = requests.get('https://raw.githubusercontent.com/SuspectWorkers/cf_scan_443/main/'+str(a), verify=False)
            open(str(a), "wb").write(rep.content)
    else:
        file_list = open("file_list.txt", "r")
        for a in file_list.readlines():
            if not os.path.exists(a):
                rep = requests.get('https://raw.githubusercontent.com/SuspectWorkers/cf_scan_443/main/'+str(a), verify=False)
                open(str(a), "wb").write(rep.content)

def cdn_check(domain, hostname, path, right_answer):
    try:
        r = requests.get('http://'+str(domain)+str(path), allow_redirects=False, verify=False, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36', 'Host': str(hostname)})
        if str(right_answer) in r.text:
            print(f'{bcolors.OKGREEN} [+] ' + '80 HTTP ' + str(domain) + f'{bcolors.ENDC}')
    except:
        pass
    try:
        r = requests.get('https://'+str(domain)+str(path), verify=False, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36', 'Host': str(hostname)})
        if str(right_answer) in r.text:
            print(f'{bcolors.OKGREEN} [+] ' + '443 TLS ' + str(domain) + f'{bcolors.ENDC}')
    except:
        pass
    global counts
    counts-=1

def ping_check(ip):
    global tasks, counts
    try:
        result = ping(ip)
        if result:
            print("Working ip found!")
            tasks.put(str(ip) + ';ip_pinger.txt')
    except:
        pass
    counts-=1

def cf_443_check(ip):
    global tasks
    try:
        r = requests.get("https://" + str(ip) + "/", timeout=int(config.timeout_cf_443), headers={'Host':'sni.cloudflaressl.com'}, verify=False, allow_redirects=False)
        if '403' in r.text:
            print("Working host found!")
            tasks.put(str(ip) + ';cflare_output_443.txt')
        elif r.headers['Location'] == 'https://www.cloudflare.com/':
            print("Working host found!")
            tasks.put(str(ip) + ';cflare_output_443.txt')
    #except requests.exceptions.ConnectTimeout:
        #pass
    #except requests.exceptions.SSLError:
        #print("Working host found!")
        #tasks.put(str(ip) + ';cflare_output_443.txt')
    except:
        pass
    global counts
    counts-=1

def cf_80_check(ip):
    global tasks
    try:
        r = requests.get("http://" + str(ip) + "/", timeout=int(config.timeout_cf_80), verify=False).text
        if "Direct IP access not allowed" in r:
            print("Working host found!")
            tasks.put(str(ip) + ';cflare_output_80.txt')
    except:
        pass
    global counts
    counts-=1

def fastly_443_check(ip):
    global tasks
    try:
        r = requests.get("https://" + str(ip) + "/", timeout=int(config.timeout_fastly_443), verify=False).text
        if "Fastly error" in r:
            print("Working host found!")
            tasks.put(str(ip) + ';fastly_output_443.txt')
    except:
        pass
    global counts
    counts-=1

def fastly_80_check(ip):
    global tasks
    try:
        r = requests.get("http://" + str(ip) + "/", timeout=int(config.timeout_fastly_80), verify=False).text
        if "Fastly error" in r:
            print("Working host found!")
            tasks.put(str(ip) + ';fastly_output_80.txt')
    except:
        pass
    global counts
    counts-=1

def azure_443_check(ip):
    global tasks
    try:
        r = requests.get("https://" + str(ip) + "/", timeout=int(config.timeout_azure_443), verify=False).text
        if "<h2>" in r:
            print("Working host found!")
            tasks.put(str(ip) + ';azure_output_443.txt')
    except:
        pass
    global counts
    counts-=1

def azure_80_check(ip):
    global tasks
    try:
        r = requests.get("http://" + str(ip) + "/", timeout=int(config.timeout_azure_80), verify=False).text
        if "<h2>" in r:
            print("Working host found!")
            tasks.put(str(ip) + ';azure_output_80.txt')
    except:
        pass
    global counts
    counts-=1

def cfront_443_check(ip):
    global tasks
    try:
        r = requests.get("https://" + str(ip) + "/", timeout=int(config.timeout_cfront_443), verify=False).text
        if "cloudfront" in r:
            print("Working host found!")
            tasks.put(str(ip) + ';cfront_output_443.txt')
    except:
        pass
    global counts
    counts-=1

def cfront_80_check(ip):
    global tasks
    try:
        r = requests.get("http://" + str(ip) + "/", timeout=int(config.timeout_cfront_80), verify=False).text
        if "cloudfront" in r:
            print("Working host found!")
            tasks.put(str(ip) + ';cfront_output_80.txt')
    except:
        pass
    global counts
    counts-=1

def arvan_443_check(ip, work_host):
    global tasks
    try:
        #socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #socket_client.settimeout(5)
        #socket_client.connect((str(ip), 443))
        #socket_client = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2).wrap_socket(
        #    socket_client, server_hostname=str(work_host), do_handshake_on_connect=True
        #)
        s = requests.Session()
        s.mount('https://', FrontingAdapter(fronted_domain=str(work_host)))
        r = s.get("https://" + str(ip) + "/", headers={"Host": "live.faranesh.com"}, timeout=int(config.timeout_arvan_443), verify=False, allow_redirects=False).text
        if r.headers['Server'] == 'ArvanCloud':
            print("Working host found!")
            tasks.put(str(ip) + ';arvan_output_443.txt')
    except:
        pass
    global counts
    counts-=1

def arvan_80_check(ip):
    global tasks
    try:
        r = requests.get("http://" + str(ip) + "/", timeout=int(config.timeout_arvan_80), verify=False, allow_redirects=False).text
        if "html" in r:
            print("Working host found!")
            tasks.put(str(ip) + ';arvan_output_80.txt')
    except:
        pass
    global counts
    counts-=1

def gcore_443_check(ip):
    global tasks
    try:
        r = requests.get("https://" + str(ip) + "/", timeout=int(config.timeout_gcore_443), headers={'Host':'cdn-cm.wgcdn.co'}, verify=False, allow_redirects=False).text
        if "html" in r:
            print("Working host found!")
            tasks.put(str(ip) + ';gcore_output_443.txt')
    except:
        pass
    global counts
    counts-=1

def gcore_80_check(ip):
    global tasks
    try:
        r = requests.get("http://" + str(ip) + "/", timeout=int(config.timeout_gcore_80), headers={'Host':'cdn-cm.wgcdn.co'}, verify=False, allow_redirects=False).text
        if "html" in r:
            print("Working host found!")
            tasks.put(str(ip) + ';gcore_output_80.txt')
    except:
        pass
    global counts
    counts-=1

def verizon_443_check(ip):
    global tasks
    try:
        r = requests.get("https://" + str(ip) + "/", timeout=int(config.timeout_verizon_443), verify=False).text
        if "title" in r:
            print("Working host found!")
            tasks.put(str(ip) + ';verizon_output_443.txt')
    except:
        pass
    global counts
    counts-=1

def verizon_80_check(ip):
    global tasks
    try:
        r = requests.get("http://" + str(ip) + "/", timeout=int(config.timeout_verizon_80), verify=False).text
        if "title" in r:
            print("Working host found!")
            tasks.put(str(ip) + ';verizon_output_80.txt')
    except:
        pass
    global counts
    counts-=1

def volterra_443_check(ip):
    global tasks
    try:
        r = requests.get("https://" + str(ip) + "/", timeout=int(config.timeout_volterra_443), headers={'Host':'volterra.hetzner.bfgdrm.buzz'}, verify=False).text
        if "title" in r:
            print("Working host found!")
            tasks.put(str(ip) + ';volterra_output_443.txt')
    except:
        pass
    global counts
    counts-=1

def volterra_80_check(ip):
    global tasks
    try:
        r = requests.get("http://" + str(ip) + "/", timeout=int(config.timeout_volterra_80), headers={'Host':'volterra.hetzner.bfgdrm.buzz'}, verify=False).text
        if "title" in r:
            print("Working host found!")
            tasks.put(str(ip) + ';volterra_output_80.txt')
    except:
        pass
    global counts
    counts-=1

def translator1_check(ip):
    global counts
    global possible_domain_count
    global parsed_domain_count
    req = urllib.request.Request('https://reverseiplookupapi.com/show_domains_with_ip.php?ip=%s' % ip, headers={'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})
    the_page = urllib.request.urlopen(req).read().decode('utf-8')
    for a in json.loads(the_page):
        possible_domain_count+=a['number_of_domains']
        for domain in a['domains']:
            parsed_domain_count+=1
            tasks.put(str(domain) + ';ip_translator.txt')
    counts-=1

def translator2_check(ip):
    global counts
    global possible_domain_count
    global parsed_domain_count
    req = urllib.request.Request('https://reverseiplookupapi.com/show_domains_with_ip.php?ip=%s' % ip, headers={'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})
    the_page = urllib.request.urlopen(req).read().decode('utf-8')
    for a in json.loads(the_page):
        possible_domain_count+=a['number_of_domains']
        for domain in a['domains']:
            parsed_domain_count+=1
            tasks.put(str(domain) + ';ip_translator.txt')
    counts-=1

def hackertarget_check(ip):
    global counts
    global possible_domain_count
    global parsed_domain_count
    possible_domain_count=0
    keks = True
    while keks:
        try:
            proxy = FreeProxy().get()
            proxies = {
                'http': str(proxy),
                'https': str(proxy),
            }
            req = requests.get('https://api.hackertarget.com/reverseiplookup/?q=%s' % ip, proxies=proxies, headers={'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})
            the_page = req.text
            if "No DNS" in the_page:
                keks = False
            elif "API" in the_page:
                raise Exception("API Count Exceeded")
            else:
                for a in the_page.splitlines():
                    parsed_domain_count+=1
                    tasks.put(str(domain) + ';hackertarget.txt')
            keks = False
        except:
            pass
    counts-=1

def free_threads():
    global threads
    global counts
    if counts <= threads:
        return True
    return False
    
def zero_threads():
    global counts
    if counts == 0:
        return True
    return False
    
def option1():
    option = ''
    global threads, counts
    print("How much threads do you want?")
    print("Recommended: 100")
    threads = int(input())
    counts = 0
    print('1. Port 443')
    print('2. Port 80')
    try:
        option = int(input('Enter your choice: '))
    except:
        print('Wrong input. Please enter a number ...')
    if option == 1:
        ips = []
        with open('cflare_ranges.txt', 'r') as read:
            lines = read.readlines()
            read.close()
        count = 0
        for line in lines:
            ips.append([str(ip) for ip in ipaddress.IPv4Network(line[:len(line) - 1])])
            count+=1

        with alive_bar(sum(len(l) for l in ips)) as bar:
            for x in range(count):
                for y in range(len(ips[x])):
                    if counts<=threads:
                        threading.Thread(target=cf_443_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
                    else:
                        wait(lambda: free_threads(), timeout_seconds=120, waiting_for="free threads")
                        threading.Thread(target=cf_443_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
            wait(lambda: zero_threads(), timeout_seconds=120, waiting_for="zero threads")
            print('Work Finished!')
    elif option == 2:
        ips = []
        with open('cflare_ranges.txt', 'r') as read:
            lines = read.readlines()
            read.close()
        count = 0
        for line in lines:
            ips.append([str(ip) for ip in ipaddress.IPv4Network(line[:len(line) - 1])])
            count+=1
        
        with alive_bar(sum(len(l) for l in ips)) as bar:
            for x in range(count):
                for y in range(len(ips[x])):
                    if counts<=threads:
                        threading.Thread(target=cf_80_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
                    else:
                        wait(lambda: free_threads(), timeout_seconds=120, waiting_for="free threads")
                        threading.Thread(target=cf_80_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
            wait(lambda: zero_threads(), timeout_seconds=120, waiting_for="zero threads")
            print('Work Finished!')
    else:
        print('Invalid option. Please enter a number between 1 and 2.')

def option2():
    print("How much threads do you want?")
    print("Recommended: 100")
    global threads, counts
    threads = int(input())
    counts = 0
    option = ''
    print('1. Port 443')
    print('2. Port 80')
    try:
        option = int(input('Enter your choice: '))
    except:
        print('Wrong input. Please enter a number ...')
    if option == 1:
        ips = []
        with open('fastly_ranges.txt', 'r') as read:
            lines = read.readlines()
            read.close()
        count = 0
        for line in lines:
            ips.append([str(ip) for ip in ipaddress.IPv4Network(line[:len(line) - 1])])
            count+=1

        with alive_bar(sum(len(l) for l in ips)) as bar:
            for x in range(count):
                for y in range(len(ips[x])):
                    if counts<=threads:
                        threading.Thread(target=fastly_443_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
                    else:
                        wait(lambda: free_threads(), timeout_seconds=120, waiting_for="free threads")
                        threading.Thread(target=fastly_443_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
            wait(lambda: zero_threads(), timeout_seconds=120, waiting_for="zero threads")
            print('Work Finished!')
    elif option == 2:
        ips = []
        with open('fastly_ranges.txt', 'r') as read:
            lines = read.readlines()
            read.close()
        count = 0
        for line in lines:
            ips.append([str(ip) for ip in ipaddress.IPv4Network(line[:len(line) - 1])])
            count+=1

        with alive_bar(sum(len(l) for l in ips)) as bar:
            for x in range(count):
                for y in range(len(ips[x])):
                    if counts<=threads:
                        threading.Thread(target=fastly_80_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
                    else:
                        wait(lambda: free_threads(), timeout_seconds=120, waiting_for="free threads")
                        threading.Thread(target=fastly_80_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
            wait(lambda: zero_threads(), timeout_seconds=120, waiting_for="zero threads")
            print('Work Finished!')
    else:
        print('Invalid option. Please enter a number between 1 and 2.')

def option2_1():
    print("How much threads do you want?")
    print("Recommended: 100")
    global threads, counts
    threads = int(input())
    counts = 0
    option = ''
    print('1. Port 443')
    print('2. Port 80')
    try:
        option = int(input('Enter your choice: '))
    except:
        print('Wrong input. Please enter a number ...')
    if option == 1:
        ips = []
        with open('azure_ranges.txt', 'r') as read:
            lines = read.readlines()
            read.close()
        count = 0
        for line in lines:
            ips.append([str(ip) for ip in ipaddress.IPv4Network(line[:len(line) - 1])])
            count+=1

        with alive_bar(sum(len(l) for l in ips)) as bar:
            for x in range(count):
                for y in range(len(ips[x])):
                    if counts<=threads:
                        threading.Thread(target=azure_443_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
                    else:
                        wait(lambda: free_threads(), timeout_seconds=120, waiting_for="free threads")
                        threading.Thread(target=azure_443_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
            wait(lambda: zero_threads(), timeout_seconds=120, waiting_for="zero threads")
            print('Work Finished!')
    elif option == 2:
        ips = []
        with open('azure_ranges.txt', 'r') as read:
            lines = read.readlines()
            read.close()
        count = 0
        for line in lines:
            ips.append([str(ip) for ip in ipaddress.IPv4Network(line[:len(line) - 1])])
            count+=1

        with alive_bar(sum(len(l) for l in ips)) as bar:
            for x in range(count):
                for y in range(len(ips[x])):
                    if counts<=threads:
                        threading.Thread(target=azure_80_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
                    else:
                        wait(lambda: free_threads(), timeout_seconds=120, waiting_for="free threads")
                        threading.Thread(target=azure_80_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
            wait(lambda: zero_threads(), timeout_seconds=120, waiting_for="zero threads")
            print('Work Finished!')
    else:
        print('Invalid option. Please enter a number between 1 and 2.')

def option2_2():
    print("How much threads do you want?")
    print("Recommended: 100")
    global threads, counts
    threads = int(input())
    counts = 0
    option = ''
    print('1. Port 443')
    print('2. Port 80')
    try:
        option = int(input('Enter your choice: '))
    except:
        print('Wrong input. Please enter a number ...')
    if option == 1:
        ips = []
        with open('cfront_ranges.txt', 'r') as read:
            lines = read.readlines()
            read.close()
        count = 0
        for line in lines:
            ips.append([str(ip) for ip in ipaddress.IPv4Network(line[:len(line) - 1])])
            count+=1

        with alive_bar(sum(len(l) for l in ips)) as bar:
            for x in range(count):
                for y in range(len(ips[x])):
                    if counts<=threads:
                        threading.Thread(target=cfront_443_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
                    else:
                        wait(lambda: free_threads(), timeout_seconds=120, waiting_for="free threads")
                        threading.Thread(target=cfront_443_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
            wait(lambda: zero_threads(), timeout_seconds=120, waiting_for="zero threads")
            print('Work Finished!')
    elif option == 2:
        ips = []
        with open('cfront_ranges.txt', 'r') as read:
            lines = read.readlines()
            read.close()
        count = 0
        for line in lines:
            ips.append([str(ip) for ip in ipaddress.IPv4Network(line[:len(line) - 1])])
            count+=1

        with alive_bar(sum(len(l) for l in ips)) as bar:
            for x in range(count):
                for y in range(len(ips[x])):
                    if counts<=threads:
                        threading.Thread(target=cfront_80_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
                    else:
                        wait(lambda: free_threads(), timeout_seconds=120, waiting_for="free threads")
                        threading.Thread(target=cfront_80_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
            wait(lambda: zero_threads(), timeout_seconds=120, waiting_for="zero threads")
            print('Work Finished!')
    else:
        print('Invalid option. Please enter a number between 1 and 2.')

def option2_3():
    print("How much threads do you want?")
    print("Recommended: 100")
    global threads, counts
    threads = int(input())
    counts = 0
    option = ''
    print('1. Port 443')
    print('2. Port 80')
    try:
        option = int(input('Enter your choice: '))
    except:
        print('Wrong input. Please enter a number ...')
    if option == 1:
        ips = []
        with open('gcore_ranges.txt', 'r') as read:
            lines = read.readlines()
            read.close()
        count = 0
        for line in lines:
            ips.append([str(ip) for ip in ipaddress.IPv4Network(line[:len(line) - 1])])
            count+=1

        with alive_bar(sum(len(l) for l in ips)) as bar:
            for x in range(count):
                for y in range(len(ips[x])):
                    if counts<=threads:
                        threading.Thread(target=gcore_443_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
                    else:
                        wait(lambda: free_threads(), timeout_seconds=120, waiting_for="free threads")
                        threading.Thread(target=gcore_443_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
            wait(lambda: zero_threads(), timeout_seconds=120, waiting_for="zero threads")
            print('Work Finished!')
    elif option == 2:
        ips = []
        with open('gcore_ranges.txt', 'r') as read:
            lines = read.readlines()
            read.close()
        count = 0
        for line in lines:
            ips.append([str(ip) for ip in ipaddress.IPv4Network(line[:len(line) - 1])])
            count+=1

        with alive_bar(sum(len(l) for l in ips)) as bar:
            for x in range(count):
                for y in range(len(ips[x])):
                    if counts<=threads:
                        threading.Thread(target=gcore_80_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
                    else:
                        wait(lambda: free_threads(), timeout_seconds=120, waiting_for="free threads")
                        threading.Thread(target=gcore_80_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
            wait(lambda: zero_threads(), timeout_seconds=120, waiting_for="zero threads")
            print('Work Finished!')
    else:
        print('Invalid option. Please enter a number between 1 and 2.')

def option2_4():
    print("How much threads do you want?")
    print("Recommended: 100")
    global threads, counts
    threads = int(input())
    counts = 0
    option = ''
    work_host = ''
    print('1. Port 443')
    print('2. Port 80')
    try:
        option = int(input('Enter your choice: '))
        if option == 1:
            work_host = str(input('Enter Working host for arvan: '))
    except:
        print('Wrong input. Please enter a number ...')
    if option == 1:
        ips = []
        with open('arvan_ranges.txt', 'r') as read:
            lines = read.readlines()
            read.close()
        count = 0
        for line in lines:
            ips.append([str(ip) for ip in ipaddress.IPv4Network(line[:len(line) - 1])])
            count+=1

        with alive_bar(sum(len(l) for l in ips)) as bar:
            for x in range(count):
                for y in range(len(ips[x])):
                    if counts<=threads:
                        threading.Thread(target=arvan_443_check, args=((str(ips[x][y])), work_host,)).start()
                        counts+=1
                        bar()
                    else:
                        wait(lambda: free_threads(), timeout_seconds=120, waiting_for="free threads")
                        threading.Thread(target=arvan_443_check, args=((str(ips[x][y])), work_host,)).start()
                        counts+=1
                        bar()
            wait(lambda: zero_threads(), timeout_seconds=120, waiting_for="zero threads")
            print('Work Finished!')
    elif option == 2:
        ips = []
        with open('arvan_ranges.txt', 'r') as read:
            lines = read.readlines()
            read.close()
        count = 0
        for line in lines:
            ips.append([str(ip) for ip in ipaddress.IPv4Network(line[:len(line) - 1])])
            count+=1

        with alive_bar(sum(len(l) for l in ips)) as bar:
            for x in range(count):
                for y in range(len(ips[x])):
                    if counts<=threads:
                        threading.Thread(target=arvan_80_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
                    else:
                        wait(lambda: free_threads(), timeout_seconds=120, waiting_for="free threads")
                        threading.Thread(target=arvan_80_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
            wait(lambda: zero_threads(), timeout_seconds=120, waiting_for="zero threads")
            print('Work Finished!')
    else:
        print('Invalid option. Please enter a number between 1 and 2.')

def option2_5():
    print("How much threads do you want?")
    print("Recommended: 100")
    global threads, counts
    threads = int(input())
    counts = 0
    option = ''
    print('1. Port 443')
    print('2. Port 80')
    try:
        option = int(input('Enter your choice: '))
    except:
        print('Wrong input. Please enter a number ...')
    if option == 1:
        ips = []
        with open('verizon_ranges.txt', 'r') as read:
            lines = read.readlines()
            read.close()
        count = 0
        for line in lines:
            ips.append([str(ip) for ip in ipaddress.IPv4Network(line[:len(line) - 1])])
            count+=1

        with alive_bar(sum(len(l) for l in ips)) as bar:
            for x in range(count):
                for y in range(len(ips[x])):
                    if counts<=threads:
                        threading.Thread(target=verizon_443_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
                    else:
                        wait(lambda: free_threads(), timeout_seconds=120, waiting_for="free threads")
                        threading.Thread(target=verizon_443_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
            wait(lambda: zero_threads(), timeout_seconds=120, waiting_for="zero threads")
            print('Work Finished!')
    elif option == 2:
        ips = []
        with open('verizon_ranges.txt', 'r') as read:
            lines = read.readlines()
            read.close()
        count = 0
        for line in lines:
            ips.append([str(ip) for ip in ipaddress.IPv4Network(line[:len(line) - 1])])
            count+=1

        with alive_bar(sum(len(l) for l in ips)) as bar:
            for x in range(count):
                for y in range(len(ips[x])):
                    if counts<=threads:
                        threading.Thread(target=verizon_80_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
                    else:
                        wait(lambda: free_threads(), timeout_seconds=120, waiting_for="free threads")
                        threading.Thread(target=verizon_80_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
            wait(lambda: zero_threads(), timeout_seconds=120, waiting_for="zero threads")
            print('Work Finished!')
    else:
        print('Invalid option. Please enter a number between 1 and 2.')

def option3():
    a = str(input("Enter filename with ip_list: "))
    ips = []
    with open(a, 'r') as read:
        lines = read.readlines()
        read.close()
    for line in lines:
        ips.append(line.rstrip())
    global tasks
    global threads
    global counts
    global possible_domain_count
    global parsed_domain_count
    option = ''
    print('1. [FREE][UltraSLOW]ReverseIpLookup*')
    print('    *Max 10 domains per ip')
    print('2. [WIP][FREE]viewdns.info*')
    print('    *Needs proxy')
    print('3. [WIP][PAID]2ip.ru*')
    print('    *Needs captcha key + mb proxy')
    print('4. [WIP][FREE]SecurityTrails*')
    print('    *Maybe needs proxy')
    print('    *[WIP] = WorkInProgress')
    print('5. [FREE][Ultra++Slow]HackerTarget API Bypassed*')
    print('    *Best From ALL from Domain Count Perspective')
    try:
        option = int(input('Enter your choice: '))
    except:
        print('Wrong input. Please enter a number ...')
    if option == 1:
        possible_domain_count = 0
        parsed_domain_count = 0
        threads = 10
        counts = 0
        with alive_bar(len(ips)) as bar:
            for ip in ips:
                if counts<=threads:
                    threading.Thread(target=translator1_check, args=((str(ip)),)).start()
                    counts+=1
                    bar()
                else:
                    wait(lambda: free_threads(), timeout_seconds=120, waiting_for="free threads")
                    threading.Thread(target=translator1_check, args=((str(ip)),)).start()
                    counts+=1
                    bar()
        wait(lambda: zero_threads(), timeout_seconds=120, waiting_for="zero threads")
        print('Possible domain count: ' + str(possible_domain_count))
        print('Parsed domain count: ' + str(parsed_domain_count))
        tasks.put('Possible domain count: ' + str(possible_domain_count) + ';ip_translator.txt')
        tasks.put('Parsed domain count: ' + str(parsed_domain_count) + ';ip_translator.txt')
    elif option == 2:
        print('Not working for now')
        exit()
        for ip in ips:
            req = urllib.request.Request('https://viewdns.info/reverseip/?host=%s&t=1' % ip, headers={'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})
            the_page = urllib.request.urlopen(req).read().decode('utf-8')
            soup = BeautifulSoup(the_page, "html.parser")
            try:
                table = (soup.find("table", {"border" : "1"})).find_all("td")
                count = 0
                with open('ip_translator.txt', 'a+') as out:
                    for link in table:
                        count+=1
                        if count % 2 == 0:
                            continue
                        elif link.get_text(strip=True) == 'Domain':
                            continue
                        else:
                            print(link.get_text)
                            out.write(link.get_text + '\n')
            except:
                continue
    elif option == 3:
        print('Not working for now')
    elif option == 4:
        possible_domain_count = 0
        parsed_domain_count = 0
        threads = 10
        counts = 0
        with alive_bar(len(ips)) as bar:
            for ip in ips:
                if counts<=threads:
                    threading.Thread(target=translator2_check, args=((str(ip)),)).start()
                    counts+=1
                    bar()
                else:
                    wait(lambda: free_threads(), timeout_seconds=120, waiting_for="free threads")
                    threading.Thread(target=translator2_check, args=((str(ip)),)).start()
                    counts+=1
                    bar()
        wait(lambda: zero_threads(), timeout_seconds=120, waiting_for="zero threads")
        print('Possible domain count: ' + str(possible_domain_count))
        print('Parsed domain count: ' + str(parsed_domain_count))
        tasks.put('Possible domain count: ' + str(possible_domain_count) + ';ip_translator.txt')
        tasks.put('Parsed domain count: ' + str(parsed_domain_count) + ';ip_translator.txt')
    elif option == 5:
        possible_domain_count = 0
        parsed_domain_count = 0
        threads = 100
        counts = 0
        with alive_bar(len(ips)) as bar:
            for ip in ips:
                if counts<=threads:
                    threading.Thread(target=hackertarget_check, args=((str(ip)),)).start()
                    counts+=1
                    bar()
                else:
                    wait(lambda: free_threads(), timeout_seconds=12000, waiting_for="free threads")
                    threading.Thread(target=hackertarget_check, args=((str(ip)),)).start()
                    counts+=1
                    bar()
        wait(lambda: zero_threads(), timeout_seconds=12000, waiting_for="zero threads")
        print('Possible domain count: ' + str(possible_domain_count))
        print('Parsed domain count: ' + str(parsed_domain_count))
        tasks.put('Possible domain count: ' + str(possible_domain_count) + ';hackertarget.txt')
        tasks.put('Parsed domain count: ' + str(parsed_domain_count) + ';hackertarget.txt')
    else:
        print('Invalid option. Please enter a number between 1 and 5.')
    #table = (soup.find("div", {"id" : "result-anchor"})).find_all("a", href=True)
    #for link in table:
    #    print(link.get('href').replace('http', 'https'))

def tools():
    global threads, counts
    option = ''
    print('1. Subfinder - Subdomain Scanner Ultra')
    print('2. SSL Check')
    print('3. Domain to ip + network info')
    print('4. CDN Domain Checker')
    print('5. IP Range Pinger')
    try:
        option = int(input('Enter your choice: '))
    except:
        print('Wrong input. Please enter a number ...')
    if option == 1:
        if platform.system() == 'Windows':
            domain = str(input('Input domain to scan: '))
            subprocess.run(f'subfinder_x86_64.exe -d {domain} -all -o {domain}.txt', stdout=subprocess.PIPE).stdout.decode('utf-8')
        else:
            domain = str(input('Input domain to scan: '))
            #subprocess.run(f'./subfinder_arm64 -d {domain} -all -o {domain}.txt', stdout=subprocess.PIPE).stdout.decode('utf-8')
            subprocess.run(f'./subfinder_arm64 -d {domain} -all -o {domain}.txt', capture_output=True).stdout.decode("utf-8")
    elif option == 2:
        domain_file = str(input('Enter filename with domain_list: '))
        domains = []
        with open(domain_file, 'r') as read:
            lines = read.readlines()
            read.close()
        for line in lines:
            domains.append(line.rstrip())
        for domain in domains:
            try:
                requests.get('https://'+str(domain)+'/', headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})
                print(f'{bcolors.OKGREEN} [+] ' + str(domain) + f'{bcolors.ENDC}')
            except:
                pass
    elif option == 3:
        domain_file = str(input('Enter filename with domain_list: '))
        domains = []
        with open(domain_file, 'r') as read:
            lines = read.readlines()
            read.close()
        for line in lines:
            domains.append(line.rstrip())
        for domain in domains:
            try:
                ip = socket.gethostbyname(hostname)
                requests.get('https://'+str(domain)+'/', headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})
                print(f'{bcolors.OKGREEN} [+] ' + str(domain) + f'{bcolors.ENDC}')
            except:
                pass
    elif option == 4:
        domain_file = str(input('Enter filename with domain_list: '))
        hostname = str(input('Enter Host header for CDN to check: '))
        path = str(input('Enter url path for CDN to check: '))
        right_answer = str(input('Enter good keyword: '))
        print("How much threads do you want?")
        print("Recommended: 100")
        threads = int(input())
        counts = 0
        domains = []
        with open(domain_file, 'r') as read:
            lines = read.readlines()
            read.close()
        for line in lines:
            domains.append(line.rstrip())
        with alive_bar(len(domains)) as bar:
            for domain in domains:
                if counts<=threads:
                    threading.Thread(target=cdn_check, args=(str(domain), str(hostname), str(path), str(right_answer),)).start()
                    counts+=1
                    bar()
                else:
                    wait(lambda: free_threads(), timeout_seconds=120, waiting_for="free threads")
                    threading.Thread(target=cdn_check, args=(str(domain), str(hostname), str(path), str(right_answer),)).start()
                    counts+=1
                    bar()
            wait(lambda: zero_threads(), timeout_seconds=120, waiting_for="zero threads")
            print('Work Finished!')
    elif option == 5:
        print("How much threads do you want?")
        print("Recommended: 30")
        threads = int(input())
        counts = 0
        ips = []
        f_name = str(input("Enter file name: "))
        with open(f_name, 'r') as read:
            lines = read.readlines()
            read.close()
        count = 0
        for line in lines:
            ips.append([str(ip) for ip in ipaddress.IPv4Network(line[:len(line) - 1])])
            count+=1
        with alive_bar(sum(len(l) for l in ips)) as bar:
            for x in range(count):
                for y in range(len(ips[x])):
                    if counts<=threads:
                        threading.Thread(target=ping_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
                    else:
                        wait(lambda: free_threads(), timeout_seconds=120, waiting_for="free threads")
                        threading.Thread(target=ping_check, args=((str(ips[x][y])),)).start()
                        counts+=1
                        bar()
            wait(lambda: zero_threads(), timeout_seconds=120, waiting_for="zero threads")
            print('Work Finished!')
    else:
        print('Invalid option. Please enter a number between 1 and 4.')

def option4():
    a = urllib.request.urlopen(urllib.request.Request('https://www.cloudflare.com/ips-v4', data=None, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})).read()
    a = a.decode('utf-8')
    with open('cflare_ranges.txt', 'w') as out:
        out.write(a + '\n')
        out.close()

def print_menu():
    for key in menu_options.keys():
        print (key, '--', menu_options[key] )

menu_options = {
    1: 'CloudFlare ip check',
    2: 'Fastly ip check',
    3: 'Azure ip check',
    4: 'CloudFront ip check',
    5: 'G-Core ip check',
    6: 'ArvanCloud ip check',
    7: 'EdgeCast/Edgio/Verizon ip check',
    8: '[WIP]Volterra/F5.com ip check',
    9: '[WIP]UDomain ip check',
    10: 'SECRET',
    11: '[WIP]IP to Domain Translator(After 10 checks ip ban)',
    12: 'Tools',
    13: 'Update CloudFlare ranges',
    14: 'Exit',
}
        
if __name__=='__main__':
    version = 0.48
    print('Checking for updates...')
    try:
        if (float(requests.get('https://raw.githubusercontent.com/SuspectWorkers/cf_scan_443/main/version.txt', verify=False, timeout=5).text) > float(version)):
            update_script(1)
        else:
            print('No updates found')
            update_script(0)
    except:
        pass
    threading.Thread(target=FileHandler, args=()).start()
    while(True):
        print_menu()
        option = ''
        try:
            option = int(input('Enter your choice: '))
        except:
            print('Wrong input. Please enter a number ...')
        if option == 1:
           option1()
        elif option == 2:
            option2()
        elif option == 3:
            option2_1()
        elif option == 4:
            option2_2()
        elif option == 5:
            option2_3()
        elif option == 6:
            option2_4()
        elif option == 7:
            option2_5()
        elif option == 11:
            option3()
        elif option == 12:
            tools()
        elif option == 13:
            option4()
        elif option == 14:
            print('Goodbye!')
            exit()
        else:
            print('Invalid option. Please enter a number between 1 and 8.')



    

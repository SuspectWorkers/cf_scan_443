# cdn_scan_80 + 443

# Termux 
  > ## Installation 
  ```
  pkg update && pkg install openssl wget python3 git -y && pip3 install waiting ipaddress alive-progress bs4 requests warnings && git clone https://github.com/SuspectWorkers/cf_scan_443 && cd cf_scan_443 && python3 scan.py
  ```

  > ## Start
  ```
  cd cf_scan_443; python3 scan.py
  ```

  > ## Output Result :
  > Results saved to file (cflare_output.txt; cfront_output...)

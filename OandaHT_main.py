from OandaHT_function import *

login_file='/Users/MengfeiZhang/Desktop/tmp/login_info.csv'

set_obj=set(5, 500, 50000, login_file)

HFobj1=HFtrading("EUR_USD", set_obj)
HFobj2=HFtrading("USD_JPY", set_obj)

hf_vet=[HFobj1, HFobj2]

#start trading
threads=[]
for hf in hf_vet:
    threads.append(threading.Thread(target=hf.start(),args=None))


for thread in threads:
    thread.start()

for thread in threads:
    thread.join()
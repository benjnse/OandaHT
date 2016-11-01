from OandaHT_function import *

login_file='/Users/MengfeiZhang/Desktop/tmp/login_info.csv'

set_obj=set(60, 5000, 50000, login_file)

HFobj1=HFtrading("EUR_USD", set_obj)
HFobj2=HFtrading("USD_JPY", set_obj)
HFobj3=HFtrading("GBP_USD", set_obj)
HFobj4=HFtrading("AUD_USD", set_obj)
HFobj5=HFtrading("NZD_USD", set_obj)
HFobj6=HFtrading("USD_CHF", set_obj)
HFobj7=HFtrading("USD_CAD", set_obj)
HFobj8=HFtrading("EUR_CHF", set_obj)


hf_vet=[HFobj1, HFobj2, HFobj3, HFobj4, HFobj5, HFobj6, HFobj7, HFobj8]

#start trading
threads=[]
for hf in hf_vet:
    threads.append(threading.Thread(target=hf.start(),args=None))


for thread in threads:
    thread.start()

for thread in threads:
    thread.join()
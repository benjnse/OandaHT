from pyoanda import Order, Client, PRACTICE
import time
import datetime
import threading
import csv
import numpy as np
from OandaHT_model import *


class HFtrading:

    def __init__(self, underlying, set_obj):
        run_time=time.strftime("%Y%m%d_%H%M%S")
        self.underlying=underlying
        self.set_obj=set_obj
        self.mid_price=0
        self.vol=None
        log_dir='/Users/MengfeiZhang/Desktop/tmp'
        self.f=open(log_dir+'/'+self.underlying+'_hf_log_'+run_time+'.txt','w')
        self.weekday=None
        self.now=None
        self.client=None
        self.q=0
        self.max_inventory=set_obj.get_max_inventory()
        if ('JPY' in self.underlying)==True:
            self.prec=3
        else:
            self.prec=5
        #connect
        self.connect()
        sabr_calib=SABRcalib(0.5, 1.0/52)
        sabr_calib.calib(self.get_hist_data(262*5))
        self.SABRpara=sabr_calib.get_para()


    def connect(self):
        try:
            self.client = Client(
                environment=PRACTICE,
                account_id=self.set_obj.get_account_id(),
                access_token=self.set_obj.get_token()
            )
            print self.underlying+' connection succeeded...'
        except:
            print self.underlying+' connection failed...'
            time.sleep(5)
            self.connect()


    def get_mid_price(self):
        try:
            price_resp=self.client.get_prices(instruments=self.underlying, stream=False) #, stream=True
            price_resp=price_resp['prices'][0]
            return (price_resp['ask']+price_resp['bid'])/2
        except Exception as err:
            print >>self.f, err


    def get_atm_vol(self):
        return self.SABRpara[0]*self.get_mid_price()**(self.SABRpara[1]-1)

    def get_hist_data(self, hist_len):
        hist_resp=self.client.get_instrument_history(
            instrument=self.underlying,
            candle_format="midpoint",
            granularity="D",
            count=hist_len,
        )
        price=[]
        for i in range(0,len(hist_resp['candles'])):
            price.append(hist_resp['candles'][i]['closeMid'])

        return price

    def get_hist_vol(self):

        hist_resp=self.client.get_instrument_history(
            instrument=self.underlying,
            candle_format="midpoint",
            granularity="S5",
            count=100,
        )

        ret_tmp=[]
        for i in range(1,len(hist_resp['candles'])):
            ret_tmp.append(hist_resp['candles'][i]['closeMid']-hist_resp['candles'][i-1]['closeMid'])

        return np.std(ret_tmp)

    def get_live_sprd(self):
        try:
            price_resp=self.client.get_prices(instruments=self.underlying, stream=False) #, stream=True
            price_resp=price_resp['prices'][0]
            return price_resp['ask']-price_resp['bid']
        except Exception as err:
            print >>self.f, err
            return 0

    def get_current_inventory(self):
        return float(self.get_position())/self.max_inventory

    def get_position(self):
        try:
            resp=self.client.get_position(instrument=self.underlying)
            if resp['side']=='buy':
                return resp['units']
            elif resp['side']=='sell':
                return -resp['units']
        except Exception as err:
                return 0

    def load_data(self):
        self.mid_price=self.get_mid_price()
        self.weekday=datetime.datetime.today().weekday()
        self.now=datetime.datetime.now()
        self.q=self.get_current_inventory()
        #self.vol=self.get_atm_vol()
        self.vol=self.get_hist_vol()

    def start(self):
        self.load_data()
        if (int(self.weekday)==4 and int(self.now.hour)>=17): #Friday 5pm
            print 'market closed...'
            return None

        model=HFmodel(self.vol)
        model.calib(self.get_live_sprd())
        model.calc(self.mid_price, self.q, 0, 1)

        print >> self.f, 'market mid price: '+str(self.mid_price)
        print >> self.f, 'model reservation price: '+str(model.get_mid_rev_price())
        print >> self.f, 'model bid price: '+str(model.get_opt_bid(self.prec))
        print >> self.f, 'model ask price: '+str(model.get_opt_ask(self.prec))
        print >> self.f, 'gamma: '+str(model.gamma)
        print >> self.f, 'inventory: '+str(self.q)
        print >> self.f, 'volatility (5s): '+str(self.vol)

        try:
            print 'heartbeat('+self.underlying+') '+str(self.now)+'...'
            #close all outstanding orders
            resp_order=self.client.get_orders(instrument=self.underlying)
            for order in resp_order['orders']:
                resp_close_order=self.client.close_order(order_id=order['id'])

            expiry_order=self.now + datetime.timedelta(days=1)
            expiry_order=expiry_order.isoformat('T') + "Z"
            order_ask = Order(
                instrument=self.underlying,
                units=self.set_obj.get_trade_size(),
                side="sell",
                type="limit",
                price=model.get_opt_ask(self.prec),
                expiry=expiry_order,
            )

            order_bid = Order(
                instrument=self.underlying,
                units=self.set_obj.get_trade_size(),
                side="buy",
                type="limit",
                price=model.get_opt_bid(self.prec),
                expiry=expiry_order,
            )
            #place order
            try:
                if self.q>=1: #long limit reached
                    resp_order_ask = self.client.create_order(order=order_ask)
                elif self.q<=-1: #short limit reached
                    resp_order_bid = self.client.create_order(order=order_bid)
                else:
                    resp_order_ask = self.client.create_order(order=order_ask)
                    resp_order_bid = self.client.create_order(order=order_bid)
            except Exception as err:
                print err
                if ('halt' in str(err))==True:
                    print 'market closed...'
                    return None
                else:
                    print "cannot place order..."

            time.sleep(self.set_obj.get_timer())
        except Exception as error:
            print error
            print self.underlying+' disconnected, try to reconnect '+str(self.now)+'...'
            self.connect()

        threading.Timer(1, self.start).start()


class set:
    def __init__(self, timer, trade_size, max_inventory, login_file):
        self.timer=timer
        self.trade_size=trade_size
        self.max_inventory=max_inventory

        file = open(login_file, 'r')
        i=1
        try:
            reader = csv.reader(file)
            for row in reader:
                if i==1:
                    self.account_id=row[0]
                elif i==2:
                    self.token=row[0]
                elif i==3:
                    self.email_login=row[0]
                elif i==4:
                    self.email_pwd=row[0]
                i+=1

        finally:
            file.close()

    def get_timer(self):
        return self.timer

    def get_account_id(self):
        return str(self.account_id)

    def get_token(self):
        return str(self.token)

    def get_email_login(self):
        return str(self.email_login)

    def get_email_pwd(self):
        return str(self.email_pwd)

    def get_trade_size(self):
        return self.trade_size

    def get_max_inventory(self):
        return self.max_inventory
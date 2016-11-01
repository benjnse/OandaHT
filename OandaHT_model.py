import math
import numpy as np
from scipy.optimize import minimize


class HFmodel:

    def __init__(self, sigma):

        self.sigma=sigma
        self.gamma=0
        self.k=1.5
        self.mid_rev_price=None

    def calc(self, s, q, t, T):
        self.mid_rev_price=s-q*self.gamma*self.sigma**2*(T-t)

    def calib(self, sprd):
        x0=[3]
        result = minimize(self.obj_func, x0, args=(sprd), method='nelder-mead', options={'xtol': 1e-8, 'disp': False})
        self.gamma=result.x[0]
        #print 'gamma: '+str(self.gamma)

    def obj_func(self, gamma, sprd):
        return (sprd-2/gamma*math.log(1+gamma/self.k))**2

    def get_mid_rev_price(self):
        return self.mid_rev_price

    def get_opt_bid(self, prec):
        return round(self.mid_rev_price-1/self.gamma*math.log(1+self.gamma/self.k), prec)

    def get_opt_ask(self, prec):
        return round(self.mid_rev_price+1/self.gamma*math.log(1+self.gamma/self.k), prec)


class SABRcalib:

    def __init__(self, beta, T):
        self.T=T #T for future use
        self.alpha=0
        self.beta=beta
        self.rho=0
        self.nu=0
        self.vol_atm=None
        self.garch_para=None
        self.para=None

    def calib(self, hist_price):

        ret=price2ret(hist_price)
        T=len(ret)
        hist_alpha = np.empty(T)
        d_w1=np.empty(T-1)
        d_w2=np.empty(T-1)

        #calibrate garch model
        vol_obj=garch(ret)
        vol_obj.estimation()
        self.garch_para=vol_obj.theta
        self.vol_atm=vol_obj.get_fitted_vol()

        for i in range(0,T):
            hist_alpha[i]=self.vol_atm[i]*math.pow(hist_price[i+1], 1-self.beta)

        self.alpha=hist_alpha[-1]
        ret_alpha=price2ret(hist_alpha)
        self.nu=np.std(ret_alpha)

        hist_price_tmp=hist_price[1:]
        for i in range(1,T):
            d_w1[i-1]=(hist_price_tmp[i]-hist_price_tmp[i-1])/(hist_alpha[i-1]*pow(hist_price_tmp[i-1],self.beta))
            d_w2[i-1]=(hist_alpha[i]-hist_alpha[i-1])/(hist_alpha[i-1]*self.nu)


        self.rho=np.corrcoef(d_w1, d_w2)[0, 1]

        self.para = self.alpha, self.beta, self.rho, self.nu

    def get_para(self):

        return self.para


class garch:

    def __init__(self, data):
        self.data=data
        self.theta=None

    def logfunc(self, theta):
        c, a, b=theta
        ret=self.data
        T = len(ret)
        ret=ret-np.mean(ret)
        h = np.empty(T)
        h[0] = np.var(ret)

        logfunc=0
        for i in range(1, T):
            h[i] = c + a*ret[i-1]**2 + b*h[i-1]  # GARCH(1,1) model
            logfunc+=-0.5*math.log(h[i])-0.5*ret[i]**2/h[i]

        return -logfunc

    def estimation(self):
        x0=[0.5,0.1,0.85]
        lb=0.0001
        bnds=[(0,10), (lb,1), (lb,1)]
        result = minimize(self.logfunc, x0, method='L-BFGS-B', bounds=bnds, options={'maxiter':99999999, 'disp': False})
        self.theta=result.x

    def get_fitted_vol(self):
        ret=self.data
        c, a, b=self.theta
        T = len(ret)
        ret=ret-np.mean(ret)
        h = np.empty(T)
        vol = np.empty(T)
        h[0] = np.var(ret)
        vol[0]=math.sqrt(h[0])

        for i in range(1, T):
            h[i] = c + a*ret[i-1]**2 + b*h[i-1]
            vol[i]=math.sqrt(h[i])

        return vol*math.sqrt(262)

def price2ret(price):
    ret_tmp=[]
    for i in range(1,len(price)):
        ret_tmp.append(math.log(price[i]/price[i-1]))
    return ret_tmp




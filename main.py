# -*- coding:utf8 -*-
import base64
from urllib import    request, parse
import json
import requests
import time
import  login
import  config
from cache import Cache
import itchat
'''
获取数据接口
'''
headers = {'content-type': 'application/json'}
def queryMarketData(pageNo,pageSize,querySortType):

    try:
        data ={
            "appId": 1,
            "lastAmount":None,
            "lastRareDegree":3,
            "pageNo": pageNo,
            "pageSize": pageSize,
            "petIds": [],
            "querySortType": querySortType,
            "tpl":"",
            "requestId":time.time()
        }
       # print(data)
        s =  requests.post("https://pet-chain.baidu.com/data/market/queryPetsOnSale",  data=json.dumps(data), headers=headers,timeout=5)
    except:
        raise BusinessException("服务器异常")
    status =  s.status_code
    if status==200:
        res = json.loads(s.content)
        msg = res["errorMsg"]

        if msg == "success":
            data = res["data"]["petsOnSale"]
            return data

        else:
            raise BusinessException("接口获取错误")
    else:
        raise BusinessException("接口异常"+str(status))
'''
下单接口
'''
def purchase(request,petId,pet_amount,pet_validCode):
    try:

        data = {
            "appId":1,
            "petId":petId,
            "requestId":time.time(),
            "tpl":"",
            "amount":"{}".format(pet_amount),
            "validCode": pet_validCode
        }
        seed, captcha =  get_captcha(request)
        data['captcha'] = captcha
        data['seed'] = seed
        page = request.post("https://pet-chain.baidu.com/data/txn/create", headers=headers, data=json.dumps(data), timeout=2)
        res = json.loads(page.content)
        print(res)
        msg = res["errorMsg"]
        if msg == "success":
            print("购买成功")
    except Exception as e:
        raise BusinessException("验证码获取异常")

'''
验证码接口
'''
def get_captcha(request):
    seed = -1
    captcha = -1
    data = {
        "requestId": int(time.time() * 1000),
        "appId": 1,
        "tpl": ""
    }
    page = request.post("https://pet-chain.baidu.com/data/captcha/gen", data=json.dumps(data),
                         headers=headers)
    res = json.loads(page.content)
    msg = res["errorMsg"]
    if msg == "success":
        img = "data: image / jpeg;base64," + res["data"]["img"]
        seed = res["data"]["seed"]
        captcha =getValidCode(img)
    else:
        raise BusinessException("验证码获取异常")
    return seed, captcha





'''
AMOUNT_ASC 金额排序
RAREDEGREE_DESC  稀有度排序


'''
def main():
    # 开启微信助手提醒需要扫码登录
    if config.sendMsg ==0:
        itchat.auto_login()
    request = None
    # 自动刷狗则需要登录
    if config.type==1:
        request = login.login(config.username,config.password)

    cache =  Cache()
    while True:
        try:
         # 获取数据默认按照时间倒叙
         data =  queryMarketData(1,10,"AMOUNT_ASC")
         for item in data:
             #没猜错的话这个是等级  0-4
             rareDegree = item["rareDegree"]
             amount = float(item["amount"])
             maxAmount = config.rares[rareDegree]
             petid = item["petId"]
             if(amount<=maxAmount):
                 print("等级： " + str(rareDegree) + "价格：" + str(amount))
                 validCode = item["validCode"]
                 if validCode=='':
                     continue
                 buyUrl = config.urlDetail+petid+"&validCode="+validCode
                 if (buyUrl == cache.get(petid)):
                     continue
                 print(buyUrl)
                 # 发送微信提醒
                 if config.sendMsg==0:
                     itchat.send("等级： " + str(rareDegree) + "价格：" + str(amount), toUserName=config.toUserName)
                     itchat.send(buyUrl, toUserName=config.toUserName)
                  #根据petid 缓存url 过期时间为30秒 刷过链接就不在刷了
                 cache.set(petid, buyUrl,30)
                 if config.type==1:
                     #下单
                     purchase(request,petid,amount,validCode)



        except BusinessException as e:
            print(e.value)
            continue

'''
调用第三方验证码接口

'''
def getValidCode(imgBase64):
    send_data = parse.urlencode([
        ('showapi_appid', config.showapi_appid)
        , ('showapi_sign', config.showapi_sign)
        , ('img_base64', imgBase64)
        , ('typeId', 34)
        , ('convert_to_jpg', 0)

    ])
    req = request.Request(config.apiurl)
    try:
        response = request.urlopen(req, data=send_data.encode('utf-8'), timeout = 10) # 10秒超时反馈
    except Exception as e:
        raise BusinessException("第三方接口服务器异常")
    result = response.read().decode('utf-8')
    result_json = json.loads(result)
    print ('result_json data is:', result_json)
    if result_json["showapi_res_code"] ==0:
       return  result_json["showapi_res_body"]["Result"]
    else:
         raise BusinessException("第三方接口错误")

#自定义异常
class BusinessException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


main()
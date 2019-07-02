#coding:utf-8
import binascii
import hashlib
import hmac
import urllib.parse
import urllib.request
import time
import random
import base64
import itchat
import os
from aip import AipSpeech
from pydub import AudioSegment
import wave
import io
import sys
sys.path.append('./wechatHelpers')
from apscheduler.schedulers.blocking import BlockingScheduler
import _thread
from AutomaticReplier import AutomaticReplier
from BabyCareAbouter import BabyCareAbouter
from GFWeather import GFWeather


class ChatManager:   
    babyCareAbouters = {}
    automaticRepliers = {}
	
    def __init__(self):
        self.GFWeather = None



    def keepAliveJob(self):
        scheduler = BlockingScheduler()
        scheduler.add_job(self.keepAlive, 'interval', seconds=60*30)
        scheduler.start()	

    def keepAlive(self):
        # 不准时发送，防止被微信查封
        sleepSeconds = random.randint(1, 5)
        time.sleep(sleepSeconds)
        ChatManager.set_system_notice('keepAlive')
		
    @staticmethod 
    def addBabyCareAbouter(wechat_name):
        friends = itchat.search_friends(name=wechat_name)
        if not friends:
            return '昵称有误,添加失败！'
        name_uuid = friends[0].get('UserName')
        babyCareAbouter = BabyCareAbouter(wechat_name,name_uuid)
        ChatManager.babyCareAbouters[name_uuid] = babyCareAbouter
        return wechat_name + '已添加到关心者中，他已可以获得隐藏功能！'
	
    @staticmethod 
    def addAutomaticReplier(wechat_name):
        friends = itchat.search_friends(name=wechat_name)
        if not friends:
            return '昵称有误,添加失败！'
        name_uuid = friends[0].get('UserName')
        automaticReplier = AutomaticReplier(wechat_name,name_uuid)
        ChatManager.automaticRepliers[name_uuid] = automaticReplier
#        print(ChatManager.automaticRepliers)
        return wechat_name + '已添加到自动回复列表中，他的所有消息将会被自动回复！'

    @staticmethod 
    def delBabyCareAbouter(wechat_name):
        friends = itchat.search_friends(name=wechat_name)
        name_uuid = friends[0].get('UserName')
        if not ChatManager.babyCareAbouters[name_uuid]:
            return '昵称有误,删除失败！'  
        del ChatManager.babyCareAbouters[name_uuid]
        return wechat_name + '已从关心者中删除！'
	
    @staticmethod 
    def delAutomaticReplier(wechat_name):
        friends = itchat.search_friends(name=wechat_name)
        name_uuid = friends[0].get('UserName')
        if not ChatManager.automaticRepliers[name_uuid]:
            return '昵称有误,删除失败！'
        del ChatManager.automaticRepliers[name_uuid]
        return wechat_name + '已从自动删除列表！'
    
	
	
    def is_online(self, auto_login=False):
        '''
        判断是否还在线,
        :param auto_login: bool,如果掉线了则自动登录(默认为 False)。
        :return: bool,当返回为 True 时，在线；False 已断开连接。
        '''

        def online():
            '''
            通过获取好友信息，判断用户是否还在线
            :return: bool,当返回为 True 时，在线；False 已断开连接。
            '''
            try:
                if itchat.search_friends():
                    return True
            except:
                return False
            return True

        if online():
            return True
        # 仅仅判断是否在线
        if not auto_login:
            return online()

        # 登陆，尝试 5 次
        for _ in range(5):
            # 命令行显示登录二维码
            # itchat.auto_login(enableCmdQR=True)
            print('正在打印登陆二维码')
            if os.environ.get('MODE') == 'server':
                itchat.auto_login(enableCmdQR=2,hotReload=True)
                _thread.start_new_thread(itchat.run,())
            else:
                itchat.auto_login(hotReload=True)
                _thread.start_new_thread(itchat.run,())
            if online():
                print('登录成功')
                return True
        else:
            print('登录成功')
            return False
	
    @staticmethod 
    def getOrders():
        '''
        获取命令都有哪些
        '''	
        return (
            '命令错误，请按照下面提示来输入命令:\n'
            '    增加自动回复+空格+要加的人 \n'
            '    增加关心女友+空格+要加的人\n' 
            '    删除自动回复+空格+要删除的人\n'
            '    删除关心女友+空格+要删除的人\n' 
            '    查看自动回复\n'
            '    查看关心女友\n'
            '    设置忙什么+空格+你正在做什么'
            )
			
    @staticmethod     
    def executiveOrder(orderWords):
        '''
        处理各种命令
        '''
        order = orderWords.split(' ',1)
        if order[0] == '增加自动回复':
            return ChatManager.addAutomaticReplier(order[1])
        elif order[0] == '增加关心女友':
            return ChatManager.addBabyCareAbouter(order[1])
        elif order[0] == '删除自动回复':
            return ChatManager.delAutomaticReplier(order[1])
        elif order[0] == '删除关心女友':
            return ChatManager.delBabyCareAbouter(order[1])
        elif order[0] == '设置忙什么':
            BabyCareAbouter.what_i_am_doing = order[1]
            return "回复    "+order[1]+"   设置成功"
        elif order[0] == '查看自动回复':
            if not ChatManager.automaticRepliers:
                return '列表为空'
            allAutomaticRepliers = '自动回复人员有:'
            for automaticReplier in ChatManager.automaticRepliers.values():
                allAutomaticRepliers += '\n       ' + automaticReplier.wechat_name
            return allAutomaticRepliers
        elif order[0] == '查看关心女友':	
            if not ChatManager.babyCareAbouters:
                return '列表为空'
            allBabyCareAbouters = '关心人员有:'
            for babyCareAbouter in ChatManager.babyCareAbouters.values():
                allBabyCareAbouters+= '\n       ' + babyCareAbouter.wechat_name
            return allBabyCareAbouters
        else:
            return ChatManager.getOrders()
		

    @staticmethod 
    def asr(msg):
        #将语音消息存入文件，想通过百度翻译，再通过获得图灵机器人的回复
        APP_ID = '16516161'
        API_KEY = 'eycPzd5xfCMsd0jn4aWrjwDz'
        SECRET_KEY = 'PLWIGyEIYcsYQoHuw6lPzxmBrrmSgsoc'
        client = AipSpeech(APP_ID, API_KEY, SECRET_KEY)
        msg['Text'](msg['FileName'])
        #先从本地获取mp3的bytestring作为数据样本
        fp=open(msg['FileName'],'rb')
        data=fp.read()
        fp.close()
        #主要部分
        aud=io.BytesIO(data)
        sound=AudioSegment.from_file(aud,format='mp3')
        raw_data = sound._data
        #写入到文件，验证结果是否正确。
        l=len(raw_data)
        f=wave.open("tmp.wav",'wb')
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        f.setnframes(l)
        f.writeframes(raw_data)
        f.close()
        fp = open("tmp.wav", 'rb')
        result = client.asr(fp.read(), 'wav', 16000, {'dev_pid': 1536, })
        fp.close()
        os.remove('tmp.wav')
        os.remove(msg['FileName'])
        return result['result'][0]
   
    @staticmethod     
    def set_system_notice(text):
        """
        给文件传输助手发送系统日志。
        :param text:日志内容
        :return:None
        """
        if text:
            text = '*' * 30 + '\n\n' + text + '\n\n' + '*' * 30
            itchat.send(text, toUserName='filehelper')


  



		
    @itchat.msg_register(itchat.content.TEXT)
    def replyText(msg):
        '''
        接受文本消息，并进行回复！
        '''
        fromUserName = msg['FromUserName']
        toUserName = msg['ToUserName']
        #如果是发给filehelper的微信消息，则处理该命令
        if toUserName == 'filehelper':
            ChatManager.set_system_notice(ChatManager.executiveOrder(msg['Text']))
            return
        automaticReplier = ChatManager.automaticRepliers.get(fromUserName)
        if automaticReplier:
            automaticReplier.reply(msg['Text'])
        else:
            babyCareAbouter = ChatManager.babyCareAbouters.get(fromUserName)
            if babyCareAbouter:
                babyCareAbouter.reply(msg['Text'])
#        print(msg)


    @itchat.msg_register(itchat.content.RECORDING)
    def replyRECORDING(msg):
        '''
        绑定语音消息，并进行回复！
        '''
        fromUserName = msg['FromUserName']
        automaticReplier = ChatManager.automaticRepliers.get(fromUserName)
        if automaticReplier:
            asrMessage = ChatManager.asr(msg)
            automaticReplier.reply(asrMessage)
        else:
            babyCareAbouter = ChatManager.babyCareAbouters.get(fromUserName)
            if babyCareAbouter:
                asrMessage = ChatManager.asr(msg)
                babyCareAbouter.reply(asrMessage)
	

    def run(self):
        '''
        主运行入口
        :return:None
        '''
        # 自动登录
        print('正在登陆')
        if not self.is_online(auto_login=True):
            return
        _thread.start_new_thread(self.keepAliveJob,())
        print('正在加载GFWeather')
        self.GFWeather = GFWeather()
        self.GFWeather.run()

		

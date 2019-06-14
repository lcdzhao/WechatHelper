import requests
import json
import itchat
import time

class BabyCareAbouter:
    '''
    该类是用来关心自己想关心的人的类。
    '''

    what_i_am_doing = '我在学习呢'       # 类变量,所有的BabyCareAbouter获得的状态都一样
    qinghua = '我没有很刻意的去想念你，因为我知道，遇到了就应该感恩，路过了就需要释怀。我只是在很多很多的小瞬间，想起你。比如一部电影，一首歌，一句歌词，一条马路和无数个闭上眼睛的瞬间。'
	
    def __init__(self,wechat_name,name_uuid):
        '''
        初始化
        '''
        self.wechat_name = wechat_name
        self.is_using = False
        self.is_talk_with_zhao = False
        self.name_uuid = name_uuid


    def get_lovelive_info(self):
        '''
        从土味情话中获取每日一句。
        :return: str,土味情话
        '''
        return BabyCareAbouter.qinghua
        print('获取土味情话...')
        resp = requests.get("https://api.lovelive.tools/api/SweetNothings")
        if resp.status_code == 200:
            return resp.text + "\n"
        else:
            print('每日一句获取失败')
            return None

    def set_doing(self,doingWhat):
        '''
        设置自己正在干嘛的答复
        '''
        BabyCareAbouter.what_i_am_doing = doingWhat


		
    def get_zhao_words(self,babyWords):
        '''
        获取图灵机器人的回复。
		return 图灵机器人的回复
        '''
        info = babyWords.encode('utf8')
        api_url = 'http://www.tuling123.com/openapi/api'   # 图灵机器人网址
        data = {
            'key': 'cefc853e3aa4404faf56b649fcff4763',     
            'info': info,                                  # 这是我们从好友接收到的消息 然后转发给图灵机器人
            'userid': 'wechat-robot',                      # 这里你想改什么都可以
        }
        r = requests.post(api_url, data=data).json()       # 把data数据发
        return r.get('text')


    def reply(self,babyWords):
        '''
        回复该被关心的人的消息
        '''
        reply_words = ''
        if self.is_talk_with_zhao:
            if babyWords != '好啦，我不无聊啦':
                reply_words = self.get_zhao_words(babyWords)
            else:
                self.is_talk_with_zhao = False
                reply_words = '好叽，那下次聊啦！'
        else:
            if babyWords == '有点无聊':
                self.is_talk_with_zhao = True
                reply_words = '那小昭昭陪你聊会天啦，你说“好啦，我不无聊啦”，小昭昭的陪聊就结束啦！'
            elif babyWords == '想你了':
                reply_words = self.get_lovelive_info()
            elif babyWords == '不玩了':
                self.is_using = False
                reply_words = '好叽，下次来玩！'
            elif babyWords == '在干什么':
                reply_words = BabyCareAbouter.what_i_am_doing
            elif babyWords == '七月份的尾巴你是狮子座':
                self.is_using = True
                reply_words = ('暗号对接成功！进入隐藏功能页面！\n '
                    '1.语音发送“在干什么”，我会告诉你我正在忙什么啦！\n'
                    '2.语音发送“想你了”，那我会对你说情话，每天都不一样哦！\n'
                    '3.语音发送“有点无聊”，性感小昭，在线陪聊！\n'
                    '4.语音发送“不玩了”，隐藏功能页面就关闭啦！\n')
            elif self.is_using:
                reply_words = ('正在隐藏功能页面！\n'
                    '1.语音发送“在干什么”，我会告诉你我正在忙什么啦！\n'
                    '2.语音发送“想你了”，那我会对你说情话，每天都不一样哦！\n'
                    '3.语音发送“有点无聊”，性感小昭，在线陪聊！\n'
                    '4.语音发送“不玩了”，隐藏功能页面就关闭啦！\n')
		#延时1s后发送
        time.sleep(1)
        itchat.send_msg(reply_words,toUserName=self.name_uuid)
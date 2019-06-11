import requests
import json
import itchat


class BabyCareAbouter:
    '''
    该类是用来关心自己想关心的人的类。
    '''

    what_i_am_doing = '我在学习呢'       # 类变量,所有的BabyCareAbouter获得的状态都一样
	
    def __init__(self,wechat_name,name_uuid):
        '''
        初始化
        '''
        self.wechat_name = wechat_name
        self.is_using = false
        self.is_talk_with_zhao = false
        self.name_uuid = name_uuid


    def get_lovelive_info(self):
        '''
        从土味情话中获取每日一句。
        :return: str,土味情话
        '''
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
            'key': 'b8b30d45beb94009ab53aa2718b03792',     
            'info': info,                                  # 这是我们从好友接收到的消息 然后转发给图灵机器人
            'userid': 'wechat-robot',                      # 这里你想改什么都可以
        }
        r = requests.post(api_url, data=data).json()       # 把data数据发
        return r.get('text')


    def reply_to_baby(self,babyWords):
        '''
        回复该被关心的人的消息
        '''	
        if self.is_talk_with_zhao:
            if babyWords != '好啦，我不无聊啦':
                reply_words = get_zhao_words(babyWords)
            else:
                self.is_talk_with_zhao = false
                reply_words = '好叽，那下次聊啦！'
        else:
            if babyWords == '亲爱哒，我有点无聊':
                self.is_talk_with_zhao = true
                reply_words = '那小昭昭陪你聊会天啦，你说“好啦，我不无聊啦”，小昭昭的陪聊就结束啦！'
            elif babyWords == '亲爱哒，想你啦':
                reply_words = get_lovelive_info();
            elif babyWords == '好啦，不玩啦':
                self.is_using = false
                reply_words = '好叽，下次来玩！'
            elif babyWords == '亲爱哒，在干嘛呢':
                reply_words = BabyCareAbouter.what_i_am_doing
            elif babyWords == '天王盖地虎':
                self.is_using = true
                reply_words = ('宝塔镇河妖！\n 暗号对接成功！进入隐藏功能页面！\n '
                    '1.发送“亲爱哒，在干嘛呢”，我会告诉你我正在忙什么啦！\n'
                    '2.发送“亲爱哒，想你啦”，那我会对你说情话，每天都不一样哦！\n'
                    '3.发送“亲爱哒，我有点无聊”，性感小昭，在线陪聊！\n'
                    '4.发送“好啦，不玩啦”，隐藏功能页面就关闭啦！\n')
            else:
                reply_words = ('正在隐藏功能页面！\n'
                    '1.发送“亲爱哒，在干嘛呢”，我会告诉你我正在忙什么啦！\n'
                    '2.发送“亲爱哒，想你啦”，那我会对你说情话，每天都不一样哦！\n'
                    '3.发送“亲爱哒，我有点无聊”，性感小昭，在线陪聊！\n'
                    '4.发送“好啦，不玩啦”，隐藏功能页面就关闭啦！\n')
        itchat.send_msg(reply_words,toUserName=self.name_uuid)
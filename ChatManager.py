

class ChatManager:
    
    def __init__(self):
        self.babyCareAbouters = {}
        self.automaticRepliers = {}
        self.GFWeather
	
	
	
    def addBabyCareAbouter(self,wechat_name):
        friends = itchat.search_friends(name=wechat_name)
        if not friends:
            return '昵称有误,添加失败！'
        name_uuid = friends[0].get('UserName')
        babyCareAbouter = BabyCareAbouter(wechat_name,name_uuid)
        self.babyCareAbouters['name_uuid'] = babyCareAbouter
        return wechat_name + '已添加到关心者中，他已可以获得隐藏功能！'
	
    def addAutomaticReplier(self,wechat_name):
        friends = itchat.search_friends(name=wechat_name)
        if not friends:
            return '昵称有误,添加失败！'
        name_uuid = friends[0].get('UserName')
        automaticReplier = AutomaticReplier(wechat_name,name_uuid)
        self.automaticRepliers['name_uuid'] = automaticReplier
        return wechat_name + '已添加到自动回复列表中，他的所有消息将会被自动回复！'

    
	
	
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
            if os.environ.get('MODE') == 'server':
                itchat.auto_login(enableCmdQR=2)
            else:
                itchat.auto_login(enableCmdQR=True)
            if online():
                print('登录成功')
                return True
        else:
            print('登录成功')
            return False
			
    def getOrders(self):
        

    
	def executiveOrder(self,orderWords):
    

    def run(self):
        '''
        主运行入口
        :return:None
        '''
        # 自动登录
        if not self.is_online(auto_login=True):
            return
        self.GFWeather = GFWeather()
        self.GFWeather.run()

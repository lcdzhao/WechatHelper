import os
import time
from datetime import datetime

import itchat
import requests
import yaml
from apscheduler.schedulers.blocking import BlockingScheduler
from bs4 import BeautifulSoup

import city_dict


class GFWeather:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36",
    }
    dictum_channel_name = {1: 'ONE●一个', 2: '词霸(每日英语)', 3: '土味情话'}

    def __init__(self):
        self.girlfriend_list, self.alarm_hour, self.alarm_minute, self.dictum_channel = self.get_init_data()

    def get_init_data(self):
        '''
        初始化基础数据
        :return: None
        '''
        with open('_config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.load(f, Loader=yaml.Loader)

        alarm_timed = config.get('alarm_timed').strip()
        init_msg = f"每天定时发送时间：{alarm_timed}\n"

        dictum_channel = config.get('dictum_channel', -1)
        init_msg += f"格言获取渠道：{self.dictum_channel_name.get(dictum_channel, '无')}\n"

        girlfriend_list = []
        girlfriend_infos = config.get('girlfriend_infos')
        for girlfriend in girlfriend_infos:
            girlfriend.get('wechat_name').strip()
            # 根据城市名称获取城市编号，用于查询天气。查看支持的城市为：http://cdn.sojson.com/_city.json
            city_name = girlfriend.get('city_name').strip()
            city_code = city_dict.city_dict.get(city_name)
            if not city_code:
                print('您输入的城市无法收取到天气信息')
                break
            girlfriend['city_code'] = city_code
            girlfriend_list.append(girlfriend)

            print_msg = f"女朋友的微信昵称：{girlfriend.get('wechat_name')}\n\t女友所在城市名称：{girlfriend.get('city_name')}\n\t" \
                f"在一起的第一天日期：{girlfriend.get('start_date')}\n\t最后一句为：{girlfriend.get('sweet_words')}\n"
            init_msg += print_msg

        print(u"*" * 50)
        print(init_msg)

        hour, minute = [int(x) for x in alarm_timed.split(':')]
        return girlfriend_list, hour, minute, dictum_channel

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

    def run(self):
        '''
        主运行入口
        :return:None
        '''
        # 自动登录
        if not self.is_online(auto_login=True):
            return
        for girlfriend in self.girlfriend_list:
            wechat_name = girlfriend.get('wechat_name')
            friends = itchat.search_friends(name=wechat_name)
            if not friends:
                print('昵称有误')
                return
            name_uuid = friends[0].get('UserName')
            girlfriend['name_uuid'] = name_uuid

        # 定时任务
        scheduler = BlockingScheduler()
        # 每天定时给女朋友发送每日一句
        scheduler.add_job(self.start_today_info, 'cron', hour=self.alarm_hour, minute=self.alarm_minute)
        # 每隔 2 分钟发送一条数据用于测试。
        # scheduler.add_job(self.start_today_info, 'interval', seconds=120)
        scheduler.start()

    def start_today_info(self, is_test=False):
        '''
        每日定时开始处理。
        :param is_test:bool, 测试标志，当为True时，不发送微信信息，仅仅获取数据。
        :return: None。
        '''
        print("*" * 50)
        print('获取相关信息...')

        if self.dictum_channel == 1:
            dictum_msg = self.get_dictum_info()
        elif self.dictum_channel == 2:
            dictum_msg = self.get_ciba_info()
        elif self.dictum_channel == 3:
            dictum_msg = self.get_lovelive_info()
        else:
            dictum_msg = ''

        for girlfriend in self.girlfriend_list:
            city_code = girlfriend.get('city_code')
            start_date = girlfriend.get('start_date').strip()
            sweet_words = girlfriend.get('sweet_words')
            today_msg = self.get_weather_info(dictum_msg, city_code=city_code, start_date=start_date,
                                              sweet_words=sweet_words)
            name_uuid = girlfriend.get('name_uuid')
            wechat_name = girlfriend.get('wechat_name')
            print(f'给『{wechat_name}』发送的内容是:\n{today_msg}')

            if not is_test:
                if self.is_online(auto_login=True):
                    itchat.send(today_msg, toUserName=name_uuid)
                # 防止信息发送过快。
                time.sleep(5)

        print('发送成功..\n')

    def isJson(self, resp):
        '''
        判断数据是否能被 Json 化。 True 能，False 否。
        :param resp: request
        :return: bool, True 数据可 Json 化；False 不能 JOSN 化。
        '''
        try:
            resp.json()
            return True
        except:
            return False

    def get_ciba_info(self):
        '''
        从词霸中获取每日一句，带英文。
        :return:str ,返回每日一句（双语）
        '''
        print('获取格言信息（双语）...')
        resp = requests.get('http://open.iciba.com/dsapi')
        if resp.status_code == 200 and self.isJson(resp):
            conentJson = resp.json()
            content = conentJson.get('content')
            note = conentJson.get('note')
            # print(f"{content}\n{note}")
            return f"{content}\n{note}\n"
        else:
            print("没有获取到数据")
            return None

    def get_dictum_info(self):
        '''
        获取格言信息（从『一个。one』获取信息 http://wufazhuce.com/）
        :return: str， 一句格言或者短语
        '''
        print('获取格言信息...')
        user_url = 'http://wufazhuce.com/'
        resp = requests.get(user_url, headers=self.headers)
        if resp.status_code == 200:
            soup_texts = BeautifulSoup(resp.text, 'lxml')
            # 『one -个』 中的每日一句
            every_msg = soup_texts.find_all('div', class_='fp-one-cita')[0].find('a').text
            return every_msg + "\n"
        print('每日一句获取失败')
        return ''

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
			
			
			
    def get_tem_words(self,low_c,high_c):
        '''
        通过温度，获取爱心天气句子
        '''
        tem_words = f'今天的温度大概是{high_c}℃/{low_c}℃。'
        low_c = float(low_c)
        high_c = float(high_c)
        if low_c>=10:
            if high_c >= 38:
                tem_words = tem_words + '卧槽，卧槽！爆表了。都超过38℃了，今天还是呆在宿舍好好吹空调吧。运动的话，不要太晚了哦。'
            elif high_c >= 35:
                tem_words = tem_words + '好热好热啊！出去的时候记得带伞哦，不然晒黑了的话，哼，我要退货的！还有别忘了今天的运动哦，不要太晚啦！'	
            elif high_c >= 30:
            	tem_words = tem_words + '不算很热，但也有点热啦。不太适合出去玩儿，不下雨的话，晚上倒是挺适合出去散步。也要记得今天的运动鸭！'
            elif high_c >= 26:
                tem_words = tem_words + '咦，气温蛮舒服的嘛！热那么一丢丢，如果没有下雨的话，很适合出去玩哦！但是别光顾着玩哦，也要记得运动鸭！'
            elif high_c >= 20:
                tem_words = tem_words + '哈哈哈哈哈，气温真滴是很舒服了！要是没有下雨的话，适合出去蹦蹦跳跳哦。今天的运动可以放在下午哦，据说下午5-6点最适合运动了'
            elif high_c >= 15:
                tem_words = tem_words + '可能稍微有一丢丢的冷，记得要穿上长袖啦！也别忘了今天的运动哦，这种天气最适合运动啦。'
            else:
            	tem_words = tem_words + '有一丢丢的冷，记得衣服要穿厚一点哦！到了运动的时间可不要偷懒鸭！'
        else:
            if low_c < -10:
                tem_words = tem_words + '天呐，怎么会这么冷的一天！记得要穿的厚厚的，看起来胖一点没关系啦，暖暖的最重要！如果下雪的话，今天就不要跑步啦！'
            if low_c < -5 :
            	tem_words = tem_words + '好冷好冷啊！记得套上暖暖的毛衣~。还要记得今天的运动呦！'
            if low_c < 0 :
            	tem_words = tem_words + '好冷鸭!你不会现在还没有穿秋裤吧！没穿的话要打你PP！还有别忘了今天的运动鸭！'
            if low_c < 5 :
                tem_words = tem_words + '秋裤要拿出来放在身边，随时记得穿，这种天气就差不多要穿了,刚刚好暖暖的，不过运动的时候，秋裤还是要脱掉'
            else:
                tem_words = tem_words + '有一丢丢冷哦，穿好外套，要照顾好自己，别让自己感冒啦！也别忘了今天的运动鸭！'
        return tem_words 	

    def get_aqi_words(self,aqi):
        aqi_words = f'还有空气指数大概是{aqi},'
        aqi = float(aqi)
        if aqi >= 200:
            aqi_words = aqi_words + '天呐，这污染强度，建议不要呼吸！一定记得要戴口罩！'
        elif aqi >= 150:
            aqi_words = aqi_words + '欧呦，空气不太好，一点都不适合跑步哦,有口罩的话，尽量带着口罩啦！'	
        elif aqi >= 100:
            aqi_words = aqi_words + '轻度污染的一天，不要在外面运动啦！'	
        elif aqi >= 50:
            aqi_words = aqi_words + '空气还行，可以正常呼吸哦！'
        else: 
            aqi_words = aqi_words + '哈哈哈哈哈，这么好的空气，建议出去的时候多吸几口！'	
        return aqi_words

    def get_weather_info(self, dictum_msg='', city_code='101030100', start_date='2018-01-01',
                         sweet_words='From your Valentine'):
        '''
        获取天气信息。网址：https://www.sojson.com/blog/305.html
        :param dictum_msg: str,发送给朋友的信息
        :param city_code: str,城市对应编码
        :param start_date: str,恋爱第一天日期
        :param sweet_words: str,来自谁的留言
        :return: str,需要发送的话。
        '''
        print('获取天气信息...')
        weather_url = f'http://t.weather.sojson.com/api/weather/city/{city_code}'
        resp = requests.get(url=weather_url)
        if resp.status_code == 200 and self.isJson(resp) and resp.json().get('status') == 200:
            weatherJson = resp.json()
            # 今日天气
            today_weather = weatherJson.get('data').get('forecast')[0]
            # 今日日期
            today_time = datetime.now().strftime('%Y{y}%m{m}%d{d} %H:%M:%S').format(y='年', m='月', d='日')
            # 今日天气注意事项
            notice = today_weather.get('notice')
            # 温度
            high = today_weather.get('high')
            high_c = high[high.find(' ') + 1:high.find('℃')]
            low = today_weather.get('low')
            low_c = low[low.find(' ') + 1:low.find('℃')]
            temperature = self.get_tem_words(low_c,high_c)

            # 风
            fx = today_weather.get('fx')
            fl = today_weather.get('fl')
            wind = f'昨晚夜观天象，天象显示今天的风会是{fx}，强度大概{fl}。'

            # 空气指数
            aqi = today_weather.get('aqi')
            aqi = self.get_aqi_words(aqi)

            # 在一起，一共多少天了，如果没有设置初始日期，则不用处理
            if start_date:
                try:
                    start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
                    day_delta = (datetime.now() - start_datetime).days
                    delta_msg = f'一起运动 {day_delta} 天啦！今天也要加油鸭！\n'
                except:
                    delta_msg = ''
            else:
                delta_msg = ''
            #加格言版本
            #today_msg = f'{delta_msg}\n{notice}。\n{temperature}\n{wind}{aqi}\n\n{dictum_msg}\n{sweet_words if sweet_words else ""}'
            #不加格言的版本
            today_msg = f'{delta_msg}\n{notice}。\n{temperature}\n{wind}{aqi}'
            return today_msg
	
    
	
	



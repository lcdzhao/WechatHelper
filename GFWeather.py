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
        init_msg = f"每天定时发送时间:{alarm_timed}\n"

        dictum_channel = config.get('dictum_channel', -1)
        init_msg += f"格言获取渠道:{self.dictum_channel_name.get(dictum_channel, '无')}\n"

        girlfriend_list = []
        girlfriend_infos = config.get('girlfriend_infos')
        for girlfriend in girlfriend_infos:
            girlfriend.get('wechat_name').strip()
            # 根据城市名称获取城市编号，用于查询天气。查看支持的城市为:http://cdn.sojson.com/_city.json
            city_name = girlfriend.get('city_name').strip()
            city_code = city_dict.city_dict.get(city_name)
            if not city_code:
                print('您输入的城市无法收取到天气信息')
                break
            girlfriend['city_code'] = city_code
            girlfriend_list.append(girlfriend)

            print_msg = f"女朋友的微信昵称:{girlfriend.get('wechat_name')}\n\t女友所在城市名称:{girlfriend.get('city_name')}\n\t" \
                f"在一起的第一天日期:{girlfriend.get('start_date')}\n\t最后一句为:{girlfriend.get('sweet_words')}\n"
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
        random_choice = random.randint(1, 3)
        if low_c>=10:
            if high_c >= 38:
                if random_choice == 1:
                    tem_words = tem_words + '卧槽，卧槽！爆表了。都超过38℃了，今天还是呆在宿舍好好吹空调吧。运动的话，不要太晚了哦。'
                elif random_choice == 2:
                    tem_words = tem_words + '天呐！天呐！怎么肥四！这天气是肿么了？？？好好呆在宿舍吧。太阳下山后再去运动！'
                else:
                    tem_words = tem_words + '！！！？？？这天气，我只想把自己塞在冰箱里一动不动，祝你安好，我的多多同学。不要被热傻了然后忘记运动了！'
            elif high_c >= 35:
                if random_choice == 1:
                    tem_words = tem_words + '好热好热啊！出去的时候记得带伞哦，不然晒黑了的话，哼，我要退货的！还有别忘了今天的运动哦，不要太晚啦！'
                elif random_choice == 2:
                    tem_words = tem_words + '真的，超过35℃，我想多多同学的世界就只有宿舍这么大了，还是不要出去了。太阳下山后再去运动叭！'
                else:
                    tem_words = tem_words + '如果有什么出游计划的话，我建议取消，真的会热傻的！想出去的话建议晚上出去跑步呼吸一下新鲜空气就可以啦！'	
            elif high_c >= 30:
                if random_choice == 1:
                    tem_words = tem_words + '不算很热，但也有点热啦。不太适合出去玩儿，不下雨的话，晚上倒是挺适合出去散步。也要记得今天的运动鸭！'
                elif random_choice == 2:
                    tem_words = tem_words + '我觉得这个温度还可以，勉强可以接受，但是也好热啊，但是一般这种天气，晚点天空超好看！可以欣赏，还有看完记得运动鸭！'
                else:
                    tem_words = tem_words + '可以出门，不会被热胡！但是也有点热了，太阳下山后还是可以安全出去的！晚上适合运动呦~'
            elif high_c >= 26:
                if random_choice == 1:
                    tem_words = tem_words + '咦，气温蛮舒服的嘛！热那么一丢丢，如果没有下雨的话，很适合出去玩哦！但是别光顾着玩哦，也要记得运动鸭！'
                elif random_choice == 2:
                    tem_words = tem_words + '这样的天气适合在太阳下山后欣赏夕阳，如果在我们学校的话，会看到超美的夕阳！不知道你那边怎么样？晚上可以告诉我鸭！还有运动别忘啦！'
                else:
                    tem_words = tem_words + 'emmmmmm,气温还行，感觉早晨和太阳下山后会很舒服！这两个时间点适合出游和运动呦~'
            elif high_c >= 20:
                if random_choice == 1:
                    tem_words = tem_words + '哈哈哈哈哈，气温真滴是很舒服了！要是没有下雨的话，适合出去蹦蹦跳跳哦。今天的运动可以放在下午哦，据说下午5-6点最适合运动了'
                elif random_choice == 2:
                    tem_words = tem_words + '这么爽的天气！我直接点吧，今天适合跑十公里！'
                else:
                    tem_words = tem_words + '这么好的气温，如果没有雨，是不是要计划一下去哪玩呢？但也别忘记运动呦~'
            elif high_c >= 15:
                if random_choice == 1:
                    tem_words = tem_words + '可能稍微有一丢丢的冷，要穿上长袖啦！也别忘了今天的运动哦，这种天气最适合运动啦。'
                elif random_choice == 2:
                    tem_words = tem_words + '最喜欢这种时候了，气温刚刚好，穿一件长袖就可以好好感受这个季节了！这种天气运动也很舒服！'
                else:
                    tem_words = tem_words + '出门要记得穿上长袖还有长裤子！如果没下雨，适合下午运动啦！'
            else:
                if random_choice == 1:
                    tem_words = tem_words + '有一丢丢的冷，记得衣服要穿厚一点哦！到了运动的时间可不要偷懒鸭！'
                elif random_choice == 2:
                    tem_words = tem_words + '哇，真滴，写这个程序很累的，比如这里，我很累了，但是我还坚持写，我要亲亲我不管！'
                else:
                    tem_words = tem_words + '这种温度，最适合盖好被子，躺在床上了！享受一会儿就起来啦，不要赖床哦，小懒猪！'
        else:
            if low_c < -10:
                if random_choice == 1:
                    tem_words = tem_words + '天呐，怎么会这么冷的一天！记得要穿的厚厚的，看起来胖一点没关系啦，暖暖的最重要！如果下雪的话，今天就不要跑步啦！'
                elif random_choice == 2:
                    tem_words = tem_words + '太冷啦，太冷啦！一定要穿的厚厚哦，不要把自己冻着啦！下雪的话，要注意小心脚下鸭！运动的话，不要出太多汉，不然好难受的。'
                else:
                    tem_words = tem_words + '这种温度，最适合盖紧被子，躺在床上了！享受一会儿就起来啦，不要赖床哦，小懒猪！'
            if low_c < -5 :
                if random_choice == 1:
                    tem_words = tem_words + '好冷好冷啊！记得套上暖暖的毛衣~。还要记得今天的运动呦！'
                elif random_choice == 2:
                    tem_words = tem_words + '好冷呀，想到我会不会让你温暖一点点勒~嘿嘿嘿，起床啦，这种天气，我知道你肯定要赖床了。'
                else:
                    tem_words = tem_words + '这种温度，最适合盖紧被子，躺在床上了！享受一会儿就起来啦，不要赖床哦，小懒猪！'
            if low_c < 0 :
                if random_choice == 1:
                    tem_words = tem_words + '好冷鸭!你不会现在还没有穿秋裤吧！没穿的话要打你PP！还有别忘了今天的运动鸭！'
                elif random_choice == 2:
                    tem_words = tem_words + '最低温度低于0度了，要注意照顾好自己，穿的暖和一点哦！'
                else:
                    tem_words = tem_words + '蛮冷的啊！穿的厚厚的哦！多喝热水暖暖身子，给你买的保温杯要一直接满水哦~'
            if low_c < 5 :
                if random_choice == 1:
                    tem_words = tem_words + '秋裤要拿出来放在身边，这种天气就差不多要穿了,刚刚好暖暖的，不过运动的时候，秋裤还是要脱掉'
                elif random_choice == 2:
                    tem_words = tem_words + '容易感冒的季节，要保护好自己哦！要穿的暖暖哒！'
                else:
                    tem_words = tem_words + '有点微冷，建议多想想我，会暖和很多，嘿嘿嘿~'
            else:
                if random_choice == 1:
                    tem_words = tem_words + '有一丢丢冷哦，穿好外套，要照顾好自己，别让自己感冒啦！也别忘了今天的运动鸭！'
                elif random_choice == 2:
                    tem_words = tem_words + '这几天感冒的人应该特别多，记得多喝热水！还有按时运动，运动多了，真的感冒就离得远远的！'
                else:
                    tem_words = tem_words + '有点微冷，建议多想想我，会暖和很多，嘿嘿嘿~'
        return tem_words 	

    def get_aqi_words(self,aqi):
        aqi_words = f'还有空气指数大概是{aqi},'
        aqi = float(aqi)
        random_choice = random.randint(1, 3)
        if aqi >= 200:
            if random_choice == 1:
                aqi_words = aqi_words + '天呐，这污染强度，建议不要呼吸！一定记得要戴口罩！'
            elif random_choice == 2:
                aqi_words = aqi_words + '卧槽，空气有毒，慎吸！！！！！！'
            else:
                aqi_words = aqi_words + '戴好口罩，做好防毒措施！'
        elif aqi >= 150:
            if random_choice == 1:
                aqi_words = aqi_words + '欧呦，空气不太好，一点都不适合跑步哦,有口罩的话，尽量带着口罩啦！'	
            elif random_choice == 2:
                aqi_words = aqi_words + '不适合室外运动！！！谨记！'
            else:
                aqi_words = aqi_words + '记得带上口罩鸭！'
        elif aqi >= 100:
            if random_choice == 1:
                aqi_words = aqi_words + '轻度污染的一天，不要在外面运动啦！'
            elif random_choice == 2:
                aqi_words = aqi_words + '不太适合在室外运动哟~'
            else:
                aqi_words = aqi_words + '能少吸几口就少吸几口吧！'	
        elif aqi >= 50:
            if random_choice == 1:
                aqi_words = aqi_words + '空气还行，可以正常呼吸哦！'
            elif random_choice == 2:
                aqi_words = aqi_words + '比较适合在室外运动哦~'
            else:
                aqi_words = aqi_words + 'emmmmm，是可以正常呼吸的一天'
        else: 
            if random_choice == 1:
                aqi_words = aqi_words + '哈哈哈哈哈，这么好的空气，建议出去的时候多吸几口！'
            elif random_choice == 2:
                aqi_words = aqi_words + '今天超级适合在室外运动哟~'
            else:
                aqi_words = aqi_words + '今天的空气多吸几口会不会醉了?'	
        return aqi_words

    def get_weather_info(self, dictum_msg='', city_code='101030100', start_date='2018-01-01',
                         sweet_words='From your Valentine'):
        '''
        获取天气信息。网址:https://www.sojson.com/blog/305.html
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
            random_choice = random.randint(1, 6)
            fx = today_weather.get('fx')
            fl = today_weather.get('fl')
            if random_choice == 1:
                wind = f'昨晚夜观天象，天象显示今天的风会是{fx}，强度大概{fl}。'
            elif random_choice == 2:
                wind = f'强度{fl}的{fx}今天将向你吹来。'
            elif random_choice == 3:
                wind = f'今天吹的是{fx}，强度{fl}。'
            elif random_choice == 4:
                wind = f'吹呀吹，今天吹的是{fx}呦~，强度{fl}。'
            elif random_choice == 5:
                wind = f'{fl}的{fx}在天空盘旋。'
            else:
                wind = f'今天天空挂的是强度{fl}的{fx}。'

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
            random_choice = random.randint(1, 10)
            if random_choice == 5:
                #不加格言但是有土味情话的版本
                today_msg = f'{delta_msg}\n{notice}。\n{temperature}\n{wind}{aqi}\n\n{dictum_msg}'
            else:
                #不加格言和土味情话的版本
                today_msg = f'{delta_msg}\n{notice}。\n{temperature}\n{wind}{aqi}'
            #加格言版本
            #today_msg = f'{delta_msg}\n{notice}。\n{temperature}\n{wind}{aqi}\n\n{dictum_msg}\n{sweet_words if sweet_words else ""}'
            return today_msg
	
    
	
	

if __name__ == '__main__':
    # 直接运行
    # GFWeather().run()

    # 只查看获取数据，
    # GFWeather().start_today_info(True)

    # 测试获取词霸信息
    # ciba = GFWeather().get_ciba_info()
    # print(ciba)

    # 测试获取每日一句信息
    # dictum = GFWeather().get_dictum_info()
    # print(dictum)

    # 测试获取天气信息
    # wi = GFWeather().get_weather_info('sorry \n')
    # print(wi)
    pass

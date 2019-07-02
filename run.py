"""
程序运行入口
"""
from wechatHelpers.ChatManager import ChatManager

def run():
    """
    主程序入口
    :return: None
    """
    print('开始运行')
    chatManager = ChatManager()
    print('chatManager创建成功')
    chatManager.run()


if __name__ == '__main__':
    run()

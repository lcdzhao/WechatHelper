"""
程序运行入口
"""
from wechatHelpers import ChatManager

def run():
    """
    主程序入口
    :return: None
    """
    chatManager = ChatManager()
    chatManager.run()


if __name__ == '__main__':
    run()

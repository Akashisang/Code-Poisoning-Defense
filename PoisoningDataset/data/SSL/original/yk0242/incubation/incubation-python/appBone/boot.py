# -*- coding: utf-8 -*-

# test project using modules and pulling all trial elements together

from argparse import ArgumentParser
import os.path
from sys import stdout
import logging.config
import pygame

os.environ["KIVY_NO_ARGS"] = "1"  # necessary before kivy imports for custom args to work
from kivy.app import App
from kivy.resources import resource_add_path
from kivy.uix.screenmanager import ScreenManager, NoTransition
import kivy.logger

# === set up file logging ### must be called BEFORE other modules' imports!!! ###
logging.Logger.manager.root = kivy.logger.Logger  # cf http://stackoverflow.com/a/36109848/3799649
logging.config.fileConfig('common/logging.conf', disable_existing_loggers=True)  # set False for kivy logs
logger = logging.getLogger(__name__)

# --- フォントファイル等を階層依存無しに名称のみで呼び出せるように以下を実施
#     cf https://github.com/kivy/kivy/issues/4458 and watch for updates
resource_add_path(os.path.abspath(os.path.join(os.path.dirname(__file__), 'extlib', 'fonts', 'SourceHanSansJP')))
resource_add_path(os.path.abspath(os.path.join(os.path.dirname(__file__), 'extlib', 'fonts', 'SourceHanSerifJP')))
# ---
# --- import all subsystems to be used here ---
import top
from systools import *
from subsystema import *
# ---

pygame.mixer.init()

# ### constants to set ### #
DO_HTTPS_LOGGING = False   # ### True for production and https logging testing
DEBUG_MODE = False        # ### False for production
FILE_HANDLER = 'TimedRotatingFileHandler'  # remember to fix this if we change our FileHandler


def _init_logging():
    # --- set up https logging
    if DO_HTTPS_LOGGING and not DEBUG_MODE:
        import ssl
        https_ip = "192.168.1.2"
        logr = logging.getLogger()  # the ROOT LOGGER

        # create HTTPS handler and set level to INFO
        empty_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)  # insecure--only for testing purposes

        # ### NB remove context entry for python 3.4.2
        hh = logging.handlers.HTTPHandler(https_ip, 'https://' + https_ip + '/random/server_stub.php',
                                          method='POST', secure=True, credentials=None, context=empty_context)
        hh.setLevel(logging.WARNING)

        # add handler to root logger
        logr.addHandler(hh)
    # ---

    # --- allow for command-line setting of a verbose/debug flag
    #     cf http://stackoverflow.com/a/14098306/3799649
    parser = ArgumentParser(
        description='Description of main program'
    )
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    parser.add_argument("-d", "--debug", help="output debug messages", action="store_true")
    args = parser.parse_args()

    if args.verbose or args.debug:
        fh = _get_file_handler()
        if args.verbose:
            logging.basicConfig(level=logging.INFO)
            fh.setLevel(logging.INFO)
            logger.info("--- コンソールからログ出力レベルを INFO (--verbose) に設定しました。 ---")
        if args.debug:
            logging.basicConfig(level=logging.DEBUG)
            fh.setLevel(logging.DEBUG)
            logger.info("--- コンソールからログ出力レベルを (--debug) に設定しました。 ---")
    # ---

    # --- set levels to DEBUG in debug mode
    if DEBUG_MODE:
        logging.basicConfig(level=logging.DEBUG)
        fh = _get_file_handler()
        fh.setLevel(logging.DEBUG)
        logger.info("------- DEBUG_MODE でログ出力中 -------")
        sh = logging.StreamHandler(stdout)
        sh.setFormatter(logging.Formatter('%(asctime)s %(name)s(%(lineno)s) [:%(levelname)s:] %(message)s'))
        sh.setLevel(logging.DEBUG)
        logging.getLogger().addHandler(sh)  # DEBUG_MODE でも stdout に出力できるようにする
    # ---

    logger.info("loggerの初期化を行いました。")
# end init_logging


def _get_file_handler():
    """gets the currently used brand of FileHandler attached to the root logger
    raises ReferenceError if not found 
    """
    fh = None
    logr = logging.getLogger()
    for h in logr.handlers:
        if type(h).__name__ == FILE_HANDLER:
            fh = h
            break
    if fh is None:
        raise ReferenceError("目的のFile Handlerが見つかりませんでした。")
    return fh


class ProjNameApp(App):
    def build(self):
        global logger
        # --- add ALL screens to sm, the first being the top screen ---
        sm = ScreenManager(transition=NoTransition())
        # トップ画面
        sm.add_widget(top.TopScreen(name="top"))
        # システムツール関係
        sm.add_widget(sys_password.SysPasswordScreen(name="sys_password"))
        sm.add_widget(b_system_top.SystemScreen(name="system_top"))
        sm.add_widget(shutdown_rel.ShutdownScreen(name="shutdown_rel"))
        sm.add_widget(lang_change.LangChangeScreen(name="lang_change"))
        # サブシステムA関係
        sm.add_widget(b_sub_a_top.SubATopScreen(name="sub_a_top"))
        # ---
        return sm


if __name__ == "__main__":
    _init_logging()
    ProjNameApp().run()

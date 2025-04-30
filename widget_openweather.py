# import os
# import sys
# import time
# from typing import Dict
#
# import requests
# from flask import request, url_for
#
# from server import app
#
#
# class CacheItem:
#     def __init__(self, value, cb, duration=None):
#         self.value = value
#         self.cb = cb
#         self.duration = duration if duration is not None else 30 * 60
#         self.creation = time.time()
#
#     def is_expired(self) -> bool:
#         return self.creation + self.duration < time.time()
#
#
# CACHE: Dict[str, CacheItem] = {}
# APPID = os.environ["OPENWEATHER_APPID"]
#
#
# @app.route("/wdgt/<path:path>")
# @app.route("/wdgt//<path:path>")
# @app.route("/wdgt///<path:path>")
# @app.route("/wdgt////<path:path>")
# @app.route("/wdgt/////<path:path>")
# def wdgt(path):
#     global CACHE, APPID
#     path = path.lstrip('/')
#     cache_item = CACHE.get(path)
#     callback = request.args['callback']
#     if cache_item is None or cache_item.is_expired():
#         if not (cache_item is None):
#             print("expired!")
#         f = lambda x: x if x != 'myappid' else APPID
#         query = '&'.join(f'{key}={f(value)}' for key, value in request.args.items())
#         url = f'http://{path}?{query}'
#         print("url->", url)
#         req = requests.get(url)
#         ret = req.text
#         print("rqcb:", callback)
#         print("recv:", ret[:200])
#         if 'error' in ret:
#             print("weather error:", ret, file=sys.stderr)
#             return ret
#         print("callback in ret:", callback in ret, file=sys.stderr)
#         if callback in ret:
#             print("saving result!")
#             CACHE[path] = cache_item = CacheItem(ret, cb=callback)
#     else:
#         print("Using cached value..")
#         pre = ret = cache_item.value
#         print("orig:", ret[:200])
#         print("cccb:", cache_item.cb)
#         print("rqcb:", callback)
#         ret = ret.replace(cache_item.cb, callback)
#         print("orig:", ret[:200])
#         print("fail:", ret == pre)
#     return ret
#
#
# WIDGET = None
#
#
# @app.route("/widget.js")
# def widget_retrival():
#     global WIDGET
#     if WIDGET is None:
#         url = 'http://openweathermap.org/themes/openweathermap/assets/vendor/owm/js/weather-widget-generator.js'
#         req = requests.get(url)
#         WIDGET = req.text
#     domain = url_for('wdgt', path='')
#     return WIDGET.replace("u.urlDomain", f"'{domain}/'+u.urlDomain")

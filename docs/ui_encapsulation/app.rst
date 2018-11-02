.. _encap_app:

封装App
=====

======
App类概述
======

在demolib/app.py中封装你的应用App类DemoApp,实现App类的基本功能 :class:`qt4a.androidapp.AndroidApp` 类提供了常见功能，如检测安装包、等待窗口出现，关闭当前窗口等，用户需要声明自己的App类，继承于AndroidApp基类。

======
App类封装
======

我们仍以Demo App为例，完整代码见Demo工程。被测应用的基本App类继承于AndroidApp类，只需实现最基本的功能，如下::

   # -*- coding: utf-8 -*-
   
   from qt4a.androidapp import AndroidApp
   
   class DemoApp(AndroidApp):
       '''安卓Demo App类
       '''
       # 包名,必须定义
       package_name = 'com.qta.qt4a.demo'
   
       def __init__(self, device=None, clear_state=True, kill_process=True, net_type='wifi', start_extra_params={}):
           '''
           :param device: 设备实例
           :type device:  Device
           '''
           super(DemoApp, self).__init__(self.package_name, device)  #第一个参数传入主进程名，在demo app中，主进程名和包名相同
           self._start(clear_state, kill_process, start_extra_params=start_extra_params)
           
       def _start(self, clear_state=True, kill_process=True, start_extra_params={}):
           '''启动Android demo apk
           '''
           if kill_process == True:
               self.device.kill_process(self.package_name)  # 杀死已有进程
           if clear_state == True:
               self.device.clear_data(self.package_name) #清除包数据
           self.device.adb.start_activity('%s/%s.MainActivity' % (self.package_name, self.package_name), extra=start_extra_params)  
            
上述代码只实现了最基本的功能，你可以根据需要定义更多的接口。__init__函数中需要实现:

* 声明package_name属性，传入包名，AndroidApp类会去检查被测应用是否已安装。

* 调用基类的__init__函数，以便初始化操作得以执行，此处传入了参数主进程名和device对象。

* 杀死应用进程(kill_process调用),清除应用数据(clear_data调用),以便每次都会从应用的初始状态开始进入,这样可以知道每一步都会到达什么窗口界面，从而定义使用预期窗口。

* 启动应用(start_activity调用)。

启动应用时，需要传入要启动的Activity参数，如果你不清楚被测应用的启动Activity，你可以调用QT4A的接口::

    from qt4a.androiddriver.util import AndroidPackage
    package = AndroidPackage(r'D:\demo.apk')
    print (package.start_activity)
    print (package.package_name)

由上可知，应用的包名也可以同时读取出来。更多的包信息可以参考该类的接口文档获取。这样便实现了一个最简单的被测应用App类。

===========
App类功能自定义实现
===========

如果你在启动应用前需要自定义一些其他操作，可以再自行实现。例如你在启动应用前希望去连接WIFI,那么可以在调用_start接口前先进行连接WIFI操作::

   self._connect_network('wifi')
   self._start(clear_state, kill_process, start_extra_params=start_extra_params)

然后自行实现_connect_network接口，例如::

   def _connect_network(self, net_type):
   '''连接网络
   '''
      pass

所以请根据实际功能进行扩展开发。

======
App类使用
======

在用例中申请完设备后，即可开始实例化被测App，如下::

      app = DemoApp(device)
     
传入设备实例参数device，在__init__函数中会先对应用数据进行清除，杀死应用进程，再启动应用，保证应用都是从启动界面开始。实例化App后，App会启动，进入启动界面：

   .. image:: ../img/ui_encapsulation/app/login.png     

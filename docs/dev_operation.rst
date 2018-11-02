常见设备操作
======

在Android自动化过程中，避免不了的是对设备的各种操作，如获取当前窗口、发送按键、滑动窗口等，现针对常见的设备操作进行解析，更多的功能请参考接口文档。

=========
执行shell命令
=========

当本地安装了adb之后，就可以打开shell命令窗口执行各类命令，如获取设备信息，执行各种设备操作、访问各个目录文件等，QT4A中提供了统一的访问接口run_shell_cmd::

   device = self.acquire_device()
   device.run_shell_cmd('ls -l /data/local/tmp') #查看tmp目录下的文件信息
   device.run_shell_cmd('df')  #查看磁盘信息
   device.run_shell_cmd('getprop | grep model')  #获取设备的model信息

QT4A中使用该接口封装了很多常用操作，你可以优先使用QT4A中已经封装好的接口。如果在QT4A中找不到你所需要的操作，你还可以直接调用该接口进行你的操作。下文中的device对象也如该代码片段中实例化，不再重复。

如果你需要root权限或应用权限才能执行命令成功，而你的手机又未root，执行Device类的run_shell_cmd遇到权限问题的话，可以改为如下调用::

   app = DemoApp(device)
   app.run_shell_cmd('ls -l /data/data/com.qta.qt4a.demo')
   
如上，调用App类的run_shell_cmd的话，会区分当前手机是否root，来对应调用。所以你可以根据实际自行决定调用Device类的还是AndroidApp类的run_shell_cmd接口。

====
点击屏幕
====

如果你不希望调用界面各个控件如TextView等封装的click接口去点击屏幕，你可以使用点击屏幕坐标的方式::

    screen_width,screen_heght = device.screen_size  #获取屏幕宽度、高度
    device.run_shell_cmd('input tap %d %d' % (screen_width/2, screen_heght/2))
   
这样你便实现了点击屏幕正中间的功能。

.. warning:: 通常情况下请优先使用QT4A各个控件类型提供的click接口去点击，只有在特殊情况下不方便使用该接口才改为点击屏幕固定坐标的方式。

======
发送虚拟按键
======

Android设备上有很多虚拟按键，如HOME键、BACK键等，QT4A封装了常见的按键，在用例中实例化App类后可以获得app对象::

   device = self.acquire_device()
   app = DemoApp(device)

然后可以模拟发送各类按键，如发送返回键::

   app.send_back_key()

发送HOME键::

   app.send_home_key()

发送ENTER键::

   app.send_enter_key()  
    
如有其他按键，你还可以调用send_key接口发送，如发送DEL键::

   from qt4a.androiddriver.util import KeyCode
   app.send_key(KeyCode.KEYCODE_DEL) 

====
滑动屏幕
====

有时候你需要针对屏幕进行滑动，而屏幕又没有ListView、ScrollView、ViewPager等控件(该类控件QT4A已封装了滑动相关接口)，你需要自行调用滑动屏幕的接口，例如若App类开头有一些广告页面，需要滑动才会消失，那么可以调用::

   screen_width, screen_height = device.screen_size
   x1 = screen_width / 4  
   x2 = screen_width*3 / 4
   y1 = y2 = screen_height / 2
   app.get_driver().drag(x1, y1, x2, y2)

这样便实现了水平滑动的操作，但不同界面滑动的坐标需要做不同的设置才能滑动成功,所以请根据实际产品功能设置坐标值。

.. note:: 如果是滑动ListView、ScrollView、 ViewPager等，请优先使用QT4A已经封装的滑动接口，不要自行再去调用drag接口。

==============
获取当前窗口Activity
==============

在用例编写过程中，我们常常需要知道当前窗口是什么，有可能应用会根据场景弹出不同的窗口，这个时候可以先判断当前窗口，再去实例化对应的面板类(我们在lib层定义的面板，如LoginPanel等)，就可以处理不确定窗口出现的场景::

   current_activity = device.get_current_activity()

即可获取当前窗口Activity，同时，这在需要等待一些目标窗口出现时十分有用(有可能前序会有广告窗口的自动跳转，然后才出现目标窗口),假设你已经获得device类对象，如::

   import time
   current_activity = None
   timeout = 5
   time0 = time.time()
   while time.time() - time0 < timeout:
      current_activity = device.get_current_activity()
      if current_activity != LoginPanel.Activity:
          time.sleep(0.5)
      else:
          break
   else:
      raise RuntimeError('登录窗口未找到，当前窗口为%s' % current_activity)   

====
屏幕截图
====

在执行用例过程中，有些场景需要截图下来帮助分析，可以调用接口::

   device.take_screen_shot(pic_path) #pic_path传入保存到本地的路径
   
当然，QT4A在用例失败时也会截图保存App现场。如你还需其他截图，可自行调用。


   
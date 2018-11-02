.. _encap_activity:

封装Activity
==========

==========
Activity概述
==========

每个Android应用都包含多个窗口(Activity)，每个窗口可以封装成一个面板类，在lib库中实现，建议App中一个产品功能模块封装在一个py文件中，例如app的主面板相关作为一个py文件mainpanel.py，app的登录相关作为一个文件login.py，在文件中再具体实现多个相关类的UI封装。

==========
Activity封装
==========

封装的面板类需要直接继承于标准Window基类。声明的面板类一般如下:

* 继承于 :class:`qt4a.andrcontrols.Window` 。

* 声明Activity属性：这可以用控件探测工具探测得到

* 声明Process属性：如Process='com.qta.qt4a.demo:tools'，如果进程名和包名相同则可以省略该属性，当前登录界面就在主进程内，故可不声明Process属性。

* __init__函数需要传入app实例作为参数

* 在__init__接口中调用self.updateLocator接口，来声明窗口内的各个控件元素，如登录按钮、帐号等，控件是使用QPath进行封装定位的，如何封装可参考《:ref:`encap_qpath`》一节。

* 面板类中可以封装该面板内的各功能函数，如登录功能等。

根据以上原则，demolib/login.py中实现的 **LoginPanel类** 如下::

      # -*- coding: utf-8 -*-
      
      from qt4a.andrcontrols import Window, Button, EditText, TextView
      from qt4a.qpath import QPath
      
      class LoginPanel(Window):
          '''登录界面
          '''
          Activity = 'com.qta.qt4a.demo.MainActivity'  # 登录界面
      
          def __init__(self, demoapp):
              super(LoginPanel, self).__init__(demoapp)
              self.updateLocator({'帐号': {'type': EditText, 'root': self, 'locator': QPath('/Id="editAcc"')},
                                  '密码': {'type': EditText, 'root': self, 'locator': QPath('/Id="editPwd"')},
                                  '登录': {'type': Button, 'root': self, 'locator': QPath('/Id="btnLogin"')},
                            
                                  })
      
          def login(self, acc, pwd):
              '''登录界面
              '''
              self.wait_for_exist()
              self.Controls["帐号"].text = acc
              self.Controls["密码"].text = pwd
              self.Controls["登录"].click()

一般来说，app随着网络环境、手机性能等不同因素的影响，打开不同页面耗时不同，所以必要时可以加上一些等待逻辑，如login函数中，首先调用self.wait_for_exist()等待登录窗口出现再进行操作。当然，qt4a底层本身也已针对这些情况做了适配，所以封装时未必一定需要该类等待，如果你的应用打开某个页面很慢，或等待某个控件加载很耗时，例如超过10s，才需要自己再加等待出现逻辑。

获取控件的方式是self.Controls[xx],该调用返回的对象是你在self.updateLocator接口中声明的各个类型的对象,如self.Controls["帐号"]返回的是EditText类对象，再调用其对应接口即可。详细控件封装使用方式可参考《:ref:`encap_native_control`》一节和《:ref:`encap_defined_control`》一节。

==========
Activity使用
==========

定义好面板类后，在用例中可以实例化面板类，并调用对应的功能接口::

   login_panel = LoginPanel(app)
   login_panel.login('admin', 'admin')

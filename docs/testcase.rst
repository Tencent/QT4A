.. include:: links/link.ref

快速入门
====

====
测试项目
====

测试用例归属于一个测试项目，在设计测试用例之前，如果没有测试项目，请先参考《|project|_》。按照该指引你可以创建一个例如名称为"demo"的项目。

====
测试环境
====

你可以选择你习惯的开发环境，如Eclipse、命令行执行、PyCharm等，推荐使用Eclipse开发环境。

======
安装QT4A
======

通过pip安装的方式安装QT4A::

   pip install qt4a

====
Demo工程
====

可于github(`<https://github.com/qtacore/QT4ADemoProj>`_)上下载demo工程，其中包括demo测试项目源码和demo apk，本文的分析基于该demo工程进行。

=======
安装被测App
=======

-------
手机已root
-------

手机已root的情况下，下载提供的demo apk到本地(如保存为D:\\demo.apk)，本文档以测试该App的登录功能为例讲解如何编写一个基本的QT4A用例。可以通过在控制台窗口执行命令以安装该应用::

   adb install D:\demo.apk

该被测App的功能是：只要你帐号密码不为空，就会跳转到登录成功界面，若帐号或密码为空，则跳转到登录失败界面。

-------
手机未root
-------

如果你的手机未root，请先将你的apk进行重打包(假设你已经按照《:ref:`qt4a_setup`》一节装好了jdk)，再安装重打包后的apk,重打包方法如下::

   from qt4a.apktool.repack import repack_apk
   apk_path = r'E:\1.apk'
   print (repack_apk(apk_path))

耐心等待执行完成，会打印出一个重打包后的apk路径，到该路径下拷贝重打包后的apk,安装重打包后的apk即可。

----------
安装release包
----------

上面都是安装的debug包，给出的demo apk也是debug版本的，未经过混淆。建议安装debug版本的App,通常debug版本的App没有做过混淆，QT4A可以顺利找到控件。如果你安装的是release版本的App，做过混淆，则需把对应的混淆还原文件push到手机tmp目录下，文件名为/data/local/tmp/{{package_name}}_map.txt，其中{{package_name}}是你的应用包名::

   $ adb push D:\demo_map.txt /data/local/tmp/com.qta.qt4a.demo_map.txt

执行成功后可以看到文件已在目标目录:

   .. image:: ./img/testcases/map.png   
   
当然，提供的demo app是debug包，所以无需执行上述命令，只是举例说明release包的安装方法。

======
理解UI结构
======

Android的UI结构涉及三个概念，应用(App)、窗口(Window)、控件(Control):

* **App:** 每一个Android应用是一个App，这是我们开发出来待测试的应用程序，安装在我们的手机上，App基类由 :class:`qt4a.androidapp.AndroidApp` 实现。

* **Window:** 一个App包含多个Window(Activity)，Window表示一个被测的用户窗口界面，一般和Android应用中的Activity对应，我们需要对每个窗口进行定义，以测试目标窗口，窗口基类由 :class:`qt4a.andrcontrols.Window` 实现 。

* **Control:** 一个Window包含多个Control,即每一个窗口包含了多个控件元素，QT4A中用QPath来查找定位控件，以便对各个控件进行操作。Android中控件类型较多，相应地QT4A中实现了对各个类型的封装，如 :class:`qt4a.andrcontrols.TextView` ,  :class:`qt4a.andrcontrols.Button` 等，全部控件类型请阅读接口文档。

所以我们需要以QT4A中的实现为基础，针对三种UI元素分别进行封装使用。
 
=======
第一个测试用例
=======

开始写QT4A的第一个用例前，请先参考《|testcase|_》熟悉用例基本结构。由开头可知，我们已经创建了一个名为demo的项目，其中，

- demotest:测试用例集合，这里存储所有测试用例的脚本。
- demolib:测试业务库，这里存放所有测试业务lib层的代码,使得不同用例可以复用demolib的接口。
- settings.py:项目配置文件，可以配置你所需要的项。

demotest目录下会自动生成hello.py文件，我们在该文件实现第一个简单的测试用例。
 
demotest/hello.py中实现 **HelloTest类**::

   # -*- coding: utf-8 -*-
   
   '''示例登录测试用例
   '''
   
   from demolib.demotestbase import DemoTestBase
   from demolib.demoapp import DemoApp
   
         
       '''示例登录测试用例
       '''
       owner = "Administrator"
       timeout = 5
       priority = DemoTestBase.EnumPriority.High
       status = DemoTestBase.EnumStatus.Design
       
       def run_test(self):
           #--------------------------
           self.start_step('1、登录Android demo')
           #--------------------------
           acc = "admin"
           pwd = "admin"
           device = self.acquire_device()
           app = DemoApp(device)
           app.login(acc, pwd)
           self.waitForEqual('当前Activity为：com.qta.qt4a.demo.HomeActivity', app.device, 'current_activity', 'com.qta.qt4a.demo.HomeActivity')
   
   if __name__ == '__main__':
       HelloTest().debug_run()

            
.. warning:: 在测试用例中强烈建议只调用lib封装的接口和断言操作，以保证App UI变化时用例的逻辑不需要改动，只需要统一修改lib层接口，这样也能保持用例的简洁易懂。

.. note:: 一个基本的用例结构如上述代码所述，用例名命名为XXTest，每个用例必须实现run_test接口。

-------
继承于测试基类
-------

首先，用例继承于DemoTestBase测试基类，针对测试基类的封装可以参考《:ref:`encap_testbase`》一节。然后在run_test接口中编写你的测试用例。

----
获取设备
----

在用例中首先需要获取连接在你PC上的Android设备，利用以下代码::

   device = self.acquire_device() #申请Android设备，返回设备对象device
      
即可返回设备对象，此处参数未指定特定设备，会自动选择插在你电脑上的其中一台设备。返回类型为 :class:`qt4a.device.Device` ，所以你可以查找该类的接口并进行使用。

.. note:: 如果在命令行中执行adb devices命令，返回结果没有device字样出现，证明手机连接不正常，则会抛出异常，需重新连接手机后再试。

-------
实例化App类
-------

申请到设备后，开始实例化你的应用App类，针对DemoApp的封装可以参考《:ref:`encap_app`》一节::

   app = DemoApp(device)   

------
业务逻辑操作
------

在用例中只调用业务逻辑接口，而业务逻辑实现在demolib库下的各个文件中。本测试用例是为了验证登录功能是否如预期，故此处调用::

   app.login(acc, pwd)

从实现::

    def login(self, acc, pwd):
     '''登录demo
     '''
        from login import LoginPanel, HomePanel
        login_panel = LoginPanel(self)
        login_panel.login(acc, pwd)
        self.wait_for_activity(HomePanel.Activity, 10)

可以看出，该函数调用了LoginPanel的login函数，即输入帐号密码并点击登录的功能，预期是跳转到登录成功的页面。所以接下来验证测试功能点，是否是跳转到了目标页面::

      self.waitForEqual('当前Activity为：com.qta.qt4a.demo.HomeActivity', app.device, 'current_activity', 'com.qta.qt4a.demo.HomeActivity')
      
当然，此处只是验证跳转到的目标Activity对不对，如果你要做更细致的判断，例如判断目标页面的提示语是否正确，可以继续封装。

本测试用例比较简单，所以只有一个步骤， 如果业务逻辑更加复杂，可以继续往下写self.start_step('2、验证xx功能')等。  至此，一个基本的用例就完成了。此时app界面如下:
   
   .. image:: ./img/testcases/login_add_acc.png     

   .. image:: ./img/testcases/login_success.png    

.. note:: 此处正好将login接口封装在DemoApp类中，所以可以直接调用，一般把登录、登出函数放在应用App类中实现，其他功能逻辑不建议放入应用App中，以免App类显得冗余。其他功能逻辑可放各个面板类中，在用例中直接声明面板类，并调用其接口即可。

而login接口中实际是去调用封装好的窗口类LoginPanel的接口函数，针对登录窗口的封装可以参考《:ref:`encap_activity`》一节。




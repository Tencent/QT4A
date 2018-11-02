.. include:: ../links/link.ref

.. _encap_testbase:

封装测试基类
======

======
测试基类概述
======

QTAF中实现的测试基类《|qtaf-testcase|_》提供了很多功能接口，如环境准备和清理、断言、日志相关等功能,详细见测试基类的相关说明。QT4A中的测试基类AndroidTestBase重载了QTAF提供的测试基类，复用其功能，并扩展Android需要的特定功能，如配置Android设备HOST,保存logcat或qt4a日志等。

======
测试基类封装
======

目前qt4a的测试基类 :class:`qt4a.androidtestbase.AndroidTestBase` 已经实现了Android需要的常用功能。你可以在demolib/demotestbase.py中封装你的测试基类DemoTestBase，并且该类继承于AndroidTestBase,即可使用AndroidTestBase中已有功能，同时可重载各个接口扩展针对你测试项目的自定义的功能。例如可如下使用::
      
      # -*- coding: utf-8 -*-
      '''示例测试基类
      '''
      
      from qt4a.device import Device
      from qt4a.androidtestbase import AndroidTestBase
      
      class DemoTestBase(AndroidTestBase):
          '''demo测试用例基类
          '''
      
          def post_test(self):
              '''清理测试用例
              '''
              from qt4a.androiddriver.util import logger
              logger.info('post_test run')
              super(DemoTestBase, self).post_test()
              Device.release_all_device()  # 释放所有设备
              logger.info('postTest complete')
          
          def acquire_device(self, type='Android', device_id='', **kwds):
              '''申请设备
              
              :param type: 申请的设备类型，目前尚未使用
              :type type:  string
              :param device_id: 申请的设备ID，默认不指定设备ID
              :type device_id:  string
              '''
              device = super(DemoTestBase, self).acquire_device(device_id, **kwds)
              device.adb.start_logcat([])
              return device
 
即可实现测试用例的环境准备或环境清理功能。除了以上封装的基本功能，你可能还需重载其他接口，如:

* 自定义被测应用的crash提取规则，如果logcat日志中有匹配到这里定义的规则，相关的crash日志将会被单独提取出来，供分析。详细请参考 :ref:`extract_crash` 一节::

   def extract_crash_by_patterns(self):  
   
* 每个步骤前自定义一些操作，例如每个步骤前都打印出时间戳，看出每个步骤耗时等，可以重载下面接口::

   def start_step(self, step):

等等，更多参考QTAF和QT4A接口文档。

.. warning:: 重载基类各个接口时，必须显式调用基类的函数，以免基类的逻辑无法被执行到。

======
测试基类使用
======

在用例中将该类作为测试用例的基类::
      
      class HelloTest(DemoTestBase):
      
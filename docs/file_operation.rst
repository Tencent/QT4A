日志图片操作
======

========
查看QT4A日志
========

在用例执行过程中，qt4a会生成详细的log并保存在本地，供用例失败时分析原因，其日志保存在:

* Win32: 保存在%APPDATA%目录下的qt4a文件夹中
* linux: 保存在HOME目录下的qt4a文件夹中

==========
logcat日志操作
==========

--------
启动logcat
--------

在用例开始时会去申请Android设备(调用项目测试基类的acquire_device接口)，在其中调用start_logcat接口，则会启动logcat日志的生成，如下::

   from qt4a.androidtestbase import AndroidTestBase
   class DemoTestBase(AndroidTestBase):
       '''demo测试用例基类
       '''
       
       def acquire_device(self, type='Android', device_id='', **kwds):
           device = super(DemoTestBase, self).acquire_device(device_id, **kwds)
           device.adb.start_logcat([])
           return device
           
所以，在用例中调用self.acquire_device()就会开始logcat日志的监控了。

.. note:: 下文对logcat的操作都是建立在你开启了logcat的前提上。

----------
查看logcat日志
----------

在AndroidTestBase类的post_test接口中，会把logcat日志保存到当前用例所在目录下。同时在控制台会打印出logcat日志路径,如下::

   INFO: logcat日志
      设备:d012se304：D:\proj\AndroidDemoTest\demotest\LoginTest_d012304_1539931489.log

可以在用例执行结束后查看logcat日志，来分析用例失败原因等。

.. _extract_crash:

----------------
从logcat提取crash日志
----------------

如果你希望自动抓取logcat中的crash日志，以便分析应用crash原因，除了qt4a定义的一些系统crash类型外，你还可以自定义crash提取规则,实现如下::

   class DemoTestBase(AndroidTestBase):
       '''demo测试用例基类
       '''
       def extract_crash_by_patterns(self):  
           """
               #用户定义的crash规则
               @return: 返回规则列表
           """
           
           self._target_crash_proc_list = [r'com\.qta\.qt4a\.demo.*']  # 要提取crash，必须对该变量赋值你所关心的进程，用正则表达式,关心多个应用则写多个正则
   
           # pattern_list中的每一个元素是一个二元组(tag_regex, content_regex)。
           # qt4a的logcat日志格式基本是"[com.qta.qt4a.demo(21679)] [2017-01-04 15:44:30.516] E/crash(21679): com.qta.qt4a.demo in current activity is crashed."样式。
           # 其中tag="crash", content="com.qta.qt4a.demo in current activity is crashed.",这2个标签都支持正则。
           # 如果你希望logcat日志中存在该类日志，则判定为crash，那么此时可添加pattern_list.append((r".*", r'.*com\.qta\.qt4a\.demo.* is crashed\.'))。
           pattern_list = []                           
           pattern_list.append((r'.*', r'.*com\.qta\.qt4a\.demo.* is crashed\.'))  # crash规则一，只是举例的crash规则，实际根据App来定
           pattern_list.append((r'StatisticCollector', r'getCrashExtraMessage\s+isNativeCrashed.*')) #crash规则二，只是举例的crash规则，实际根据App来定
           #你还可以继续添加其他crash规则
           
           return pattern_list

通过在项目测试基类的extract_crash_by_patterns接口中自定义你的应用crash规则(规则支持正则匹配),用例执行期间如果logcat日志内容中匹配到你定义的规则，则会在用例执行完成时，在控制台窗口打印出保存的crash日志的路径。

------------
读取logcat日志内容
------------

在用例执行过程中，你也可能需要读取logcat日志内容，以判断某些逻辑是否正常,那么在你申请到设备后，可以调用设备类的read_logcat接口，如下::

    def run_test(self):
        device = self.acquire_device()
        # UI operation
        err_msg = r'.*failCode:.* errorMsg:.* service:.*' 
        log = self.device.read_logcat('crash', 'com.qta.qt4a.demo', err_msg)
        # other operation
       
如上，可以调用read_logcat接口读取出最近一条或所有满足规则的日志，read_logcat的第一个参数传入tag，可传入正则，第二个参数是行日志的进程名，第三个参数是行日志的content，可传入正则。

====
手机日志
====

在用例执行过程中，随着App的自动操作，在手机目录中也可能产生App生成的日志，假如你需要这些日志，可以从手机中pull出来到PC上，在每个用例的开始会通过接口申请设备::

   device = self.acquire_device()
   
返回了一个device实例，然后可以调用devcie实例的接口把日志提取到PC上，如::

   device.pull_file('/sdcard/demo_logs/log.txt', 'tmp_log.txt')

tmp_log.txt也可以传入保存的全路径，即可把手机日志提取到PC。其他类型文件的提取也可调用该接口。如果是需要拷贝文件夹，则可以调用pull_dir接口，详细见接口文档。

==========
日志作为测试结果附件
==========

我们本地会生成一系列日志，QT4A日志，logcat日志，或App本身产生的日志，这些日志如果需要作为测试结果附件，可以达到:

* 本地调试:控制台显式地显示日志信息及路径

* 远程执行任务: 日志会一并上传到报告平台展示出来

只需要在用例中或测试基类(如DemoTestBase)的接口(例如post_test接口)中调用::

   phone_files = {'device_id': 'D:\testcase\phone_log.txt'}
   self.test_result.info('手机日志', attachments=phone_files)
   
====
图片操作
====

有时测试用例需要准备一些手机环境，如需要使得手机系统图库中有照片，在App中实现相关图片功能时才能选择图片来使用测试。所以需要我们push图片到手机中去，可以如下::

   device = self.acquire_device()
   dst_path = '/sdcard/dcim/demo_pic_folder/1.png'
   device.push_file(r'D:\1.png', dst_path)   
   device.refresh_media_store(dst_path) #刷新媒体库

push成功的话可以在手机路径下查看到图片:

   .. image:: ./img/file_operation/push_png.png
   
请注意，在push_file完成后，还需要调用接口refresh_media_store来刷新系统图库，使得我们push到手机的图片能及时在系统图库中显示。然后你再声明App，并进行你的业务逻辑操作，在业务逻辑中需要选择图库中的图片则不会出现没有任何图片可选的情况，保证了用例的稳定性。
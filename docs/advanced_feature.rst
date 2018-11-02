高级特性
====

QT4A中有部分功能是不常需要用到的，不过特定场景下可以使用的，列举如下。

======
禁止窗口弹出
======

有的应用，会不定期弹出特定窗口(是应用定义的窗口，不是系统弹窗)，这些时机无法把握，也就无法在用例中特定时机进行处理。这个时候，如果该窗口不是我们的测试点，可以在项目App类屏蔽该窗口弹出::

   class DemoApp(AndroidApp):
       def __init__(self, device=None, clear_state=True, kill_process=True, net_type='wifi', start_extra_params={}):
           import time
           super(DemoApp, self).__init__(self.process_dict['Main'], device)
           #other operation
           self._start(clear_state, kill_process, start_extra_params=start_extra_params)
           
       def _start(self, clear_state=True, kill_process=True, start_extra_params={}):
           '''启动Android demo apk
           '''
           # 启动Activity的相关代码，此处省略，详细见Demo样例
           #接下来新增禁止窗口弹出逻辑
           self.set_demo_ads_activtiy_popup()
   
       def set_demo_ads_activtiy_popup(self, popup=False):
           '''设置广告页面是否可以弹出
           '''
           self.set_activity_popup('com.xx.xxActivity', popup)  #第一个参数是Activity名

假设在应用中，不定期会弹出广告窗口，可以按上面调用set_activity_popup接口禁止弹出，由于Demo App实际没有什么广告窗口，所以这里随意指定了个Activity名。

该接口并不是任何场景都能用的，

* 如果你要禁止的Activity，有不同的窗口页面对应，那么你会把其他正常需要弹出的页面也屏蔽掉，所以需要这个Activity只对应了广告这个窗口，才可使用。
* 这个接口不能作用于非App内页面，如一些系统弹框等，该接口不适用。
* 并不是App类任意页面都可以随意禁用掉，如果页面间有关联，有可能影响其他功能逻辑，所以请根据实际，需要且可用时才使用该功能。

====
监控任务
====

如果在应用中，不定期会弹出一些窗口，且这类窗口你希望禁用掉，但由于该窗口与其他你不希望禁用掉的窗口有相同的Activity名，所以不能直接按上面禁止窗口弹出的方法处理，此时你可以建个监控任务，监控到需要点掉的窗口，再去处理::

   class DemoApp(AndroidApp):
       def __init__(self, device=None, clear_state=True, kill_process=True, net_type='wifi', start_extra_params={}):
           import time
           super(DemoApp, self).__init__(self.process_dict['Main'], device)
           #other operation
           self._start(clear_state, kill_process, start_extra_params=start_extra_params)
           
       def _start(self, clear_state=True, kill_process=True, start_extra_params={}):
           '''启动Android demo apk
           '''
           # 启动Activity的相关代码，此处省略，详细见Demo样例
           #接下来新增应用启动后检测无用窗口
           self.add_monitor_task(self.detect_invalid_activity)
   
       def detect_invalid_activity(self):
           '''检测不想要弹出的窗口
           '''
           current_activity = self.device.get_current_activity()
           if current_activity == 'xx.xx.upgradeActivity':
               self.send_back_key()
           elif current_activity == 'xx.xx.adviseActivity':
               #定义该面板，并点击面板中的例如关闭按钮关闭页面。例如：
               # advise_panel = AdvisePanel(self)
               #if advise_panel.Controls['关闭推荐'].exist():
                  #advise_panel.Controls['关闭推荐'].click()
               pass
           #……
        
如上，调用AndroidApp类提供的add_monitor_task接口，可以启动监控线程监控不期望弹出的窗口。当有监控线程监控的窗口弹出时，可以例如判断该窗口是否有特定按钮存在，如果有，就是需要关闭的窗口，可以点击关闭按钮关闭，如果没有，这个窗口就不是该监控线程需要处理的。当你需要停止监控时，可以调用AndroidApp类的stop_monitor接口停止监控。 

.. note:: 监控线程监控是有时延的，因为其是每间隔一段时间才去判断一次是否有窗口需要处理，所以只有在窗口不定期弹出需要处理掉才使用监控线程的方式。

======
系统授权弹窗
======

在Android6.0及以上系统，发现即使root过的机型，也还是无法关闭系统授权弹框，此时可以尝试调用如下接口grant_all_runtime_permissions::

   class DemoApp(AndroidApp):
       def __init__(self, device=None, clear_state=True, kill_process=True, net_type='wifi', start_extra_params={}):
           import time
           super(DemoApp, self).__init__(self.process_dict['Main'], device)
           #other operation
           self._start(clear_state, kill_process, start_extra_params=start_extra_params)
           self.grant_all_runtime_permissions()
   
调用该接口且生效的话，用例执行过程中就不再会弹出授权提示框，使用例可以正常执行完成。当然，该接口不适用于非root机型。非root机型的系统弹框需要再自行关闭。
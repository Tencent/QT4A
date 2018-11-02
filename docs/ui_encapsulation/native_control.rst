.. _encap_native_control:

封装原生控件
======

Android系统中提供了丰富的控件类型供使用，如TextView,ListView, ScrollView, Button等，我们简称为原生控件，QT4A在Python层也对这些控件的自动化做了封装，以供使用。当然，有时候这些类型还不足以满足用户的需求，用例可以再重载定义新的更为复杂功能更丰富的控件类型，我们简称为自绘控件，这类控件暂不在本篇文档讨论范围内。

======
控件基本用法
======

我们知道，一个简单的控件定义如下::

   class LoginPanel(Window):
       '''登录界面
       '''
       Activity = 'com.qta.qt4a.demo.MainActivity'  # 登录界面
   
       def __init__(self, demoapp):
           super(LoginPanel, self).__init__(demoapp)
           self.updateLocator({'acc': {'type': TextView, 'root': self, 'locator': QPath('/Id="account"')}, })

定义完后，在LoginPanel的接口下调用方式如下::
   
    self.Controls['acc']

调用返回的对象的类型是我们定义的type，此处为TextView，再查看TextView类实现的属性和方法，可以看出TextView类下有text属性，那么可以读取text属性::

   print (self.Controls['acc'].text)
   
同时，TextView继承于View类，View实现了click方法，所以又可以调用方法::

   self.Controls['acc'].click()
   
当然，从实现上，acc控件没有实现点击触发逻辑，所以可以根据实际实现调用需要的接口。

=============
样例:EditText类型
=============

我们以帐号控件为例，其类型是EditText::

   self.updateLocator({'帐号': {'type': EditText, 'root': self, 'locator': QPath('/Id="editAcc"')}, })
   
EditText类型的控件通常是一个文本输入框，可以让用户输入文本，从QT4A的实现中，可以看出EditText继承于TextView::

   class EditText(TextView):
  
而TextView中又实现了@text.setter装饰的接口text::
 
   class TextView(View):

    @text.setter
    def text(self, value):

所以对于文本框可以直接赋值::

   self.Controls['帐号'].text = "admin"

请注意，在赋值前，QT4A会先关闭软键盘以避免软键盘的干扰，调用了其disable_soft_input接口，所以你执行完用例后，如果发现软键盘无法调出，而你手动又需要使用的话，可以自行在手机设置中切换输入法，则会恢复输入法开启状态或重启手机。

====
其他类型
====

其他类型的使用也与上述的TextView、EditText用法类似，各个类型实现的属性和类型不同，只需根据实际调用不同的属性和接口即可。

.. include:: links/link.ref

Web自动化测试
========

========
Web自动化概述
========

QT4A使用了 |QT4W|_ 提供的Web自动化基础能力来支持Web自动化测试，以下两种模式均可支持:

* 纯网页开发的应用(Web App)
* 原生控件+网页混合开发的应用(Hybrid App)

开始本节学习前，请熟悉以下基础知识：

* 学习 |QT4W|_ 基础知识
* 根据 :ref:`qt4a_testcase` 一节实践QT4A的基本使用

======
安装QT4W
======

在安装了QT4A后，如果需要进行Web自动化测试，还需要通过pip安装的方式安装QT4W::

   pip install qt4w

=============
内嵌WebView基本结构
=============

本节以内嵌WebView为例，说明一个基本web用例该如何编写。Web页面涉及几个重要的概念，如WebView、WebPage、WebElement等:

* **WebView:** 是Android平台上一个特殊的Native View， 可用来显示网页，由 :class:`qt4a.andrcontrols.WebView` 实现。

* **WebPage:** 一个WebPage对应一个H5页面，包含多个Web控件元素，该类在QT4W库中提供实现 。

* **WebControl:** 是H5页面下的web控件元素，QT4W下实现了WebElement、FrameElement、InputElement、SelectElement等Web控件类型，大部分的Web控件都是WebElement类型，该类在QT4W库中提供实现 。
 
=======
Web测试用例
=======
 
你依然可从github下载 `Demo工程 <https://github.com/qtacore/QT4ADemoProj>`_。用例的基本结构、用例的native层封装，可见QT4A《:ref:`qt4a_testcase`》一节。本节主要介绍web页面的封装。

demotest/webview.py中实现 **WebViewTest用例**::

首先实例化包含native webview控件的面板DemoWebPanel，封装其webview控件并将其传给WebPage类(在该例中封装了DemoWebPage)作为参数::

     demo_webpanel = DemoWebPanel(app)
     demo_webpage = DemoWebPage(demo_webpanel.Controls["webview"])

webview控件是Android原生控件，像其他普通Android控件一样封装即可，如下::

   class DemoWebPanel(Window):
       '''Home界面
       '''
       Activity = 'com.qta.qt4a.demo.WebViewActivity'
       Process = 'com.qta.qt4a.demo'  #此时Process不写也可以，因为跟主进程一致
   
       def __init__(self, demoapp):
           super(DemoWebPanel, self).__init__(demoapp)
           self.update_locator({'webview': {'type': WebView, 'root': self, 'locator': QPath('/Id="sampleWebView"')},
                               })

webview控件的Type声明为WebView。

接下来就可以使用DemoWebPage类封装的各个Web控件了，如::

      self.assert_equal("标题应该是WebView Demo", demo_webpage.control("标题").inner_text , "WebView Demo")

中读取了Web页面的名为"标题"的控件的文本内容(inner_text属性即读取文本);而::

      demo_webpage.control("qt4a_source_code").click()

则是点击了封装的"qt4a_source_code"Web控件。最后验证点击后页面是否发生跳转，可以通过读取Web页面的url属性来判断，如下::

      self.wait_for_equal('页面发生跳转，url变为https://github.com/Tencent/QT4A', demo_webpage, 'url', 'https://github.com/Tencent/QT4A')

.. note:: 从上面可看出，Android原生控件获取方式为Controls["xx"],如demo_webpanel.Controls["webview"]，而Web控件的获取方式为control("xx")，如 demo_webpage.control("标题")，写时请注意区分control和Controls、小括号和中括号。

=========
WebPage封装
=========

用例中使用的DemoWebPage封装如下::

   class DemoWebPage(WebPage):
       '''Demo Web页面
       '''    
       ui_map = {'标题': XPath('//h2'),
                 'qt4a_source_code':{'type': WebElement,'locator': XPath('//div[@id="qt4a_code"]/a'),}
               #'qt4a_source_code':XPath('//div[@id="qt4a_code"]/a'), #如果type为WebElement也可直接简化为该写法，所以此时qt4a_source_code这么定义也可以
                 }

继承于WebPage基类，在ui_map字典中实例化该页面的Web控件。而Web控件的封装规则参考 |qt4w_webcontrol|_ 一节。那么在Android端，如何获取到Web控件的XPath进行封装呢？QT4A提供了AndroidUiSpy的控件探测工具进行获取。可从github下载 `AndroidUiSpy工具 <https://github.com/qtacore/AndroidUISpy/releases/>`_,并参考 `AndroidUiSpy使用文档 <https://github.com/qtacore/AndroidUISpy/blob/master/usage.md>`_ 。

====
用例执行
====

用例执行请参考《|qtaf-run|_》一节。用例执行后结果如下:

   .. image:: ./img/web_test/login.png
   
   .. image:: ./img/web_test/click_go_to_webview.png
   
   .. image:: ./img/web_test/click_web_btn.png
   
   .. image:: ./img/web_test/jump_to_new_page.png


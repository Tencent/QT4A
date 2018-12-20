.. include:: ../links/link.ref

.. _encap_qpath:

设计QPath
=======

====
使用场景
====

App中每个窗口包含多个控件元素，要对各个元素进行操作，需要首先使用QPath来标识各个元素。从demo实例中可以看出，最终是在面板类的__init__接口中调用::

   self.updateLocator({'帐号': {'type': EditText, 'root': self, 'locator': QPath('/Id="editAcc"')},
                            })

进行QPath的封装的，QPath的学习请先参考《|qtaf-qpath|_》。如上代码所示，在封装控件时还需要指定其type和root属性。

* **type:** 指定控件的类型，和Android中定义的控件类型相对应，如 :class:`qt4a.andrcontrols.TextView` 、  :class:`qt4a.andrcontrols.Button` 、 :class:`qt4a.andrcontrols.ListView` 等。目前QT4A已封装的全部类型见接口文档。
* **root:** 指定控件的父节点，指定父节点后，查找控件时，会先找到父节点，然后以父节点为根节点，从根节点开始查找目标控件,这对于你定义的QPath找到多个的情况非常有用，如果指定了父节点，就只会返回父节点下的节点，否则找到多个重复节点就会报错。 如果指定为self,则表示会从整颗控件树根节点开始查找目标控件。
* **locator:** 指定QPath，QPath的封装详见下文。

==============
QT4A支持的QPath属性
==============

QT4A目前支持的QPath关键字有Id、Text、Instance、MaxDepth、Visible、Type。同时支持全匹配(=)和正则匹配(~=)。以下通过AndroidUiSpy控件树探测工具抓取窗口控件树来一一说明用法,可从github下载 `AndroidUiSpy工具 <https://github.com/qtacore/AndroidUISpy/releases/>`_ ，并参考 `AndroidUiSpy使用文档 <https://github.com/qtacore/AndroidUISpy/blob/master/usage.md>`_ 。

----
Id属性
----

Id属性最常用，使用控件Id标识控件，首选。如果控件没定义(例如控件ID显示为None)，才选择其他属性进行定义。如下的帐号控件：

   .. image:: ../img/ui_encapsulation/qpath/id.png
   
可用Id定义::

   'acc': {'type': TextView, 'root': self, 'locator': QPath('/Id="account"')},

虽然type在探测工具中显示的是AppCompatTextView，不过由于其继承于TextView，可以直接声明为qt4a中 :class:`qt4a.andrcontrols.TextView` 已经实现的控件类型TextView。
   
------
Text属性
------

有时控件没有定义Id，但其是一个文本控件，text属性不为空，此时可用Text属性辅助定位，如下的控件:

   .. image:: ../img/ui_encapsulation/qpath/text.png
   
可用Text定义::

   'demo': {'type': TextView, 'root': self, 'locator': QPath('/Text="demo"')},
   
----------
Instance属性
----------

有时你想要定义一个控件下的第几个子控件，又没有直接的Id可以定位，可以借助Instance，如下，我们还是需要探测界面中的demo属性，假如不用Text定义，用Instance也可以定义：

   .. image:: ../img/ui_encapsulation/qpath/instance.png
  
可定义为::

   'demo': {'type': TextView, 'root': self, 'locator': QPath('/Id="action_bar"/Instance=0')},
   
.. note:: /表示控件树的不同层，例如/Id="action_bar"/Instance=0表示查找直接父节点Id为action_bar下的第一个直接子节点;而&&描述的是同一层的节点，如/Id="action_bar"&&Instance=0"表示查找的是第一个Id为action_bar的节点。在本控件树中，只有一个action_bar，所以表示的是这个action_bar自身，此时可省略Instance字段的声明了。

----------
MaxDepth属性
----------

有时你需要定义跨层的控件，例如M层定义后，接下来要定义第N层(M-N>1)的控件，如果一层一层定义下来比较费事，可以借助MaxDepth，即会搜索M层下的N层内的所有控件，假设我们仍然要定义Id为account的这个控件:

   .. image:: ../img/ui_encapsulation/qpath/maxdepth.png
   
借助MaxDepth的话可定义为::

   'acc': {'type': TextView, 'root': self, 'locator': QPath('/Id="LinearLayout02"/Id="account"&&MaxDepth="2"')},

加上MaxDepth，那么找到LinearLayout02节点后，除了查找它的直接子节点是否有account节点，还会再查找第二层的节点，最终在第二层找到目标节点。如果不加MaxDepth，那么只会查找LinearLayout02的直接子节点，找不到就报错了。

.. note:: 这里MaxDepth="2"的2是字符串写法，表示从上一个声明的节点下来，最多查找2层。

---------
Visible属性
---------

有时有多个控件，控件Id相同，Visible属性不同，可以借助Visible属性来指定目标控件，如下：

   .. image:: ../img/ui_encapsulation/qpath/visible.png
   
假如你要定义editPwd这个控件，而该控件树还有一个Id为editPwd，但Visible属性为False的控件，通过下面的定义::

   '密码': {'type': EditText, 'root': self, 'locator': QPath('/Id="editPwd"&&Visible="True"')},
   
就可以找到你要的目标控件了。当然，本控件树中，正好没有Id为editPwd,Visible为False的控件，所以此处的Visible属性省略也可以。

------
Type属性
------

type属性一般不建议使用，只有在上述几种方式还无法定义目标控件才使用。密码输入框这个控件(看Visible属性一节的控件截图)，假如借助Type来定义，可如下::


   '密码': {'type': EditText, 'root': self, 'locator': QPath('/Type="AppCompatEditText"&&Instance=1')},
   
由于当前控件树总共有2个type为AppCompatEditText的控件，我们要找的是第二个，所以加上Instance关键字来辅助定位。

.. note:: 在QPath中声明的Type字段需要写控件的真实类型AppCompatEditText，用于定位控件用，而不能简化为Python层定义的EditText。而上图声明的'type'字段声明的类型才是从包qt4a.andrcontrols中查找合适的类型EditText来用即可，以便后面调用该控件对应的方法和属性。

----
正则匹配
----

在上面的例子中，我们都是用全匹配的方式，即在QPath中都是用"="，如果要定义的内容有部分是变化的，可以考虑用正则匹配的方式，例如Text属性中提到的demo控件，如果前后有可能有别的变化的内容，可如下定义::

   'demo': {'type': TextView, 'root': self, 'locator': QPath('/Text~=".*demo.*"')},
   
.. note:: 从上面可以看出，同一个控件是可以有多种写法的，所以定义时应该选择最简洁的写法，不要不必要地复杂化。当需要多个字段辅助定义才能定位一个控件时，才进行结合使用。

============
QPath的root声明
============

以上的控件定义,root都声明为了self，因为没有复杂的控件树结构。如果复杂情况下需要先声明父控件，再在父控件下声明子控件::

   'LinearLayout_account': {'type': LinearLayout, 'root': self, 'locator': QPath('/Id="LinearLayout_account"')},
   'acc': {'type': TextView, 'root': 'LinearLayout_account', 'locator': QPath('/Id="account"')},
   
如上，会先找到LinearLayout_account节点，再去查找其下的account节点。
   
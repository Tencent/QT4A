.. include:: links/link.ref

.. _qt4a_setup:

使用前准备
=====

QT4A依赖QTAF模块，使用前请参考《|setup|_》一节。
   
=====
准备ADB
=====

你可以下载google官方提供的ADB安装即可。如果你电脑已经安装配置了Android Studio，那么ADB也已安装。在终端输入命令::

   $ adb version

可以看到显示adb版本，则代表adb安装成功。
   
===========
准备Android设备
===========

QT4A使用需要至少有一台Android设备。

1. 连接到PC

 手机需要通过USB连接到对应的PC，并安装相关的驱动，如驱动没有自动安装，可以使用腾讯“电脑管家”进行驱动安装。
 
2. 设置可以ADB调试
 
 修改手机的配置，打开“USB调试”功能。
 保证adb工具可以识别出来。
 可以通过adb工具检查设备是否连接和安装成功::

   $ adb devices
   List of devices attached
   3fr4343aa12   device
 
3. 如果你的手机是root过的设备，那么该步骤可跳过。如果你的手机未root，请先在你的电脑上安装jdk 64位，并配置环境变量，同时把bin目录下的jarsigner.exe加入到环境变量中，为后面重打包apk准备环境。

.. note:: 建议优先使用root过的设备，这样没有各类系统授权弹框的干扰，也无需重打包APK后再安装应用。


   
   



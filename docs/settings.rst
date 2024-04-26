QT4A配置项
=======

配置项可在项目根目录下的settings.py中进行配置。特别是对于一些QT4A库已经实现的功能，你直接在配置项中开启即可使用。

======
配置HOST
======

当用例需要在测试环境中才能顺利执行时，你可能需要对手机配置HOST，AndroidTestBase中已实现这样的功能。用例开始会调用到AndroidTestBase的acquire_device申请设备，在该接口中实现了HOST的配置。如果你想开启配置HOST的功能，只需要增加下面的配置项::

      QT4A_DEVICE_HOSTS="103.22.4.120 a.b.c.com\n103.12.4.120 c.d.com"
      
具体的HOST内容请修改为你测试的HOST，那么，在调用接口acquire_device申请到设备时，就会将你设置的HOST自动配置到手机环境中。同时，用例执行结束时，也会自动在测试基类的post_test中恢复Android设备的HOST环境。

======
配置WIFI
======

有时需要在特定WIFI下进行测试，这时可以配置需要连接的网络，如::

   QT4A_WIFI_SSID="wifi_name"
   QT4A_WIFI_PASSWORD="wifi_password"

那么在调用::

   device.enable_wifi()
   
接口时会尝试去连接wifi。不过高系统版本的非root手机的系统权限变得更加严格了，可能会由于权限弹框等问题自动连接失败。所以通常可以优先选择手动把wifi连接好，再跑自动化用例，这时可以不配置这两个配置项。
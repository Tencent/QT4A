# 测试桩插件

## 什么是测试桩插件

QT4A通过将测试桩注入到被测应用进程中，获取进程中的相关数据，如控件树信息等。但是有些情况下，用户也需要注入自己的代码，以获取自己期望的数据。QT4A测试桩提供了一种将用户指定的`dex`文件注入到被测进程中的能力，同时，借助于QT4A的通信通道，用户可以传输自己的数据，而不需要自己创建信道。

## 如何实现测试桩插件

测试桩插件本质上还是一个`dex`，可以使用`Java`语言编写。但是与普通的dex相比，它还是存在着一些差异。最主要的，就是它需要实现一个入口类，用来作为整个插件的执行入口。

```java
public class MyPlugin {
    private int handleRequest(String arg){
        // do your job
        return 123;
    }

    public static JSONObject main(JSONObject args) {
		JSONObject result = new JSONObject();
		try{
			String cmd = args.getString("SubCmd");
            View view = (View)args.get("Control"); //获取View实例
            String arg = args.getString("Arg"); // 获取参数
            if("Hello".equals(cmd)){
                MyPlugin plugin = new MyPlugin();
                try{
                    result.put("Result", plugin.handleRequest(arg));
                }catch(Exception e){
                    result.put("Error", e.toString());
                }
            }else{
                result.put("Result", -1);
            }
		}catch(JSONException e){
			e.printStackTrace();
		}
		return result;
	}
}
```

`MyPlugin.main`是整个dex的入口函数，会被QT4A测试桩调起，并传入客户端传入的参数。`main`里一般会解析这些参数，并调用相应的方法，返回结果可以通过`Result`字段返回，函数执行的报错信息，可以通过`Error`字段返回，也可以打印到`logcat`中。不过，不捕获异常也没有关系，因为QT4A测试桩在调用插件函数的时候也会主动捕获异常的。


## 如何编译测试桩插件

1. 使用普通编译apk的方式编译，然后提取出apk中的`classes.dex`
2. 使用命令行方式编译，具体命令如下：

```bash
javac -encoding utf-8 -target 1.7 -d bin src/com/test/plugin/MyPlugin.java -bootclasspath $SDK_ROOT/platforms/android-24/android.jar # $SDK_ROOT为Android SDK根路径

cd bin
jar cvf plugin.jar com

$SDK_ROOT/build-tools/25.0.3/dx --dex --output=plugin.jar ../plugin.jar # 25.0.3要改成实际安装的版本
```

这样会在根目录生成目标文件`plugin.jar`，虽然这个文件是`.jar`结尾，但本质上是一个zip格式的`dex`文件。


## 如何使用测试桩插件

先将编译出来的dex/jar文件push到设备某一路径下，如：`/data/local/tmp/plugin.jar`。

然后使用以下代码来调用：

```python

result = driver.call_external_method(jar_path, # plugin.jar在设备中的路径
    'com.test.plugin.MyPlugin', # 替换为真正的插件入口类路径
    Control=hashcode, # 如果需要操作控件可以在这里指定控件的hashcode
    SubCmd='Hello', # 子命令
    Arg='you param' # 子命令的参数
    )
```

`driver`是`AndroidDriver`实例。建议用户对接口再做一层封装，这样更像是本地方法调用。

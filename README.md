# QT4A

[![Build Status](https://github.com/tencent/qt4a/actions/workflows/unittest.yml/badge.svg)](https://github.com/Tencent/QT4A/actions/workflows/unittest.yml) 
[![PyPi version](https://img.shields.io/pypi/v/qt4a.svg)](https://pypi.python.org/pypi/qt4a/) 
[![Documentation Status](https://readthedocs.org/projects/qt4a/badge/?version=latest)](https://qt4a.readthedocs.io/zh_CN/latest/?badge=latest)
[![GitHub tag](https://img.shields.io/github/tag/Tencent/QT4A.svg)](https://GitHub.com/Tencent/QT4A/tags/)
[![codecov.io](https://codecov.io/github/tencent/QT4A/coverage.svg?branch=master)](https://codecov.io/github/tencent/QT4A)

QT4A (Quick Test for Android) is a QTA test automation driver for Android application.

### Features

 * Support most versions of Android OS from 4.0 to 14(armeabi-v7a、arm64-v8a、x86、x86_64)
 * Multiple devices can be used simultaneously in a test
 * Support testing multi-process application, and multiple application can be tested simultaneously
 * Support testting code obfuscated application
 * Support testing with custom controls
 * Support non-root devices
 
QT4A should be used with [QTAF](https://github.com/Tencent/QTAF), please check it first.

### Links
* [Demo Project](https://github.com/qtacore/QT4ADemoProj)
* [Usage Document](https://qt4a.readthedocs.io/zh_CN/latest)
* [Design Document](https://github.com/Tencent/QT4A/blob/master/design.md)
* [AndroidUISpy Tool](https://github.com/qtacore/AndroidUISpy/blob/master/usage.md)

### Statement

QT4A of version 3.2.0-3.2.2 employed the https://github.com/obfusk/reproducible-apk-tools/blob/284dd69ac46e804e643b1014049993207f0768fa/zipalign.py, Copyright (C) 2024 FC (Fay) Stegerman flx@obfusk.net, which is subject to GPL v3（https://github.com/obfusk/reproducible-apk-tools/blob/284dd69ac46e804e643b1014049993207f0768fa/LICENSE.GPLv3）.

Thus, we kindly ask you to adhere to GPL v3 when using Version 3.2.0-3.2.2 of QT4A.

------------------------------

QT4A (Quick Test for Android)，基于QTA提供面向Android应用的UI测试自动化测试解决方案。

### 特性介绍

1. 支持Android 4.0 - 14 版本(armeabi-v7a、arm64-v8a、x86、x86_64)
2. 支持多设备协同测试
3. 支持跨进程、跨应用测试
4. 支持进行过控件混淆的安装包
5. 支持自定义（自绘）控件
6. 支持非root设备

QT4A需要和[QTAF](https://github.com/Tencent/QTAF)一起使用，请先参考QTAF的使用

### 链接

* [Demo项目代码](https://github.com/qtacore/QT4ADemoProj)
* [使用文档](https://qt4a.readthedocs.io/zh_CN/latest)
* [设计文档](https://github.com/Tencent/QT4A/blob/master/design.md)
* [AndroidUISpy工具](https://github.com/qtacore/AndroidUISpy/blob/master/usage.md)

------------------------------

欢迎加入QQ群（432699528）交流使用和反馈

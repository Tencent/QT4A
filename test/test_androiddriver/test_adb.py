# -*- coding: UTF-8 -*-
#
# Tencent is pleased to support the open source community by making QTA available.
# Copyright (C) 2016THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the BSD 3-Clause License (the "License"); you may not use this 
# file except in compliance with the License. You may obtain a copy of the License at
# 
# https://opensource.org/licenses/BSD-3-Clause
# 
# Unless required by applicable law or agreed to in writing, software distributed 
# under the License is distributed on an "AS IS" basis, WITHOUT WARRANTIES OR CONDITIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.
#

'''adb模块单元测试
'''

try:
    from unittest import mock
except:
    import mock
import os
import shlex
import tempfile
import unittest

from qt4a.androiddriver.adb import ADB, LocalADBBackend

def mock_run_shell_cmd(cmd_line, root=False, **kwds):
    args = shlex.split(cmd_line)
    if args[0] == 'ls':
        path = args[-1]
        if '-l' in args:
            if path == '/data/data':
                if not root:
                    return '''opendir failed, Permission denied'''
                else:
                    return '''drwxr-x--x u0_a16   u0_a16            2017-06-20 09:44 com.android.apps.tag
drwxr-x--x u0_a1    u0_a1             2017-06-20 09:44 com.android.backupconfirm
drwxr-x--x bluetooth bluetooth          2017-06-20 11:07 com.android.bluetooth
drwxr-x--x u0_a22   u0_a22            2017-07-21 08:11 com.android.browser
drwxr-x--x u0_a25   u0_a25            2017-06-20 09:44 com.android.calculator2
drwxr-x--x u0_a26   u0_a26            2017-06-20 09:45 com.android.calendar
drwxr-x--x u0_a27   u0_a27            2017-06-20 09:45 com.android.camera2
drwxr-x--x u0_a28   u0_a28            2017-06-20 09:44 com.android.captiveportallogin
drwxr-x--x u0_a4    u0_a4             2017-06-20 09:45 com.android.cellbroadcastreceiver
drwxr-x--x u0_a29   u0_a29            2017-06-20 09:44 com.android.certinstaller
drwxr-x--x u0_a5    u0_a5             2017-06-20 09:44 com.android.contacts
drwxr-x--x u0_a6    u0_a6             2017-06-20 10:02 com.android.defcontainer
drwxr-x--x u0_a30   u0_a30            2017-06-20 09:45 com.android.deskclock
drwxr-x--x system   system            2017-06-20 09:44 com.android.development
drwxr-x--x u0_a7    u0_a7             2017-06-20 09:45 com.android.dialer
drwxr-x--x u0_a31   u0_a31            2017-06-20 10:50 com.android.documentsui
drwxr-x--x u0_a21   u0_a21            2017-06-20 09:44 com.android.dreams.basic
drwxr-x--x u0_a48   u0_a48            2017-06-20 09:44 com.android.dreams.phototable
drwxr-x--x u0_a33   u0_a33            2017-06-20 09:45 com.android.email
drwxr-x--x u0_a34   u0_a34            2017-06-20 09:45 com.android.exchange
drwxr-x--x u0_a9    u0_a9             2017-06-20 10:50 com.android.externalstorage
drwxr-x--x u0_a35   u0_a35            2017-06-20 09:44 com.android.galaxy4
drwxr-x--x u0_a36   u0_a36            2017-06-20 09:45 com.android.gallery3d
drwxr-x--x u0_a37   u0_a37            2017-06-20 09:44 com.android.htmlviewer
drwxr-x--x u0_a7    u0_a7             2017-06-20 09:45 com.android.incallui
drwxr-x--x system   system            2017-06-20 09:44 com.android.inputdevices
drwxr-x--x u0_a39   u0_a39            2017-06-22 08:06 com.android.inputmethod.latin
drwxr-x--x system   system            2017-06-20 10:50 com.android.keychain
drwxr-x--x system   system            2017-06-20 09:44 com.android.location.fused
drwxr-x--x u0_a10   u0_a10            2017-06-20 09:45 com.android.managedprovisioning
drwxr-x--x u0_a11   u0_a11            2017-06-20 09:45 com.android.mms
drwxr-x--x radio    radio             2017-06-20 09:44 com.android.mms.service
drwxr-x--x u0_a55   u0_a55            2017-06-20 09:44 com.android.musicvis
drwxr-x--x nfc      nfc               2017-06-20 09:45 com.android.nfc
drwxr-x--x u0_a43   u0_a43            2017-06-20 09:44 com.android.noisefield
drwxr-x--x u0_a12   u0_a12            2017-06-20 09:45 com.android.onetimeinitializer
drwxr-x--x u0_a45   u0_a45            2017-06-20 09:45 com.android.packageinstaller
drwxr-x--x u0_a44   u0_a44            2017-06-20 09:44 com.android.pacprocessor
drwxr-x--x u0_a46   u0_a46            2017-06-20 09:44 com.android.phasebeam
drwxr-x--x radio    radio             2017-06-20 09:45 com.android.phone
drwxr-x--x u0_a50   u0_a50            2017-06-20 09:45 com.android.printspooler
drwxr-x--x u0_a3    u0_a3             2017-06-20 09:45 com.android.providers.calendar
drwxr-x--x u0_a5    u0_a5             2017-06-20 09:45 com.android.providers.contacts
drwxr-x--x u0_a8    u0_a8             2017-06-20 12:16 com.android.providers.downloads
drwxr-x--x u0_a8    u0_a8             2017-06-20 09:44 com.android.providers.downloads.ui
drwxr-x--x u0_a8    u0_a8             2017-06-20 09:45 com.android.providers.media
drwxr-x--x system   system            2017-06-20 09:44 com.android.providers.settings
drwxr-x--x radio    radio             2017-06-20 09:49 com.android.providers.telephony
drwxr-x--x u0_a5    u0_a5             2017-06-20 09:49 com.android.providers.userdictionary
drwxr-x--x u0_a52   u0_a52            2017-06-20 09:46 com.android.provision
drwxr-x--x u0_a13   u0_a13            2017-06-20 09:44 com.android.proxyhandler
drwxr-x--x system   system            2017-06-20 09:45 com.android.server.telecom
drwxr-x--x system   system            2017-07-13 16:36 com.android.settings
drwxr-x--x u0_a14   u0_a14            2017-06-20 09:44 com.android.sharedstoragebackup
drwxr-x--x shell    shell             2017-06-20 09:44 com.android.shell
drwxr-x--x u0_a56   u0_a56            2017-06-20 09:45 com.android.smspush
drwxr-x--x u0_a53   u0_a53            2017-06-20 09:44 com.android.soundrecorder
drwxr-x--x radio    radio             2017-06-20 09:44 com.android.stk
drwxr-x--x u0_a15   u0_a15            2017-07-04 06:49 com.android.systemui
drwxr-x--x u0_a54   u0_a54            2017-06-20 09:44 com.android.terminal
drwxr-x--x u0_a19   u0_a19            2017-06-20 09:44 com.android.vpndialogs
drwxr-x--x u0_a40   u0_a40            2017-06-20 09:44 com.android.wallpaper
drwxr-x--x u0_a38   u0_a38            2017-06-20 09:44 com.android.wallpaper.holospiral
drwxr-x--x u0_a41   u0_a41            2017-06-20 09:44 com.android.wallpaper.livepicker
drwxr-x--x u0_a20   u0_a20            2017-06-20 09:44 com.android.wallpapercropper
drwxr-x--x u0_a57   u0_a57            2017-06-20 09:44 com.android.webview
drwxr-x--x u0_a32   u0_a32            2017-06-20 09:45 com.cyanogenmod.eleven
drwxr-x--x u0_a23   u0_a23            2017-06-20 09:44 com.cyanogenmod.filemanager
drwxr-x--x u0_a42   u0_a42            2017-06-20 09:45 com.cyanogenmod.lockclock
drwxr-x--x radio    radio             2017-06-20 09:44 com.cyanogenmod.samsungservicemode
drwxr-x--x system   system            2017-06-20 09:45 com.cyanogenmod.setupwizard
drwxr-x--x u0_a18   u0_a18            2017-06-20 09:46 com.cyanogenmod.trebuchet
drwxr-x--x u0_a2    u0_a2             2017-06-20 09:45 com.cyanogenmod.updater
drwxr-x--x u0_a24   u0_a24            2017-06-20 09:44 com.cyanogenmod.wallpapers
drwxr-x--x system   system            2017-06-20 09:44 com.dsi.ant.server
drwxr-x--x u0_a49   u0_a49            2017-06-20 09:45 com.svox.pico
drwxr-x--x u0_a595  u0_a595           2018-10-17 12:59 com.tencent.liveassistant
drwxr-x--x u0_a1309 u0_a1309          2018-10-17 16:32 com.tencent.mobileqq
drwxr-x--x u0_a1308 u0_a1308          2018-10-17 17:32 com.tencent.nijigen
drwxr-x--x u0_a234  u0_a234           2017-08-23 21:14 com.test.androidspy
drwxr-x--x system   system            2017-06-20 09:44 cyanogenmod.platform
drwxr-x--x u0_a58   u0_a58            2017-06-20 10:01 eu.chainfire.supersu
drwxr-x--x u0_a0    u0_a0             2017-06-20 09:45 org.cyanogenmod.audiofx
drwxr-x--x shell    shell             2017-06-20 09:45 org.cyanogenmod.bugreport
drwxr-x--x system   system            2017-06-20 09:45 org.cyanogenmod.cmsettings
drwxr-x--x u0_a51   u0_a51            2017-06-20 09:45 org.cyanogenmod.profiles
drwxr-x--x u0_a17   u0_a17            2018-10-17 17:03 org.cyanogenmod.theme.chooser
drwxr-x--x u0_a17   u0_a17            2017-06-20 09:45 org.cyanogenmod.themes.provider
drwxr-x--x u0_a47   u0_a47            2017-06-20 09:44 org.cyanogenmod.wallpapers.photophase'''
            elif path == '/data/local/tmp/1.txt':
                return '-rw-rw-rw- root     root      4096000 2018-03-23 06:12 1.txt\n'
            else:
                raise NotImplementedError(path)
    elif args[0] == 'getprop':
        if args[1] == 'ro.build.version.sdk':
            return '21'
        elif args[1] == 'ro.build.version.release':
            return '5.0.2'
        elif args[1] == 'ro.product.cpu.abi':
            return 'armeabi-v7a'
        elif args[1] == 'ro.product.model':
            return 'MI 4C'
        elif args[1] == 'ro.product.brand':
            return 'Xiaomi'
        elif args[1] == 'ro.sf.lcd_density':
            return '320'
        elif args[1] == 'ro.kernel.android.qemud':
            return '0'
        elif args[1] == 'ro.secure':
            return '1'
        elif args[1] == 'ro.debuggable':
            return '0'
        else:
            raise NotImplementedError('Not supported property: %s' % args[1])
    elif args[0] == 'id':
        return 'uid=2000(shell) gid=2000(shell) groups=1004(input),1007(log),1011(adb),1015(sdcard_rw),1028(sdcard_r),3001(net_bt_admin),3002(net_bt),3003(inet),3006(net_bw_stats) context=u:r:shell:s0'
    elif args[0] == 'pm':
        if args[1] == 'path':
            if len(args) >= 3:
                return 'package:/data/app/%s-1/base.apk\n' % args[2]
            else:
                return 'Error: no package specified\n'
    elif args[0] == 'run-as':
        if args[2] == 'id':
            return 'uid=10059(u0_a59) gid=10059(u0_a59) groups=1003(graphics),1004(input),1007(log),1011(adb),1015(sdcard_rw),1028(sdcard_r),3001(net_bt_admin),3002(net_bt),3003(inet),3006(net_bw_stats)\n'
        else:
            raise NotImplementedError(args[2])
    elif args[0] == 'dumpsys':
        if args[1] == 'iphonesubinfo':
            return '''
Phone Subscriber Info:
  Phone Type = CDMA
  Device ID = 99000567737777
'''
    elif args[0] == 'getenforce':
        return 'Disabled'
    elif args[0] == 'ps':
        return '''
USER     PID   PPID  VSIZE  RSS     WCHAN    PC        NAME
root      1     0     8908   736   ffffffff 00000000 S /init
root      2     0     0      0     ffffffff 00000000 S kthreadd
root      3     2     0      0     ffffffff 00000000 S ksoftirqd/0
root      6     2     0      0     ffffffff 00000000 S migration/0
root      7     2     0      0     ffffffff 00000000 S watchdog/0
root      20    2     0      0     ffffffff 00000000 S khelper
root      480   2     0      0     ffffffff 00000000 S sync_supers
root      482   2     0      0     ffffffff 00000000 S bdi-default
root      484   2     0      0     ffffffff 00000000 S kblockd
root      499   2     0      0     ffffffff 00000000 S spi2
root      502   2     0      0     ffffffff 00000000 S spi3
root      510   2     0      0     ffffffff 00000000 S khubd
root      528   2     0      0     ffffffff 00000000 S irq/524-max7780
root      555   2     0      0     ffffffff 00000000 S irq/519-sec-pmi
root      640   2     0      0     ffffffff 00000000 S cfg80211
root      743   2     0      0     ffffffff 00000000 S khungtaskd
root      744   2     0      0     ffffffff 00000000 S kswapd0
root      745   2     0      0     ffffffff 00000000 S ksmd
root      793   2     0      0     ffffffff 00000000 S fsnotify_mark
root      815   2     0      0     ffffffff 00000000 S ecryptfs-kthrea
root      822   2     0      0     ffffffff 00000000 S crypto
root      926   2     0      0     ffffffff 00000000 S pvr_timer
root      1086  2     0      0     ffffffff 00000000 S irq/533-arizona
root      1110  2     0      0     ffffffff 00000000 S drd_switch
root      1147  2     0      0     ffffffff 00000000 S f_mtp
root      1153  2     0      0     ffffffff 00000000 S file-storage
root      1170  2     0      0     ffffffff 00000000 S f54_status_work
root      1171  2     0      0     ffffffff 00000000 S irq/526-synapti
root      1208  2     0      0     ffffffff 00000000 S gsc0_irq_wq_nam
root      1212  2     0      0     ffffffff 00000000 S gsc1_irq_wq_nam
root      1216  2     0      0     ffffffff 00000000 S gsc2_irq_wq_nam
root      1220  2     0      0     ffffffff 00000000 S gsc3_irq_wq_nam
root      1227  2     0      0     ffffffff 00000000 S kfimg2dd
root      1230  2     0      0     ffffffff 00000000 S irq/128-s5p-mfc
root      1235  2     0      0     ffffffff 00000000 S s5p_mfc/watchdo
root      1236  2     0      0     ffffffff 00000000 S s5p_mfc/sched
root      1241  2     0      0     ffffffff 00000000 S khdcpd
root      1244  2     0      0     ffffffff 00000000 S hdmi-mixer
root      1268  2     0      0     ffffffff 00000000 S sii8240-cmdwq
root      1269  2     0      0     ffffffff 00000000 S sii8240-aviwq
root      1270  2     0      0     ffffffff 00000000 S irq/559-sii8240
root      1292  2     0      0     ffffffff 00000000 S dw-mci-card
root      1294  2     0      0     ffffffff 00000000 S dw-mci-card
root      1296  2     0      0     ffffffff 00000000 S dw-mci-card
root      1298  2     0      0     ffffffff 00000000 S irq/532-dw_mmc.
root      1373  2     0      0     ffffffff 00000000 S binder
root      1386  2     0      0     ffffffff 00000000 S irq/525-fuelgau
root      1391  2     0      0     ffffffff 00000000 S mmcqd/0
root      1406  2     0      0     ffffffff 00000000 S max77803-charge
root      1417  2     0      0     ffffffff 00000000 S irq/531-wpc-int
root      1419  2     0      0     ffffffff 00000000 S hap_work
root      1443  2     0      0     ffffffff 00000000 S ssp_debug_wq
root      1444  2     0      0     ffffffff 00000000 S irq/539-SSP_Int
root      1458  2     0      0     ffffffff 00000000 S ssp_sensorhub_t
root      1460  2     0      0     ffffffff 00000000 S mc_fastcall
root      1514  2     0      0     ffffffff 00000000 S kswitcher_0
root      1515  2     0      0     ffffffff 00000000 S kswitcher_3
root      1516  2     0      0     ffffffff 00000000 S kswitcher_2
root      1517  2     0      0     ffffffff 00000000 S kswitcher_1
root      1519  2     0      0     ffffffff 00000000 S usb_tx_wq
root      1520  2     0      0     ffffffff 00000000 S usb_rx_wq
root      1522  2     0      0     ffffffff 00000000 S linkpmd
root      1557  2     0      0     ffffffff 00000000 S s3c-fb
root      1579  2     0      0     ffffffff 00000000 S s3c-fb-vsync
root      1583  2     0      0     ffffffff 00000000 S vsync_workqueue
root      1584  2     0      0     ffffffff 00000000 S deferwq
root      1587  2     0      0     ffffffff 00000000 S irq/513-flip_co
root      1593  2     0      0     ffffffff 00000000 S irq/547-sec_tou
root      1595  2     0      0     ffffffff 00000000 S ondemand_wq
root      1602  2     0      0     ffffffff 00000000 S devfreq_wq
root      1607  2     0      0     ffffffff 00000000 S sec-battery
root      1620  2     0      0     ffffffff 00000000 S barcode_init
root      1635  2     0      0     ffffffff 00000000 S wl_event_handle
root      1642  2     0      0     ffffffff 00000000 S dhd_watchdog_th
root      1643  2     0      0     ffffffff 00000000 S dhd_dpc
root      1644  2     0      0     ffffffff 00000000 S dhd_rxf
root      1650  1     8904   516   ffffffff 00000000 S /sbin/ueventd
u0_a17    1903  2598  1574760 86756 ffffffff 00000000 S org.cyanogenmod.theme.chooser
root      2527  2     0      0     ffffffff 00000000 S jbd2/mmcblk0p20
root      2528  2     0      0     ffffffff 00000000 S ext4-dio-unwrit
root      2532  2     0      0     ffffffff 00000000 S flush-179:0
root      2542  2     0      0     ffffffff 00000000 S jbd2/mmcblk0p19
root      2543  2     0      0     ffffffff 00000000 S ext4-dio-unwrit
root      2547  2     0      0     ffffffff 00000000 S jbd2/mmcblk0p21
root      2548  2     0      0     ffffffff 00000000 S ext4-dio-unwrit
root      2552  2     0      0     ffffffff 00000000 S jbd2/mmcblk0p3-
root      2553  2     0      0     ffffffff 00000000 S ext4-dio-unwrit
logd      2559  1     18228  3512  ffffffff 00000000 S /system/bin/logd
root      2560  1     9844   356   ffffffff 00000000 S /sbin/healthd
root      2561  1     10556  1192  ffffffff 00000000 S /system/bin/lmkd
system    2562  1     9516   728   ffffffff 00000000 S /system/bin/servicemanager
root      2563  1     17948  1820  ffffffff 00000000 S /system/bin/vold
system    2564  1     145896 20344 ffffffff 00000000 S /system/bin/surfaceflinger
root      2565  1     8900   264   ffffffff 00000000 S /sbin/watchdogd
root      2571  2     0      0     ffffffff 00000000 S pvr_workqueue
root      2576  2     0      0     ffffffff 00000000 S kauditd
shell     2577  1     9356   752   c026a6bc b6f6db90 S /system/bin/sh
audit     2579  1     9264   612   ffffffff 00000000 S /system/bin/auditd
root      2580  1     22804  1592  ffffffff 00000000 S /system/bin/netd
root      2581  1     10104  1300  ffffffff 00000000 S /system/bin/debuggerd
radio     2583  1     28560  7228  ffffffff 00000000 S /system/bin/rild
drm       2584  1     25916  4144  ffffffff 00000000 S /system/bin/drmserver
media     2585  1     170652 16392 ffffffff 00000000 S /system/bin/mediaserver
install   2586  1     9424   756   ffffffff 00000000 S /system/bin/installd
keystore  2588  1     12476  1820  ffffffff 00000000 S /system/bin/keystore
radio     2590  1     15216  156   ffffffff 00000000 S /system/bin/cbd
drmrpc    2591  1     17680  916   ffffffff 00000000 S /system/bin/mcDriverDaemon
root      2598  1     1486896 48780 ffffffff 00000000 S zygote
media_rw  2601  1     15412  2036  ffffffff 00000000 S /system/bin/sdcard
shell     2606  1     18008  616   ffffffff 00000000 S /sbin/adbd
root      2611  2     0      0     ffffffff 00000000 S mc_log
root      2828  1     9352   476   ffffffff 00000000 S daemonsu:mount:master
root      2856  1     15496  3288  ffffffff 00000000 S daemonsu:master
system    3021  2598  1707492 134532 ffffffff 00000000 S system_server
u0_a15    3136  2598  1620628 110372 ffffffff 00000000 S com.android.systemui
u0_a8     3157  2598  1520468 48044 ffffffff 00000000 S android.process.media
nfc       3193  2598  1531524 46308 ffffffff 00000000 S com.android.nfc
u0_a234   3463  2598  1535956 61340 ffffffff 00000000 S com.test.androidspy
u0_a42    3496  2598  1504436 41000 ffffffff 00000000 S com.cyanogenmod.lockclock
dhcp      3602  1     9356   760   ffffffff 00000000 S /system/bin/dhcpcd
u0_a0     3613  2598  1498792 38644 ffffffff 00000000 S org.cyanogenmod.audiofx
u0_a7     3634  2598  1495288 35708 ffffffff 00000000 S com.android.incallui
radio     3654  2598  1526784 58864 ffffffff 00000000 S com.android.phone
u0_a18    3677  2598  1578640 90756 ffffffff 00000000 S com.cyanogenmod.trebuchet
u0_a234   3780  2598  1505824 47708 ffffffff 00000000 S com.test.androidspy:acc_service
u0_a56    3796  2598  1495256 34884 ffffffff 00000000 S com.android.smspush
root      3970  2856  15496  3460  ffffffff 00000000 S daemonsu:0
gps       4358  1     29864  5092  ffffffff 00000000 S /system/bin/gpsd
bluetooth 4511  2598  1539260 49928 ffffffff 00000000 S com.android.bluetooth
root      4803  2856  16520  664   ffffffff 00000000 S daemonsu:10058
u0_a33    5075  2598  1516548 40680 ffffffff 00000000 S com.android.email
u0_a595   5480  2598  1574788 59188 ffffffff 00000000 S com.tencent.liveassistant:wns
u0_a2     7572  2598  1502488 43776 ffffffff 00000000 S com.cyanogenmod.updater
u0_a30    7848  2598  1499776 38628 ffffffff 00000000 S com.android.deskclock
root      15093 2     0      0     ffffffff 00000000 S kworker/u:1
u0_a58    16041 2598  1499012 37692 ffffffff 00000000 S eu.chainfire.supersu
system    16094 2598  1526292 46296 ffffffff 00000000 S com.android.settings
root      16247 2     0      0     ffffffff 00000000 S kworker/u:0
shell     16511 2606  9356   772   c026a6bc b6f61b90 S /system/bin/sh
root      16547 2     0      0     ffffffff 00000000 S kworker/u:2
root      17402 2     0      0     ffffffff 00000000 S kworker/0:2
u0_a3     18045 2598  1497536 41128 ffffffff 00000000 S com.android.providers.calendar
u0_a26    18080 2598  1504928 41824 ffffffff 00000000 S com.android.calendar
u0_a595   18162 2598  1565540 63360 ffffffff 00000000 S com.tencent.liveassistant:web
wifi      20194 1     12504  2652  ffffffff 00000000 S /system/bin/wpa_supplicant
root      21966 2     0      0     ffffffff 00000000 S kworker/u:3
root      22006 2     0      0     ffffffff 00000000 S kworker/0:1
shell     22889 2598  1495600 34984 ffffffff b6e6f290 S org.cyanogenmod.bugreport
root      23590 2     0      0     ffffffff 00000000 S kworker/0:0
root      23706 2     0      0     ffffffff 00000000 S migration/1
root      23709 2     0      0     ffffffff 00000000 S kworker/1:0
root      23710 2     0      0     ffffffff 00000000 S ksoftirqd/1
root      23711 2     0      0     ffffffff 00000000 S watchdog/1
root      23712 2     0      0     ffffffff 00000000 S migration/2
root      23713 2     0      0     ffffffff 00000000 S kworker/2:0
root      23714 2     0      0     ffffffff 00000000 S ksoftirqd/2
root      23715 2     0      0     ffffffff 00000000 S watchdog/2
root      23716 2     0      0     ffffffff 00000000 S migration/3
root      23718 2     0      0     ffffffff 00000000 S kworker/3:0
root      23719 2     0      0     ffffffff 00000000 S ksoftirqd/3
root      23720 2     0      0     ffffffff 00000000 S watchdog/3
root      23721 2     0      0     ffffffff 00000000 S kworker/3:1
root      23722 2     0      0     ffffffff 00000000 S kworker/1:1
root      23730 2     0      0     ffffffff 00000000 S kworker/2:1
shell     23740 2606  10640  968   00000000 b6f42b90 R ps
u0_a1308  23911 2598  2173820 273648 ffffffff 00000000 S com.tencent.nijigen
root      23940 1     1373476 35712 ffffffff 00000000 S com.test.androidspy:service
u0_a1308  23957 2598  1608592 78264 ffffffff 00000000 S com.tencent.nijigen:wns
u0_a1308  24145 2598  1786384 151352 ffffffff 00000000 S com.tencent.nijigen:QALSERVICE
u0_a1308  24517 2598  1588632 72300 ffffffff 00000000 S com.tencent.nijigen:xg_service_v3
u0_a1308  24558 2598  1634068 86392 ffffffff 00000000 S com.tencent.nijigen:picker
u0_a1308  24887 1     9272   448   ffffffff 00000000 S /data/data/com.tencent.nijigen/lib/libxguardian.so
'''
    elif args[0] == 'logcat':
        return ''
    else:
        raise NotImplementedError('Not supported command: %s' % cmd_line)
    
class TestADB(unittest.TestCase):
    '''ADB类测试用例
    '''
    
    def test_get_cpu_abi(self):
        for arch in ['armeabi-v7a', 'x86']:
            ADB.run_shell_cmd = mock.Mock(return_value=arch)
            adb_backend = LocalADBBackend('127.0.0.1', '')
            adb = ADB(adb_backend)
            self.assertEqual(adb.get_cpu_abi(), arch)
    
    def test_get_sdk_version(self):
        ADB.run_shell_cmd = mock.Mock(side_effect=mock_run_shell_cmd)
        adb_backend = LocalADBBackend('127.0.0.1', '')
        adb = ADB(adb_backend)
        self.assertEqual(adb.get_sdk_version(), 21)
    
    def test_list_process(self):
        ADB.run_shell_cmd = mock.Mock(side_effect=mock_run_shell_cmd)
        adb_backend = LocalADBBackend('127.0.0.1', '')
        adb = ADB(adb_backend)
        result = adb.list_process()
        self.assertEqual(len(result), 172)
        self.assertEqual(result[0]['ppid'], 0)
        self.assertEqual(result[0]['pid'], 1)
        self.assertEqual(result[0]['proc_name'], '/init')
        
    def test_get_pid(self):
        ADB.run_shell_cmd = mock.Mock(side_effect=mock_run_shell_cmd)
        adb_backend = LocalADBBackend('127.0.0.1', '')
        adb = ADB(adb_backend)
        self.assertEqual(adb.get_pid('android.process.media'), 3157)
    
    def test_get_device_imei(self):
        ADB.run_shell_cmd = mock.Mock(side_effect=mock_run_shell_cmd)
        ADB.is_rooted = mock.Mock(return_value=False)
        adb_backend = LocalADBBackend('127.0.0.1', '')
        adb = ADB(adb_backend)
        self.assertEqual(adb.get_device_imei(), '99000567737777')
    
    def test_get_device_model(self):
        ADB.run_shell_cmd = mock.Mock(side_effect=mock_run_shell_cmd)
        ADB.is_rooted = mock.Mock(return_value=False)
        adb_backend = LocalADBBackend('127.0.0.1', '')
        adb = ADB(adb_backend)
        self.assertEqual(adb.get_device_model(), 'Xiaomi MI 4C')
    
    def test_get_system_version(self):
        ADB.run_shell_cmd = mock.Mock(side_effect=mock_run_shell_cmd)
        ADB.is_rooted = mock.Mock(return_value=False)
        adb_backend = LocalADBBackend('127.0.0.1', '')
        adb = ADB(adb_backend)
        self.assertEqual(adb.get_system_version(), '5.0.2')
    
    def test_get_uid(self):
        ADB.run_shell_cmd = mock.Mock(side_effect=mock_run_shell_cmd)
        adb_backend = LocalADBBackend('127.0.0.1', '')
        adb = ADB(adb_backend)
        self.assertEqual(adb.get_uid('com.tencent.mobileqq'), 'u0_a1309')
    
    def test_list_dir(self):
        ADB.run_shell_cmd = mock.Mock(side_effect=mock_run_shell_cmd)
        ADB.is_rooted = mock.Mock(return_value=True)
        adb_backend = LocalADBBackend('127.0.0.1', '')
        adb = ADB(adb_backend)
        dir_list, file_list = adb.list_dir('/data/data')
        self.assertEqual(len(dir_list), 89)
        self.assertEqual(len(file_list), 0)
        self.assertEqual(dir_list[0]['name'], 'com.android.apps.tag')
        self.assertEqual(dir_list[0]['attr'], 'rwxr-x--x')
        
    def test_save_log(self):
        adb_backend = LocalADBBackend('127.0.0.1', '')
        adb = ADB(adb_backend)
        adb.start_logcat()
        adb.insert_logcat('test', 2019, '0101', '10:51:42.899', 'I', 'test', 1, '我们')
        adb.insert_logcat('test', 2019, '0101', '10:51:42.899', 'I', 'test', 1, u'中国'.encode('gbk'))
        adb.insert_logcat('test', 2019, '0101', '10:51:42.899', 'I', 'test', 1, u'\ub274')
        save_path = tempfile.mkstemp('.log')[1]
        adb.save_log(save_path)
        with open(save_path, 'rb') as fp:
            text = fp.read()
            try:
                text = text.decode('utf8')
            except:
                text = text.decode('gbk')
            self.assertIn(u'我们', text)
            self.assertIn(u'中国', text)

    
if __name__ == '__main__':
    unittest.main()
    

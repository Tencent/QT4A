#!/system/bin/sh

script_name=$0
dir_name=${script_name%/*}

if [ $dir_name = "SpyHelper.sh" ]; then
    dir_name="."
fi

base=$(cd $dir_name; pwd)
export CLASSPATH=$base/SpyHelper.jar
#export LD_PRELOAD=
export LD_LIBRARY_PATH_32=/vendor/lib:/system/lib
export LD_LIBRARY_PATH_64=/vendor/lib64:/system/lib64
#export LD_LIBRARY_PATH=/vendor/lib*:/system/lib*
#http://stackoverflow.com/questions/11773506/how-to-launch-jar-with-exec-app-process-on-android-ics
#app_process $base --nice-name=com.test.androidspy com.test.androidspy.SpyHelper $@

if [ -d $base/cache/dalvik-cache ]; then
	export ANDROID_DATA=$base/cache # dalvikCacheDir
fi

#export ANDROID_DATA=$base # dalvikCacheDir

api_version=`getprop ro.build.version.sdk`
service_pid=0

get_pid(){
    cmdline="ps"
    if [ $api_version -ge 26 ]; then
        cmdline="ps -A"
    fi
    #echo $cmdline
    result=`$cmdline`
    if [[ $result != *$1* ]]; then
        service_pid=0
        return
    fi
    directory="/proc"
    for file in `ls $directory`
    do
        if [ ! -z "${file##+([0-9])}" -o $file -le 1 ]; then
            continue
        fi
        #if [ -f $directory/$file ]; then
        #    continue
        #fi
        cmd_path="$directory/$file/cmdline"
        if [ ! -f $cmd_path ]; then
            continue
        fi

        cmdline=`cat $cmd_path`
        if [ "$cmdline" = "$1" ]; then
            service_pid=$file
            return
        fi
    done
    service_pid=0
}

file_path="$base/app_process"
if [ ! -f $file_path ]; then
    file_path="/system/bin/app_process32_original" # supersu
fi
if [ ! -f $file_path ]; then
    file_path="/system/bin/app_process64" #oppo手机上使用app_process32会报错
    if [ ! -f $file_path ]; then
        file_path="/system/bin/app_process"
        export LD_LIBRARY_PATH=/vendor/lib:/system/lib
    fi
fi

#echo $file_path
if [ "$1" = "runServer" ]; then
    service_process="com.test.androidspy:service"
    get_pid $service_process
    if [ $service_pid -gt 0 ]; then
        echo "service is running, pid=$service_pid"
        exit
    fi
    
    (exec $file_path $base com.test.androidspy.SpyHelper "$@" > /dev/null 2> /dev/null &)

    i=10
    while [ i -gt 0 ]; do
        get_pid $service_process
        if [ $service_pid -eq 0 ]; then
            i=$((i-1))
            sleep 1
            continue
        fi

        #old_pid=$service_pid
        #sleep 0.5 # check service process exit
        #get_pid $service_process
        if [ $service_pid -gt 0 ]; then
            echo "service run success, pid=$service_pid"
        #else
        #    echo "service process $old_pid exit"
        fi
        exit
    done

    echo "service run failed"
else
    exec $file_path $base com.test.androidspy.SpyHelper "$@"
fi


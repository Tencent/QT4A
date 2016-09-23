base=/data/local/tmp/qt4a
export CLASSPATH=$base/SpyHelper.jar
#export LD_PRELOAD=
export LD_LIBRARY_PATH_32=/vendor/lib:/system/lib
export LD_LIBRARY_PATH_64=/vendor/lib64:/system/lib64
#export LD_LIBRARY_PATH=/vendor/lib*:/system/lib*
#http://stackoverflow.com/questions/11773506/how-to-launch-jar-with-exec-app-process-on-android-ics
#app_process $base --nice-name=com.test.androidspy com.test.androidspy.SpyHelper $@

file_path="/system/bin/app_process32"
if [ ! -f $file_path ]; then
    file_path="/system/bin/app_process"
    export LD_LIBRARY_PATH=/vendor/lib:/system/lib
fi
#echo $file_path
exec $file_path $base com.test.androidspy.SpyHelper "$@"

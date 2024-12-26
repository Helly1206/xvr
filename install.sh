#!/bin/bash
NAME="xvr"
INSTALL="/usr/bin/install -c"
INSTALL_DATA="$INSTALL -m 644"
INSTALL_PROGRAM="$INSTALL"
INSTALL_FOLDER="cp -r *"
ETCDIR="/etc"
OPTDIR="/opt"
OPTLOC="$OPTDIR/$NAME"
ETCLOC=$ETCDIR
SERVICEDIR="$ETCDIR/systemd/system"
SERVICESCRIPT="$NAME.service"
DAEMON="$NAME.py"
DEBFOLDER="debian"

if [ "$EUID" -ne 0 ]
then
	echo "Please execute as root ('sudo install.sh' or 'sudo make install')"
	exit
fi

if [ "$1" == "-u" ] || [ "$1" == "-U" ]
then
	echo "$NAME uninstall script"

	echo "Uninstalling service $NAME"
	systemctl stop "$SERVICESCRIPT"
	systemctl disable "$SERVICESCRIPT"
	if [ -e "$SERVICEDIR/$SERVICESCRIPT" ]; then rm -f "$SERVICEDIR/$SERVICESCRIPT"; fi

    echo "Uninstalling $NAME"
	if [ -d "$OPTLOC" ]; then rm -rf "$OPTLOC"; fi
elif [ "$1" == "-h" ] || [ "$1" == "-H" ]
then
	echo "Usage:"
	echo "  <no argument>: install $NAME"
	echo "  -u/ -U       : uninstall $NAME"
	echo "  -h/ -H       : this help file"
	echo "  -d/ -D       : build debian package"
	echo "  -c/ -C       : Cleanup compiled files in install folder"
elif [ "$1" == "-c" ] || [ "$1" == "-C" ]
then
	echo "$NAME Deleting compiled files in install folder"
	py3clean .
	rm -f ./*.deb
	rm -rf "$DEBFOLDER"/${NAME,,}
	rm -rf "$DEBFOLDER"/.debhelper
    rm -f "$DEBFOLDER"/debhelper-build-stamp
	rm -f "$DEBFOLDER"/files
	rm -f "$DEBFOLDER"/files.new
	rm -f "$DEBFOLDER"/${NAME,,}.*
elif [ "$1" == "-d" ] || [ "$1" == "-D" ]
then
	echo "$NAME build debian package"
	py3clean .
	fakeroot debian/rules clean binary
	mv ../*.deb .
else
	echo "$NAME install script"

	echo "Stop running services"
	systemctl stop $SERVICESCRIPT
    systemctl disable $SERVICESCRIPT

    py3clean .

    echo "Installing $NAME"
    if [ -d "$OPTLOC" ]; then rm -rf "$OPTLOC"; fi
	if [ ! -d "$OPTLOC" ]; then
		mkdir "$OPTLOC"
		chmod 755 "$OPTLOC"
	fi

	#$INSTALL_FOLDER $OPTLOC
	cp -r ".$OPTLOC"/* "$OPTLOC"
	$INSTALL_PROGRAM ".$OPTLOC/$DAEMON" "$OPTLOC"

	echo "Install required packages, based on debian/ ubuntu system"
	echo "If apt not available, manually install these packages"
	apt -y install ffmpeg
	apt -y install python3
    apt -y install python3-paho-mqtt
    apt -y install python3-yaml
    apt -y install python3-httpx
    apt -y install python3-ciso8601
    apt -y install python3-urllib3
    apt -y install python3-psutil

	echo "Installing service $NAME"
	read -p "Do you want to install an automatic startup service for $NAME (Y/n)? " -n 1 -r
	echo    # (optional) move to a new line
	if [[ $REPLY =~ ^[Nn]$ ]]
	then
		echo "Skipping install automatic startup service for $NAME"
	else
		echo "Install automatic startup service for $NAME"
		$INSTALL_DATA ".$SERVICEDIR/$SERVICESCRIPT" "$SERVICEDIR/$SERVICESCRIPT"

		systemctl enable $SERVICESCRIPT
		systemctl start $SERVICESCRIPT
	fi
fi
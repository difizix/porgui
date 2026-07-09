help:
	echo ...

restartPodman:
	cd ../pods/compose && podman-compose build porsmgui
	podman rm -f porsmgui || true
	cd ../pods/compose && podman-compose up -d porsmgui
	cd ../pods/compose && podman-compose up -d --force-recreate pingapsrvr
	podman ps -a


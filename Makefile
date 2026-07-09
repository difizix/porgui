help:
	echo ...

restartPodman:
	cd ../pods/compose && podman-compose build porsmgui
	cd ../pods/compose && podman-compose stop porsmgui pingapsrvr
	podman rm -f porsmgui pingapsrvr || true
	cd ../pods/compose && podman-compose up -d --force-recreate porsmgui pingapsrvr
	podman ps -a


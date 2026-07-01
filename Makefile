help:
	echo ...

restartPodman:
	cd ../pods/compose && podman-compose stop img3gui pingapsrvr
	podman rm -f pingapsrvr || true
	podman rm -f img3gui || true
	cd ../pods/compose && podman-compose up -d --build img3gui
	cd ../pods/compose && podman-compose up -d pingapsrvr
	podman ps -a
	echo waiting for 10 seconds to refresh
	sleep 10

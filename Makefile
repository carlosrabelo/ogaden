start:

	docker compose up --detach --build --force-recreate

stop:

	docker compose down --remove-orphans --volumes

restart: stop start

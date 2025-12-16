#run in dev mode
dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# Run in Prod Simulation (No hot reload, no local keys)
prod-sim:
	docker-compose up --build

# Stop everything
down:
	docker-compose down
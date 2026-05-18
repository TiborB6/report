.PHONY: go local server sass postgres docker

go:
	reflex -s -v go run cmd/server/main.go

run:
	sudo docker build -t report-server .
	sudo docker run -p 8080:8080 report-server

docker:
	sudo docker build -t report-server .
	sudo docker tag report-server tiborb6/report-server
	sudo docker push tiborb6/report-server:latest

launch:
	sudo yum update -y
	sudo amazon-linux-extras install docker -y
	sudo service docker start
	docker run -d --rm -ti --network host -e POSTGRES_PASSWORD=secret postgres
	sudo docker pull tiborb6/report-server:latest
	sudo docker run -d -p 80:3000 tiborb6/report-server:latest

sass:
	sass --watch static/styles/dev:static/styles/ --style compressed --no-source-map

postgres:
	docker run -d --rm -ti --network host -e POSTGRES_PASSWORD=secret postgres

migrate-down:
	migrate -path db/migrations -database "postgresql://postgres:secret@localhost/?sslmode=disable" down
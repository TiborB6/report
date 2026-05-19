.PHONY: go local server sass postgres docker

run:
	sudo docker build -t report-server .
	sudo docker run -p 8080:8080 report-server

docker:
	docker buildx create --name multiarch-builder --use
	docker buildx inspect --bootstrap
	docker buildx build --platform linux/amd64,linux/arm64 \
		-t tiborb6/report-server:latest \
		--push .
.PHONY: go local server sass postgres docker

run:
	sudo docker build -t report-server .
	sudo docker run -p 8080:8080 report-server

docker:
	sudo docker buildx rm multiarch-builder 2>/dev/null || true
	sudo docker buildx create --name multiarch-builder --driver docker-container --use
	sudo docker buildx inspect --bootstrap
	sudo docker buildx build --platform linux/amd64,linux/arm64 \
		-t tiborb6/report-server:latest \
		--push .
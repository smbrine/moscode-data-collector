docker:
	docker build -t smbrine/moscode-data-collector .
	docker push smbrine/moscode-data-collector

postgres:
	docker run -ePOSTGRES_PASSWORD=password -p5432:5432 postgres
FROM golang:1.19-alpine

WORKDIR /app

COPY go.mod ./
COPY go.sum ./
RUN go mod download

COPY . ./

RUN go build ./cmd/api.go

EXPOSE 8080

CMD [ "./api" ]
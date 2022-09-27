FROM golang:1.19-alpine as build

WORKDIR /app

COPY go.mod ./
COPY go.sum ./
RUN go mod download

COPY . ./

RUN go build ./cmd/api.go

FROM alpine

COPY --from=build /app/api /usr/local/bin/api

EXPOSE 8080

CMD [ "/usr/local/bin/api" ]
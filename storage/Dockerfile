FROM mcr.microsoft.com/azure-function/java:4.0-java11-build as build-stage

COPY . /src/java-function-app
WORKDIR /src/java-function-app
RUN mkdir -p /home/site/wwwroot
RUN mvn clean package

WORKDIR /src/java-function-app/target/azure-functions
RUN cd $(ls -d */|head -n 1) && cp -a . /home/site/wwwroot

FROM mcr.microsoft.com/azure-function/java:4.0-java11-appservice

ENV AzureWebJobsScriptRoot=/home/site/wwwroot
ENV AzureFunctionsJobHost__Logging__Console__IsEnabled=true

COPY --from=build-stage ["/home/site/wwwroot", "/home/site/wwwroot"]
EXPOSE 80
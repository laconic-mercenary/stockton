if ! [ -d java ]
then
    case "$(uname -s)" in
        Linux*)     JRE_OS=linux;;
        Darwin*)    JRE_OS=mac;;
        CYGWIN*)    JRE_OS=windows;;
        MINGW*)     JRE_OS=windows;;
        *)          echo "Unsupported platform"; exit 1;;
    esac

    case "$(uname -m)" in
        x86_64)     JRE_ARCH=x64;;
        arm64)      JRE_ARCH=aarch64;;
        *)          echo "Unsupported architecture"; exit 1;;
    esac
    JRE_LTS=$(curl -s https://api.adoptopenjdk.net/v3/info/available_releases | jq -r ".most_recent_lts")
    JRE_LINK=$(curl -s "https://api.adoptopenjdk.net/v3/assets/latest/$(curl -s https://api.adoptopenjdk.net/v3/info/available_releases | jq -r ".most_recent_lts")/hotspot" | jq -r ".[] | .binary | select(.os == \"$JRE_OS\" and .architecture == \"$JRE_ARCH\" and .image_type == \"jre\") | .package.link")

    wget $JRE_LINK
    tar -xzf OpenJDK*.tar.gz
    mv jdk-*-jre java
    rm OpenJDK*.tar.gz
fi

if ! [ -d jars ]
then
    wget https://download2.interactivebrokers.com/portal/clientportal.gw.zip
    unzip clientportal.gw.zip
    rm clientportal.gw.zip
fi

rm root/webapps/demo/index.html
ln -s "$PWD/index.html" "$PWD/root/webapps/demo/index.html"
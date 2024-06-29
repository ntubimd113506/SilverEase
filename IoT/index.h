const char PAGE_INDEX[] PROGMEM= R"=====( 
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document</title>
</head>
<body>
    <div id="wifiInfo">
        <form action="/wifiInfo" method="POST">
            <div>WiFi SSID:<input type="text" name="ssid"></div>
            <div>Password:<input type="text" name="password"></div>
            <div><input type="submit" value="連線"></div>
        </form>
    </div>
</body>
</html>
)=====";
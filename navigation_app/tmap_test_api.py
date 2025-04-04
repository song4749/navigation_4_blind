import requests

url = "https://apis.openapi.sk.com/tmap/pois?version=1&searchKeyword=SK%20T%ED%83%80%EC%9B%8C&searchType=all&searchtypCd=A&reqCoordType=WGS84GEO&resCoordType=WGS84GEO&page=1&count=20&multiPoint=N&poiGroupYn=N"

headers = {
    "Accept": "application/json",
    "appKey": "Yz2qEZKW5d6VTpdo5UKGNauYXF5So0NVaaD881sx"
}

response = requests.get(url, headers=headers)

print(response.text)
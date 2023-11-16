from flask import Flask, render_template, request
import requests  # pip install requests
from urllib.parse import urlencode, unquote
import json
import csv
from dotenv import load_dotenv
import os
from datetime import *
import random
import time
import RPi.GPIO as GPIO

#GPIO핀번호 리스트 전체 초기화 용도
PIN_num = {40, 38, 36, 37, 35, 33, 31}

#핀모드로 설정
GPIO.setmode(GPIO.BOARD)

# 전체 출력으로설정후 LED = OFF 로 초기화
for i in PIN_num:
    GPIO.setup(i, GPIO.OUT, initial = GPIO.LOW)

# .env 파일 불러오기
load_dotenv()

# env 파일에있는 공공 API키값 넣어주기
myWeatherKey = os.environ.get("WEATHER_FORECAST_KEY")

#네이버 API ID값과 secret값 입력 (고유번호임)
ncreds = {"client_id": "", "client_secret": ""}
nheaders = {
    "X-Naver-Client-Id": ncreds.get("client_id"),
    "X-Naver-Client-Secret": ncreds.get("client_secret"),
}

# 웹서버 초기화
app = Flask(__name__)  # Initialise app

# Config

# csv 키값 받을 딕셔너리 생성
city_dict = {}
sido_dict = {}

# csv에서 키값과 value값을 저장
with open(
    "/home/pi/webapps/mini_project/city.csv",
    mode="r",
    encoding="UTF-8",
) as inp:
    reader = csv.reader(inp)
    city_dict = {rows[0]: rows[1] for rows in reader}

with open(
    "/home/pi/webapps/mini_project/city.csv",
    mode="r",
    encoding="UTF-8",
) as inp:
    reader = csv.reader(inp)
    sido_dict = {rows[0]: rows[2] for rows in reader}

# print(city_dict)
# print(mise_dict)

# 미세먼지 정보 추출 메서드
def getCtprvnRltmMesureDnsty(sido_id):
    # call back URL
    url = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getCtprvnRltmMesureDnsty"

    # url뒤에 들어가는 키값들(형식 json, 도시이름, sido_id = csv에서 가지고온 value값)
    queryString = "?" + urlencode(
        {
            "serviceKey": unquote(myWeatherKey),
            "returnType": "JSON",
            "numOfRows": "100",
            "pageNo": "1",
            "sidoName": sido_id,
            "ver": "1.0",
        }
    )

    # url + querystring을 합친 url안에 정보를 전부 가지고온다.
    response = requests.get(url + queryString)
    # response 정보를 json형식으로 변환한다.
    r_dict = json.loads(response.text)
    # 그안에서 response를 찾아서 넣는다.
    r_response = r_dict.get("response")
    # body를 찾아서 안에 정보를 저장한다.
    r_body = r_response.get("body")
    # items를 찾아서 안에정보를 저장한다.
    r_item = r_body.get("items")

    # 미세먼지 정보가지고는 변수 초기화
    pm10values = []

    # items에있는 모든 미세먼지값을 가지고온다.
    for item in r_item:
        pm10value = item.get("pm10Value")
        if pm10value is not None:
            pm10values.append(pm10value)

    # 1번째 인덱스가 현시간이기때문에 1번째 인덱스의값을 value에넣고 리턴해준다.
    value = pm10values[1]

    return value

# 날씨정보 추출 메서드
def getWeather(city_id):
    # 현재 시간에 따라 numEF가 바뀌기때문에 정의해줬다.
    click = datetime.now()
    if click.hour < 5:
        numEf = 0
    elif click.hour < 11:
        numEf = 1
    elif click.hour < 17:
        numEf = 0
    else:
        numEf = 0

    # 날씨정보의 callback URL이다.
    url = "http://apis.data.go.kr/1360000/VilageFcstMsgService/getLandFcst"
    # 날씨정보의 보내는 값이다.
    queryString = "?" + urlencode(
        {
            "ServiceKey": unquote(myWeatherKey),
            "pageNo": "1",
            "numOfRows": "10",
            "dataType": "JSON",
            "regId": city_id,
        }
    )
    # 위의 미세먼지 메서드랑 동일하다
    response = requests.get(url + queryString)
    r_dict = json.loads(response.text)
    r_response = r_dict.get("response")
    r_body = r_response.get("body")
    r_item = r_body.get("items")

    #items 안에 item 들을 전부 저장한다.
    item_list = r_item.get("item")

    # for문을 돌리면서 찾는다.
    for item in item_list:
        #언제든 검색가능하게 모든조건을 넣어줬다.
        if numEf == 0 or numEf == 1:
            # 온도를 저장한다.
            temp = item.get("ta")
            # 온도가 ""가 아니라면 실행
            if temp != "":
                # 날씨(예- 흐리고 비, 맑음 등), 강수상황(예- 비, 눈, 비/눈, 강수없음)이 숫자로 들어온다, 강수확률을 가지고오면 for문을 나간다.
                weather = item.get("wf")
                waters = item.get("rnYn")
                rainper = item.get("rnSt")
                break
    
    # 0이면 강수없음, 1이면 비, 2면 비/눈, 3이면 눈이다, 4는 소나기다.
    if waters == 0:
        water = "강수없음"
    elif waters == 1:
        water = "비"
    elif waters == 2:
        water = "비/눈"
    elif waters == 3:
        water = "눈"
    elif waters == 4:
        water = "소나기"
    
    #추출한값들을 리턴해준다.
    return temp, weather, water, rainper

# 맛집 링크와 맛집이름 추출 메서드
def Ran_food(food, location, naver_local_url, recommands):
    #while문돌릴 변수선언
    i = 0
    # 음식 3개 랜덤으로 뽑기
    select_food = random.sample(food, 3)
    #3개만 돌리기
    while i < 3:
        #i번째 인덱스의 음식
        foods = select_food[i]
        #외부에서 매개변수로 받아온값들을 합치기
        query = location + " " + foods + " 맛집"
        params = "sort=random" + "&query=" + query + "&display=" + "15"

        #네이버 API를 활용해서 정보 추출
        res = requests.get(naver_local_url + params, headers=nheaders)
        #res의 items에있는것들을 전부 가지고온다.
        result_list = res.json().get("items")
        for result in result_list:
            #link가 있으면 실행 5개를 돌려서 없으면 안나온다.
            if result["link"]:
                recommands.append(result)
                break

        i += 1
    return select_food, recommands

#음식 랜덤 추천 메서드
def choice_food(temp, water, val_per, city_name):
    #음식 3개 고를수있는 리스트
    select_food = []
    #링크및 정보들 저장 리스트
    recommands = []
    #네이버 API url이다.
    naver_local_url = "https://openapi.naver.com/v1/search/local.json?"
    #도시이름 가져오기
    location = city_name

    #비나눈이나소나기면 아래를추천
    if water == "비" or water == "비/눈" or water == "소나기":
        food = [
            "김치찌개",
            "부대찌개",
            "불고기전골",
            "순두부찌개",
            "감자탕",
            "비빔밥",
            "어묵탕",
            "우동",
            "만두국",
            "닭볶음탕",
        ]
        select_food, recommands = Ran_food(food, location, naver_local_url, recommands)
        return select_food, recommands

    #미세먼지가 나쁨이나 매우나쁨이면 아래음식을 추천
    elif val_per == "나쁨" or val_per == "매우나쁨":
        food = [
            "녹두전",
            "미역국",
            "콩나물해장국",
            "삼겹살",
            "오리주물럭",
            "고등어구이",
            "북어국",
            "도라지비빔밥",
        ]
        select_food, recommands = Ran_food(food, location, naver_local_url, recommands)
        return select_food, recommands

    #온도가 25도이상이면 아래음식을 추천
    elif temp >= "25":
        food = [
            "냉면",
            "막국수",
            "냉채족발",
            "삼계탕",
            "추어탕",
            "백숙",
            "비빔밥",
            "메밀국수",
        ]
        select_food, recommands = Ran_food(food, location, naver_local_url, recommands)
        return select_food, recommands

    #거의 기본값이다.
    elif temp < "25":
        food = [
            "자장면",
            "칼국수",
            "떡볶이",
            "만두전골",
            "비빔국수",
            "텐동",
            "물갈비",
            "오리주물럭",
            "순대국밥",
            "삼겹살",
            "파스타",
            "불고기",
            "초밥",
            "곤드레밥",
        ]
        select_food, recommands = Ran_food(food, location, naver_local_url, recommands)
        return select_food, recommands

#정보를 감춰서 가지고온다
@app.route("/", methods=["GET", "POST"])
def index():
    #웹페이지의 시간정보를 표시해주기위해 사용했다
    base_times = datetime.now()
    base_time = str(base_times.year)
    base_time += "년" + str(base_times.month)
    base_time += "월" + str(base_times.day)
    base_time += "일" + str(base_times.hour)
    base_time += "시" + str(base_times.minute) + "분"

    #post에 요청이 들어왔을때 실행
    if request.method == "POST":
        #form의 name값을 cityname에 넣는다
        city_name = request.form["name"]
        #cityname을 citydict를 통해 value값을 가지고온다
        city_id = city_dict.get(city_name)
        #cityname을 sidodict를 통해 value값을 가지고온다
        sido_id = sido_dict.get(city_name)

        #city_id가 없으면 그냥 리턴
        if city_id == None:
            return render_template("index.html")
        
        #미세먼지 메서드실행하여 정보가지고옴
        value = getCtprvnRltmMesureDnsty(sido_id)
        #날씨 메서드 실행하여 정보가지고옴
        temp, weather, water, rainper = getWeather(city_id)

        #value가 str이기때문에 int로 형변환후 값비교하여 좋음, 보통, 나쁨, 매우나쁨으로 나눈다
        #그리고 상황에맞게 LED를 ON한다.
        if int(value) <= 30:
            val_per = "좋음"
            GPIO.output(37, GPIO.HIGH)
            GPIO.output(35, GPIO.LOW)
            GPIO.output(33, GPIO.LOW)
            GPIO.output(31, GPIO.LOW)
        elif int(value) <= 80:
            val_per = "보통"
            GPIO.output(37, GPIO.LOW)
            GPIO.output(35, GPIO.HIGH)
            GPIO.output(33, GPIO.LOW)
            GPIO.output(31, GPIO.LOW)
        elif int(value) <= 150:
            val_per = "나쁨"
            GPIO.output(37, GPIO.LOW)
            GPIO.output(35, GPIO.LOW)
            GPIO.output(33, GPIO.HIGH)
            GPIO.output(31, GPIO.LOW)
        else:
            val_per = "매우나쁨"
            GPIO.output(37, GPIO.LOW)
            GPIO.output(35, GPIO.LOW)
            GPIO.output(33, GPIO.LOW)
            GPIO.output(31, GPIO.HIGH)

        # 음식정보를 가지고오는 메서드 실행
        select_food, recommands = choice_food(temp, water, val_per, city_name)

        #기상상황에 따라 LED가 ON될수있게 만들었다.
        if water == "강수없음":
            GPIO.output(40, GPIO.LOW)
            GPIO.output(38, GPIO.LOW)
            GPIO.output(36, GPIO.LOW)
            if int(temp) > 25:
                GPIO.output(40, GPIO.HIGH)
        elif water == "비":
            GPIO.output(40, GPIO.LOW)
            GPIO.output(38, GPIO.LOW)
            GPIO.output(36, GPIO.HIGH)
        elif water == "비/눈":
            GPIO.output(40, GPIO.LOW)
            GPIO.output(36, GPIO.HIGH)
            GPIO.output(38, GPIO.HIGH)
        elif water == "눈":
            GPIO.output(40, GPIO.LOW)
            GPIO.output(36, GPIO.LOW)
            GPIO.output(38, GPIO.HIGH)
        elif water == "소나기":
            GPIO.output(40, GPIO.LOW)
            GPIO.output(36, GPIO.LOW)
            GPIO.output(38, GPIO.LOW)
            #소나기면 무한으로 깜빡이게 만들었다.
            while True:
                GPIO.output(36, GPIO.HIGH)
                time.sleep(0.5)
                GPIO.output(36, GPIO.LOW)
                time.sleep(0.5)

        #웹페이지에 보여주는 값을들 리턴해줬다.
        return render_template(
            "index.html",
            base_time=base_time,
            temp=temp,
            weather=weather,
            water=water,
            rainper=rainper,
            city_name=city_name,
            value=value,
            val_per=val_per,
            select_food=select_food,
            recommands=recommands,
        )
    #post에 값이 안들어왔으면 그냥 현제시간만 리턴해준다
    else:
        return render_template(
            "index.html",
            base_time=base_time,
        )

#웹 실행
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)

#핀 클리어해주기
GPIO.cleanup()

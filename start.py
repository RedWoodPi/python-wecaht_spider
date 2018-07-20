#encoding:utf-8
from selenium import webdriver
import bs4, requests
import time
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import oss2
import pymysql as db
import random

base ='https://mp.weixin.qq.com'
#accountList = [ '人民日报', '新华社', '央视新闻', '环球时报']
query = 'http://weixin.sogou.com/weixin?type=1&s_from=input&query='

# 获取公众号链接
def getAccountURL(searchURL):
    res = requests.get(searchURL)
    res.raise_for_status()
    soup = bs4.BeautifulSoup(res.text, "lxml")
    # 选择第一个链接
    account = soup.select('a[uigs="account_name_0"]')
    return account[0]['href']

# 获取首篇文章的链接，如果有验证码返回None
def getArticleURL(accountURL):
    time.sleep(random.randint(3,6))
    browser = webdriver.PhantomJS('/usr/local/Cellar/phantomjs/2.1.1/bin/phantomjs')
    # 进入公众号
    try:
        browser.get(accountURL)
    except:
        browser.quit()
        getArticleURL(accountURL)
    # 获取网页信息
    html = browser.page_source
    accountSoup = bs4.BeautifulSoup(html, "lxml")
    time.sleep(1)
    contents = accountSoup.find_all(hrefs=True)
    arr = []
    for content in contents:
        arr.append(base + content['hrefs'])

    try:
        partitialLink = contents[1]['hrefs']
    except IndexError:
        print('CAPTCHA!')
        time.sleep(7253)
        getArticleURL(accountURL)

    arr = list(set(arr))
    browser.quit()
    return arr



#图片上传oss
def downloadImg(imgs, oss_key, oss_secret, bucket, endpoint):
    auth = oss2.Auth(oss_key, oss_secret)
    bucket = oss2.Bucket(auth, "http://"+endpoint, bucket)
    for img in imgs:
        status = 0
        index = 0
        if(img.get('data-src')):
            src = img["data-src"]
            name = src.replace("https://mmbiz.qpic.cn/", '')
            name = name.replace("?wx_fmt=", '.')
            while True:
                try:
                    resp = requests.get(src)
                    break
                except:
                    index = index + 1
                    if(index == 3):
                        status = 1
                        break
                    continue

            if (status):
                continue
            #content = resp.content
            bucket.put_object(name, resp)
        else:
            continue

#内容，作者，标题入库
def saveContens(title, author, content, dbconfig, bucket, endpoint):
    content = content.replace("https://mmbiz.qpic.cn/", "https://"+bucket+"."+endpoint+'/')
    content = content.replace("?wx_fmt=", '.')
    content = content.replace("data-src", 'src')
    content = content.replace("'", "\"")
    conn = db.connect(**dbconfig)
    cur = conn.cursor()
    sql_insert = ("insert into contents (author, content, title) values ('%s', '%s', '%s')" % (author, content, title))
    try:
        cur.execute(sql_insert)
        conn.commit()
    except:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

#判断是否已下载
def downloaded(title, author,dbconfig):
    conn = db.connect(**dbconfig)
    cur = conn.cursor()
    sql = "select * from contents where title='%s' and author='%s'" % (title, author)
    result = cur.execute(sql)
    cur.close()
    conn.close()
    if(result):
        return 1
    else:
        return 0

#更改服务器状态
def changeStatus(ip, status, dbconfig):
    conn = db.connect(**dbconfig)
    cur = conn.cursor()
    sql = "update server_list set working = '%d' where ip = '%s'" % (status, ip)
    try:
        cur.execute(sql)
        conn.commit()
    except:
        conn.rollback()
        changeStatus(ip,status, dbconfig)
        raise
    finally:
        cur.close()
        conn.close()

#爬虫主逻辑
def spider(accountList, ip, dbconfig, oss_key, oss_secret, bucket, endpoint):
    #重载编码
    #reload(sys)
    #sys.setdefaultencoding('utf-8')
    #抑制警告
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    start = time.time()
    #更改服务器状态
    changeStatus(ip, 1, dbconfig)
    for account in accountList:
        time.sleep(random.randint(6,12))
        print(account)
        searchURL = query + account
        accountURL = getAccountURL(searchURL)
        time.sleep(random.randint(9,18))
        articleURL = getArticleURL(accountURL)

        for article in articleURL:
            if article != None:
                time.sleep(random.randint(6,18))
                status = 0
                while True:
                    try:
                        res = requests.get(article, verify=False)
                        break
                    except:
                        status = 1
                        break
                if(status):
                    continue

                detailPage = bs4.BeautifulSoup(res.text, "lxml")
                title = detailPage.select('.rich_media_title')
                if(not title):
                    continue
                title = title[0].string.strip()
                imgs = detailPage.find_all('img')
                if(downloaded(title, account, dbconfig)):
                    continue
                else:
                    print("get article")
                    downloadImg(imgs, oss_key, oss_secret, bucket, endpoint)
                    saveContens(title, account, res.text, dbconfig, bucket, endpoint)
            else:
                continue
    changeStatus(ip, 0, dbconfig)
    end = time.time()
    spend = end - start
    print(spend)

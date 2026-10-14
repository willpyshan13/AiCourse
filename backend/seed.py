"""Generate demo data for the practice classroom application."""
import httpx
import os
import json
import sys
import time

BASE = "http://localhost:8000/api"
token = None


def api(method, path, **kwargs):
    url = f"{BASE}{path}"
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with httpx.Client() as client:
        resp = client.request(method, url, headers=headers, **kwargs)
        if resp.status_code >= 400:
            print(f"  [!] {method} {path} -> {resp.status_code}: {resp.text[:120]}")
            return None
        return resp.json()


def login():
    global token
    res = api("POST", "/auth/login", json={
        "name": "王老师",
        "password": os.environ["SEED_TEACHER_PASSWORD"],
    })
    token = res["access_token"]
    print(f"[OK] 登录成功 - {res['name']}")
    return res


def create_class(name, grade, desc=""):
    res = api("POST", "/classes", json={"name": name, "grade": grade, "description": desc})
    if res:
        print(f"[OK] 创建班级: {name}")
    return res


def create_team(class_id, name):
    res = api("POST", f"/classes/{class_id}/teams", json={"name": name})
    if res:
        print(f"[OK]   小组: {name}")
    return res


def add_student(class_id, name, student_no, role, birth_date="2012-01-01"):
    res = api("POST", f"/classes/{class_id}/students", json={
        "name": name,
        "student_no": student_no,
        "grade": "2024级",
        "birth_date": birth_date,
        "role": role,
    })
    return res


def assign_student(student_id, team_id):
    api("PUT", f"/students/{student_id}", json={"team_id": team_id})


def create_practice(team_id, title, content, member_works=None):
    if member_works is None:
        member_works = []
    # Using POST with multipart form data
    url = f"{BASE}/practices/team/{team_id}"
    headers = {"Authorization": f"Bearer {token}"}
    data = {"title": title, "content": content, "member_works": json.dumps(member_works)}
    with httpx.Client() as client:
        resp = client.post(url, headers=headers, data=data)
        if resp.status_code >= 400:
            print(f"  [!] 创建实践失败: {resp.text[:120]}")
            return None
        res = resp.json()
        print(f"[OK]   实践: {title[:20]}...")
        return res


def generate_qrcode(team_id):
    api("GET", f"/teams/{team_id}/qrcode")


CLASS_DATA = [
    {
        "name": "2024级1班",
        "grade": "2024级",
        "desc": "综合实践特色班级，注重动手能力培养",
        "teams": [
            {
                "name": "探索者联盟",
                "students": [
                    ("张明", "2024001", "组长/动手实践", "2011-09-15"),
                    ("李华", "2024002", "记录数据", "2012-02-20"),
                    ("王小花", "2024003", "分析数据", "2012-05-10"),
                    ("刘洋", "2024004", "查阅资料", "2011-11-30"),
                    ("陈晓", "2024005", "动手实践", "2012-03-25"),
                ],
                "practices": [
                    {
                        "title": "校园植物多样性调查",
                        "content": "对校园内的植物种类进行调查和分类，记录不同区域的植物分布情况。共发现乔木12种、灌木8种、草本植物15种。我们小组负责东侧花园区域，记录了5种乔木、3种灌木和7种草本植物。通过查阅资料，我们了解了每种植物的名称、科属和生长习性。张明负责测量树木胸径和高度，李华记录数据到表格，王小花用手机拍摄植物照片用于后续分析。",
                        "works": [
                            {"name": "张明", "desc": "负责测量树木胸径和高度，使用卷尺和测量杆完成数据采集"},
                            {"name": "李华", "desc": "实时记录测量数据，整理成电子表格，确保数据准确无误"},
                            {"name": "王小花", "desc": "拍摄各植物照片50余张，制作植物图鉴PPT"},
                            {"name": "刘洋", "desc": "查阅植物分类学资料，鉴定植物种类，撰写调查报告"},
                            {"name": "陈晓", "desc": "协助测量，维护设备，采集植物标本"},
                        ],
                    },
                    {
                        "title": "校园水质检测与分析",
                        "content": "对校园内人工湖和周边水体的水质进行检测。使用pH试纸、TDS笔等工具检测水样，记录各项指标数据。取水样6份，检测了pH值、浊度、溶解氧、氨氮含量等指标。数据分析发现，人工湖水质总体良好，但靠近教学楼一侧的水样氨氮含量略高，可能与地面径流有关。",
                        "works": [
                            {"name": "张明", "desc": "负责采集水样，使用专业工具检测各项水质指标"},
                            {"name": "李华", "desc": "记录每次检测数据，计算平均值，绘制数据对比图表"},
                            {"name": "王小花", "desc": "分析水质数据变化趋势，撰写分析报告"},
                            {"name": "刘洋", "desc": "查阅国家水质标准，对比检测结果是否达标"},
                            {"name": "陈晓", "desc": "准备实验器材，协助检测过程"},
                        ],
                    },
                ],
            },
            {
                "name": "绿色卫士",
                "students": [
                    ("赵强", "2024006", "组长/动手实践", "2012-01-18"),
                    ("孙丽", "2024007", "记录数据", "2011-12-05"),
                    ("周杰", "2024008", "分析数据", "2012-04-12"),
                    ("吴桐", "2024009", "查阅资料", "2012-07-22"),
                    ("郑欣", "2024010", "汇报展示", "2011-10-08"),
                ],
                "practices": [
                    {
                        "title": "校园垃圾分类情况调研",
                        "content": "对全校各区域的垃圾分类情况进行为期一周的观察和记录。重点调查了教学楼、食堂、操场、宿舍区的垃圾桶设置和分类准确率。共统计垃圾桶数量86个，观察分类投放行为300余次。结果显示，教学楼区域分类准确率最高（78%），食堂区域因厨余垃圾混投严重，准确率仅45%。我们向学校提交了改进建议报告。",
                        "works": [
                            {"name": "赵强", "desc": "设计调研方案，分配各区域观察任务，汇总调研数据"},
                            {"name": "孙丽", "desc": "每日记录各区域垃圾分类情况，拍照存档"},
                            {"name": "周杰", "desc": "统计分析数据，计算分类准确率，制作图表"},
                            {"name": "吴桐", "desc": "查阅其他学校垃圾分类成功案例，整理最佳实践"},
                            {"name": "郑欣", "desc": "制作调研报告PPT，在班会上进行汇报展示"},
                        ],
                    },
                    {
                        "title": "环保手工艺品制作",
                        "content": "利用废旧物品制作环保手工艺品。收集了废纸箱、塑料瓶、旧衣物等材料，经过清洗处理后，制作了收纳盒、花瓶、笔筒等实用物品。共完成作品12件，在班级环保展览中展出。本小组的作品'废纸变花瓶'获得最佳创意奖。并通过义卖筹集了环保基金236元。",
                        "works": [
                            {"name": "赵强", "desc": "负责整体设计和工艺指导，制作了纸箱收纳柜"},
                            {"name": "孙丽", "desc": "记录制作过程，拍摄步骤照片，编写制作手册"},
                            {"name": "周杰", "desc": "计算材料成本和环保效益，评估减碳量"},
                            {"name": "吴桐", "desc": "查阅环保手工艺资料，收集作品创意灵感"},
                            {"name": "郑欣", "desc": "负责作品解说词撰写和展览现场讲解"},
                        ],
                    },
                    {
                        "title": "校园节水方案设计",
                        "content": "调查校园用水情况，设计节水方案。查看了学校每个月的用水记录，发现用水量在夏季明显偏高。我们检查了教学楼、宿舍、食堂的水龙头和冲水设施，发现有部分水龙头存在滴漏现象。设计了包括更换节水龙头、雨水收集利用、节水宣传教育在内的综合节水方案，预计可为学校节约30%的用水量。",
                        "works": [
                            {"name": "赵强", "desc": "调查校园用水设施，检测水管漏水情况"},
                            {"name": "孙丽", "desc": "记录月度用水数据，分析用水量变化趋势"},
                            {"name": "周杰", "desc": "计算节水方案的投入产出比，编写可行性分析"},
                            {"name": "吴桐", "desc": "查阅节水技术和设备资料，对比各种方案优劣"},
                            {"name": "郑欣", "desc": "制作节水宣传海报和倡议书，在全校推广"},
                        ],
                    },
                ],
            },
        ],
    },
    {
        "name": "2024级3班",
        "grade": "2024级",
        "desc": "科创实践特色班",
        "teams": [
            {
                "name": "未来科学家",
                "students": [
                    ("黄磊", "2024011", "组长/实验操作", "2012-03-15"),
                    ("林雪", "2024012", "数据记录", "2012-06-28"),
                    ("何明", "2024013", "数据分析", "2011-08-19"),
                    ("宋佳", "2024014", "文献查阅", "2012-01-05"),
                ],
                "practices": [
                    {
                        "title": "太阳能小车制作",
                        "content": "利用太阳能电池板和电机组装太阳能小车。选择了轻量化车体材料，设计了三轮结构以提高稳定性。测试了不同光照条件下的车速和续航。在晴好天气下，小车最高时速达到0.8m/s，阴天时降至0.3m/s。通过加装聚光透镜，提高了20%的能量转换效率。",
                        "works": [
                            {"name": "黄磊", "desc": "负责小车整体设计和电路连接"},
                            {"name": "林雪", "desc": "记录不同光照条件下的测试数据"},
                            {"name": "何明", "desc": "分析数据，计算能量转换效率"},
                            {"name": "宋佳", "desc": "查阅太阳能应用资料，撰写项目报告"},
                        ],
                    },
                    {
                        "title": "简易净水器设计与实验",
                        "content": "使用活性炭、细沙、砾石、棉花等材料制作简易净水器。设计了3种不同过滤层排列方案进行对比实验。测试了进水浊度约为200NTU的模拟污水。经过3层过滤后，方案A（活性炭在顶层）出水浊度降至15NTU，方案B（活性炭在中层）降至22NTU，方案C（活性炭在底层）降至35NTU。最佳方案过滤效果接近市售家用净水器初级过滤水平。",
                        "works": [
                            {"name": "黄磊", "desc": "设计净水器方案，动手组装过滤装置"},
                            {"name": "林雪", "desc": "记录每次实验的水质数据，拍照记录"},
                            {"name": "何明", "desc": "对比分析三种方案的过滤效果差异"},
                            {"name": "宋佳", "desc": "查阅水质净化原理资料，总结实验结论"},
                        ],
                    },
                ],
            },
            {
                "name": "数据侦探",
                "students": [
                    ("马超", "2024015", "组长/数据采集", "2012-02-14"),
                    ("胡婷", "2024016", "数据整理", "2011-07-30"),
                    ("万磊", "2024017", "数据分析", "2012-05-18"),
                    ("叶诗", "2024018", "报告撰写", "2012-08-03"),
                    ("钱进", "2024019", "技术支持", "2011-12-25"),
                ],
                "practices": [
                    {
                        "title": "空气污染物浓度监测",
                        "content": "使用PM2.5检测仪和空气质量传感器，连续一周每天分早中晚三次监测校园空气质量。记录温度、湿度、PM2.5、PM10、CO2浓度等数据。监测发现，校园空气质量整体良好，PM2.5日均值在25-45μg/m³之间。下午放学时段因家长接送车辆增多，校门口PM2.5浓度会出现短暂升高。",
                        "works": [
                            {"name": "马超", "desc": "操作检测设备，定时到各监测点采集数据"},
                            {"name": "胡婷", "desc": "整理每日监测数据，制作数据表格"},
                            {"name": "万磊", "desc": "分析数据变化规律，绘制趋势图"},
                            {"name": "叶诗", "desc": "撰写空气质量监测报告，向学校提出建议"},
                            {"name": "钱进", "desc": "维护检测设备，搭建数据自动记录系统"},
                        ],
                    },
                ],
            },
        ],
    },
    {
        "name": "2023级5班",
        "grade": "2023级",
        "desc": "传统文化实践方向",
        "teams": [
            {
                "name": "文化传承者",
                "students": [
                    ("杨帆", "2023020", "组长/统筹协调", "2010-11-10"),
                    ("罗琳", "2023021", "记录整理", "2011-03-22"),
                    ("谢涛", "2023022", "摄影摄像", "2011-01-15"),
                    ("唐雅", "2023023", "资料搜集", "2010-09-28"),
                    ("韩冰", "2023024", "访谈采访", "2011-05-06"),
                ],
                "practices": [
                    {
                        "title": "社区传统节日文化调研",
                        "content": "走访社区老年人，了解端午、中秋、春节等传统节日的习俗变迁。采访了12位60岁以上的老人，记录了他们对传统节日的回忆和感受。发现年轻一代对传统节日习俗的了解正在减少，但大多数人表示愿意参与传统节日活动。建议学校开展传统节日体验活动，让更多学生了解传统文化。",
                        "works": [
                            {"name": "杨帆", "desc": "制定调研计划，安排采访日程，协调团队分工"},
                            {"name": "罗琳", "desc": "详细记录每次访谈内容，整理访谈纪要"},
                            {"name": "谢涛", "desc": "拍摄访谈视频和照片，记录传统习俗实景"},
                            {"name": "唐雅", "desc": "搜集传统节日的历史资料，对比古今习俗变化"},
                            {"name": "韩冰", "desc": "负责与社区老人沟通，完成采访任务"},
                        ],
                    },
                    {
                        "title": "地方戏曲文化探寻",
                        "content": "调查本地传统戏曲的种类和发展现状。通过走访文化馆、采访老艺人、查阅文史资料，了解到本地有2种地方戏曲被列为非物质文化遗产。观看了3场传统戏曲演出，记录了演员的表演特点和观众的反馈。制作了'走进地方戏曲'宣传手册，在学校文化节上发放。",
                        "works": [
                            {"name": "杨帆", "desc": "联系文化馆，组织团队参观和采访活动"},
                            {"name": "罗琳", "desc": "记录演出细节和采访内容，整理成文字资料"},
                            {"name": "谢涛", "desc": "拍摄演出视频片段和后台花絮"},
                            {"name": "唐雅", "desc": "查阅地方戏曲史料，梳理发展脉络"},
                            {"name": "韩冰", "desc": "采访老艺人和观众，收集第一手资料"},
                        ],
                    },
                ],
            },
            {
                "name": "匠心手作坊",
                "students": [
                    ("曹磊", "2023025", "组长/手工制作", "2010-12-03"),
                    ("方晴", "2023026", "设计绘图", "2011-06-17"),
                    ("彭浩", "2023027", "材料研究", "2011-02-28"),
                ],
                "practices": [
                    {
                        "title": "传统剪纸艺术实践",
                        "content": "学习中国传统剪纸艺术，从简单的对称剪纸开始，逐步掌握复杂图案的剪制技巧。学习了团花、窗花、生肖等主题的剪法。共完成剪纸作品15幅，包括12生肖系列和传统吉祥图案。在学校艺术节上举办了小型剪纸展览，并现场教授其他同学剪纸技巧。通过学习了解到剪纸已被列入联合国教科文组织非物质文化遗产。",
                        "works": [
                            {"name": "曹磊", "desc": "负责剪纸制作，完成主要作品"},
                            {"name": "方晴", "desc": "设计剪纸图案，绘制图样模板"},
                            {"name": "彭浩", "desc": "研究不同纸张材质对剪纸效果的影响"},
                        ],
                    },
                ],
            },
        ],
    },
]


def main():
    print("=" * 50)
    print("  智慧综合实践课堂 - 种子数据生成")
    print("=" * 50)

    # Login
    login()

    student_id_counter = 0

    for cls_data in CLASS_DATA:
        cls = create_class(cls_data["name"], cls_data["grade"], cls_data.get("desc", ""))
        if not cls:
            print(f"  [!] 跳过班级: {cls_data['name']}")
            continue
        class_id = cls["id"]

        # Need to get the actual students since API assigns IDs
        all_students = []

        for team_data in cls_data["teams"]:
            team = create_team(class_id, team_data["name"])
            if not team:
                continue
            team_id = team["id"]

            # Add students
            team_students = []
            for s_name, s_no, s_role, s_birth in team_data["students"]:
                s = add_student(class_id, s_name, s_no, s_role, s_birth)
                if s:
                    team_students.append(s)
                    all_students.append(s)

            # Assign to team
            for s in team_students:
                assign_student(s["id"], team_id)

            print(f"[OK]   成员{len(team_students)}人已分配到{team_data['name']}")

            # Create practices with member works
            for prac in team_data.get("practices", []):
                # Map student names to their IDs in this team
                name_to_id = {s["name"]: s["id"] for s in team_students}
                works = []
                for w in prac.get("works", []):
                    sid = name_to_id.get(w["name"])
                    if sid:
                        works.append({"student_id": sid, "work_description": w["desc"]})

                create_practice(team_id, prac["title"], prac["content"], works)

            # Generate QR code
            generate_qrcode(team_id)
            print(f"[OK]   二维码已生成")

        print()

    # Summary
    print("=" * 50)
    print("  数据生成完成!")
    print(f"  班级: {len(CLASS_DATA)}")
    total_teams = sum(len(c["teams"]) for c in CLASS_DATA)
    print(f"  小组: {total_teams}")
    total_students = sum(len(t["students"]) for c in CLASS_DATA for t in c["teams"])
    print(f"  学生: {total_students}")
    total_practices = sum(len(t.get("practices", [])) for c in CLASS_DATA for t in c["teams"])
    print(f"  实践记录: {total_practices}")
    print("=" * 50)


if __name__ == "__main__":
    main()

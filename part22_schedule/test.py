import time
import threading
import schedule


class TaskScheduler:
    """
    定时任务调度类，支持添加、删除和列出任务，以及语音提醒。
    """

    def __init__(self):
        self.tasks = []  # 存储任务的列表
        self.handle_command('添加 every().day.at("11:57") 提醒，请注意遵守劳动纪律')
        self.handle_command('添加 every().day.at("18:57") 提醒，请注意遵守劳动纪律')

        self.handle_command('添加 every().day.at("17:30") 提醒，请准备一天工作日报')
        self.handle_command('添加 every().monday.at("15:30") 提醒，跟进信用网、个人公共信用报告、信易贷、专家库进展')
        self.handle_command('添加 every().wednesday.at("15:30") 提醒，跟进信用网、个人公共信用报告、信易贷、专家库进展')

        self.handle_command('添加 every().monday.at("09:20") 提醒，请准时参加周例会')

        self.handle_command('添加 every().thursday.at("09:30") 提醒，报送本周重点工作和业务数据')
        self.handle_command('添加 every().thursday.at("10:30") 提醒，报送本周重点工作和业务数据')

        self.handle_command('添加 every().hour.at("30:00") 提醒，久坐伤身，请多运动')
        self.handle_command('添加 every().hour.at("00:00") 提醒，久坐伤身，请多运动')
        self.handle_command('添加 every().minute 测试提醒')
        self.scheduler_thread = threading.Thread(target=self._task_scheduler, daemon=True)
        self.scheduler_thread.start()


    def add_task(self, time_str, message, repeat=True, custom_function=None, days=None, *args, **kwargs):
        """
        添加定时任务
        :param time_str: 任务时间 (支持格式: HH:MM, HH:MM:SS 或定时器格式如 every().day.at())
        :param message: 提醒内容
        :param repeat: 是否重复执行 (默认: False)
        :param custom_function: 自定义任务函数，可选
        :param days: 指定执行的天，例如 ['monday', 'tuesday']
        :param args: 自定义函数的参数
        :param kwargs: 自定义函数的关键字参数
        """
        def task():
            print(f"提醒：{message}")
            if custom_function:
                custom_function(*args, **kwargs)
            if not repeat:
                self.tasks = [t for t in self.tasks if t['time'] != time_str or t['message'] != message]

        # 根据时间字符串和指定天数添加任务
        if days:
            for day in days:
                eval(f"schedule.every().{day}.at(time_str).do(task)")
        elif time_str.startswith("every"):
            eval(f"schedule.{time_str}.do(task)")  # 动态调用 schedule 的方法
        else:
            schedule.every().day.at(time_str).do(task)

        self.tasks.append({"time": time_str, "message": message, "repeat": repeat, "days": days})
        print(f"任务已添加：{time_str} - {message} {'(重复)' if repeat else ''} {'执行于: ' + ', '.join(days) if days else ''}")

    def list_tasks(self):
        """列出所有定时任务"""
        if not self.tasks:
            print("当前没有任何定时任务。")
        else:
            print("当前定时任务：")
            for i, task in enumerate(self.tasks, start=1):
                repeat = "是" if task["repeat"] else "否"
                days = task.get("days", [])
                day_str = f", 执行于: {', '.join(days)}" if days else ""
                print(f"{i}. 时间: {task['time']}, 内容: {task['message']}, 是否重复: {repeat}{day_str}")

    def show_tasks(self):
        """列出所有定时任务"""
        result = ''
        if not self.tasks:
            print("当前没有任何定时任务。")
            result = "当前没有任何定时任务。"
        else:
            result = "当前定时任务："
            print("当前定时任务：")
            for i, task in enumerate(self.tasks, start=1):
                repeat = "是" if task["repeat"] else "否"
                days = task.get("days", [])
                day_str = f", 执行于: {', '.join(days)}" if days else ""
                atask = f"{i}. 时间: {task['time']}, 内容: {task['message']}, 是否重复: {repeat}{day_str}"
                result += atask + "\n"
                print(atask)
        return result

    def delete_task(self, index):
        """删除指定任务"""
        try:
            task = self.tasks.pop(index - 1)
            print(f"已删除任务：时间: {task['time']}, 内容: {task['message']}")
        except IndexError:
            print("无效的任务编号！")

    def _task_scheduler(self):
        """定时任务调度线程"""
        while True:
            schedule.run_pending()
            time.sleep(1)

    def handle_command(self, command):
        """处理语音助手命令"""
        if command.startswith("添加"):
            try:
                parts = command.split()
                time_str = parts[1]
                message = " ".join(parts[2:])
                self.add_task(time_str, message)
            except Exception as e:
                print(f"添加任务失败：{e}")
        elif command == "列出任务":
            self.list_tasks()
        elif command.startswith("删除"):
            try:
                index = int(command.split()[1])
                self.delete_task(index)
            except Exception as e:
                print(f"删除任务失败：{e}")
        elif command == "退出":
            print("语音助手已退出。")
            return False
        else:
            print("无效命令，请重试。")
        return True


# 集成到语音助手
if __name__ == "__main__":
    task_scheduler = TaskScheduler()
    print("语音助手启动，欢迎使用！")

    task_scheduler.handle_command('添加 every().day.at("23:10").minutes 提醒尿尿')
    while True:
        print("\n命令列表：")
        print("1. 添加任务 (格式: 添加 09:00 提醒吃药 或 添加 every(2).minutes 提醒喝水 或 添加 08:00 提醒开会 monday tuesday)")
        print("2. 列出任务")
        print("3. 删除任务 (格式: 删除 1)")
        print("4. 退出")
        user_command = input("请输入命令：").strip()
        task_scheduler.handle_command(user_command)

